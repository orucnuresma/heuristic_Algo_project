import random
from genetic_operators import initialize_chromosome, apply_crossover, apply_mutation
from decode import decode_chromosome, calculate_penalty

# --- HIZ OPTİMİZASYONU İÇİN GLOBAL ÖNBELLEK ---
GLOBAL_FOOD_METRICS = {}

def _build_metrics_cache(foods_df):
    global GLOBAL_FOOD_METRICS
    if GLOBAL_FOOD_METRICS: return
    for _, r in foods_df.iterrows():
        f_id = int(r["id"])
        GLOBAL_FOOD_METRICS[f_id] = {
            "cost": float(r["cost"]),
            "co2": float(r["co2"]),
            "preference": float(r["preference"])
        }

LAMBDA = 1.0
FORBIDDEN_PENALTY = 100.0

def evaluate(individual, foods_df, nutrients_df, dri_df, user_info, diversity_enabled=False,
             user_foods_df=None):
    _build_metrics_cache(foods_df)

    selected_foods = decode_chromosome(
        individual, foods_df, nutrients_df, dri_df, user_info, user_foods_df
    )

    user_prefs = user_info.get("preferences", {})

    total_cost = 0.0
    total_co2 = 0.0
    total_preference = 0.0
    forbidden_count = 0

    for f_id in selected_foods:
        metrics = GLOBAL_FOOD_METRICS.get(f_id, {"cost": 0.0, "co2": 0.0, "preference": 0.0})
        total_cost += metrics["cost"]
        total_co2 += metrics["co2"]

        if user_prefs:
            pref_val = user_prefs.get(f_id, metrics["preference"])
            if pref_val is None or pref_val != pref_val:  # None veya NaN kontrolu
                pref_val = 0.0
            elif pref_val == -1:
                forbidden_count += 1
                pref_val = 0.0
            total_preference += pref_val
        else:
            total_preference += metrics["preference"]

    R = calculate_penalty(
        selected_foods, foods_df, nutrients_df, dri_df, user_info, user_foods_df, diversity_on=diversity_enabled
    )
    R += forbidden_count * FORBIDDEN_PENALTY

    obj_preference = -total_preference + LAMBDA * R
    obj_cost = total_cost + LAMBDA * R
    obj_co2 = total_co2 + LAMBDA * R

    return [obj_preference, obj_cost, obj_co2]


# ============================================================
# ORTAK YARDIMCI FONKSIYON
# ============================================================

def _dominates(obj_a, obj_b):
    at_least_one_better = False
    for a_val, b_val in zip(obj_a, obj_b):
        if a_val > b_val:
            return False
        if a_val < b_val:
            at_least_one_better = True
    return at_least_one_better


# ============================================================
# NSGA-II YARDIMCI FONKSIYONLARI
# ============================================================

def fast_non_dominated_sort(fitness_values):
    pop_size = len(fitness_values)
    domination_count = [0] * pop_size
    dominated_set = [[] for _ in range(pop_size)]
    rank = [0] * pop_size
    fronts = [[]]

    for p in range(pop_size):
        for q in range(p + 1, pop_size):
            p_dom_q = _dominates(fitness_values[p], fitness_values[q])
            q_dom_p = _dominates(fitness_values[q], fitness_values[p])
            if p_dom_q:
                dominated_set[p].append(q)
                domination_count[q] += 1
            elif q_dom_p:
                dominated_set[q].append(p)
                domination_count[p] += 1

        if domination_count[p] == 0:
            rank[p] = 0
            fronts[0].append(p)

    # domination_count[p] for p > 0 might not be finalized yet
    # Re-check: actually the loop above only processes p < q pairs.
    # We need to finalize counts for all individuals.
    # The fronts[0] check above only catches p where ALL q > p don't dominate p,
    # but misses q < p that might dominate p. Let me fix this properly.

    # Actually let me just revert to the correct O(N²/2) approach:
    domination_count = [0] * pop_size
    dominated_set = [[] for _ in range(pop_size)]
    fronts = [[]]

    for p in range(pop_size):
        for q in range(p + 1, pop_size):
            p_dom_q = _dominates(fitness_values[p], fitness_values[q])
            q_dom_p = _dominates(fitness_values[q], fitness_values[p])
            if p_dom_q:
                dominated_set[p].append(q)
                domination_count[q] += 1
            elif q_dom_p:
                dominated_set[q].append(p)
                domination_count[p] += 1

    for p in range(pop_size):
        if domination_count[p] == 0:
            rank[p] = 0
            fronts[0].append(p)

    i = 0
    while fronts[i]:
        next_front = []
        for p in fronts[i]:
            for q in dominated_set[p]:
                domination_count[q] -= 1
                if domination_count[q] == 0:
                    rank[q] = i + 1
                    next_front.append(q)
        i += 1
        fronts.append(next_front)

    if not fronts[-1]:
        fronts.pop()

    return fronts


def crowding_distance(fitness_values, front):
    distances = {i: 0.0 for i in front}
    if len(front) <= 2:
        for i in front:
            distances[i] = float('inf')
        return distances

    num_objectives = len(fitness_values[0])

    for m in range(num_objectives):
        sorted_front = sorted(front, key=lambda i: fitness_values[i][m])
        distances[sorted_front[0]] = float('inf')
        distances[sorted_front[-1]] = float('inf')

        obj_min = fitness_values[sorted_front[0]][m]
        obj_max = fitness_values[sorted_front[-1]][m]
        range_val = obj_max - obj_min

        if range_val == 0:
            continue

        for k in range(1, len(sorted_front) - 1):
            prev_val = fitness_values[sorted_front[k - 1]][m]
            next_val = fitness_values[sorted_front[k + 1]][m]
            distances[sorted_front[k]] += (next_val - prev_val) / range_val

    return distances


def nsga2_tournament_selection(population, fitness_values, fronts):
    rank = [0] * len(population)
    cd = [0.0] * len(population)

    for front_idx, front in enumerate(fronts):
        distances = crowding_distance(fitness_values, front)
        for ind in front:
            rank[ind] = front_idx
            cd[ind] = distances[ind]

    def tournament(idx1, idx2):
        if rank[idx1] < rank[idx2]:
            return idx1
        elif rank[idx1] > rank[idx2]:
            return idx2
        elif cd[idx1] > cd[idx2]:
            return idx1
        else:
            return idx2

    selected = []
    for _ in range(len(population)):
        i1, i2 = random.sample(range(len(population)), 2)
        winner = tournament(i1, i2)
        selected.append(population[winner])

    return selected


# ============================================================
# NSGA-II ANA DONGUSU (OPTİMİZE)
# ============================================================

EARLY_STOP_PATIENCE = 15  # Bu kadar jenerasyon iyileşme yoksa dur

def run_nsga2(breakfast_ids, lunch_ids, pop_size, num_generations,
              foods_df, nutrients_df, dri_df, user_info,
              crossover_rate=0.9, ref_point=None, diversity_enabled=False,
              user_foods_df=None):

    # --- Baslangic populasyonu ---
    population = [initialize_chromosome(breakfast_ids, lunch_ids) for _ in range(pop_size)]

    fitness_values = [
        evaluate(ind, foods_df, nutrients_df, dri_df, user_info, diversity_enabled, user_foods_df)
        for ind in population
    ]

    hv_history = []
    gen_fronts = []  # Post-hoc HV hesabi icin per-gen front fitness

    # Early stopping icin
    prev_best = None
    stale_count = 0
    actual_gens = 0

    # Ilk non-dominated sort (sonraki jenerasyonlarda tekrar kullanilacak)
    current_fronts = fast_non_dominated_sort(fitness_values)

    # --- Ana dongu ---
    for gen in range(num_generations):
        actual_gens = gen + 1

        # 1. Secim (current_fronts zaten hesaplandi)
        selected = nsga2_tournament_selection(population, fitness_values, current_fronts)

        # 2. Cocuk uretimi
        offspring = []
        for i in range(0, len(selected) - 1, 2):
            p1_break, p1_lunch = selected[i]
            p2_break, p2_lunch = selected[i + 1]
            child_break, child_lunch = apply_crossover(
                p1_break, p1_lunch, p2_break, p2_lunch, crossover_rate
            )
            child_break, child_lunch = apply_mutation(child_break, child_lunch)
            offspring.append((child_break, child_lunch))

        if len(selected) % 2 == 1:
            last = selected[-1]
            m_break, m_lunch = apply_mutation(last[0][:], last[1][:])
            offspring.append((m_break, m_lunch))

        # 3. Offspring fitness
        offspring_fitness = [
            evaluate(ind, foods_df, nutrients_df, dri_df, user_info, diversity_enabled, user_foods_df)
            for ind in offspring
        ]

        # 4. Birlestir
        combined_pop = population + offspring
        combined_fitness = fitness_values + offspring_fitness

        # 5. Non-dominated sort (combined, tek sort)
        fronts = fast_non_dominated_sort(combined_fitness)

        # 6. Survivor selection
        new_population = []
        new_fitness = []

        for front in fronts:
            if len(new_population) + len(front) <= pop_size:
                for idx in front:
                    new_population.append(combined_pop[idx])
                    new_fitness.append(combined_fitness[idx])
            else:
                distances = crowding_distance(combined_fitness, front)
                sorted_front = sorted(front, key=lambda i: distances[i], reverse=True)
                remaining = pop_size - len(new_population)
                for idx in sorted_front[:remaining]:
                    new_population.append(combined_pop[idx])
                    new_fitness.append(combined_fitness[idx])
                break

        population = new_population
        fitness_values = new_fitness

        # 7. Yeni populasyonun front'larini hesapla (sonraki gen icin + convergence)
        current_fronts = fast_non_dominated_sort(fitness_values)
        first_front_fit = [fitness_values[i] for i in current_fronts[0]]

        # Per-gen front kaydet (post-hoc HV icin)
        gen_fronts.append(first_front_fit)

        # HV hesabi (ref_point varsa)
        if ref_point is not None:
            from experiment import hypervolume
            hv = hypervolume(first_front_fit, ref_point)
            hv_history.append(hv)

        # 8. Early stopping
        current_best = tuple(
            min(f[obj] for f in first_front_fit) for obj in range(len(first_front_fit[0]))
        )
        if prev_best is not None:
            improved = any(
                current_best[i] < prev_best[i] - abs(prev_best[i]) * 0.001
                for i in range(len(current_best))
            )
            if not improved:
                stale_count += 1
            else:
                stale_count = 0
        prev_best = current_best

        if stale_count >= EARLY_STOP_PATIENCE and gen >= 30:
            print(f"    [NSGA-II] Erken durdurma: Gen {gen+1} "
                  f"(son {EARLY_STOP_PATIENCE} gen iyilesme yok)")
            break

        # 9. Ilerleme raporu
        if (gen + 1) % 20 == 0 or gen == 0:
            print(f"    [NSGA-II] Gen {gen+1}/{num_generations} — PF: {len(current_fronts[0])}")

    # --- Sonuc ---
    pareto_indices = current_fronts[0]
    pareto_front = [
        {"individual": population[i], "fitness": fitness_values[i]}
        for i in pareto_indices
    ]

    return pareto_front, hv_history, gen_fronts

import random
import math
from genetic_operators import initialize_chromosome, apply_crossover, apply_mutation
from nsga2 import evaluate, _dominates


# ============================================================
# SPEA2 YARDIMCI FONKSIYONLARI
# ============================================================

def spea2_fitness_assignment(fitness_values, archive_fitness):
    all_fitness = fitness_values + archive_fitness
    n = len(all_fitness)

    if n == 0:
        return []

    # Strength + Raw: tek O(N²) dongude ikisini birden hesapla
    strength = [0] * n
    raw_fitness = [0.0] * n

    for i in range(n):
        for j in range(i + 1, n):
            i_dom_j = _dominates(all_fitness[i], all_fitness[j])
            j_dom_i = _dominates(all_fitness[j], all_fitness[i])
            if i_dom_j:
                strength[i] += 1
            elif j_dom_i:
                strength[j] += 1

    # Raw fitness: domine edenlerin strength toplami
    for i in range(n):
        for j in range(n):
            if i != j and _dominates(all_fitness[j], all_fitness[i]):
                raw_fitness[i] += strength[j]

    # Density: k-NN
    k = max(1, int(math.sqrt(n)))

    density = [0.0] * n
    for i in range(n):
        distances = []
        for j in range(n):
            if i == j:
                continue
            dist_sq = sum((a - b) ** 2 for a, b in zip(all_fitness[i], all_fitness[j]))
            distances.append(dist_sq)
        distances.sort()
        sigma_k = math.sqrt(distances[k - 1]) if k - 1 < len(distances) else 0
        density[i] = 1.0 / (sigma_k + 2.0)

    final_fitness = [raw_fitness[i] + density[i] for i in range(n)]
    return final_fitness


def spea2_environmental_selection(combined_pop, combined_fitness,
                                  spea2_fitness, archive_size):
    non_dominated = [i for i in range(len(combined_pop)) if spea2_fitness[i] < 1.0]

    if len(non_dominated) == archive_size:
        new_archive = [combined_pop[i] for i in non_dominated]
        new_archive_fitness = [combined_fitness[i] for i in non_dominated]

    elif len(non_dominated) < archive_size:
        dominated = [i for i in range(len(combined_pop)) if spea2_fitness[i] >= 1.0]
        dominated.sort(key=lambda i: spea2_fitness[i])
        fill = archive_size - len(non_dominated)
        selected = non_dominated + dominated[:fill]
        new_archive = [combined_pop[i] for i in selected]
        new_archive_fitness = [combined_fitness[i] for i in selected]

    else:
        indices = non_dominated[:]
        while len(indices) > archive_size:
            dist_matrix = {}
            for i in indices:
                dists = []
                for j in indices:
                    if i == j:
                        continue
                    d = math.sqrt(sum(
                        (a - b) ** 2
                        for a, b in zip(combined_fitness[i], combined_fitness[j])
                    ))
                    dists.append(d)
                dists.sort()
                dist_matrix[i] = dists

            remove_idx = min(indices, key=lambda i: dist_matrix[i])
            indices.remove(remove_idx)

        new_archive = [combined_pop[i] for i in indices]
        new_archive_fitness = [combined_fitness[i] for i in indices]

    return new_archive, new_archive_fitness


# ============================================================
# SPEA2 ANA DONGUSU (OPTİMİZE)
# ============================================================

EARLY_STOP_PATIENCE = 15

def run_spea2(breakfast_ids, lunch_ids, pop_size, archive_size, num_generations,
              foods_df, nutrients_df, dri_df, user_info,
              crossover_rate=0.9, ref_point=None, diversity_enabled=False,
              user_foods_df=None):

    population = [initialize_chromosome(breakfast_ids, lunch_ids) for _ in range(pop_size)]

    pop_fitness = [
        evaluate(ind, foods_df, nutrients_df, dri_df, user_info, diversity_enabled, user_foods_df)
        for ind in population
    ]

    archive = []
    archive_fitness = []

    hv_history = []
    gen_fronts = []  # Post-hoc HV icin

    # Early stopping
    prev_best = None
    stale_count = 0

    for gen in range(num_generations):
        # Fitness atamasi
        combined_pop = population + archive
        combined_obj = pop_fitness + archive_fitness

        spea2_fit = spea2_fitness_assignment(pop_fitness, archive_fitness)

        # Environmental selection
        archive, archive_fitness = spea2_environmental_selection(
            combined_pop, combined_obj, spea2_fit, archive_size
        )

        # Per-gen front kaydet
        gen_fronts.append([f[:] for f in archive_fitness] if archive_fitness else [])

        # HV (ref_point varsa)
        if ref_point is not None and archive_fitness:
            from experiment import hypervolume
            hv = hypervolume(archive_fitness, ref_point)
            hv_history.append(hv)

        # Mating selection — SPEA2 fitness'i TEKRAR hesaplama, archive_fitness'tan
        # basit binary tournament yap (fitness_assignment gereksiz burada)
        if len(archive) < 2:
            mating_pool = [population[i % len(population)] for i in range(pop_size)]
        else:
            mating_pool = []
            for _ in range(pop_size):
                i1, i2 = random.sample(range(len(archive)), 2)
                # Basit karsilastirma: domine eden kazanir, yoksa rastgele
                if _dominates(archive_fitness[i1], archive_fitness[i2]):
                    mating_pool.append(archive[i1])
                elif _dominates(archive_fitness[i2], archive_fitness[i1]):
                    mating_pool.append(archive[i2])
                else:
                    mating_pool.append(archive[random.choice([i1, i2])])

        # Cocuk uretimi
        new_population = []
        for i in range(0, len(mating_pool) - 1, 2):
            p1_break, p1_lunch = mating_pool[i]
            p2_break, p2_lunch = mating_pool[i + 1]
            child_break, child_lunch = apply_crossover(
                p1_break, p1_lunch, p2_break, p2_lunch, crossover_rate
            )
            child_break, child_lunch = apply_mutation(child_break, child_lunch)
            new_population.append((child_break, child_lunch))

        if len(mating_pool) % 2 == 1:
            last = mating_pool[-1]
            m_break, m_lunch = apply_mutation(last[0][:], last[1][:])
            new_population.append((m_break, m_lunch))

        population = new_population
        pop_fitness = [
            evaluate(ind, foods_df, nutrients_df, dri_df, user_info, diversity_enabled, user_foods_df)
            for ind in population
        ]

        # Early stopping
        if archive_fitness:
            current_best = tuple(
                min(f[obj] for f in archive_fitness) for obj in range(len(archive_fitness[0]))
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
                print(f"    [SPEA2] Erken durdurma: Gen {gen+1} "
                      f"(son {EARLY_STOP_PATIENCE} gen iyilesme yok)")
                break

        # Ilerleme raporu
        if (gen + 1) % 20 == 0 or gen == 0:
            nd_count = sum(1 for f in spea2_fit[:len(population)] if f < 1.0)
            print(f"    [SPEA2] Gen {gen+1}/{num_generations} — "
                  f"Arsiv: {len(archive)}, ND: {nd_count}")

    # --- Sonuc ---
    if archive_fitness:
        final_fit = spea2_fitness_assignment(archive_fitness, [])
        pareto_front = [
            {"individual": archive[i], "fitness": archive_fitness[i]}
            for i in range(len(archive))
            if final_fit[i] < 1.0
        ]
        if not pareto_front:
            pareto_front = [
                {"individual": archive[i], "fitness": archive_fitness[i]}
                for i in range(len(archive))
            ]
    else:
        pareto_front = [
            {"individual": population[i], "fitness": pop_fitness[i]}
            for i in range(len(population))
        ]

    return pareto_front, hv_history, gen_fronts

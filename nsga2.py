import random
from genetic_operators import initialize_chromosome, apply_crossover, apply_mutation
from decode import decode_chromosome, calculate_penalty


# ============================================================
# FITNESS DEGERLENDIRME
# ============================================================
# Gorev 3'ten gelen fonksiyonlar:
#   decode_chromosome(individual, foods_df, nutrients_df, dri_df, user_info)
#       → selected_foods: list of food ID'leri (menuye secilen yemekler)
#
#   calculate_penalty(selected_foods, foods_df, nutrients_df, dri_df, user_info)
#       → R: float (penalty degeri, 0 = ihlal yok)
#
# Gorev 3'u yapan arkadas bu iki fonksiyonu decode.py icinde tanimlamali.

LAMBDA = 1.0  # Penalty agirligi (PDF: lambda = 1.0 ile basla, deneysel ayarla)


def evaluate(individual, foods_df, nutrients_df, dri_df, user_info):
    """
    Kromozomu decode edip 3 objective degeri dondurur (hepsi MINIMIZE).
    PDF kurali: 3 objective secilecek:
      1) preference → MAX oldugu icin negatif alinir (-preference)
      2) cost → MIN
      3) co2 → MIN
    Her objective'e penalty eklenir: obj + lambda * R
    """
    # Adim 1: Kromozomu decode et → menuye secilen yemeklerin ID listesi
    selected_foods = decode_chromosome(
        individual, foods_df, nutrients_df, dri_df, user_info
    )

    # Adim 2: Secilen yemeklerin objective degerlerini hesapla
    selected_data = foods_df[foods_df["id"].isin(selected_foods)]

    total_cost = selected_data["cost"].sum()
    total_co2 = selected_data["co2"].sum()

    # Preference: user_foods tablosundan kullaniciya ozel tercih puani alinir
    # Eger user_info icinde user_id varsa user_foods'tan cekilir
    # Yoksa foods tablosundaki preference kullanilir
    total_preference = selected_data["preference"].sum()

    # Adim 3: Penalty hesapla (nutrient kisitlarindan sapma)
    R = calculate_penalty(
        selected_foods, foods_df, nutrients_df, dri_df, user_info
    )

    # Adim 4: Penalized objective degerlerini dondur (hepsi MINIMIZE)
    obj_preference = -total_preference + LAMBDA * R  # MAX → negatif al + penalty
    obj_cost = total_cost + LAMBDA * R               # MIN + penalty
    obj_co2 = total_co2 + LAMBDA * R                 # MIN + penalty

    return [obj_preference, obj_cost, obj_co2]


# ============================================================
# ORTAK YARDIMCI FONKSIYON
# ============================================================

def _dominates(obj_a, obj_b):
    """a cozumu b'yi domine ediyor mu kontrol eder. Tum objective'ler minimize."""
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
    """
    Populasyonu domine iliskilerine gore front'lara ayirir.
    Front 0 = en iyi (domine edilmeyen), Front 1 = ikinci en iyi, ...
    """
    pop_size = len(fitness_values)
    domination_count = [0] * pop_size   # beni domine eden birey sayisi
    dominated_set = [[] for _ in range(pop_size)]  # benim domine ettiklerim
    rank = [0] * pop_size
    fronts = [[]]

    for p in range(pop_size):
        for q in range(pop_size):
            if p == q:
                continue
            if _dominates(fitness_values[p], fitness_values[q]):
                dominated_set[p].append(q)
            elif _dominates(fitness_values[q], fitness_values[p]):
                domination_count[p] += 1

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

    # Son bos front'u kaldir
    if not fronts[-1]:
        fronts.pop()

    return fronts


def crowding_distance(fitness_values, front):
    """
    Ayni front'taki bireylerin birbirine ne kadar yakin oldugunu olcer.
    Yuksek deger = etrafinda az birey var = cesitlilik icin daha degerli.
    """
    distances = {i: 0.0 for i in front}
    if len(front) <= 2:
        for i in front:
            distances[i] = float('inf')
        return distances

    num_objectives = len(fitness_values[0])

    for m in range(num_objectives):
        # Bu objective'e gore front'u sirala
        sorted_front = sorted(front, key=lambda i: fitness_values[i][m])

        # Sinirdaki bireyler sonsuz distance alir
        distances[sorted_front[0]] = float('inf')
        distances[sorted_front[-1]] = float('inf')

        # Objective'in deger araligini bul (normalizasyon icin)
        obj_min = fitness_values[sorted_front[0]][m]
        obj_max = fitness_values[sorted_front[-1]][m]
        range_val = obj_max - obj_min

        if range_val == 0:
            continue

        # Aradaki bireyler icin mesafe hesapla
        for k in range(1, len(sorted_front) - 1):
            prev_val = fitness_values[sorted_front[k - 1]][m]
            next_val = fitness_values[sorted_front[k + 1]][m]
            distances[sorted_front[k]] += (next_val - prev_val) / range_val

    return distances


def nsga2_tournament_selection(population, fitness_values, fronts):
    """
    Rastgele 2 birey secer, daha iyi rank'a sahip olan kazanir.
    Rank esitse crowding distance'i yuksek olan kazanir.
    """
    # Her bireye rank ve crowding distance ata
    rank = [0] * len(population)
    cd = [0.0] * len(population)

    for front_idx, front in enumerate(fronts):
        distances = crowding_distance(fitness_values, front)
        for ind in front:
            rank[ind] = front_idx
            cd[ind] = distances[ind]

    def tournament(idx1, idx2):
        # Daha dusuk rank (daha iyi front) kazanir
        if rank[idx1] < rank[idx2]:
            return idx1
        elif rank[idx1] > rank[idx2]:
            return idx2
        # Ayni rank ise daha yuksek crowding distance kazanir
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
# NSGA-II ANA DONGUSU
# ============================================================

def run_nsga2(breakfast_ids, lunch_ids, pop_size, num_generations,
              foods_df, nutrients_df, dri_df, user_info,
              crossover_rate=0.9, ref_point=None):
    """
    NSGA-II ana dongusu. Populasyon olusturur, her jenerasyonda
    secim-crossover-mutasyon-birlestirme-siralama yapar.
    Sonucta Pareto front + convergence verisi dondurur.
    """
    from experiment import hypervolume

    # --- Baslangic populasyonu ---
    population = []
    for _ in range(pop_size):
        ind = initialize_chromosome(breakfast_ids, lunch_ids)
        population.append(ind)

    fitness_values = [
        evaluate(ind, foods_df, nutrients_df, dri_df, user_info)
        for ind in population
    ]

    # Convergence takibi: her jenerasyondaki hypervolume
    hv_history = []

    # --- Ana dongu ---
    for gen in range(num_generations):
        # Ebeveyn secimi
        selected = nsga2_tournament_selection(population, fitness_values,
                                              fast_non_dominated_sort(fitness_values))

        # Cocuk uretimi (crossover + mutation)
        offspring = []
        for i in range(0, len(selected) - 1, 2):
            p1_break, p1_lunch = selected[i]
            p2_break, p2_lunch = selected[i + 1]

            child_break, child_lunch = apply_crossover(
                p1_break, p1_lunch, p2_break, p2_lunch, crossover_rate
            )
            child_break, child_lunch = apply_mutation(child_break, child_lunch)
            offspring.append((child_break, child_lunch))

        # Tek kalan varsa direkt ekle
        if len(selected) % 2 == 1:
            last = selected[-1]
            m_break, m_lunch = apply_mutation(last[0][:], last[1][:])
            offspring.append((m_break, m_lunch))

        # Cocuklarin fitness degerlerini hesapla
        offspring_fitness = [
            evaluate(ind, foods_df, nutrients_df, dri_df, user_info)
            for ind in offspring
        ]

        # Ebeveyn + cocuk birlestir (R_t = P_t U Q_t)
        combined_pop = population + offspring
        combined_fitness = fitness_values + offspring_fitness

        # Non-dominated sort
        fronts = fast_non_dominated_sort(combined_fitness)

        # Yeni populasyonu sec (en iyi pop_size kadar birey)
        new_population = []
        new_fitness = []

        for front in fronts:
            if len(new_population) + len(front) <= pop_size:
                # Front tamamen sigar
                for idx in front:
                    new_population.append(combined_pop[idx])
                    new_fitness.append(combined_fitness[idx])
            else:
                # Bu front'tan crowding distance'a gore sec
                distances = crowding_distance(combined_fitness, front)
                sorted_front = sorted(front, key=lambda i: distances[i], reverse=True)
                remaining = pop_size - len(new_population)
                for idx in sorted_front[:remaining]:
                    new_population.append(combined_pop[idx])
                    new_fitness.append(combined_fitness[idx])
                break

        population = new_population
        fitness_values = new_fitness

        # Convergence: bu jenerasyonun hypervolume degerini kaydet
        if ref_point is not None:
            front_indices = fast_non_dominated_sort(fitness_values)[0]
            front_fitness = [fitness_values[i] for i in front_indices]
            hv = hypervolume(front_fitness, ref_point)
            hv_history.append(hv)

        # Ilerleme raporu (her 10 jenerasyonda)
        if (gen + 1) % 10 == 0 or gen == 0:
            first_front = fast_non_dominated_sort(fitness_values)[0]
            print(f"[NSGA-II] Jenerasyon {gen + 1}/{num_generations} — "
                  f"Pareto front boyutu: {len(first_front)}")

    # --- Sonuc: Pareto front ---
    final_fronts = fast_non_dominated_sort(fitness_values)
    pareto_indices = final_fronts[0]
    pareto_front = [
        {"individual": population[i], "fitness": fitness_values[i]}
        for i in pareto_indices
    ]

    return pareto_front, hv_history

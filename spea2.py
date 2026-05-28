import random
import math
from genetic_operators import initialize_chromosome, apply_crossover, apply_mutation
from nsga2 import evaluate, _dominates


# ============================================================
# SPEA2 YARDIMCI FONKSIYONLARI
# ============================================================

def spea2_fitness_assignment(fitness_values, archive_fitness):
    """
    Her bireye SPEA2 fitness degeri atar.
    Strength (kac birey domine ediyor) + Raw (domine edenler) + Density (yogunluk).
    Sonuc: dusuk deger = iyi birey. F < 1.0 ise domine edilmiyor demektir.
    """
    all_fitness = fitness_values + archive_fitness
    n = len(all_fitness)

    # Strength hesapla: S(i) = bireyin domine ettigi birey sayisi
    strength = [0] * n
    for i in range(n):
        for j in range(n):
            if i != j and _dominates(all_fitness[i], all_fitness[j]):
                strength[i] += 1

    # Raw fitness: R(i) = bireyi domine edenlerin strength toplami
    raw_fitness = [0.0] * n
    for i in range(n):
        for j in range(n):
            if i != j and _dominates(all_fitness[j], all_fitness[i]):
                raw_fitness[i] += strength[j]

    # Density: D(i) = 1 / (sigma_k + 2)
    # sigma_k = k-inci en yakin komsunun mesafesi, k = sqrt(N)
    k = int(math.sqrt(n))
    if k < 1:
        k = 1

    density = [0.0] * n
    for i in range(n):
        distances = []
        for j in range(n):
            if i == j:
                continue
            dist = math.sqrt(sum(
                (a - b) ** 2 for a, b in zip(all_fitness[i], all_fitness[j])
            ))
            distances.append(dist)
        distances.sort()
        sigma_k = distances[k - 1] if k - 1 < len(distances) else 0
        density[i] = 1.0 / (sigma_k + 2.0)

    # Final fitness = R(i) + D(i)
    final_fitness = [raw_fitness[i] + density[i] for i in range(n)]

    return final_fitness


def spea2_environmental_selection(combined_pop, combined_fitness,
                                  spea2_fitness, archive_size):
    """
    SPEA2 arsivini gunceller. Domine edilmeyenleri arsive alir.
    Az ise en iyi domine edilenlerle doldurur, cok ise en yakin komsulari cikarir.
    """
    # Domine edilmeyenler: fitness < 1 olan bireyler
    non_dominated = [i for i in range(len(combined_pop)) if spea2_fitness[i] < 1.0]

    if len(non_dominated) == archive_size:
        new_archive = [combined_pop[i] for i in non_dominated]
        new_archive_fitness = [combined_fitness[i] for i in non_dominated]

    elif len(non_dominated) < archive_size:
        # Eksik yerleri en iyi domine edilenlerle doldur
        dominated = [i for i in range(len(combined_pop)) if spea2_fitness[i] >= 1.0]
        dominated.sort(key=lambda i: spea2_fitness[i])
        fill = archive_size - len(non_dominated)
        selected = non_dominated + dominated[:fill]
        new_archive = [combined_pop[i] for i in selected]
        new_archive_fitness = [combined_fitness[i] for i in selected]

    else:
        # Truncation: en yakin komsulari olan bireyi iteratif cikar
        indices = non_dominated[:]
        while len(indices) > archive_size:
            # Her birey ciftinin mesafesini hesapla
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

            # En kucuk k-inci komsulugu olan bireyi bul ve cikar
            remove_idx = min(indices, key=lambda i: dist_matrix[i])
            indices.remove(remove_idx)

        new_archive = [combined_pop[i] for i in indices]
        new_archive_fitness = [combined_fitness[i] for i in indices]

    return new_archive, new_archive_fitness


# ============================================================
# SPEA2 ANA DONGUSU
# ============================================================

def run_spea2(breakfast_ids, lunch_ids, pop_size, archive_size, num_generations,
              foods_df, nutrients_df, dri_df, user_info,
              crossover_rate=0.9, ref_point=None, diversity_enabled=False):
    """
    SPEA2 ana dongusu. Ayri bir arsiv tutar, her jenerasyonda
    fitness atama-arsiv guncelleme-secim-crossover-mutasyon yapar.
    Sonucta arsivdeki domine edilmeyen cozumler + convergence verisi dondurur.
    """
    from experiment import hypervolume

    # --- Baslangic populasyonu ---
    population = []
    for _ in range(pop_size):
        ind = initialize_chromosome(breakfast_ids, lunch_ids)
        population.append(ind)

    pop_fitness = [
        evaluate(ind, foods_df, nutrients_df, dri_df, user_info, diversity_enabled)
        for ind in population
    ]

    archive = []
    archive_fitness = []

    # Convergence takibi: her jenerasyondaki hypervolume
    hv_history = []

    # --- Ana dongu ---
    for gen in range(num_generations):
        # Fitness atamasi (populasyon + arsiv)
        combined_pop = population + archive
        combined_obj = pop_fitness + archive_fitness

        spea2_fit = spea2_fitness_assignment(pop_fitness, archive_fitness)

        # Environmental selection — yeni arsivi olustur
        archive, archive_fitness = spea2_environmental_selection(
            combined_pop, combined_obj, spea2_fit, archive_size
        )

        # Convergence: arsivdeki domine edilmeyenlerin hypervolume'u
        if ref_point is not None:
            nd_fitness = [archive_fitness[i] for i in range(len(archive_fitness))]
            hv = hypervolume(nd_fitness, ref_point)
            hv_history.append(hv)

        # Arsivden mating selection (binary tournament)
        archive_spea2_fit = spea2_fitness_assignment(archive_fitness, [])
        mating_pool = []
        for _ in range(pop_size):
            i1, i2 = random.sample(range(len(archive)), 2)
            if archive_spea2_fit[i1] < archive_spea2_fit[i2]:
                mating_pool.append(archive[i1])
            else:
                mating_pool.append(archive[i2])

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
            evaluate(ind, foods_df, nutrients_df, dri_df, user_info, diversity_enabled)
            for ind in population
        ]

        # Ilerleme raporu
        if (gen + 1) % 10 == 0 or gen == 0:
            nd_count = sum(1 for f in spea2_fit[:len(population)] if f < 1.0)
            print(f"[SPEA2] Jenerasyon {gen + 1}/{num_generations} — "
                  f"Arsiv boyutu: {len(archive)}, Domine edilmeyen: {nd_count}")

    # --- Sonuc: Arsivdeki domine edilmeyenler ---
    final_fit = spea2_fitness_assignment(archive_fitness, [])
    pareto_front = [
        {"individual": archive[i], "fitness": archive_fitness[i]}
        for i in range(len(archive))
        if final_fit[i] < 1.0
    ]

    # Eger hicbiri domine edilmiyorsa tum arsivi don
    if not pareto_front:
        pareto_front = [
            {"individual": archive[i], "fitness": archive_fitness[i]}
            for i in range(len(archive))
        ]

    return pareto_front, hv_history

import random
import math
import csv
import os
import json
from nsga2 import run_nsga2
from spea2 import run_spea2
from visualization import (
    plot_algorithm_comparison,
    plot_convergence,
    plot_pareto_front,
    plot_3d_pareto,
    plot_user_comparison
)


# ============================================================
# 1. HYPERVOLUME (3 objective destekli)
# ============================================================

def hypervolume(pareto_fitness, ref_point):
    """
    3 objective icin hypervolume hesabi (genel recursive yaklaşim).
    Ref point'u domine etmeyen noktalar otomatik elenir.
    Yuksek hypervolume = daha iyi Pareto front.
    """
    # Ref point'u domine eden noktalari filtrele
    points = [p for p in pareto_fitness if all(p[i] < ref_point[i] for i in range(len(ref_point)))]

    if not points:
        return 0.0

    n_obj = len(ref_point)

    if n_obj == 1:
        return ref_point[0] - min(p[0] for p in points)

    if n_obj == 2:
        return _hypervolume_2d(points, ref_point)

    if n_obj == 3:
        return _hypervolume_3d(points, ref_point)

    # 4+ objective icin basit Monte Carlo yaklasimi
    return _hypervolume_monte_carlo(points, ref_point, samples=10000)


def _hypervolume_2d(points, ref_point):
    """2D hypervolume — sweep line algoritmasi."""
    # Ilk objective'e gore sirala
    sorted_pts = sorted(points, key=lambda x: x[0])
    hv = 0.0
    prev_x = ref_point[0]
    prev_y = ref_point[1]

    for p in reversed(sorted_pts):
        if p[1] < prev_y:
            hv += (prev_x - p[0]) * (prev_y - p[1])
            prev_x = p[0]
            prev_y = p[1]

    return hv


def _hypervolume_3d(points, ref_point):
    """
    3D hypervolume — z eksenine gore dilimleyip her dilimde 2D hesaplar.
    """
    # z degerine gore sirala (kucukten buyuge)
    sorted_pts = sorted(points, key=lambda x: x[2])
    hv = 0.0
    prev_z = ref_point[2]

    # Her z dilimi icin, o z'nin altindaki tum noktalarin 2D hypervolume'unu hesapla
    unique_z = sorted(set(p[2] for p in sorted_pts), reverse=True)

    for z_val in unique_z:
        # Bu z degerine kadar olan tum noktalar (z <= z_val olan)
        slice_pts = [[p[0], p[1]] for p in sorted_pts if p[2] <= z_val]

        if slice_pts:
            # Bu dilimin 2D hypervolume'u
            hv_2d = _hypervolume_2d(slice_pts, [ref_point[0], ref_point[1]])
            # Dilimin z yuksekligi
            z_height = prev_z - z_val
            hv += hv_2d * z_height
            prev_z = z_val

    return hv


def _hypervolume_monte_carlo(points, ref_point, samples=10000):
    """4+ objective icin Monte Carlo tahmini."""
    # Ideal nokta (her objective'in minimumu)
    n_obj = len(ref_point)
    ideal = [min(p[i] for p in points) for i in range(n_obj)]

    # Toplam hacim
    total_vol = 1.0
    for i in range(n_obj):
        total_vol *= (ref_point[i] - ideal[i])

    if total_vol <= 0:
        return 0.0

    count = 0
    for _ in range(samples):
        sample = [random.uniform(ideal[i], ref_point[i]) for i in range(n_obj)]
        # Bu sample herhangi bir Pareto noktasi tarafindan domine ediliyor mu?
        for p in points:
            if all(p[j] <= sample[j] for j in range(n_obj)):
                count += 1
                break

    return total_vol * (count / samples)


# ============================================================
# 2. SPACING METRIGI
# ============================================================

def spacing(pareto_fitness):
    """
    Pareto front'taki cozumlerin birbirine ne kadar esit mesafede dagildigini olcer.
    Dusuk spacing = daha esit dagilim = daha iyi.
    """
    if len(pareto_fitness) <= 1:
        return 0.0

    min_distances = []
    for i, p in enumerate(pareto_fitness):
        dists = []
        for j, q in enumerate(pareto_fitness):
            if i == j:
                continue
            d = sum(abs(a - b) for a, b in zip(p, q))
            dists.append(d)
        min_distances.append(min(dists))

    d_mean = sum(min_distances) / len(min_distances)
    variance = sum((d - d_mean) ** 2 for d in min_distances) / len(min_distances)
    return math.sqrt(variance)


# ============================================================
# 3. REFERANS NOKTASI OTOMATIK HESAPLAMA
# ============================================================

def compute_reference_point(all_fitness_values):
    """
    PDF kurali: tum run'lardaki en kotu deger + %10 margin.
    Tum algoritmalar ayni referans noktasini kullanir.

    NOT: Negatif degerler icin worst * 1.10 yanlis sonuc verir
    (daha kucuk = daha iyi yapar). Bu yuzden mutlak deger bazli
    margin kullanilir: ref = worst + |worst| * 0.10
    Bu her zaman "daha kotu" (daha buyuk) bir referans noktasi uretir.
    """
    if not all_fitness_values:
        return None

    n_obj = len(all_fitness_values[0])
    ref = []
    for i in range(n_obj):
        worst = max(f[i] for f in all_fitness_values)
        # Pozitif veya negatif farketmez, her zaman worst'ten buyuk ref uret
        margin = max(abs(worst) * 0.10, 0.01)
        ref.append(worst + margin)

    return ref


# ============================================================
# 4. CSV EXPORT
# ============================================================

def save_pareto_to_csv(pareto_front, filename, experiment_name):
    """Pareto front sonuclarini CSV dosyasina kaydeder."""
    os.makedirs("results", exist_ok=True)
    filepath = os.path.join("results", filename)

    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)

        # Baslik satiri
        n_obj = len(pareto_front[0]["fitness"]) if pareto_front else 0
        header = [f"obj_{i+1}" for i in range(n_obj)]
        writer.writerow(["experiment", "solution_id"] + header)

        # Veriler
        for idx, sol in enumerate(pareto_front):
            row = [experiment_name, idx] + list(sol["fitness"])
            writer.writerow(row)

    print(f"  Kaydedildi: {filepath}")

def save_sample_menu_to_csv(pareto_front, filename, experiment_name):
    print("SAMPLE MENU FONKSIYONU CALISTI")

    os.makedirs("results/sample_menus", exist_ok=True)

    filepath = os.path.join("results/sample_menus", filename)

    with open(filepath, "w", newline="", encoding="utf-8") as f:

        writer = csv.writer(f)

        writer.writerow([
            "experiment",
            "solution_id",
            "obj_1",
            "obj_2",
            "obj_3",
            "breakfast_ids",
            "lunch_ids"
        ])

        for idx, sol in enumerate(pareto_front):

            breakfast_part, lunch_part = sol["individual"]

            writer.writerow([
                experiment_name,
                idx,
                *sol["fitness"],
                str(breakfast_part),
                str(lunch_part)
            ])

    print(f"Sample menu kaydedildi: {filepath}")


def save_convergence_to_csv(hv_history, filename, algorithm_name):
    """Convergence verisini (hypervolume vs generation) CSV'ye kaydeder."""
    os.makedirs("results", exist_ok=True)
    filepath = os.path.join("results", filename)

    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["algorithm", "generation", "hypervolume"])
        for gen, hv in enumerate(hv_history):
            writer.writerow([algorithm_name, gen + 1, hv])

    print(f"  Kaydedildi: {filepath}")
    # ============================================================
# JSON EXPORT
# ============================================================

def save_pareto_to_json(pareto_front, filename, experiment_name):

    os.makedirs("results/json", exist_ok=True)

    filepath = os.path.join("results/json", filename)

    data = []

    for idx, sol in enumerate(pareto_front):

        entry = {
            "experiment": experiment_name,
            "solution_id": idx,
            "fitness": list(sol["fitness"])
        }

        data.append(entry)

    with open(filepath, "w", encoding="utf-8") as f:

        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"JSON kaydedildi: {filepath}")

def save_sample_menu_to_json(pareto_front, filename, experiment_name,
                             foods_df=None, nutrients_df=None, dri_df=None, user_info=None):
    """
    PDF gereksinimi (s.7): "at least 3 Pareto solutions: food items,
    nutrient totals vs. DRI bounds, objective values"
    """
    from decode import decode_chromosome, NUTRIENT_IDS, _build_cache, GLOBAL_FOOD_MAP, _filter_dri_for_user

    os.makedirs("results/sample_menus", exist_ok=True)
    filepath = os.path.join("results/sample_menus", filename)

    # En fazla 3 ornek cozum (PDF: "at least 3")
    sample_count = min(3, len(pareto_front))
    # Farkli bolgelerdeki cozumleri sec (bastan, ortadan, sondan)
    if len(pareto_front) >= 3:
        indices = [0, len(pareto_front) // 2, len(pareto_front) - 1]
    else:
        indices = list(range(sample_count))

    data = []
    for idx in indices:
        sol = pareto_front[idx]
        breakfast_part, lunch_part = sol["individual"]

        entry = {
            "experiment": experiment_name,
            "solution_id": idx,
            "fitness": {
                "obj_preference": sol["fitness"][0],
                "obj_cost": sol["fitness"][1],
                "obj_co2": sol["fitness"][2]
            },
            "breakfast_ids": breakfast_part,
            "lunch_ids": lunch_part
        }

        # Detayli menu bilgisi (foods_df verilmisse)
        if foods_df is not None and nutrients_df is not None and dri_df is not None and user_info is not None:
            selected_foods = decode_chromosome(
                sol["individual"], foods_df, nutrients_df, dri_df, user_info
            )

            # Food names
            food_names = []
            for fid in selected_foods:
                row = foods_df[foods_df["id"] == fid]
                if not row.empty:
                    food_names.append({"id": int(fid), "name": str(row.iloc[0]["name"])})
            entry["selected_foods"] = food_names

            # Nutrient totals
            _build_cache(foods_df, nutrients_df, dri_df, user_info)
            nutrient_totals = {nid: 0.0 for nid in NUTRIENT_IDS}
            for fid in selected_foods:
                fn = GLOBAL_FOOD_MAP.get(fid, {nid: 0.0 for nid in NUTRIENT_IDS})
                for nid in NUTRIENT_IDS:
                    nutrient_totals[nid] += fn[nid]

            # DRI bounds
            user_dri = _filter_dri_for_user(dri_df, user_info)
            nutrient_names = {5: "Energy", 15: "Protein", 8: "Carbohydrate", 4: "Fiber", 17: "Sodium"}
            nutrients_vs_dri = []
            for nid in NUTRIENT_IDS:
                dri_row = user_dri[user_dri["nutrient_id"] == nid]
                rll = float(dri_row.iloc[0]["RLL"]) if not dri_row.empty else 0.0
                rul = float(dri_row.iloc[0]["RUL"]) if not dri_row.empty else 9999.0
                total = nutrient_totals[nid]
                within = rll <= total <= rul
                nutrients_vs_dri.append({
                    "nutrient": nutrient_names.get(nid, str(nid)),
                    "total": round(total, 2),
                    "RLL": round(rll, 2),
                    "RUL": round(rul, 2),
                    "within_bounds": within
                })
            entry["nutrients_vs_dri"] = nutrients_vs_dri
            entry["constraints_met"] = sum(1 for n in nutrients_vs_dri if n["within_bounds"])
            entry["total_constraints"] = len(NUTRIENT_IDS)

            # Distinct food groups
            group_ids = set()
            for fid in selected_foods:
                row = foods_df[foods_df["id"] == fid]
                if not row.empty:
                    group_ids.add(int(row.iloc[0]["foodGroupId"]))
            entry["distinct_food_groups"] = len(group_ids)

        data.append(entry)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"Sample menu kaydedildi: {filepath}")




# ============================================================
# 5. EXPERIMENT SENARYOLARI
# ============================================================

# --- Ortak parametreler ---
POP_SIZE = 100
ARCHIVE_SIZE = 100
NUM_GENERATIONS = 80    # Early stopping ile genelde 40-60'ta durur
CROSSOVER_RATE = 0.9
NUM_RUNS = 3


def _run_single_comparison(breakfast_ids, lunch_ids,
                           foods_df, nutrients_df, dri_df, user_info,
                           label="", diversity_enabled=False, user_foods_df=None):
    """
    NSGA-II ve SPEA2'yi ayni kosullarda calistirip sonuclari dondurur.
    On-run KALDIRILDI — ref_point gercek run sonuclarindan post-hoc hesaplanir.
    HV convergence da post-hoc hesaplanir (gen_fronts'tan).
    """
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"  Pop: {POP_SIZE} | Gen: {NUM_GENERATIONS} (+ early stop) | Runs: {NUM_RUNS}")
    print(f"{'='*60}")

    # --- Tek seferde gercek run'lar (on-run YOK) ---
    nsga2_results = []
    spea2_results = []
    nsga2_gen_fronts_all = []
    spea2_gen_fronts_all = []
    all_fitness = []

    for run in range(NUM_RUNS):
        print(f"\n--- Run {run + 1}/{NUM_RUNS} ---")
        seed = 42 + run

        random.seed(seed)
        print("  NSGA-II calisiyor...")
        nsga2_pf, _, nsga2_gf = run_nsga2(
            breakfast_ids, lunch_ids, POP_SIZE, NUM_GENERATIONS,
            foods_df, nutrients_df, dri_df, user_info, CROSSOVER_RATE,
            diversity_enabled=diversity_enabled, user_foods_df=user_foods_df
        )
        nsga2_results.append(nsga2_pf)
        nsga2_gen_fronts_all.append(nsga2_gf)
        for sol in nsga2_pf:
            all_fitness.append(sol["fitness"])

        random.seed(seed)
        print("  SPEA2 calisiyor...")
        spea2_pf, _, spea2_gf = run_spea2(
            breakfast_ids, lunch_ids, POP_SIZE, ARCHIVE_SIZE, NUM_GENERATIONS,
            foods_df, nutrients_df, dri_df, user_info, CROSSOVER_RATE,
            diversity_enabled=diversity_enabled, user_foods_df=user_foods_df
        )
        spea2_results.append(spea2_pf)
        spea2_gen_fronts_all.append(spea2_gf)
        for sol in spea2_pf:
            all_fitness.append(sol["fitness"])

    # --- Post-hoc: ref_point hesapla ---
    ref_point = compute_reference_point(all_fitness)
    print(f"\n  Referans noktasi (post-hoc): {ref_point}")

    # --- Post-hoc: HV history hesapla (gen_fronts'tan) ---
    nsga2_hv_histories = []
    spea2_hv_histories = []

    for gen_fronts in nsga2_gen_fronts_all:
        hv_hist = []
        for front_fit in gen_fronts:
            hv_hist.append(hypervolume(front_fit, ref_point) if front_fit else 0.0)
        nsga2_hv_histories.append(hv_hist)

    for gen_fronts in spea2_gen_fronts_all:
        hv_hist = []
        for front_fit in gen_fronts:
            hv_hist.append(hypervolume(front_fit, ref_point) if front_fit else 0.0)
        spea2_hv_histories.append(hv_hist)

    # --- Sonuclari raporla ---
    print(f"\n{'='*60}")
    print(f"  SONUCLAR — {label}")
    print(f"{'='*60}")

    for run in range(NUM_RUNS):
        nsga2_fit = [r["fitness"] for r in nsga2_results[run]]
        spea2_fit = [r["fitness"] for r in spea2_results[run]]

        nsga2_hv = hypervolume(nsga2_fit, ref_point) if nsga2_fit else 0
        spea2_hv = hypervolume(spea2_fit, ref_point) if spea2_fit else 0

        print(f"\n  Run {run + 1}:")
        print(f"    NSGA-II — PF boyutu: {len(nsga2_fit)}, "
              f"HV: {nsga2_hv:.4f}, Spacing: {spacing(nsga2_fit):.4f}")
        print(f"    SPEA2   — PF boyutu: {len(spea2_fit)}, "
              f"HV: {spea2_hv:.4f}, Spacing: {spacing(spea2_fit):.4f}")

    return {
        "nsga2_results": nsga2_results,
        "spea2_results": spea2_results,
        "nsga2_hv_histories": nsga2_hv_histories,
        "spea2_hv_histories": spea2_hv_histories,
        "ref_point": ref_point
    }


# --- DENEY 1: Kullanici karsilastirmasi ---

def experiment_user_comparison(breakfast_ids, lunch_ids,
                               foods_df, nutrients_df, dri_df,
                               user1_info, user2_info, user_foods_df=None):
    """
    PDF Deney 1: User 1 (non-vegetarian) ve User 2 (vegetarian) icin
    algoritmalari ayri ayri calistirip Pareto front'lari karsilastirir.
    """
    print("\n" + "#" * 60)
    print("# DENEY 1: KULLANICI KARSILASTIRMASI")
    print("#" * 60)

    result_u1 = _run_single_comparison(
        breakfast_ids, lunch_ids,
        foods_df, nutrients_df, dri_df, user1_info,
        label="User 1 (Non-vegetarian)", user_foods_df=user_foods_df
    )

    result_u2 = _run_single_comparison(
        breakfast_ids, lunch_ids,
        foods_df, nutrients_df, dri_df, user2_info,
        label="User 2 (Vegetarian)", user_foods_df=user_foods_df
    )

    # CSV + JSON kaydet
    for run in range(NUM_RUNS):

        save_pareto_to_csv(
        result_u1["nsga2_results"][run],
        f"user1_nsga2_run{run+1}.csv",
        "user1_nsga2"
    )

        save_pareto_to_json(
        result_u1["nsga2_results"][run],
        f"user1_nsga2_run{run+1}.json",
        "user1_nsga2"
    )
        save_sample_menu_to_json(
            result_u1["nsga2_results"][run],
            f"user1_nsga2_menu_run{run+1}.json",
            "user1_nsga2",
            foods_df, nutrients_df, dri_df, user1_info
        )

        save_pareto_to_csv(
            result_u1["spea2_results"][run],
            f"user1_spea2_run{run+1}.csv",
            "user1_spea2"
        )

        save_pareto_to_json(
            result_u1["spea2_results"][run],
            f"user1_spea2_run{run+1}.json",
            "user1_spea2"
        )
        save_sample_menu_to_json(
            result_u1["spea2_results"][run],
            f"user1_spea2_menu_run{run+1}.json",
            "user1_spea2",
            foods_df, nutrients_df, dri_df, user1_info
        )

        save_pareto_to_csv(
            result_u2["nsga2_results"][run],
            f"user2_nsga2_run{run+1}.csv",
            "user2_nsga2"
        )

        save_pareto_to_json(
            result_u2["nsga2_results"][run],
            f"user2_nsga2_run{run+1}.json",
            "user2_nsga2"
        )
        save_sample_menu_to_json(
            result_u2["nsga2_results"][run],
            f"user2_nsga2_menu_run{run+1}.json",
            "user2_nsga2",
            foods_df, nutrients_df, dri_df, user2_info
        )

        save_pareto_to_csv(
            result_u2["spea2_results"][run],
            f"user2_spea2_run{run+1}.csv",
            "user2_spea2"
        )

        save_pareto_to_json(
            result_u2["spea2_results"][run],
            f"user2_spea2_run{run+1}.json",
            "user2_spea2"
        )
        save_sample_menu_to_json(
            result_u2["spea2_results"][run],
            f"user2_spea2_menu_run{run+1}.json",
            "user2_spea2",
            foods_df, nutrients_df, dri_df, user2_info
        )

    return result_u1, result_u2


# --- DENEY 2: Algoritma karsilastirmasi ---

def experiment_algorithm_comparison(breakfast_ids, lunch_ids,
                                    foods_df, nutrients_df, dri_df, user_info, user_foods_df=None):
    """
    PDF Deney 2: NSGA-II ve SPEA2 ayni parametrelerle karsilastirilir.
    Convergence curve verileri CSV'ye kaydedilir.
    """
    print("\n" + "#" * 60)
    print("# DENEY 2: ALGORITMA KARSILASTIRMASI")
    print("#" * 60)

    result = _run_single_comparison(
        breakfast_ids, lunch_ids,
        foods_df, nutrients_df, dri_df, user_info,
        label="Algoritma Karsilastirmasi", user_foods_df=user_foods_df
    )

    # Convergence CSV kaydet
    for run in range(NUM_RUNS):
        save_convergence_to_csv(result["nsga2_hv_histories"][run],
                                f"convergence_nsga2_run{run+1}.csv", "NSGA-II")
        save_convergence_to_csv(result["spea2_hv_histories"][run],
                                f"convergence_spea2_run{run+1}.csv", "SPEA2")


    # Pareto front CSV
    for run in range(NUM_RUNS):

        save_pareto_to_csv(
            result["nsga2_results"][run],
            f"algo_nsga2_run{run+1}.csv",
            "nsga2"
       )

        save_sample_menu_to_csv(
            result["nsga2_results"][run],
            f"algo_nsga2_menu_run{run+1}.csv",
            "algo_nsga2"
        )
        save_sample_menu_to_json(
            result["nsga2_results"][run],
            f"algo_nsga2_menu_run{run+1}.json",
            "algo_nsga2",
            foods_df, nutrients_df, dri_df, user_info
        )

        save_pareto_to_csv(
            result["spea2_results"][run],
            f"algo_spea2_run{run+1}.csv",
            "spea2"
        )

        save_sample_menu_to_csv(
            result["spea2_results"][run],
            f"algo_spea2_menu_run{run+1}.csv",
            "algo_spea2"
        )
        save_sample_menu_to_json(
            result["spea2_results"][run],
            f"algo_spea2_menu_run{run+1}.json",
            "algo_spea2",
            foods_df, nutrients_df, dri_df, user_info
        )

    return result


# --- DENEY 3: Diversity etkisi ---

def experiment_diversity_impact(breakfast_ids, lunch_ids,
                                foods_df, nutrients_df, dri_df, user_info, user_foods_df=None):
    """
    PDF Deney 3: Diversity mekanizmasi acik/kapali karsilastirmasi.
    Bu fonksiyon evaluate fonksiyonundaki diversity flag'e gore calisir.
    """
    print("\n" + "#" * 60)
    print("# DENEY 3: DIVERSITY ETKISI")
    print("#" * 60)

    print("\n--- Diversity KAPALI ---")
    result_off = _run_single_comparison(
        breakfast_ids, lunch_ids,
        foods_df, nutrients_df, dri_df, user_info,
        label="Diversity KAPALI", diversity_enabled=False, user_foods_df=user_foods_df
    )

    print("\n--- Diversity ACIK ---")
    result_on = _run_single_comparison(
        breakfast_ids, lunch_ids,
        foods_df, nutrients_df, dri_df, user_info,
        label="Diversity ACIK", diversity_enabled=True, user_foods_df=user_foods_df
    )


    # CSV kaydet
    for run in range(NUM_RUNS):

        save_pareto_to_csv(
            result_off["nsga2_results"][run],
            f"div_off_nsga2_run{run+1}.csv",
            "diversity_off_nsga2"
        )

        save_sample_menu_to_csv(
            result_off["nsga2_results"][run],
            f"div_off_nsga2_menu_run{run+1}.csv",
            "diversity_off_nsga2"
        )
        save_sample_menu_to_json(
            result_off["nsga2_results"][run],
            f"div_off_nsga2_menu_run{run+1}.json",
            "diversity_off_nsga2",
            foods_df, nutrients_df, dri_df, user_info
        )

        save_pareto_to_csv(
            result_on["nsga2_results"][run],
            f"div_on_nsga2_run{run+1}.csv",
            "diversity_on_nsga2"
        )

        save_sample_menu_to_csv(
            result_on["nsga2_results"][run],
            f"div_on_nsga2_menu_run{run+1}.csv",
            "diversity_on_nsga2"
        )
        save_sample_menu_to_json(
            result_on["nsga2_results"][run],
            f"div_on_nsga2_menu_run{run+1}.json",
            "diversity_on_nsga2",
            foods_df, nutrients_df, dri_df, user_info
        )

    return result_off, result_on


# --- TUM DENEYLER ---

def run_all_experiments(breakfast_ids, lunch_ids,
                        foods_df, nutrients_df, dri_df,
                        user1_info, user2_info, user_foods_df=None):
    """Tum deneyleri sirayla calistirir."""
    print("\n" + "=" * 60)
    print("  TUM DENEYLER BASLIYOR")
    print("=" * 60)

    # Deney 1: User karsilastirmasi
    r1_u1, r1_u2 = experiment_user_comparison(
        breakfast_ids, lunch_ids,
        foods_df, nutrients_df, dri_df,
        user1_info, user2_info, user_foods_df
    )

    # Deney 2: Algoritma karsilastirmasi (User 1 ile)
    r2 = experiment_algorithm_comparison(
        breakfast_ids, lunch_ids,
        foods_df, nutrients_df, dri_df, user1_info, user_foods_df
    )

    # Deney 3: Diversity etkisi (User 1 ile)
    r3_off, r3_on = experiment_diversity_impact(
        breakfast_ids, lunch_ids,
        foods_df, nutrients_df, dri_df, user1_info, user_foods_df
    )
    print("\nGrafikler olusturuluyor...")

        # Algorithm comparison
    plot_algorithm_comparison(
    r2["nsga2_hv_histories"][0],
    r2["spea2_hv_histories"][0]
    )

    # Convergence
    plot_convergence(
        r2["nsga2_hv_histories"][0],
        "NSGA-II"
    )

    # Pareto front
    plot_pareto_front(
        r2["nsga2_results"][0],
        "NSGA-II"
    )

    # 3D Pareto
    plot_3d_pareto(
        r2["nsga2_results"][0],
        "NSGA-II"
    )

    # User comparison
    plot_user_comparison(
        r1_u1["nsga2_results"][0],
        r1_u2["nsga2_results"][0]
    )

    print("\n" + "=" * 60)
    print("  TUM DENEYLER TAMAMLANDI")
    print(f"  Sonuclar 'results/' klasorune kaydedildi.")
    print("=" * 60)

    return {
        "user_comparison": (r1_u1, r1_u2),
        "algorithm_comparison": r2,
        "diversity_impact": (r3_off, r3_on)
    }

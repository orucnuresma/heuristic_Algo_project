# ============================================================
# GOREV 3: DECODE + CONSTRAINT / PENALTY
# ============================================================
# Bu dosya Gorev 3 sorumlulugu altindadir.
# Asagidaki iki fonksiyon nsga2.py'deki evaluate() tarafindan cagirilir.
# Fonksiyon isimleri ve parametreleri DEGISTIRILMEMELI.
#
# PDF kurallari:
#   - Kromozom: (breakfast_part, lunch_part) → her biri yemek ID permutasyonu
#   - Decode: soldan saga greedy, epsilon toleransli
#   - Kahvalti: Energy + Protein, gunluk DRI'nin %35'i
#   - Ogle+aksam: 5 nutrient, kahvaltidan kalan toplanir
#   - Epsilon: RUL_eff = RUL * 1.15, RLL_eff = RLL * 0.90
#   - Penalty: R = 0.7 * sum(viol_low) + 0.3 * sum(viol_high)
# ============================================================

NUTRIENT_IDS = [1, 2, 3, 4, 5]
BREAKFAST_IDS = [1, 2]

def decode_chromosome(individual, foods_df, nutrients_df, dri_df, user_info):
    """
    Kromozomu (genotype) menuye (phenotype) cevirir.
    Soldan saga greedy decode: her yemegi tentative ekle,
    epsilon*RUL asarsa atla, epsilon*RLL saglaninca dur.

    Parameters:
        individual: (breakfast_part, lunch_part) tuple
                    breakfast_part = 94 kahvaltilik yemek ID'sinin permutasyonu
                    lunch_part = 311 ogle+aksam yemek ID'sinin permutasyonu
        foods_df: foods tablosu (DataFrame) — id, cost, co2, preference, ...
        nutrients_df: food_nutrients tablosu (DataFrame) — foodId, nutrientId, quantity
        dri_df: dri tablosu (DataFrame) — nutrient_id, RLL, RUL, ...
        user_info: kullanici bilgileri (dict veya DataFrame row)
                   en azindan {"user_id": int, "age": int, "gender": str}

    Returns:
        selected_foods: list of int — menuye secilen yemek ID'leri
                        (kahvalti + ogle/aksam birlesik)

    Ornek donus:
        [12, 47, 3, 201, 88, 344]  (secilen 6 yemek)
    """
    # TODO: Gorev 3 — bu fonksiyonu implement et
    #
    # Adimlar:
    # 1. breakfast_part, lunch_part = individual
    # 2. DRI degerlerini dri_df'ten cek (kullaniciya gore)
    # 3. Epsilon toleranslari uygula:
    #    RUL_eff = RUL * 1.15
    #    RLL_eff = RLL * 0.90
    #    Kahvalti icin: RLL_b = RLL * 0.35, RUL_b = RUL * 0.35
    # 4. Kahvalti decode:
    #    - breakfast_part'i soldan saga tara
    #    - Her yemegi ekle, Energy veya Protein icin RUL_b * 1.15 asarsa → atla
    #    - Energy VE Protein icin RLL_b * 0.90 saglaninca → dur
    # 5. Ogle+aksam decode:
    #    - Kahvaltidan kalan nutrient toplamlariyla devam et
    #    - 5 nutrient icin ayni mantik (RUL_eff, RLL_eff)
    # 6. return kahvalti_secilen + ogle_aksam_secilen
    #
    breakfast_part, lunch_part = individual

    def get_limits():
        limits = {}
        for nutrient_id in NUTRIENT_IDS:
            row = dri_df[dri_df["nutrient_id"] == nutrient_id]
            if not row.empty:
                limits[nutrient_id] = {
                    "RLL": float(row.iloc[0]["RLL"]),
                    "RUL": float(row.iloc[0]["RUL"])
                }
        return limits
    
    def nutrient_totals(food_ids):
        selected = nutrients_df[nutrients_df["foodId"].isin(food_ids)]
        totals = selected.groupby("nutrientId")["quantity"].sum().to_dict()
    
        for nutrient_id in NUTRIENT_IDS:
            totals.setdefault(nutrient_id, 0.0)
    
        return totals
    
    limits = get_limits()
    
    selected_breakfast = []
    
    for food_id in breakfast_part:
        temp_foods = selected_breakfast + [food_id]
        totals = nutrient_totals(temp_foods)
    
        exceed = False
        for nutrient_id in BREAKFAST_IDS:
            rul_b = limits[nutrient_id]["RUL"] * 0.35
            rul_eff = rul_b * 1.15
    
            if totals[nutrient_id] > rul_eff:
                exceed = True
                break
    
        if not exceed:
            selected_breakfast.append(food_id)
    
        totals = nutrient_totals(selected_breakfast)
    
        breakfast_ok = True
        for nutrient_id in BREAKFAST_IDS:
            rll_b = limits[nutrient_id]["RLL"] * 0.35
            rll_eff = rll_b * 0.90
    
            if totals[nutrient_id] < rll_eff:
                breakfast_ok = False
                break
    
        if breakfast_ok:
            break
    
    selected_all = selected_breakfast[:]
    
    for food_id in lunch_part:
        temp_foods = selected_all + [food_id]
        totals = nutrient_totals(temp_foods)
    
        exceed = False
        for nutrient_id in NUTRIENT_IDS:
            rul_eff = limits[nutrient_id]["RUL"] * 1.15
    
            if totals[nutrient_id] > rul_eff:
                exceed = True
                break
    
        if not exceed:
            selected_all.append(food_id)
    
        totals = nutrient_totals(selected_all)
    
        all_ok = True
        for nutrient_id in NUTRIENT_IDS:
            rll_eff = limits[nutrient_id]["RLL"] * 0.90
    
            if totals[nutrient_id] < rll_eff:
                all_ok = False
                break
    
        if all_ok:
            break
    
    return selected_all


def calculate_penalty(selected_foods, foods_df, nutrients_df, dri_df, user_info):
    """
    Secilen menunun nutrient kisitlarini ne kadar ihlal ettigini hesaplar.

    PDF formulu:
        viol_low_j  = max(0, RLL_j - v_j) / (RUL_j - RLL_j)
        viol_high_j = max(0, v_j - RUL_j) / (RUL_j - RLL_j)
        R = 0.7 * sum(viol_low) + 0.3 * sum(viol_high)

    Parameters:
        selected_foods: list of int — menuye secilen yemek ID'leri
        foods_df: foods tablosu (DataFrame)
        nutrients_df: food_nutrients tablosu (DataFrame) — foodId, nutrientId, quantity
        dri_df: dri tablosu (DataFrame) — nutrient_id, RLL, RUL
        user_info: kullanici bilgileri

    Returns:
        R: float — penalty degeri (0.0 = hicbir ihlal yok)

    5 Nutrient kisiti:
        C1: Energy (kcal)
        C2: Protein (g)
        C3: Carbohydrate (g)
        C4: Fiber / Fiber_total_dietary (g)
        C5: Sodium / Na (mg)
    """
    # TODO: Gorev 3 — bu fonksiyonu implement et
    #
    # Adimlar:
    # 1. Secilen yemeklerin toplam nutrient degerlerini hesapla (v_j)
    #    nutrients_df'ten foodId ile filtrele, nutrientId bazinda topla
    # 2. DRI sinirlarini dri_df'ten cek (kullaniciya gore)
    # 3. Her nutrient j=1..5 icin:
    #    viol_low_j  = max(0, RLL_j - v_j) / (RUL_j - RLL_j)
    #    viol_high_j = max(0, v_j - RUL_j) / (RUL_j - RLL_j)
    # 4. R = 0.7 * sum(viol_low) + 0.3 * sum(viol_high)
    # 5. return R
    #
   
    selected = nutrients_df[nutrients_df["foodId"].isin(selected_foods)]
    totals = selected.groupby("nutrientId")["quantity"].sum().to_dict()
    
    total_low_violation = 0.0
    total_high_violation = 0.0
    
    for nutrient_id in NUTRIENT_IDS:
        row = dri_df[dri_df["nutrient_id"] == nutrient_id]
    
        if row.empty:
            continue
    
        rll = float(row.iloc[0]["RLL"])
        rul = float(row.iloc[0]["RUL"])
        value = float(totals.get(nutrient_id, 0.0))
    
        denominator = rul - rll
        if denominator <= 0:
            denominator = 1.0
    
        viol_low = max(0.0, rll - value) / denominator
        viol_high = max(0.0, value - rul) / denominator
    
        total_low_violation += viol_low
        total_high_violation += viol_high
    
    R = 0.7 * total_low_violation + 0.3 * total_high_violation
    
    return R

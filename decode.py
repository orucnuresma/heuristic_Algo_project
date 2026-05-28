# ============================================================
# GOREV 3: DECODE + CONSTRAINT / PENALTY (HATASIZ VE GERÇEKTEN HIZLI)
# ============================================================
import pandas as pd

# Veritabanındaki gerçek nutrient ID'leri
NUTRIENT_IDS = [5, 15, 8, 4, 17]
BREAKFAST_IDS = [5, 15]

# Vejetaryen için yasaklı yemek grupları
FORBIDDEN_GROUPS = [1, 2, 3]

# --- HIZ OPTİMİZASYONU İÇİN GLOBAL ÖNBELLEK (CACHE) ---
# Bunlar sadece 1 kere doldurulacak, her döngüde baştan hesaplanmayacak!
GLOBAL_USER_LIMITS = {}
GLOBAL_FOOD_MAP = {}
GLOBAL_GROUP_MAP = {}

def _filter_dri_for_user(dri_df, user_info):
    """
    dri tablosundan kullanıcının yaş ve cinsiyetine uyan satırları filtreler.
    """
    age = user_info.get("age", 25)
    gender = user_info.get("gender", "female").lower()

    filtered = dri_df[
        (dri_df["low_age"] <= age) &
        (dri_df["up_age"] >= age) &
        (dri_df["gender"].str.lower() == gender)
    ]

    if filtered.empty:
        filtered = dri_df[dri_df["gender"].str.lower() == gender]

    return filtered

def _build_cache(foods_df, nutrients_df, dri_df, user_info):
    """Veritabanını sadece ilk seferde hızlı okunabilir sözlüklere çevirir."""
    global GLOBAL_USER_LIMITS, GLOBAL_FOOD_MAP, GLOBAL_GROUP_MAP
    
    # Kullanıcı değişmediyse ve önbellek doluysa tekrar hesaplama
    user_key = f"{user_info.get('age')}_{user_info.get('gender')}"
    if user_key in GLOBAL_USER_LIMITS and GLOBAL_FOOD_MAP: 
        return

    # DRI limitlerini filtrele ve sözlüğe at
    user_dri = _filter_dri_for_user(dri_df, user_info)
    limits = {}
    for nutrient_id in NUTRIENT_IDS:
        row = user_dri[user_dri["nutrient_id"] == nutrient_id]
        if not row.empty:
            limits[nutrient_id] = {
                "RLL": float(row.iloc[0]["RLL"]),
                "RUL": float(row.iloc[0]["RUL"])
            }
        else:
            limits[nutrient_id] = {"RLL": 0.0, "RUL": 1e9}
    GLOBAL_USER_LIMITS[user_key] = limits

    # Besin değerlerini sözlüğe at
    GLOBAL_FOOD_MAP.clear()
    for _, r in nutrients_df.iterrows():
        f_id = int(r["foodId"])
        n_id = int(r["nutrientId"])
        qty = float(r["quantity"])
        if f_id not in GLOBAL_FOOD_MAP:
            GLOBAL_FOOD_MAP[f_id] = {nid: 0.0 for nid in NUTRIENT_IDS}
        if n_id in NUTRIENT_IDS:
            GLOBAL_FOOD_MAP[f_id][n_id] = qty

    # Yemek gruplarını sözlüğe at
    group_col = "foodGroupId" if "foodGroupId" in foods_df.columns else "food_group"
    GLOBAL_GROUP_MAP = dict(zip(foods_df["id"], foods_df[group_col]))


def decode_chromosome(individual, foods_df, nutrients_df, dri_df, user_info):
    """Kromozomu menüye çevirir."""
    
    # 1 kere çalışır, sözlükleri doldurur. Sonraki döngülerde es geçer.
    _build_cache(foods_df, nutrients_df, dri_df, user_info)
    
    user_key = f"{user_info.get('age')}_{user_info.get('gender')}"
    limits = GLOBAL_USER_LIMITS[user_key]

    breakfast_part, lunch_part = individual
    is_vegetarian = user_info.get("is_vegetarian", False)

    # --- KAHVALTI DECODE ---
    selected_breakfast = []
    current_breakfast_totals = {nid: 0.0 for nid in NUTRIENT_IDS}
    
    for food_id in breakfast_part:
        if is_vegetarian:
            if GLOBAL_GROUP_MAP.get(food_id, None) in FORBIDDEN_GROUPS:
                continue
        
        nutrients = GLOBAL_FOOD_MAP.get(food_id, {nid: 0.0 for nid in NUTRIENT_IDS})
        
        exceed = False
        for nutrient_id in BREAKFAST_IDS:
            rul_eff = limits[nutrient_id]["RUL"] * 0.35 * 1.15
            if current_breakfast_totals[nutrient_id] + nutrients[nutrient_id] > rul_eff:
                exceed = True
                break
                
        if not exceed:
            selected_breakfast.append(food_id)
            for nutrient_id in NUTRIENT_IDS:
                current_breakfast_totals[nutrient_id] += nutrients[nutrient_id]

            breakfast_ok = all(
                current_breakfast_totals[nid] >= limits[nid]["RLL"] * 0.35 * 0.90
                for nid in BREAKFAST_IDS
            )
            if breakfast_ok:
                break 

    # --- ÖĞLE + AKSAM DECODE ---
    selected_all = selected_breakfast[:]
    current_all_totals = current_breakfast_totals.copy()
    
    for food_id in lunch_part:
        if is_vegetarian:
            if GLOBAL_GROUP_MAP.get(food_id, None) in FORBIDDEN_GROUPS:
                continue

        nutrients = GLOBAL_FOOD_MAP.get(food_id, {nid: 0.0 for nid in NUTRIENT_IDS})
        
        exceed = False
        for nutrient_id in NUTRIENT_IDS:
            rul_eff = limits[nutrient_id]["RUL"] * 1.15
            if current_all_totals[nutrient_id] + nutrients[nutrient_id] > rul_eff:
                exceed = True
                break
                
        if not exceed:
            selected_all.append(food_id)
            for nutrient_id in NUTRIENT_IDS:
                current_all_totals[nutrient_id] += nutrients[nutrient_id]
            
            all_ok = all(
                current_all_totals[nid] >= limits[nid]["RLL"] * 0.90
                for nid in NUTRIENT_IDS
            )
            if all_ok:
                break 
                
    return selected_all


def calculate_penalty(selected_foods, foods_df, nutrients_df, dri_df, user_info, diversity_on=False):
    """
    Seçilen menünün nutrient kısıtlarını ne kadar ihlal ettiğini hesaplar.
    """
    _build_cache(foods_df, nutrients_df, dri_df, user_info)
    user_key = f"{user_info.get('age')}_{user_info.get('gender')}"
    limits = GLOBAL_USER_LIMITS[user_key]

    if not selected_foods:
        return 999.0 

    # Penalty kısmında da Pandas yerine hızlı sözlüğümüzü kullanıyoruz!
    totals = {nid: 0.0 for nid in NUTRIENT_IDS}
    for food_id in selected_foods:
        nutrients = GLOBAL_FOOD_MAP.get(food_id, {nid: 0.0 for nid in NUTRIENT_IDS})
        for nid in NUTRIENT_IDS:
            totals[nid] += nutrients[nid]
    
    total_low_violation = 0.0
    total_high_violation = 0.0
    
    for nutrient_id in NUTRIENT_IDS:
        rll = limits[nutrient_id]["RLL"]
        rul = limits[nutrient_id]["RUL"]
        value = totals.get(nutrient_id, 0.0)
    
        denominator = rul - rll
        if denominator <= 0:
            denominator = 1.0
    
        viol_low = max(0.0, rll - value) / denominator
        viol_high = max(0.0, value - rul) / denominator
    
        total_low_violation += viol_low
        total_high_violation += viol_high
    
    R = 0.7 * total_low_violation + 0.3 * total_high_violation
    
    # --- ÇEŞİTLİLİK (DIVERSITY) CEZASI ---
    if diversity_on:
        unique_groups = set()
        for food_id in selected_foods:
            group = GLOBAL_GROUP_MAP.get(food_id)
            if group is not None:
                unique_groups.add(group)
        
        HEDEF_GRUP_SAYISI = 4
        if len(unique_groups) < HEDEF_GRUP_SAYISI:
            diversity_penalty = (HEDEF_GRUP_SAYISI - len(unique_groups)) * 1.5
            R += diversity_penalty
    
    return R

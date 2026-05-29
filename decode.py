import pandas as pd

# --- VERİ TABANINDAN DOĞRULANAN ID'LER ---
# nutrients tablosuna göre: 5=Energy, 15=Protein, 8=Carbohydrate, 4=Fiber, 17=Sodium
NUTRIENT_IDS = [5, 15, 8, 4, 17]  # Energy, Protein, Carbohydrate, Fiber, Sodium

# Kahvaltıda sadece Energy (5) ve Protein (15) kontrol edilir
BREAKFAST_IDS = [5, 15]

# food_group tablosuna göre doğrulanmış et/tavuk/balık grupları:
# 2=Chicken Products, 3=Meat Products, 15=Chicken and Turkey based dishes,
# 23=Fish, 28=Meat based dishes
MEAT_GROUP_IDS = [2, 3, 15, 23, 28]

HUGE_PENALTY = 1000000.0  # Sert kısıt ihlalleri için devasa ceza puanı

GLOBAL_USER_LIMITS = {}
GLOBAL_FOOD_MAP = {}
GLOBAL_GROUP_MAP = {}
GLOBAL_PREF_MAP = {}


def _get_col(df, possible_names):
    for col in possible_names:
        if col in df.columns:
            return col
    return None


def _filter_dri_for_user(dri_df, user_info):
    age = user_info.get("age", 25)
    gender = str(user_info.get("gender", "female")).lower()
    filtered = dri_df[
        (dri_df["low_age"] <= age) &
        (dri_df["up_age"] >= age) &
        (dri_df["gender"].str.lower() == gender)
    ]
    if filtered.empty:
        filtered = dri_df[dri_df["gender"].str.lower() == gender]
    return filtered


def get_preference_col(user_info):
    user_id = user_info.get("user_id", 1)
    if user_id == 1:
        return "preference"
    elif user_id == 2:
        return "preference2"
    return "preference"


def detect_vegetarian_from_preferences(foods_df, preference_col):
    group_col = _get_col(foods_df, ["foodGroupId", "food_group"])
    pref_col = _get_col(foods_df, [preference_col, preference_col.capitalize(), "Preference", "Preference2"])
    if group_col is None or pref_col is None:
        return False
    meat_foods = foods_df[foods_df[group_col].isin(MEAT_GROUP_IDS)]
    if meat_foods.empty:
        return False
    return (meat_foods[pref_col] == -1).any()


def _build_cache(foods_df, nutrients_df, dri_df, user_info, user_foods_df=None):
    """
    Kullanıcıya özel tercihleri ve veritabanı şemasını hatasız hafızaya alan dinamik cache.
    """
    global GLOBAL_USER_LIMITS, GLOBAL_FOOD_MAP, GLOBAL_GROUP_MAP, GLOBAL_PREF_MAP
    user_id = user_info.get("user_id", 1)
    user_key = f"{user_info.get('age')}_{user_info.get('gender')}"

    # 1. DRI Limitleri Cache
    if user_key not in GLOBAL_USER_LIMITS:
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

    # 2. Besin İçerikleri Cache
    if not GLOBAL_FOOD_MAP:
        val_col = _get_col(nutrients_df, ["quantity", "value", "Value"])
        for _, r in nutrients_df.iterrows():
            food_id = int(r["foodId"])
            nutrient_id = int(r["nutrientId"])
            quantity_val = float(r[val_col])
            if food_id not in GLOBAL_FOOD_MAP:
                GLOBAL_FOOD_MAP[food_id] = {nid: 0.0 for nid in NUTRIENT_IDS}
            if nutrient_id in NUTRIENT_IDS:
                GLOBAL_FOOD_MAP[food_id][nutrient_id] = quantity_val

    # 3. Yiyecek Grubu Haritası
    if not GLOBAL_GROUP_MAP:
        group_col = _get_col(foods_df, ["foodGroupId", "food_group"])
        GLOBAL_GROUP_MAP = dict(zip(foods_df["id"], foods_df[group_col]))

    # 4. Kişiye Özel Tercih Haritası
    # Öncelik 1: user_info["preferences"] (main.py'den gelen kullanıcı tercihleri)
    GLOBAL_PREF_MAP = {}
    user_prefs = user_info.get("preferences", {})
    if user_prefs:
        GLOBAL_PREF_MAP["active"] = user_prefs
    elif user_foods_df is not None and not user_foods_df.empty:
        # Öncelik 2: user_foods tablosu
        user_specific = user_foods_df[user_foods_df["userId"] == user_id]
        if not user_specific.empty:
            GLOBAL_PREF_MAP["active"] = dict(zip(user_specific["foodId"], user_specific["preference"]))

    if "active" not in GLOBAL_PREF_MAP:
        # Öncelik 3: foods tablosundaki preference/preference2 sütunu
        preference_col = get_preference_col(user_info)
        for col_name in [preference_col, preference_col.lower(), preference_col.capitalize()]:
            if col_name in foods_df.columns:
                GLOBAL_PREF_MAP["active"] = dict(zip(foods_df["id"], foods_df[col_name]))
                break


def _is_forbidden_food(food_id, user_info):
    is_vegetarian = user_info.get("is_vegetarian", False)
    food_group = GLOBAL_GROUP_MAP.get(food_id)
    if is_vegetarian and food_group in MEAT_GROUP_IDS:
        return True
    pref_value = GLOBAL_PREF_MAP.get("active", {}).get(food_id, 0)
    if pref_value == -1:
        return True
    return False


# ============================================================
# ANA DECODE MEKANİZMASI
# ============================================================

def decode_chromosome(individual, foods_df, nutrients_df, dri_df, user_info, user_foods_df=None):
    _build_cache(foods_df, nutrients_df, dri_df, user_info, user_foods_df)
    user_key = f"{user_info.get('age')}_{user_info.get('gender')}"
    limits = GLOBAL_USER_LIMITS[user_key]

    breakfast_part, lunch_part = individual
    selected_breakfast = []
    current_breakfast_totals = {nid: 0.0 for nid in NUTRIENT_IDS}

    # --- KAHVALTI DECODING ---
    # Tek grup kilidi kaldırıldı: kahvaltı birden fazla gruptan yiyecek içerebilir.
    for food_id in breakfast_part:
        if _is_forbidden_food(food_id, user_info):
            continue

        nutrients = GLOBAL_FOOD_MAP.get(food_id, {nid: 0.0 for nid in NUTRIENT_IDS})

        # Üst Sınır Kontrolü (%35 RUL * 1.15 tolerans)
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

            # Energy ve Protein %35 alt sınırını (%90 toleransla) ikisi birden sağlayınca dur
            breakfast_ok = all(
                current_breakfast_totals[nid] >= limits[nid]["RLL"] * 0.35 * 0.90
                for nid in BREAKFAST_IDS
            )
            if breakfast_ok:
                break

    # --- ÖĞLE + AKŞAM DECODING ---
    selected_all = selected_breakfast[:]
    current_all_totals = current_breakfast_totals.copy()

    for food_id in lunch_part:
        if _is_forbidden_food(food_id, user_info):
            continue

        nutrients = GLOBAL_FOOD_MAP.get(food_id, {nid: 0.0 for nid in NUTRIENT_IDS})

        # Günlük Toleranslı Üst Sınır Kontrolü (RUL * 1.15)
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

    return selected_all


# ============================================================
# CEZA (PENALTY) MOTORU
# ============================================================

def calculate_penalty(selected_foods, foods_df, nutrients_df, dri_df, user_info, user_foods_df=None, diversity_on=True):
    _build_cache(foods_df, nutrients_df, dri_df, user_info, user_foods_df)

    if not selected_foods:
        return HUGE_PENALTY

    # Yasaklı ve vejetaryen kontrolleri — -1 puanlı veya et grubu (vejetaryen için)
    for food_id in selected_foods:
        food_group = GLOBAL_GROUP_MAP.get(food_id)
        pref_value = GLOBAL_PREF_MAP.get("active", {}).get(food_id, 0)
        if pref_value == -1 or (user_info.get("is_vegetarian", False) and food_group in MEAT_GROUP_IDS):
            return HUGE_PENALTY

    user_key = f"{user_info.get('age')}_{user_info.get('gender')}"
    limits = GLOBAL_USER_LIMITS[user_key]

    totals = {nid: 0.0 for nid in NUTRIENT_IDS}
    for food_id in selected_foods:
        nutrients = GLOBAL_FOOD_MAP.get(food_id, {nid: 0.0 for nid in NUTRIENT_IDS})
        for nid in NUTRIENT_IDS:
            totals[nid] += nutrients[nid]

    total_low_violation = 0.0
    total_high_violation = 0.0

    # Ödeve uygun asimetrik ceza formülü (0.7 alt ihlal / 0.3 üst ihlal)
    # Payda: (RUL - RLL) — ödev formülüne göre normalize
    for nutrient_id in NUTRIENT_IDS:
        rll = limits[nutrient_id]["RLL"]
        rul = limits[nutrient_id]["RUL"]
        value = totals.get(nutrient_id, 0.0)
        denom = (rul - rll) if (rul - rll) > 0 else 1.0

        if value < rll:
            viol_low = (rll - value) / denom
            total_low_violation += viol_low
        if value > rul:
            viol_high = (value - rul) / denom
            total_high_violation += viol_high

    R = (0.7 * total_low_violation) + (0.3 * total_high_violation)
    penalty = R

    # Çeşitlilik cezası: menüdeki farklı yemek grubu sayısı hedefin altındaysa ceza
    if diversity_on:
        all_groups = set(
            GLOBAL_GROUP_MAP.get(fid)
            for fid in selected_foods
            if GLOBAL_GROUP_MAP.get(fid) is not None
        )
        HEDEF_GRUP_SAYISI = 5
        if len(all_groups) < HEDEF_GRUP_SAYISI:
            penalty += (HEDEF_GRUP_SAYISI - len(all_groups)) * 2.0

    return penalty

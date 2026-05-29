import pandas as pd

# --- VERİ TABANINDAN DOĞRULANAN ID'LER ---
NUTRIENT_IDS = [5, 15, 8, 4, 17]  # Enerji, Protein, Kalsiyum, Demir vb.
BREAKFAST_IDS = [5, 15]           # Kahvaltıda sadece Enerji (5) ve Protein (15) kontrol edilir

# diet.sql tablosuna göre et, tavuk, balık ve etli yemek grupları
MEAT_GROUP_IDS = [3, 4, 28]       

HUGE_PENALTY = 1000000.0          # Çözümü doğrudan elemek için devasa ceza puanı

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
    group_col = _get_col(foods_df, ["foodGroupId", "food_group", "foodGroupID", "food_group_id"])
    pref_col = _get_col(foods_df, [preference_col, preference_col.capitalize(), "Preference", "Preference2"])

    if group_col is None or pref_col is None:
        return False

    meat_foods = foods_df[foods_df[group_col].isin(MEAT_GROUP_IDS)]
    if meat_foods.empty:
        return False

    # Eğer et yemeklerine -1 puan verilmişse bu kullanıcı VEJETARYENDİR
    return (meat_foods[pref_col] == -1).any()


def _build_cache(foods_df, nutrients_df, dri_df, user_info):
    global GLOBAL_USER_LIMITS, GLOBAL_FOOD_MAP, GLOBAL_GROUP_MAP, GLOBAL_PREF_MAP

    user_key = f"{user_info.get('age')}_{user_info.get('gender')}"

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

    if not GLOBAL_FOOD_MAP:
        for _, r in nutrients_df.iterrows():
            food_id = int(r["foodId"])
            nutrient_id = int(r["nutrientId"])
            quantity = float(r["quantity"])

            if food_id not in GLOBAL_FOOD_MAP:
                GLOBAL_FOOD_MAP[food_id] = {nid: 0.0 for nid in NUTRIENT_IDS}

            if nutrient_id in NUTRIENT_IDS:
                GLOBAL_FOOD_MAP[food_id][nutrient_id] = quantity

    if not GLOBAL_GROUP_MAP:
        group_col = _get_col(foods_df, ["foodGroupId", "food_group", "foodGroupID", "food_group_id"])
        GLOBAL_GROUP_MAP = dict(zip(foods_df["id"], foods_df[group_col]))

    if not GLOBAL_PREF_MAP:
        for col_name in ["preference", "preference2", "Preference", "Preference2"]:
            if col_name in foods_df.columns:
                GLOBAL_PREF_MAP[col_name.lower()] = dict(zip(foods_df["id"], foods_df[col_name]))


def _is_forbidden_food(food_id, user_info, preference_col):
    is_vegetarian = user_info.get("is_vegetarian", False)
    food_group = GLOBAL_GROUP_MAP.get(food_id)

    # Kural 1: Vejetaryen kullanıcı et grubu yiyemez
    if is_vegetarian and food_group in MEAT_GROUP_IDS:
        return True

    # Kural 2: Puanı -1 olan yiyecek asla menüye giremez
    pref_value = GLOBAL_PREF_MAP.get(preference_col.lower(), {}).get(food_id, 0)
    if pref_value == -1:
        return True

    return False


def decode_chromosome(individual, foods_df, nutrients_df, dri_df, user_info):
    """
    İki parçalı kromozomu çözer (Knapsack Seçim Filtrelemesi)
    individual[0] -> Kahvaltı genleri listesi
    individual[1] -> Öğle + Akşam genleri listesi
    """
    _build_cache(foods_df, nutrients_df, dri_df, user_info)
    preference_col = get_preference_col(user_info)

    if "is_vegetarian" not in user_info:
        user_info["is_vegetarian"] = detect_vegetarian_from_preferences(foods_df, preference_col)

    user_key = f"{user_info.get('age')}_{user_info.get('gender')}"
    limits = GLOBAL_USER_LIMITS[user_key]

    breakfast_part, lunch_part = individual

    selected_breakfast = []
    current_breakfast_totals = {nid: 0.0 for nid in NUTRIENT_IDS}

    # --- KAHVALTI PARÇASI DECODING ---
    for food_id in breakfast_part:
        if _is_forbidden_food(food_id, user_info, preference_col):
            continue

        nutrients = GLOBAL_FOOD_MAP.get(food_id, {nid: 0.0 for nid in NUTRIENT_IDS})
        
        # Toleranslı Kahvaltı Üst Sınır Kontrolü (%35 RUL * 1.15)
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

    # --- ÖĞLE + AKŞAM PARÇASI DECODING ---
    selected_all = selected_breakfast[:]
    current_all_totals = current_breakfast_totals.copy()

    for food_id in lunch_part:
        if _is_forbidden_food(food_id, user_info, preference_col):
            continue

        nutrients = GLOBAL_FOOD_MAP.get(food_id, {nid: 0.0 for nid in NUTRIENT_IDS})

        # Tüm Günlük Toleranslı Üst Sınır Kontrolü (RUL * 1.15)
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


def calculate_penalty(selected_foods, foods_df, nutrients_df, dri_df, user_info, diversity_on=True):
    """
    Hocanın dökümanındaki asimetrik (0.7 / 0.3) ceza fonksiyonunu hesaplar.
    """
    _build_cache(foods_df, nutrients_df, dri_df, user_info)
    preference_col = get_preference_col(user_info)

    if "is_vegetarian" not in user_info:
        user_info["is_vegetarian"] = detect_vegetarian_from_preferences(foods_df, preference_col)

    # EN BAŞTA KRİTİK KONTROL: Eğer boş menüyse veya yasaklı yiyecek sızdıysa doğrudan elensin
    if not selected_foods:
        return HUGE_PENALTY

    for food_id in selected_foods:
        food_group = GLOBAL_GROUP_MAP.get(food_id)
        pref_value = GLOBAL_PREF_MAP.get(preference_col.lower(), {}).get(food_id, 0)
        
        if pref_value == -1 or (user_info.get("is_vegetarian", False) and food_group in MEAT_GROUP_IDS):
            return HUGE_PENALTY  # Direkt maksimum cezayı döndür, algoritma bu çözümü ezsin.

    user_key = f"{user_info.get('age')}_{user_info.get('gender')}"
    limits = GLOBAL_USER_LIMITS[user_key]

    # Toplam besin değerlerini hesapla
    totals = {nid: 0.0 for nid in NUTRIENT_IDS}
    for food_id in selected_foods:
        nutrients = GLOBAL_FOOD_MAP.get(food_id, {nid: 0.0 for nid in NUTRIENT_IDS})
        for nid in NUTRIENT_IDS:
            totals[nid] += nutrients[nid]

    total_low_violation = 0.0
    total_high_violation = 0.0

    # Hocanın dökümanındaki formüle göre normalizasyon ve ceza hesabı
    for nutrient_id in NUTRIENT_IDS:
        rll = limits[nutrient_id]["RLL"]
        rul = limits[nutrient_id]["RUL"]
        value = totals.get(nutrient_id, 0.0)

        # Alt sınır ihlali (RLL altı) -> RLL ile normalize edilir
        if value < rll:
            viol_low = (rll - value) / (rll if rll > 0 else 1.0)
            total_low_violation += viol_low
        
        # Üst sınır ihlali (RUL üstü) -> RUL ile normalize edilir
        if value > rul:
            viol_high = (value - rul) / (rul if rul > 0 else 1.0)
            total_high_violation += viol_high

    # Asimetrik ceza formülü: R = 0.7 * Yetersiz_Beslenme + 0.3 * Aşırı_Beslenme
    R = (0.7 * total_low_violation) + (0.3 * total_high_violation)
    penalty = R

    # --- ÇEŞİTLİLİK (DIVERSITY) MEKANİZMASI (Döküman Madde 6) ---
    if diversity_on:
        unique_groups = set()
        for food_id in selected_foods:
            group = GLOBAL_GROUP_MAP.get(food_id)
            if group is not None:
                unique_groups.add(group)

        HEDEF_GRUP_SAYISI = 5  # Dökümanda istenen 4-6 ideal çeşitlilik aralığı
        if len(unique_groups) < HEDEF_GRUP_SAYISI:
            # Çeşitlilik azaldıkça doğrusal ceza ekle
            penalty += (HEDEF_GRUP_SAYISI - len(unique_groups)) * 2.0

    return penalty

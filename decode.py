import pandas as pd

NUTRIENT_IDS = [5, 15, 8, 4, 17]
BREAKFAST_IDS = [5, 15]

MEAT_GROUP_IDS = [1, 2, 3]   # Et/tavuk/balık gruplarıysa böyle kalsın
HUGE_PENALTY = 10000

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
    group_col = _get_col(foods_df, ["foodGroupId", "food_group", "foodGroupID"])
    pref_col = _get_col(foods_df, [preference_col, preference_col.capitalize(), "Preference", "Preference2"])

    if group_col is None or pref_col is None:
        return False

    meat_foods = foods_df[foods_df[group_col].isin(MEAT_GROUP_IDS)]

    if meat_foods.empty:
        return False

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
        group_col = _get_col(foods_df, ["foodGroupId", "food_group", "foodGroupID"])
        GLOBAL_GROUP_MAP = dict(zip(foods_df["id"], foods_df[group_col]))

    if not GLOBAL_PREF_MAP:
        if "preference" in foods_df.columns:
            GLOBAL_PREF_MAP["preference"] = dict(zip(foods_df["id"], foods_df["preference"]))

        if "preference2" in foods_df.columns:
            GLOBAL_PREF_MAP["preference2"] = dict(zip(foods_df["id"], foods_df["preference2"]))

        if "Preference" in foods_df.columns:
            GLOBAL_PREF_MAP["preference"] = dict(zip(foods_df["id"], foods_df["Preference"]))

        if "Preference2" in foods_df.columns:
            GLOBAL_PREF_MAP["preference2"] = dict(zip(foods_df["id"], foods_df["Preference2"]))


def _is_forbidden_food(food_id, user_info, preference_col):
    is_vegetarian = user_info.get("is_vegetarian", False)

    food_group = GLOBAL_GROUP_MAP.get(food_id)

    if is_vegetarian and food_group in MEAT_GROUP_IDS:
        return True

    pref_value = GLOBAL_PREF_MAP.get(preference_col, {}).get(food_id, 0)

    if pref_value == -1:
        return True

    return False


def decode_chromosome(individual, foods_df, nutrients_df, dri_df, user_info):
    """
    individual[0] -> breakfast
    individual[1] -> lunch + dinner
    """

    _build_cache(foods_df, nutrients_df, dri_df, user_info)

    preference_col = get_preference_col(user_info)

    if "is_vegetarian" not in user_info:
        user_info["is_vegetarian"] = detect_vegetarian_from_preferences(
            foods_df,
            preference_col
        )

    user_key = f"{user_info.get('age')}_{user_info.get('gender')}"
    limits = GLOBAL_USER_LIMITS[user_key]

    breakfast_part, lunch_part = individual

    selected_breakfast = []
    current_breakfast_totals = {nid: 0.0 for nid in NUTRIENT_IDS}

    for food_id in breakfast_part:

        if _is_forbidden_food(food_id, user_info, preference_col):
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

    selected_all = selected_breakfast[:]
    current_all_totals = current_breakfast_totals.copy()

    for food_id in lunch_part:

        if _is_forbidden_food(food_id, user_info, preference_col):
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
    _build_cache(foods_df, nutrients_df, dri_df, user_info)

    preference_col = get_preference_col(user_info)

    if "is_vegetarian" not in user_info:
        user_info["is_vegetarian"] = detect_vegetarian_from_preferences(
            foods_df,
            preference_col
        )

    user_key = f"{user_info.get('age')}_{user_info.get('gender')}"
    limits = GLOBAL_USER_LIMITS[user_key]

    if not selected_foods:
        return HUGE_PENALTY

    totals = {nid: 0.0 for nid in NUTRIENT_IDS}
    penalty = 0.0

    for food_id in selected_foods:
        food_group = GLOBAL_GROUP_MAP.get(food_id)
        pref_value = GLOBAL_PREF_MAP.get(preference_col, {}).get(food_id, 0)

        if pref_value == -1:
            penalty += HUGE_PENALTY

        if user_info.get("is_vegetarian", False) and food_group in MEAT_GROUP_IDS:
            penalty += HUGE_PENALTY

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
    penalty += R

    if diversity_on:
        unique_groups = set()

        for food_id in selected_foods:
            group = GLOBAL_GROUP_MAP.get(food_id)

            if group is not None:
                unique_groups.add(group)

        HEDEF_GRUP_SAYISI = 4

        if len(unique_groups) < HEDEF_GRUP_SAYISI:
            penalty += (HEDEF_GRUP_SAYISI - len(unique_groups)) * 1.5

    return penalty

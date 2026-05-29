from database.data_loader import (load_foods, load_food_nutrients, load_dri,
                                   load_food_groups, load_users, load_user_foods)
from experiment import run_all_experiments
from decode import MEAT_GROUP_IDS

# ============================================================
# KAHVALTI / OGLE+AKSAM YEMEK GRUBU AYIRIMI
# ============================================================
# Bu ID'ler food_group tablosundaki grup ID'leridir.
# Veritabanindaki gruplara gore ayarlayiniz.
# Bazi gruplar hem kahvaltida hem ogle+aksamda olabilir (duplicated).
#
# NOT: Asagidaki ID'ler veritabaninizdaki food_group tablosuna
#      gore guncellenmeli. Kod ilk calistiginda mevcut gruplari yazdirir.
BREAKFAST_GROUP_IDS = None   # None ise otomatik tespit edilir
LUNCH_DINNER_GROUP_IDS = None


def detect_vegetarian_from_preferences(preferences, foods_df):
    """
    Et bazli yemeklere verilen puanlara bakarak vejetaryen tespiti yapar.
    Eger et yemeklerinin cogunlugu -1 ise, kullanici vejetaryendir.
    """
    group_col = "foodGroupId" if "foodGroupId" in foods_df.columns else "food_group"
    meat_food_ids = foods_df[foods_df[group_col].isin(MEAT_GROUP_IDS)]['id'].tolist()
    meat_ratings = [preferences.get(int(fid)) for fid in meat_food_ids if int(fid) in preferences]

    if meat_ratings:
        negative_count = sum(1 for r in meat_ratings if r == -1)
        return negative_count > len(meat_ratings) * 0.5
    return False


def get_preferences_for_user(user_id, user_foods_df, foods_df):
    """
    Kullanici icin tercih sozlugu olusturur.
    Once user_foods tablosuna bakar, yoksa None dondurur (fallback icin).
    """
    user_prefs = user_foods_df[user_foods_df['userId'] == user_id]
    if not user_prefs.empty:
        return dict(zip(user_prefs['foodId'].astype(int), user_prefs['preference'].astype(float)))
    return None


def build_user_info(user_row, preferences, foods_df):
    """Kullanici bilgilerini ve tercihlerini birlestirip user_info olusturur."""
    is_veg = detect_vegetarian_from_preferences(preferences, foods_df)
    return {
        "user_id": int(user_row["id"]),
        "age": int(user_row["age"]),
        "gender": str(user_row["gender"]),
        "is_vegetarian": is_veg,
        "preferences": preferences
    }


def determine_food_group_split(foods_df, food_groups_df):
    """
    Food group'lara gore kahvalti ve ogle+aksam yemek ID'lerini belirler.
    BREAKFAST_GROUP_IDS ve LUNCH_DINNER_GROUP_IDS tanimlanmissa onlari kullanir.
    Tanimlanmamissa tum gruplari yazdirir ve varsayilan olarak
    et gruplari haric hepsini kahvaltiya, hepsini ogle+aksama atar.
    """
    global BREAKFAST_GROUP_IDS, LUNCH_DINNER_GROUP_IDS

    group_col = "foodGroupId" if "foodGroupId" in foods_df.columns else "food_group"

    # Mevcut gruplari yazdir
    print("\nYemek gruplari (food_group tablosu):")
    all_group_ids = []
    for _, g in food_groups_df.iterrows():
        gid = int(g['id'])
        all_group_ids.append(gid)
        count = len(foods_df[foods_df[group_col] == gid])
        print(f"  Grup {gid}: {g['name']} ({count} yemek)")

    if BREAKFAST_GROUP_IDS is not None and LUNCH_DINNER_GROUP_IDS is not None:
        # Kullanici tanimlamis, onlari kullan
        b_ids = foods_df[foods_df[group_col].isin(BREAKFAST_GROUP_IDS)]['id'].tolist()
        l_ids = foods_df[foods_df[group_col].isin(LUNCH_DINNER_GROUP_IDS)]['id'].tolist()
    else:
        # Otomatik ayirma: et gruplari sadece ogle+aksam, diger gruplar her ikisinde
        breakfast_groups = [g for g in all_group_ids if g not in MEAT_GROUP_IDS]
        lunch_groups = all_group_ids[:]  # Tum gruplar ogle+aksamda olabilir

        b_ids = foods_df[foods_df[group_col].isin(breakfast_groups)]['id'].tolist()
        l_ids = foods_df[foods_df[group_col].isin(lunch_groups)]['id'].tolist()

        print(f"\n  Otomatik ayrim: Kahvalti gruplari={breakfast_groups}, "
              f"Ogle+Aksam gruplari={lunch_groups}")

    return b_ids, l_ids


def main():
    print("1. Veritabanindan tablolar cekiliyor, lutfen bekle...")
    foods_df = load_foods()
    nutrients_df = load_food_nutrients()
    dri_df = load_dri()
    food_groups_df = load_food_groups()
    users_df = load_users()
    user_foods_df = load_user_foods()

    print(f"-> {len(foods_df)} yemek, {len(nutrients_df)} besin icerigi, "
          f"{len(dri_df)} DRI limiti, {len(food_groups_df)} yemek grubu, "
          f"{len(users_df)} kullanici yuklendi.\n")

    # ---- Kahvalti / Ogle+Aksam ayirimi (food group bazli) ----
    breakfast_ids, lunch_ids = determine_food_group_split(foods_df, food_groups_df)
    print(f"\nKahvalti: {len(breakfast_ids)} yemek, Ogle+Aksam: {len(lunch_ids)} yemek")

    # ---- Kullanici bilgileri (ilk 2 kullanici) ----
    if len(users_df) < 2:
        print("\nUYARI: Veritabaninda 2 kullanici bulunamadi, varsayilan degerler kullaniliyor.")
        user1_info = {"user_id": 1, "age": 23, "gender": "female",
                      "is_vegetarian": False, "preferences": {}}
        user2_info = {"user_id": 2, "age": 23, "gender": "female",
                      "is_vegetarian": True, "preferences": {}}
    else:
        user1_row = users_df.iloc[0]
        user2_row = users_df.iloc[1]

        # Kullanici tercihlerini user_foods tablosundan al
        prefs1 = get_preferences_for_user(int(user1_row['id']), user_foods_df, foods_df)
        prefs2 = get_preferences_for_user(int(user2_row['id']), user_foods_df, foods_df)

        # user_foods bossa, foods tablosundaki preference/preference2 sutunlarini kullan
        if prefs1 is None and prefs2 is None:
            print("\nuser_foods tablosu bos, foods.preference ve preference2 sutunlari kullaniliyor...")
            pref1_dict = dict(zip(foods_df['id'].astype(int), foods_df['preference'].astype(float)))
            pref2_dict = dict(zip(foods_df['id'].astype(int), foods_df['preference2'].astype(float)))

            # Hangi sutun hangi kullaniciya ait? Et bazli yemeklere bakarak tespit et
            veg1 = detect_vegetarian_from_preferences(pref1_dict, foods_df)
            veg2 = detect_vegetarian_from_preferences(pref2_dict, foods_df)

            if veg1 and not veg2:
                # preference sutunu vejetaryen → user2'ye ata, preference2 → user1'e
                prefs1 = pref2_dict
                prefs2 = pref1_dict
                print("  Tespit: preference=vejetaryen (User 2), preference2=normal (User 1)")
            elif veg2 and not veg1:
                prefs1 = pref1_dict
                prefs2 = pref2_dict
                print("  Tespit: preference=normal (User 1), preference2=vejetaryen (User 2)")
            else:
                # Ayirt edilemezse varsayilan siralama
                prefs1 = pref1_dict
                prefs2 = pref2_dict
                print("  Varsayilan: preference -> User 1, preference2 -> User 2")
        elif prefs1 is None:
            prefs1 = dict(zip(foods_df['id'].astype(int), foods_df['preference'].astype(float)))
        elif prefs2 is None:
            prefs2 = dict(zip(foods_df['id'].astype(int), foods_df['preference2'].astype(float)))

        user1_info = build_user_info(user1_row, prefs1, foods_df)
        user2_info = build_user_info(user2_row, prefs2, foods_df)

    # Kullanici bilgilerini yazdir
    forbidden1 = sum(1 for v in user1_info.get("preferences", {}).values() if v == -1)
    forbidden2 = sum(1 for v in user2_info.get("preferences", {}).values() if v == -1)
    print(f"\nUser 1: id={user1_info['user_id']}, vejetaryen={user1_info['is_vegetarian']}, "
          f"yasakli yemek={forbidden1}")
    print(f"User 2: id={user2_info['user_id']}, vejetaryen={user2_info['is_vegetarian']}, "
          f"yasakli yemek={forbidden2}")

    # ---- Deneyleri baslat ----
    print("\n2. Algoritmalar ve Deneyler Basliyor! (Bu islem biraz surebilir)...")

    run_all_experiments(
        breakfast_ids=breakfast_ids,
        lunch_ids=lunch_ids,
        foods_df=foods_df,
        nutrients_df=nutrients_df,
        dri_df=dri_df,
        user1_info=user1_info,
        user2_info=user2_info,
        user_foods_df=user_foods_df
    )

    print("\n PROJE BASARIYLA BITTI!")


if __name__ == "__main__":
    main()

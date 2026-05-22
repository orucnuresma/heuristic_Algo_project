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
    raise NotImplementedError("decode_chromosome henuz implement edilmedi")


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
    raise NotImplementedError("calculate_penalty henuz implement edilmedi")

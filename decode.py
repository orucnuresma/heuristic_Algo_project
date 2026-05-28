# ============================================================
# GOREV 3: DECODE + CONSTRAINT / PENALTY (HATASIZ VE HIZLI)
# ============================================================
import pandas as pd

NUTRIENT_IDS = [1, 2, 3, 4, 5]
BREAKFAST_IDS = [1, 2]

def decode_chromosome(individual, foods_df, nutrients_df, dri_df, user_info):
    """
    Kromozomu (genotype) menuye (phenotype) cevirir.
    Soldan saga greedy decode: her yemegi tentative ekle,
    epsilon*RUL asarsa atla.
    """
    breakfast_part, lunch_part = individual

    is_vegetarian = user_info.get("is_vegetarian", False)
    # Veritabanındaki food_group tablosuna göre et, kümes ve deniz ürünleri ID'leri
    FORBIDDEN_GROUPS = [1, 2, 3] 

    # Limitleri önceden çekelim
    limits = {}
    for nutrient_id in NUTRIENT_IDS:
        row = dri_df[dri_df["nutrient_id"] == nutrient_id]
        if not row.empty:
            limits[nutrient_id] = {
                "RLL": float(row.iloc[0]["RLL"]),
                "RUL": float(row.iloc[0]["RUL"])
            }

    # Hız Optimizasyonu: Her döngüde groupby yapmamak için yemeklerin besin değerlerini dict'e alıyoruz
    # nutrients_df içinde 'foodId', 'nutrientId' ve 'quantity' kolonları olduğu varsayılmıştır.
    food_nutrient_map = {}
    for _, r in nutrients_df.iterrows():
        f_id = int(r["foodId"])
        n_id = int(r["nutrientId"])
        qty = float(r["quantity"])
        if f_id not in food_nutrient_map:
            food_nutrient_map[f_id] = {nid: 0.0 for nid in NUTRIENT_IDS}
        if n_id in NUTRIENT_IDS:
            food_nutrient_map[f_id][n_id] = qty

    # Yemek grubu eşleşmesini hızlandırmak için dict yapıyoruz
    # sql yapınıza göre kolon ismi 'food_group_id' veya 'food_group' olabilir, kontrol ediniz.
    group_col = "food_group_id" if "food_group_id" in foods_df.columns else "food_group"
    food_group_map = dict(zip(foods_df["id"], foods_df[group_col]))

    # --- KAHVALTI DECODE ---
    selected_breakfast = []
    current_breakfast_totals = {nid: 0.0 for nid in NUTRIENT_IDS}
    
    for food_id in breakfast_part:
        if is_vegetarian:
            f_group = food_group_map.get(food_id, None)
            if f_group in FORBIDDEN_GROUPS:
                continue  # Vejetaryense etli yemeği es geç
        
        # Yemeğin besin değerlerini al
        nutrients = food_nutrient_map.get(food_id, {nid: 0.0 for nid in NUTRIENT_IDS})
        
        # Geçici üst limit kontrolü (Energy ve Protein için)
        exceed = False
        for nutrient_id in BREAKFAST_IDS:
            rul_b = limits[nutrient_id]["RUL"] * 0.35
            rul_eff = rul_b * 1.15
            if current_breakfast_totals[nutrient_id] + nutrients[nutrient_id] > rul_eff:
                exceed = True
                break
                
        if not exceed:
            selected_breakfast.append(food_id)
            for nutrient_id in NUTRIENT_IDS:
                current_breakfast_totals[nutrient_id] += nutrients[nutrient_id]

            # Koşul sağlandıysa durma kontrolü (Energy VE Protein alt limiti geçtiyse)
            breakfast_ok = True
            for nutrient_id in BREAKFAST_IDS:
                rll_eff = limits[nutrient_id]["RLL"] * 0.35 * 0.90
                if current_breakfast_totals[nutrient_id] < rll_eff:
                    breakfast_ok = False
                    break
            if breakfast_ok:
                break  # Hedef kahvaltı alt limitlerine ulaşıldı, döngüden çıkabiliriz.

    # --- ÖĞLE + AKSAM DECODE ---
    selected_all = selected_breakfast[:]
    current_all_totals = current_breakfast_totals.copy()
    
    for food_id in lunch_part:
        if is_vegetarian:
            f_group = food_group_map.get(food_id, None)
            if f_group in FORBIDDEN_GROUPS:
                continue

        nutrients = food_nutrient_map.get(food_id, {nid: 0.0 for nid in NUTRIENT_IDS})
        
        # Geçici üst limit kontrolü (5 Nutrient için)
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
            
            # Tüm 5 besin grubu da efektif alt limiti geçtiyse tamamdır
            all_ok = True
            for nutrient_id in NUTRIENT_IDS:
                rll_eff = limits[nutrient_id]["RLL"] * 0.90
                if current_all_totals[nutrient_id] < rll_eff:
                    all_ok = False
                    break
            if all_ok:
                break  # Günlük menü besin hedeflerine ulaştı, başarılı sonlandırma.
                
    return selected_all


def calculate_penalty(selected_foods, foods_df, nutrients_df, dri_df, user_info, diversity_on=False):
    """
    Secilen menunun nutrient kisitlarini ne kadar ihlal ettigini hesaplar.
    Ayrıca diversity_on=True ise yetersiz besin grubu çeşitliliğini cezalandırır.
    """
    if not selected_foods:
        return 999.0  # Menü boş kalırsa büyük bir ceza döndür

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
    
    # --- ÇEŞİTLİLİK (DIVERSITY) CEZASI ---
    if diversity_on:
        group_col = "food_group_id" if "food_group_id" in foods_df.columns else "food_group"
        selected_meta = foods_df[foods_df["id"].isin(selected_foods)]
        unique_groups = selected_meta[group_col].nunique()
        
        HEDEF_GRUP_SAYISI = 4
        if unique_groups < HEDEF_GRUP_SAYISI:
            # Eksik kalan her grup için cezayı kümülatif ekle
            diversity_penalty = (HEDEF_GRUP_SAYISI - unique_groups) * 1.5
            R += diversity_penalty
    
    return R

from database.data_loader import load_foods, load_food_nutrients, load_dri
from experiment import run_all_experiments

def main():
    print("1. Veritabanından tablolar çekiliyor, lütfen bekle...")
    foods_df = load_foods()
    nutrients_df = load_food_nutrients() 
    dri_df = load_dri()

    print(f"-> {len(foods_df)} yemek, {len(nutrients_df)} besin içeriği, {len(dri_df)} DRI limiti başarıyla yüklendi.\n")

    # --- HOCANIN İSTEDİĞİ DOĞRU GRUPLAMA MANTIĞI ---
    # Süt ürünleri, tatlılar, kahvaltılıklar, ekmekler vb. gibi kahvaltı grubu ID'lerini buraya yazmalısın.
    # Örnek olarak veri tabanındaki kahvaltılık grup ID'lerini bulup yaz (Örn: 1, 2, 5, 6, 12 vb.)
    # (Buradaki numaraları sql dökümanındaki food_group tablosuna göre teyit et kanka)
    BREAKFAST_GROUP_IDS = [1, 2, 5, 6, 10, 12, 15] 
    
    # Kahvaltı için uygun olan ~96 yiyeceğin ID listesini filtreleyerek çekiyoruz
    breakfast_ids = foods_df[foods_df['foodGroupId'].isin(BREAKFAST_GROUP_IDS)]['id'].tolist()
    
    # Öğle ve akşam yemeği için kalan (veya hem orada hem burada ortak olan) grupları çekiyoruz
    # Eğer bir grup hem kahvaltıda hem akşam yemeğinde varsa, iki listeye de girebilir (Duplicated kuralı)
    LUNCH_DINNER_GROUP_IDS = [col for col in foods_df['foodGroupId'].unique() if col not in [5, 6]] # Örnektir
    lunch_ids = foods_df[foods_df['foodGroupId'].isin(LUNCH_DINNER_GROUP_IDS)]['id'].tolist()

    print(f"-> Filtreleme Sonucu: {len(breakfast_ids)} kahvaltılık, {len(lunch_ids)} öğle/akşam yemeği belirlendi.")
    # ------------------------------------------------

    # 3. Deneyler için kullanıcı profilleri
    user1_info = {"user_id": 1, "age": 23, "gender": "female", "is_vegetarian": False}
    user2_info = {"user_id": 2, "age": 23, "gender": "female", "is_vegetarian": True}

    print("2. Algoritmalar ve Deneyler Başlıyor! (NSGA-II ve SPEA2 yarışıyor)...")
    
    run_all_experiments(
        breakfast_ids=breakfast_ids,
        lunch_ids=lunch_ids,
        foods_df=foods_df,
        nutrients_df=nutrients_df,
        dri_df=dri_df,
        user1_info=user1_info,
        user2_info=user2_info
    )

    print("\n PROJE BAŞARIYLA BİTTİ!")

if __name__ == "__main__":
    main()

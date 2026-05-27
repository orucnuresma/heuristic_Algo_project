from database.data_loader import load_foods, load_food_nutrients, load_dri
from experiment import run_all_experiments

def main():
    print("1. Veritabanından tablolar çekiliyor, lütfen bekle...")
    foods_df = load_foods()
    
    # decode.py dosyasının constraint hesaplaması için 'food_nutrients' tablosuna ihtiyacı var.
    nutrients_df = load_food_nutrients() 
    dri_df = load_dri()

    print(f"-> {len(foods_df)} yemek, {len(nutrients_df)} besin içeriği, {len(dri_df)} DRI limiti başarıyla yüklendi.\n")

    # 2. Kahvaltı (ilk 94) ve Öğle/Akşam (kalanlar) olarak ID'leri ayır
    breakfast_ids = foods_df['id'].tolist()[:94]
    lunch_ids = foods_df['id'].tolist()[94:]

    # 3. Deney 1 için iki farklı kullanıcı profili (PDF'teki kural)
    user1_info = {"user_id": 1, "age": 23, "gender": "female"}
    user2_info = {"user_id": 2, "age": 23, "gender": "female"} # (Gerekirse vejetaryen eklenebilir)

    print("2. Algoritmalar ve Deneyler Başlıyor! (NSGA-II ve SPEA2 yarışıyor, bu işlem biraz sürebilir)...")
    
    # Bütün projeyi ateşleyen ana fonksiyon (experiment.py'den çağırıyoruz)
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
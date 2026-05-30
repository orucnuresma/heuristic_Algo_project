import pandas as pd
import ast

from database.data_loader import load_foods

# Menü dosyası
menus = pd.read_csv(
    "results/sample_menus/algo_nsga2_menu_run1.csv"
)

# Veritabanından foods tablosunu çek
foods = load_foods()

food_dict = dict(zip(foods["id"], foods["name"]))

row = menus.iloc[0]

breakfast_ids = ast.literal_eval(row["breakfast_ids"])
lunch_ids = ast.literal_eval(row["lunch_ids"])

sample_breakfast = breakfast_ids[:7]
sample_lunch = lunch_ids[:10]

table = pd.DataFrame({
    "Breakfast": [food_dict[i] for i in sample_breakfast] + [""] * 3,
    "Lunch/Dinner": [food_dict[i] for i in sample_lunch]
})

print(table)
table.to_excel("sample_menu.xlsx", index=False)

print("Excel dosyası oluşturuldu: sample_menu.xlsx")
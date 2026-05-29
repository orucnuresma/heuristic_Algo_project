# database/data_loader.py

import pandas as pd
from database.db_connection import get_connection

# Sürekli aynı bağlantı kodunu yazmamak için ortak query çalıştırma fonksiyonu.
# Gelen SQL sorgusunu çalıştırıp sonucu dataframe olarak döndürüyor.
def execute_query(query):
    conn = get_connection()

    df = pd.read_sql(query, conn)

    conn.close()

    return df

# Foods tablosundaki ana yemek verilerini çekiyor.
# Algoritma tarafında kullanılacak cost, co2, preparingTime gibi bilgiler burada.
def load_foods():
    query = """
    SELECT id,
           name,
           foodGroupId,
           cost,
           preference,
           preference2,
           preparingTime,
           cookingTime,
           co2
    FROM foods
    """

    return execute_query(query)

# Her yemeğin nutrient değerlerini çekiyor.
# Örneğin protein, karbonhidrat, enerji vs.
# Constraint hesaplarında büyük ihtimal burası kullanılacak.
def load_food_nutrients():
    query = """
    SELECT foodId,
           nutrientId,
           quantity
    FROM food_nutrients
    """

    return execute_query(query)

# Nutrient isimlerini çekiyor.
# nutrientId değerlerinin hangi nutrient'e ait olduğunu anlamak için kullanılabilir.
def load_nutrients():
    query = """
    SELECT id,
           name,
           unitId
    FROM nutrients
    """

    return execute_query(query)

# Food group bilgilerini çekiyor.
# Diversity kısmında farklı food group sayısı hesaplanırken kullanılabilir.
def load_food_groups():
    query = """
    SELECT id,
           name
    FROM food_group
    """

    return execute_query(query)

# Kullanıcı bilgilerini çekiyor.
# Yaş/cinsiyet bilgileri DRI seçiminde işe yarayabilir diye ekledim.
def load_users():
    query = """
    SELECT id,
           username,
           age,
           gender,
           height,
           weight
    FROM user
    """

    return execute_query(query)

# Kullanıcının yemek preference puanlarını çekiyor.
# Hoca foods.preference yerine buranın kullanılmasını istemiş olabilir diye ayrı tuttum.
def load_user_foods():
    connection = get_connection()
    query = """
        SELECT userId, foodId, preference
        FROM user_foods
    """
    df = pd.read_sql(query, connection)
    connection.close()
    return df

  

# DRI tablosundaki nutrient sınırlarını çekiyor.
# RLL = minimum değer
# RUL = maksimum değer
# Penalty ve constraint kontrolünde kullanılacak.
def load_dri():
    query = """
    SELECT nutrient_id,
           low_age,
           up_age,
           gender,
           RLL,
           RUL
    FROM dri
    """

    return execute_query(query)
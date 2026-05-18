# database/db_connection.py

import mysql.connector
from database.db_config import DB_CONFIG

# MySQL database bağlantısını oluşturur.
# Bağlantı başarılı olursa connection nesnesini döndürür.
# Hata olursa ekrana hata mesajı yazdırır.

def get_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except mysql.connector.Error as err:
        print("Database connection error:", err)
        return None
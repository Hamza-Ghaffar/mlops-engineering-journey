import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

# Load .env from project root
load_dotenv()

hostname = os.getenv("DB_HOST", "")
database = os.getenv("DB_NAME", "")
port = os.getenv("DB_PORT", "")
username = os.getenv("DB_USER", "")
password = os.getenv("DB_PASSWORD", "REPLACE_ME")

def masked(s: str) -> str:
    if not s:
        return "(empty)"
    if s == "REPLACE_ME":
        return "(placeholder)"
    return s[0] + "*" * (max(len(s)-2, 0)) + s[-1]

print("DB config:")
print(" host:", hostname)
print(" port:", port)
print(" database:", database)
print(" user:", username)
print(" password:", masked(password))

connection = None
try:
    if password and password != "REPLACE_ME":
        connection = mysql.connector.connect(host=hostname, database=database, user=username, password=password, port=port)
        if connection.is_connected():
            db_Info = connection.get_server_info()
            print("Connected to MySQL Server version ", db_Info)
            cursor = connection.cursor()
            cursor.execute("select database();")
            record = cursor.fetchone()
            print("You're connected to database: ", record)
    else:
        print("Skipping actual DB connect because password is placeholder or empty. Update .env with real credentials to connect.")
except Error as e:
    print("Error while connecting to MySQL", e)
finally:
    if connection and connection.is_connected():
        cursor.close()
        connection.close()
        print("MySQL connection is closed")
        
        
        
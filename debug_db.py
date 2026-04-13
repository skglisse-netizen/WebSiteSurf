import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")
print(f"Connecting to: {url}")

conn = psycopg2.connect(url)
curr = conn.cursor()

curr.execute("SELECT current_database();")
db_name = curr.fetchone()[0]
print(f"Current Database: {db_name}")

curr.execute("SELECT current_schema();")
schema_name = curr.fetchone()[0]
print(f"Current Schema: {schema_name}")

curr.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'site_config';
""")
columns = curr.fetchall()
print("Columns in site_config:")
for col in columns:
    print(f" - {col[0]} ({col[1]})")

conn.close()

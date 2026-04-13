import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")
print(f"Connecting to: {url}")

try:
    conn = psycopg2.connect(url)
    conn.autocommit = True
    curr = conn.cursor()
    cols = ["school_name", "contact_address", "contact_phone", "contact_email"]
    for col in cols:
        try:
            curr.execute(f"ALTER TABLE site_config ADD COLUMN {col} VARCHAR DEFAULT '';")
            print(f"Added {col}")
        except Exception as e:
            print(f"Column {col} might already exist or error: {e}")
    conn.close()
except Exception as e:
    print(f"Global error: {e}")

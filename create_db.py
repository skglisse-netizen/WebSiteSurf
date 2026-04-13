import psycopg2
from psycopg2 import sql

# Connection to the default postgres database to create a new one
try:
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="T@st1984",
        host="localhost",
        port=5432
    )
    conn.autocommit = True

    cursor = conn.cursor()
    # Check if database exists
    cursor.execute("SELECT 1 FROM pg_database WHERE datname='SiteWebSurfBD'")
    if not cursor.fetchone():
        cursor.execute(sql.SQL("CREATE DATABASE \"SiteWebSurfBD\""))
        print("Database 'SiteWebSurfBD' created successfully!")
    else:
        print("Database 'SiteWebSurfBD' already exists.")

    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")

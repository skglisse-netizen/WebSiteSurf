import psycopg2

try:
    conn = psycopg2.connect("postgresql://postgres:T%40st1984@localhost:5432/SiteWebSurfBD")
    conn.autocommit = True
    curr = conn.cursor()
    curr.execute("ALTER TABLE site_config ADD COLUMN school_name VARCHAR DEFAULT 'WaveRider'")
    curr.execute("ALTER TABLE site_config ADD COLUMN contact_address VARCHAR DEFAULT '123 Plage des Vagues, 64200 Biarritz'")
    curr.execute("ALTER TABLE site_config ADD COLUMN contact_phone VARCHAR DEFAULT '+33 6 12 34 56 78'")
    curr.execute("ALTER TABLE site_config ADD COLUMN contact_email VARCHAR DEFAULT 'allo@waverider.fr'")
    print("Columns added successfully.")
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals():
        conn.close()

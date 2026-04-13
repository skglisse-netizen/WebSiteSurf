import psycopg2
conn = psycopg2.connect("postgresql://postgres:T%40st1984@localhost:5432/SiteWebSurfBD")
curr = conn.cursor()
curr.execute("SELECT * FROM site_config LIMIT 1;")
print("Columns:", [desc[0] for desc in curr.description])
conn.close()

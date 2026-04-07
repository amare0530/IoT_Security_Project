import sqlite3
conn = sqlite3.connect('artifacts/zenodo_crp_synthetic.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print("Tables:", tables)

if tables:
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        cols = cursor.fetchall()
        print(f"\n{table}:")
        for col in cols:
            print(f"  {col[1]} ({col[2]})")

conn.close()

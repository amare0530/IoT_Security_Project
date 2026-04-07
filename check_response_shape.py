import sqlite3
conn = sqlite3.connect('artifacts/zenodo_crp_corrected_v2.db')
cursor = conn.cursor()
cursor.execute("SELECT DISTINCT challenge FROM crp_records LIMIT 5")
challenges = cursor.fetchall()
print("Sample challenges:", [c[0] for c in challenges])

# Check response length
cursor.execute("SELECT COUNT(*), challenge FROM crp_records GROUP BY challenge LIMIT 3")
for count, chal in cursor.fetchall():
    cursor.execute("SELECT response FROM crp_records WHERE challenge = ? LIMIT 1", (chal,))
    resp = cursor.fetchone()[0]
    print(f"Challenge {chal}: {count} records, response len = {len(resp)}")

# Check device count
cursor.execute("SELECT COUNT(DISTINCT device_id) FROM crp_records")
print(f"Total devices: {cursor.fetchone()[0]}")

conn.close()

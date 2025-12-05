from db import get_conn

conn = get_conn()
with conn:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM team;")
        rows = cur.fetchall()
        print(rows)
conn.close()

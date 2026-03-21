import psycopg2

try:
    conn = psycopg2.connect(
        host='db.wzyfoqkocffuqxxubrgr.supabase.co',
        port=5432,
        database='postgres',
        user='postgres',
        password='Louistoffegee@30'
    )
    print("SUCCESS")
    conn.close()
except Exception as e:
    print(f"ERROR: {e}")

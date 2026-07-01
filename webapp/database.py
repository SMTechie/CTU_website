import os
import psycopg2

def get_db_connection():
    return psycopg2.connect(
        host="postgres",        
        database="portaldb",
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD")
    )

def close_db(cursor, conn):
    cursor.close()
    conn.close()
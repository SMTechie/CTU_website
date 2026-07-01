from psycopg2.extras import RealDictCursor
import pyotp
import bcrypt
from database import get_db_connection, close_db

def create_user(form):
    username = form["username"]
    password = form["password"]

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    secret = pyotp.random_base32()

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO users(username, password_hash, totp_secret)
            VALUES (%s, %s, %s)
        """, (username, password_hash, secret))

        conn.commit()

    except Exception as e:
        conn.rollback()
        return False, f"Error: {e}"
    
    finally:
        close_db(cursor, conn)

    return True, "User created successfully"

def get_users():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = 'SELECT username, mfa_enabled, account_status, created_at FROM users ORDER BY username'

    try:
        cursor.execute(query)

        users = cursor.fetchall()
        return users
    except Exception as e:
        conn.rollback()
        return False
    finally:
        close_db(cursor, conn)

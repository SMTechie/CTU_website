from psycopg2.extras import RealDictCursor
import pyotp
import bcrypt
from database import get_db_connection, close_db
from mfa import generate_new_secret

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

    query = 'SELECT user_id, username, mfa_enabled, account_status, last_login_at, created_at FROM users ORDER BY username'

    try:
        cursor.execute(query)

        users = cursor.fetchall()
        return users
    except Exception as e:
        conn.rollback()
        return False
    finally:
        close_db(cursor, conn)


def edit_user(form):
    user_id = form['user_id']
    account_status = form['account_status']
    reset_mfa = 'reset_mfa' in form

    conn = get_db_connection()
    cursor = conn.cursor()

    if reset_mfa:
        new_secret = generate_new_secret() 

    try:
        query = 'UPDATE users SET account_status = %s WHERE user_id = %s'
        cursor.execute(query,(account_status, user_id))

        if reset_mfa:
            query = 'UPDATE users SET mfa_enabled = FALSE, totp_secret = %s WHERE user_id = %s'
            cursor.execute(query, (new_secret, user_id))

        conn.commit()
    except Exception as e:
        conn.rollback()
        return False, f'Failed to saved changes: {e}'
    finally:
        close_db(cursor, conn)

    return True, 'Successfully saved to database'
    

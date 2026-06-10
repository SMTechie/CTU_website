from flask import Flask, request, render_template, redirect
import psycopg2
# 📥 Integrated: Importing your teammate's clean verification function
from mfa import verify_mfa  

app = Flask(__name__)

# Database connection helper
def get_db_connection():
    return psycopg2.connect(
        host="postgres",         # Matches your docker setup setup
        database="portaldb",
        user="postgres",
        password="postgres"
    )

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    # 1. Grab the values out of the HTML form fields using their 'name' attributes
    username = request.form.get('username')
    password = request.form.get('password')
    totp_token = request.form.get('totp_token')

    # 2. Check the database for the user's password and registration secret
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash, totp_secret FROM users WHERE username = %s;", (username,))
    user_record = cursor.fetchone()
    cursor.close()
    conn.close()

    if user_record:
        db_password_hash, db_totp_secret = user_record

        # 3. Verify Password (Use a hashing library like bcrypt or argon2 in production!)
        if password == db_password_hash:
            
            # 4. ✅ JODINE'S PART 
            if verify_mfa(db_totp_secret, totp_token):
                return "Authentication Successful! Welcome to the portal."
            else:
                return "MFA Code is invalid.", 401
                
    return "Invalid username or password.", 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=8080)
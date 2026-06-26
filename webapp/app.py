from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
import psycopg2.extras
import bcrypt
import pyotp
import qrcode
import io
import base64
from mfa import verify_mfa  
from email_service import send_status_update_email, send_comment_notification, send_ticket_created_email

app = Flask(__name__)
# Secure production key configuration
app.secret_key = 'ctu_solutions_FORCE_SESSION_RESET_KEY_2026'


# Database connection
def get_db_connection():
    return psycopg2.connect(
        host="postgres",        
        database="portaldb",
        user="postgres",
        password="postgres"
    )

# STRICT ACCESS CONTROL GATEWAY
@app.route('/')
def index():
    # If the user is fully logged in and MFA verified, grant entry to website
    if 'username' in session and session.get('mfa_verified') == True:
        return redirect(url_for("tickets_page"))
    
    # IF NOT AUTHENTICATED: Enforce redirect straight to the login portal screen
    return redirect(url_for('login_page'))

@app.route('/login', methods=['GET'])
def login_page():
    if 'username' in session and session.get('mfa_verified') == True:
        return redirect(url_for('tickets_page'))
    return render_template('login.html')

# STEP 1: Process Primary Credentials
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username').strip()
    incoming_password = request.form.get('password')

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # PostgreSQL utilizes standard %s dynamic parameter markers
    cursor.execute("SELECT password_hash, totp_secret, account_status FROM users WHERE username = %s;", (username,))
    user_record = cursor.fetchone()

    # Creates the random user safely
    if not user_record:
        hashed_pw = bcrypt.hashpw(incoming_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute("""
            INSERT INTO users (username, password_hash, mfa_enabled, totp_secret, account_status)
            VALUES (%s, %s, FALSE, NULL, 'active');
        """, (username, hashed_pw))
        conn.commit()
        
        cursor.execute("SELECT password_hash, totp_secret, account_status FROM users WHERE username = %s;", (username,))
        user_record = cursor.fetchone()

    db_password_hash = user_record['password_hash']
    totp_secret = user_record['totp_secret']
    account_status = user_record['account_status']

    if account_status != 'active':
        cursor.close()
        conn.close()
        flash("This account is currently deactivated.", "error")
        return redirect(url_for('login_page'))

    # Verify Password Hash Signature Matching
    if not bcrypt.checkpw(incoming_password.encode('utf-8'), db_password_hash.encode('utf-8')):
        cursor.close()
        conn.close()
        flash("Invalid username or password.", "error")
        return redirect(url_for('login_page'))

    session['pre_auth_user'] = username
    cursor.close()
    conn.close()

    # STEP 2: Multi-Factor Routing Engine
    if not totp_secret:
        return redirect(url_for('mfa_setup_page'))
    else:
        return redirect(url_for('mfa_verify_page'))

# ROUTE: MFA Provisioning Setup Wizard View
@app.route('/mfa/setup', methods=['GET'])
def mfa_setup_page():
    if 'pre_auth_user' not in session:
        return redirect(url_for('login_page'))
        
    username = session['pre_auth_user']
    temp_secret = pyotp.random_base32()
    session['temp_mfa_secret'] = temp_secret

    auth_uri = pyotp.totp.TOTP(temp_secret).provisioning_uri(
        name=username, issuer_name="CTU Solutions"
    )
    
    qr = qrcode.make(auth_uri)
    buffered = io.BytesIO()
    qr.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

    return render_template('MFA_registration_setup.html', qr_base64=qr_base64)

@app.route('/mfa/setup/confirm', methods=['POST'])
def mfa_setup_confirm():
    if 'temp_mfa_secret' not in session or 'pre_auth_user' not in session:
        return redirect(url_for('login_page'))

    user_code = request.form.get('mfa_code')
    secret = session['temp_mfa_secret']
    username = session['pre_auth_user']

    totp = pyotp.TOTP(secret)
    if totp.verify(user_code):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET totp_secret = %s, mfa_enabled = TRUE WHERE username = %s;", (secret, username))
        conn.commit()
        cursor.close()
        conn.close()

        session['username'] = username
        session['mfa_verified'] = True
        session.pop('temp_mfa_secret', None)
        session.pop('pre_auth_user', None)

        return redirect(url_for('tickets_page'))
    else:
        flash("Invalid verification code. Please try scanning again.", "error")
        return redirect(url_for('mfa_setup_page'))

# ROUTE: Prompts Returning Authenticated Users for Active Tokens
@app.route('/mfa/verify', methods=['GET', 'POST'])
def mfa_verify_page():
    if 'pre_auth_user' not in session:
        return redirect(url_for('login_page'))

    if request.method == 'POST':
        token = request.form.get('totp_token')
        username = session['pre_auth_user']

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("SELECT totp_secret FROM users WHERE username = %s;", (username,))
        user = cursor.fetchone()

        totp = pyotp.totp.TOTP(user['totp_secret'])
        if totp.verify(token):
            session['username'] = username
            session['mfa_verified'] = True
            session.pop('pre_auth_user', None)
            cursor.close()
            conn.close()
            return redirect(url_for('tickets_page'))
        else:
            cursor.close()
            conn.close()
            flash("Invalid MFA code. Please check your authenticator app.", "error")

    return render_template('mfa_verify.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

def record_audit_log(username, event_text):
    """Executes a secure database INSERT query to upload login event data."""
    try:
        print("AUDIT DEBUG 1:", username, event_text)
        conn = get_db_connection()
        cursor = conn.cursor()

        # Parameterized query matching your exact columns: username, event
        query = """INSERT INTO audit_logs (username, event) VALUES (%s, %s);"""
        cursor.execute(query, (username, event_text))

        conn.commit()
        print("commitdone", flush=True)
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error recording audit log: {e}", flush=True)

"""
@app.route('/login', methods=['POST'])
def login():
    # 1. Grab the values out of the HTML form fields using their 'name' attributes
    username = request.form.get('username')
    password = request.form.get('password')
    totp_token = request.form.get('totp_token')

    # 2. Check the database for the user's password and registration secret
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT passwords, totp_secret FROM users WHERE username = %s;", (username,))
    user_record = cursor.fetchone()
    cursor.close()
    conn.close()

    if user_record:
        db_password_hash, db_totp_secret = user_record

        # 3. Verify Password (Use a hashing library like bcrypt or argon2 in production!)
        if password == db_password_hash:
            
            # 4. ✅ JODINE'S PART 
            if verify_mfa(db_totp_secret, totp_token):
                record_audit_log(username, 'Login Success')
                return "Authentication Successful! Welcome to the portal."
            else:
                record_audit_log(username, 'Login Failed - MFA Invalid')
                return "MFA Code is invalid.", 401
                
    safe_username = username if username else "Unknown"
    record_audit_log(safe_username, 'Login Failed - Bad Credentials')
    return "Invalid username or password.", 401
"""

@app.route('/tickets')
def tickets_page():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, email, message, status
        FROM tickets
        ORDER BY id DESC
    """)

    tickets = cursor.fetchall()

    cursor.close()
    conn.close()

    first_ticket_id = tickets[0][0] if tickets else None

    return render_template("tickets.html", tickets=tickets, first_ticket_id=first_ticket_id)

@app.route('/tickets/<int:ticket_id>')
def get_ticket(ticket_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, email, message, status
        FROM tickets
        WHERE id = %s
    """, (ticket_id,))

    ticket = cursor.fetchone()

    cursor.execute("""
        SELECT comment, created_at
        FROM ticket_comments
        WHERE ticket_id = %s
        ORDER BY created_at ASC
    """, (ticket_id,))
    comments = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
        "id": ticket[0],
        "name": ticket[1],
        "email": ticket[2],
        "message": ticket[3],
        "status": ticket[4],
        "comments": [{"text": c[0], "created_at": str(c[1])} for c in comments]
    }


@app.route('/tickets/<int:ticket_id>/update', methods=['POST'])
def update_ticket_status(ticket_id):
    new_status = request.form.get('status')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name, email
        FROM tickets
        WHERE id = %s
    """, (ticket_id,))
    ticket = cursor.fetchone()

    cursor.execute("""
        UPDATE tickets
        SET status = %s
        WHERE id = %s
    """, (new_status, ticket_id))

    conn.commit()
    cursor.close()
    conn.close()

    try:
        send_status_update_email(
            ticket[0],
            ticket[1],
            new_status
        )
    except Exception as e:
        print("Email failed:", e)

    return redirect('/websitename/portal/tickets')


@app.route('/tickets/<int:ticket_id>/comment', methods=['POST'])
def add_comment(ticket_id):
    comment_text = request.form.get('comment')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get ticket owner details
    cursor.execute("""
        SELECT name, email
        FROM tickets
        WHERE id = %s
    """, (ticket_id,))
    ticket = cursor.fetchone()

    cursor.execute("""
        INSERT INTO ticket_comments (ticket_id, comment)
        VALUES (%s, %s)
    """, (ticket_id, comment_text))

    conn.commit()
    cursor.close()
    conn.close()

    # Send email notification
    try:
        send_comment_notification(
            ticket[0],  # name
            ticket[1],  # email
            comment_text
        )
    except Exception as e:
        print("Comment email failed:", e)


    return redirect('/websitename/portal/tickets')


@app.route('/email/ticket-created', methods=['POST'])
def email_ticket_created():
    data = request.json

    send_ticket_created_email(
        data["name"],
        data["email"],
        data["subject"]
    )

    return {"status": "sent"}


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=3001)
import os
import sys
import bcrypt
import psycopg2
import psycopg2.extras
import logging
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import email_service
import mfa
import users_service
import ticket_service

app = Flask(
    __name__,
    template_folder='../templates',  # Points directly to your outer templates directory
    static_folder='../website',      # Serve the website assets from the website folder
    static_url_path='/static'
)

app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY")

# Database connection
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

def is_authenticated():
    return 'username' in session and session.get('mfa_verified', False)


@app.before_request
def require_login():
    if request.endpoint == 'dashboard' and not is_authenticated():
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if is_authenticated():
            return redirect(url_for('tickets'))
        return render_template('login.html')
    
    username = request.form.get('username')
    password = request.form.get('password')

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cursor.execute("SELECT password_hash, mfa_enabled, totp_secret, account_status FROM users WHERE username = %s;", (username,))
    user_record = cursor.fetchone()

    if not user_record:
        flash("Invalid identification matrix credentials.", "danger")
        return

    mfa_enabled = user_record['mfa_enabled']
    db_password_hash = user_record['password_hash']
    totp_secret = user_record['totp_secret']
    account_status = user_record['account_status']

    close_db(cursor, conn)

    if account_status != 'Active':
        flash("This account is currently deactivated.", "error")
        return redirect(url_for('login'))
    
    if not bcrypt.checkpw(password.encode('utf-8'), db_password_hash.encode('utf-8')):
        flash("Invalid username or password.", "error")
        return redirect(url_for('login'))

    session['username'] = username
    if mfa_enabled:
        return redirect(url_for('mfa_verify'))
    else:
        return redirect(url_for('mfa_setup'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/mfa/setup', methods=['GET', 'POST'])
def mfa_setup():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cursor.execute('SELECT totp_secret FROM users WHERE username = %s;', [username],)
    totp_secret = cursor.fetchone()['totp_secret']

    if request.method == 'GET':
        qr_base64 = mfa.generate_qr_image(username, totp_secret)
        return render_template('MFA_registration_setup.html', qr_base64=qr_base64)
    
    token = request.form.get('mfa_code')

    valid = mfa.verify_totp(totp_secret, token)

    if totp_secret and mfa.verify_totp(totp_secret, token):
        session['mfa_verified'] = True
        try:
            cursor.execute('UPDATE users SET mfa_enabled = TRUE WHERE username = %s', (username,))
            conn.commit()
        except:
            return redirect(url_for('dashboard'))
        finally:
            close_db(cursor, conn)
        return redirect(url_for('dashboard'))
    
    close_db(cursor, conn)
    flash('Invalid Token entered, Please try again', 'danger')
    return redirect(url_for('mfa_setup'))


@app.route('/mfa/verify', methods=['GET', 'POST'])
def mfa_verify():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']

    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT totp_secret FROM users WHERE username = %s;', [username],)
        totp_secret = cursor.fetchone()['totp_secret']
        close_db(cursor, conn)

        token = request.form.get('mfa_code')

        if totp_secret and mfa.verify_totp(totp_secret, token):
            session['mfa_verified'] = True
            return redirect(url_for('dashboard'))
        
        flash('Invalid Token entered, Please try again', 'danger')
        return redirect(url_for('mfa_verify'))
    return render_template('mfa_verify.html')


###################################################################
# Dashboard
###################################################################
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

###################################################################
# Tickets
###################################################################
@app.route('/tickets')
def tickets():
    if not is_authenticated():
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, email, message, status
        FROM tickets
        ORDER BY id DESC
    """)

    tickets = cursor.fetchall()

    close_db(cursor, conn)

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

    close_db(cursor, conn)

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
    close_db(cursor, conn)

    try:
        email_service.send_status_update_email(
            ticket[0],
            ticket[1],
            new_status
        )
    except Exception as e:
        print("Email failed:", e)

    return redirect(url_for('tickets'))


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
    close_db(cursor, conn)

    # Send email notification
    try:
        email_service.send_comment_notification(
            ticket[0],  # name
            ticket[1],  # email
            comment_text
        )
    except Exception as e:
        print("Comment email failed:", e)


    return redirect(url_for('tickets'))

###################################################################
# HOME Page
###################################################################
@app.route('/home')
def home():
    return render_template('index.html')

@app.route('/contact-submit', methods=['POST'])
def create_ticket():
    name = request.form.get('name')
    user_email = request.form.get('email')
    message = request.form.get('message')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = """INSERT INTO tickets (name, email, message) VALUES(%s, %s, %s);"""
        cursor.execute(query, (name, user_email, message))

        conn.commit()
        flash('Ticket made successfully, You will be contacted by an agent soon', 'success')
    except Exception as e:
        flash('Error recording ticket, please try again', 'error')
    finally:
        close_db(cursor, conn)

    try:
        email_service.send_ticket_created_email(
            name,
            user_email,
            message
        )
    except Exception as e:
        print(e)

    return redirect(url_for('home'))

###################################################################
# Users
###################################################################
@app.route('/users')
def users():
    users = users_service.get_users()

    return render_template('users.html', users=users)

@app.route('/user-create', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        success, message = users_service.create_user(request.form)

        flash(message) 

        if success:
            return redirect(url_for('users'))
    
    return redirect(url_for('users'))

@app.route('/users/edit', methods=['POST'])
def edit_user():
    if request.method == 'POST':
        success = users_service.edit_user(request.form)
        
    return redirect(url_for('users'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3001, debug=True)
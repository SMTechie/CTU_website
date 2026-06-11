from flask import Flask, request, render_template, redirect
import psycopg2
# 📥 Integrated: Importing your teammate's clean verification function
from mfa import verify_mfa  
from email_service import send_status_update_email, send_comment_notification, send_ticket_created_email

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
    app.run(host='0.0.0.0', debug=True, port=8080)
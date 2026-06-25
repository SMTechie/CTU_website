import os
import sys
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

# Add the webapp folder to the system path so Python can find your custom services cleanly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import your modular logic engines
import email_service
import mfa
import ticket_service

app = Flask(
    __name__,
    template_folder='../templates',  # Points directly to your outer templates directory
    static_folder='../website',      # Serve the website assets from the website folder
    static_url_path='/static'
)

# In-memory demo ticket storage for the portal
TICKETS = [
    {
        "id": 1,
        "name": "Omogolo",
        "email": "omogolo@ctu.edu",
        "subject": "Database Connection Refused",
        "message": "Unable to connect to the student records database.",
        "status": "New",
        "comments": []
    },
    {
        "id": 2,
        "name": "Nokukhanya",
        "email": "nkuhanya@ctu.edu",
        "subject": "Password reset request",
        "message": "I need help resetting my portal password.",
        "status": "Assigned",
        "comments": []
    }
]

# Production Security Configurations
app.secret_key = os.getenv("FLASK_SECRET_KEY", "DEVELOPMENT_FALLBACK_KEY_SECRET_1987")
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True once routing through production HTTPS Certs

# ==========================================
# AUTHENTICATION ROUTING MIDDLEWARE
# ==========================================
SUPER_ADMIN_USERNAMES = {'caylee', 'admin'}


def is_authenticated():
    """Helper to verify if a session is completely authorized via Password + MFA."""
    return 'user_id' in session and session.get('mfa_verified', False)


def is_super_admin():
    """Helper to determine whether the current session belongs to an admin."""
    return session.get('role') == 'SUPER_ADMIN'


def determine_user_role(username):
    """Return a role string based on the given username."""
    if username and username.lower() in SUPER_ADMIN_USERNAMES:
        return 'SUPER_ADMIN'
    return 'USER'


@app.before_request
def require_login():
    if request.endpoint in ('login', 'static', 'mfa_setup', 'mfa_setup_confirm', 'mfa_verify'):
        return
    if request.path.startswith('/static'):
        return
    if not is_authenticated():
        return redirect(url_for('login'))


# ==========================================
# PUBLIC GATEWAY ROUTES
# ==========================================

@app.route('/')
def root_redirect():
    """Always send the first visitor to login."""
    return redirect(url_for('login'))


@app.route('/home')
def home():
    """Authenticated homepage after login."""
    if not is_authenticated():
        return redirect(url_for('login'))
    if is_super_admin():
        return redirect(url_for('admin_dashboard'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles core student/admin validation phase 1."""
    if is_authenticated():
        if is_super_admin():
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # --- PLACEHOLDER FOR YOUR DATABASE CHECK ENGINE ---
        # Example: user = db.query_user(username)
        # For demonstration, assuming verification succeeds:
        if username and password:
            session['user_id'] = username
            session['role'] = determine_user_role(username)
            session.pop('mfa_verified', None)
            session.pop('mfa_secret', None)

            # Check if user has completed MFA Setup
            # If not configured -> send to /mfa/setup
            # If configured -> send to /mfa/verify
            return redirect(url_for('mfa_verify'))

        flash("Invalid identification matrix credentials.", "danger")

    return render_template('login.html')


# ==========================================
# MULTI-FACTOR AUTHENTICATION (MFA) ENGINE
# ==========================================

@app.route('/mfa/setup', methods=['GET', 'POST'])
def mfa_setup():
    """Registers new physical authentication devices (Google/Microsoft Authenticator)."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        token = request.form.get('mfa_code')
        secret = session.get('mfa_secret')

        if secret and mfa.verify_totp(secret, token):
            session['mfa_verified'] = True
            if is_super_admin():
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('home'))

        flash("Verification token mismatch. Sync clock and try again.", "danger")
        return redirect(url_for('mfa_setup'))

    secret, qr_base64 = mfa.generate_qr_secret(session['user_id'])
    session['mfa_secret'] = secret
    return render_template('MFA_registration_setup.html', qr_base64=qr_base64)


@app.route('/mfa/setup/confirm', methods=['POST'])
def mfa_setup_confirm():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    token = request.form.get('mfa_code')
    secret = session.get('mfa_secret')

    if secret and mfa.verify_totp(secret, token):
        session['mfa_verified'] = True
        if is_super_admin():
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('home'))

    flash("Verification token mismatch. Sync clock and try again.", "danger")
    return redirect(url_for('mfa_setup'))


@app.route('/mfa/verify', methods=['GET', 'POST'])
def mfa_verify():
    """Enforces the secondary auth wall checking for active session tokens."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if 'mfa_secret' not in session:
        return redirect(url_for('mfa_setup'))

    if request.method == 'POST':
        token = request.form.get('totp_token')
        secret = session.get('mfa_secret')

        if secret and mfa.verify_totp(secret, token):
            session['mfa_verified'] = True
            if is_super_admin():
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('home'))
        flash("Verification token mismatch. Sync clock and try again.", "danger")

    return render_template('mfa_verify.html')


# ==========================================
# SECURE INTERNAL OPERATIONS PORTAL
# ==========================================

def require_admin_access():
    if not is_authenticated():
        return redirect(url_for('login'))
    if not is_super_admin():
        flash("Access denied: administrator privileges required.", "danger")
        return redirect(url_for('home'))
    return None


@app.route('/dashboard')
def dashboard():
    """Convenience admin dashboard entrypoint."""
    auth_check = require_admin_access()
    if auth_check:
        return auth_check
    return redirect(url_for('admin_dashboard'))


@app.route('/portal/dashboard')
def admin_dashboard():
    """Super Admin Master Console."""
    auth_check = require_admin_access()
    if auth_check:
        return auth_check

    unread_count = sum(1 for ticket in TICKETS if ticket['status'].lower() == 'new')
    return render_template('admin_dashboard.html', tickets=TICKETS, unread_count=unread_count)


@app.route('/portal/tickets')
def view_tickets():
    """Internal support monitoring console view layer."""
    auth_check = require_admin_access()
    if auth_check:
        return auth_check

    first_ticket_id = TICKETS[0]['id'] if TICKETS else None
    return render_template('tickets.html', tickets=TICKETS, first_ticket_id=first_ticket_id)


def find_ticket(ticket_id):
    return next((ticket for ticket in TICKETS if ticket['id'] == ticket_id), None)


@app.route('/portal/tickets/<int:ticket_id>')
def ticket_detail(ticket_id):
    auth_check = require_admin_access()
    if auth_check:
        return auth_check

    ticket = find_ticket(ticket_id)
    if not ticket:
        return jsonify({"error": "ticket not found"}), 404

    return jsonify(ticket)


@app.route('/portal/tickets/<int:ticket_id>/update', methods=['POST'])
def update_ticket(ticket_id):
    auth_check = require_admin_access()
    if auth_check:
        return auth_check

    ticket = find_ticket(ticket_id)
    if not ticket:
        flash("Ticket not found.", "danger")
        return redirect(url_for('view_tickets'))

    ticket['status'] = request.form.get('status', ticket['status'])
    flash("Ticket status updated successfully.", "success")
    return redirect(url_for('view_tickets'))


@app.route('/portal/tickets/<int:ticket_id>/comment', methods=['POST'])
def comment_ticket(ticket_id):
    auth_check = require_admin_access()
    if auth_check:
        return auth_check

    ticket = find_ticket(ticket_id)
    if not ticket:
        flash("Ticket not found.", "danger")
        return redirect(url_for('view_tickets'))

    comment_text = request.form.get('comment', '').strip()
    if comment_text:
        ticket['comments'].append({
            "text": comment_text,
            "created_at": "Just now"
        })
        flash("Comment added successfully.", "success")
    else:
        flash("Enter a comment before submitting.", "warning")

    return redirect(url_for('view_tickets'))


@app.route('/portal/courses/add', methods=['POST'])
def add_course():
    auth_check = require_admin_access()
    if auth_check:
        return auth_check

    flash("Course add request received. This is a demo endpoint.", "success")
    return redirect(url_for('admin_dashboard'))


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """Flushes active state maps securely."""
    session.clear()
    flash("Session context terminated successfully.", "success")
    return redirect(url_for('login'))


# ==========================================
# SYSTEM CORE RUN TRIGGER
# ==========================================
if __name__ == '__main__':
    # Binds directly to the open interface port configured inside your Docker entrypoint
    app.run(host='0.0.0.0', port=3001, debug=True)
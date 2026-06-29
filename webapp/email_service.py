import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


# EMAIL CONFIGURATION
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")



# Lemail-sender
def send_email(to_email, subject, body):
    if EMAIL_PASSWORD is None:
        raise ValueError("EMAIL_PASSWORD environment variable is not set.")

    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)

        print("Email sent successfully!")
        return True

    except Exception as e:
        print("Error sending email:", e)
        return False


# ticket created
def send_ticket_created_email(name, email, subject):
    body = f"""
    Hi {name},

    Your ticket has been created successfully.

    Subject: {subject}

    We have received your request and a representative will contact you shortly.

    Thank you.
    """

    return send_email(email, "Ticket Created", body)


# status updated
def send_status_update_email(name, email, status):
    body = f"""
    Hi {name},

    Your ticket status has been updated.

    New Status: {status}

    Thank you.
    """
    return send_email(email, "Ticket Status Updated", body)



# new comment
def send_comment_notification(name, email, comment):
    body = f"""
    Hi {name},

    A new comment has been added to your ticket:

    {comment}

    Thank you.
    """

    return send_email(email, "New Ticket Comment", body)



# Testing
if __name__ == "__main__":
    print('Email Service Started')
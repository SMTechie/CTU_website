# ticket_service.py

from email_service import (
    send_ticket_created_email,
    send_status_update_email,
    send_comment_notification
)

# AFTER INSERT INTO tickets TABLE
def on_ticket_created(ticket):
    send_ticket_created_email(
        ticket["name"],
        ticket["email"],
        ticket["subject"]
    )


# AFTER UPDATE tickets.status
def on_ticket_status_updated(ticket):
    send_status_update_email(
        ticket["name"],
        ticket["email"],
        ticket["status"]
    )

# AFTER INSERT INTO ticket_comments TABLE
def on_ticket_comment_added(ticket, comment):
    send_comment_notification(
        ticket["name"],
        ticket["email"],
        comment
    )
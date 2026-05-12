import resend

from backend.config import Config


def send_email(to, subject, body):
    if not Config.RESEND_API_KEY:
        return

    resend.api_key = Config.RESEND_API_KEY

    resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": to,
        "subject": subject,
        "text": body,
    })

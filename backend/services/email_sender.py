import resend

from backend.config import Config


def send_email(to, subject, body, html=None):
    if not Config.RESEND_API_KEY:
        return

    resend.api_key = Config.RESEND_API_KEY

    payload = {
        "from": Config.EMAIL_FROM,
        "to": to,
        "subject": subject,
        "text": body,
    }
    if html:
        payload["html"] = html

    resend.Emails.send(payload)

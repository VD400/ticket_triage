import secrets
import os
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlencode

import httpx

from settings import frontend_url, is_production

def generate_verification_token() -> str:
    return secrets.token_urlsafe(32)


def send_verification_email(recipient: str, token: str):
    link = f"{frontend_url()}/customerComplaint?{urlencode({'token': token})}"
    backend = os.getenv("EMAIL_BACKEND", "console")
    if backend == "console" and not is_production():
        print(f"[MOCK EMAIL] Verification link: {link}")
        return
    message = EmailMessage()
    message["From"] = os.environ["EMAIL_FROM"]
    message["To"] = recipient
    message["Subject"] = "Verify your email for Ticket Triage"
    message.set_content(f"Open this link to submit your complaint:\n\n{link}\n\n"
                        "This link expires in 30 minutes. If you did not request it, ignore this email.")
    if backend == "resend":
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}"},
            json={"from": message["From"], "to": [recipient],
                  "subject": message["Subject"], "text": message.get_content()},
            timeout=15,
        )
        response.raise_for_status()
    elif backend == "smtp":
        port = int(os.getenv("SMTP_PORT", "465"))
        context = ssl.create_default_context()
        if port == 465:
            server = smtplib.SMTP_SSL(os.environ["SMTP_HOST"], port, timeout=15, context=context)
        else:
            server = smtplib.SMTP(os.environ["SMTP_HOST"], port, timeout=15)
        with server:
            if port != 465:
                server.starttls(context=context)
            server.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
            server.send_message(message)
    else:
        raise RuntimeError("Choose EMAIL_BACKEND=resend or smtp")

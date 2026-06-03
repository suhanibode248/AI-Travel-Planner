import os
import smtplib
from email.message import EmailMessage

def send_itinerary_email(to_email: str, destination: str, plan_data: list):
    mail_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    mail_port = int(os.getenv("MAIL_PORT", 587))
    mail_username = os.getenv("MAIL_USERNAME", "")
    mail_password = os.getenv("MAIL_PASSWORD", "")
    mail_sender = os.getenv("MAIL_DEFAULT_SENDER", mail_username or "noreply@voyager.ai")

    if not mail_username or not mail_password:
        raise Exception("Email not configured in environment variables.")

    msg = EmailMessage()
    msg['Subject'] = f"Your Voyager Itinerary — {destination}"
    msg['From'] = mail_sender
    msg['To'] = to_email

    # Construct simple HTML based on the original email template
    html_content = f"""
    <html>
    <body>
        <h2>Your Trip to {destination}</h2>
    """
    for day in plan_data:
        html_content += f"<h3>{day.get('city', destination)}</h3>"
        html_content += f"<p>{day.get('plan', '').replace(chr(10), '<br>')}</p>"
    
    html_content += """
        <br><br>
        <p>Happy Travels!<br>The Voyager AI Team</p>
    </body>
    </html>
    """
    msg.add_alternative(html_content, subtype='html')

    try:
        with smtplib.SMTP(mail_server, mail_port) as server:
            server.starttls()
            server.login(mail_username, mail_password)
            server.send_message(msg)
    except Exception as e:
        raise Exception(f"Failed to send email: {e}")

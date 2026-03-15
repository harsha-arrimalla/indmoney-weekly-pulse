import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

def send_pulse_email(html_content, attachment_path=None, preamble=None):
    """
    Sends the pulse report email with optional attachment and preamble.
    """
    # Get configuration from .env
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    recipient_email = os.getenv("RECIPIENT_EMAIL")

    if not all([smtp_server, sender_email, sender_password, recipient_email]):
        raise ValueError("Missing SMTP configuration in .env file.")

    # Create message
    msg = MIMEMultipart()
    msg['From'] = f"INDMoney Pulse Bot <{sender_email}>"
    msg['To'] = recipient_email
    msg['Subject'] = f"INDMoney Weekly Pulse Report - {datetime.now().strftime('%Y-%m-%d')}"

    # Handle Preamble and HTML Body consolidation
    final_html = html_content
    if preamble:
        # Prepend preamble as a simple styled paragraph
        preamble_html = f'<p style="font-family: Arial, sans-serif; font-size: 16px; color: #333; margin-bottom: 20px;">{preamble}</p>'
        final_html = preamble_html + html_content

    # Attach HTML body
    msg.attach(MIMEText(final_html, 'html'))

    # Attach file if provided
    if attachment_path and os.path.exists(attachment_path):
        filename = os.path.basename(attachment_path)
        with open(attachment_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())

        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {filename}",
        )
        msg.attach(part)

    # Send email
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True, "Email sent successfully"
    except Exception as e:
        error_msg = str(e)
        print(f"Failed to send email: {error_msg}")
        return False, error_msg

if __name__ == "__main__":
    # Test run if pulse_report.json exists
    try:
        from email_generator import generate_html_email

        report_path = os.path.join(os.path.dirname(__file__), '..', 'Phase2', 'pulse_report.json')
        reviews_path = os.path.join(os.path.dirname(__file__), '..', 'reviews.json')

        if os.path.exists(report_path):
            with open(report_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)

            html = generate_html_email(report_data)
            success, message = send_pulse_email(html, attachment_path=reviews_path)
            if success:
                print("Test email sent successfully!")
            else:
                print("Test email failed.")
        else:
            print("Pulse report not found. Run Phase 2 first.")
    except Exception as e:
        print(f"Error during test: {e}")

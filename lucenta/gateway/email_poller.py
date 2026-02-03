import imaplib
import smtplib
import email
from email.mime.text import MIMEText
import time
import threading
import logging
from lucenta.gateway.session import SessionManager

class EmailGateway:
    def __init__(self, imap_server, smtp_server, email_user, email_pass, session_manager, triage_engine):
        self.imap_server = imap_server
        self.smtp_server = smtp_server
        self.email_user = email_user
        self.email_pass = email_pass
        self.session_manager = session_manager
        self.triage_engine = triage_engine
        self.running = False

    def poll(self):
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_user, self.email_pass)
            mail.select("inbox")

            # Search for all unread emails
            status, messages = mail.search(None, 'UNSEEN')
            if status != 'OK':
                return

            for num in messages[0].split():
                status, data = mail.fetch(num, '(RFC822)')
                if status != 'OK':
                    continue

                msg = email.message_from_bytes(data[0][1])
                sender = msg['From']
                subject = msg['Subject']

                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = msg.get_payload(decode=True).decode()

                logging.info(f"Received email from {sender}: {subject}")
                self.handle_email(sender, body)

            mail.logout()
        except Exception as e:
            logging.error(f"Email polling error: {e}")

    def handle_email(self, sender, body):
        # Extract user ID or use email as user ID
        user_id = sender

        if body.strip().upper() in ["OK", "YES", "Y"]:
            self.session_manager.grant_lease(user_id)
            self.send_email(sender, "Re: Lucenta Authorization", "Session lease granted for 30 minutes.")
            return

        if not self.session_manager.is_authorized(user_id):
            self.send_email(sender, "Re: Lucenta Authorization Required",
                            f"Your request '{body[:50]}...' requires approval. Reply 'OK' to authorize.")
            return

        response = self.triage_engine.generate(body)
        self.send_email(sender, f"Re: Lucenta Task Result", response)

    def send_email(self, recipient, subject, body):
        try:
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = self.email_user
            msg['To'] = recipient

            with smtplib.SMTP_SSL(self.smtp_server) as server:
                server.login(self.email_user, self.email_pass)
                server.send_message(msg)
        except Exception as e:
            logging.error(f"Failed to send email: {e}")

    def start_polling(self, interval=60):
        self.running = True
        def loop():
            while self.running:
                self.poll()
                time.sleep(interval)

        thread = threading.Thread(target=loop, daemon=True)
        thread.start()
        logging.info("Email polling started.")

    def stop_polling(self):
        self.running = False

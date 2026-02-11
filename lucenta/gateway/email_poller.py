import imaplib
import smtplib
import email
import asyncio
from email.mime.text import MIMEText
import time
import threading
import logging
from typing import Dict, List

class EmailGateway:
    """
    Email interface for Lucenta.
    Connects to the Central Orchestrator for task processing.
    """
    def __init__(self, imap_server, smtp_server, email_user, email_pass, orchestrator):
        self.imap_server = imap_server
        self.smtp_server = smtp_server
        self.email_user = email_user
        self.email_pass = email_pass
        self.orchestrator = orchestrator
        self.running = False
        self.user_histories: Dict[str, List[str]] = {}
        # We need a reference to the main event loop to run async tasks from the thread
        self.loop = asyncio.get_event_loop()

    def poll(self):
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_user, self.email_pass)
            mail.select("inbox")

            status, messages = mail.search(None, 'UNSEEN')
            if status != 'OK':
                return

            for num in messages[0].split():
                status, data = mail.fetch(num, '(RFC822)')
                if status != 'OK':
                    continue

                msg = email.message_from_bytes(data[0][1])
                sender = msg['From']
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = msg.get_payload(decode=True).decode()

                logging.info(f"Received email task from {sender}")
                
                # Dispatch async processing to the main loop
                asyncio.run_coroutine_threadsafe(
                    self.handle_email_async(sender, body),
                    self.loop
                )

            mail.logout()
        except Exception as e:
            logging.error(f"Email polling error: {e}")

    async def handle_email_async(self, sender, body):
        if sender not in self.user_histories:
            self.user_histories[sender] = []

        def sink(msg: str):
            logging.info(f"Email [{sender}] Status: {msg}")

        try:
            # Delegate to Orchestrator
            response = await self.orchestrator.process_message(
                body, 
                self.user_histories[sender], 
                sink
            )

            self.send_email(sender, "Re: Lucenta Task Result", response)
            
            # Update history
            self.user_histories[sender].append(f"User: {body}")
            self.user_histories[sender].append(f"Assistant: {response}")
            if len(self.user_histories[sender]) > 10:
                self.user_histories[sender] = self.user_histories[sender][-10:]

        except Exception as e:
            logging.error(f"Email Processing Error: {e}")
            self.send_email(sender, "Re: Lucenta Error", f"System Error: {e}")

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
        def loop_fn():
            while self.running:
                self.poll()
                time.sleep(interval)

        thread = threading.Thread(target=loop_fn, daemon=True)
        thread.start()
        logging.info("Email polling started.")

    def stop_polling(self):
        self.running = False

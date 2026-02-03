import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from lucenta.gateway.session import SessionManager

class TelegramGateway:
    def __init__(self, token: str, session_manager: SessionManager, triage_engine):
        self.token = token
        self.session_manager = session_manager
        self.triage_engine = triage_engine

        if not token:
            logging.warning("Telegram Token not provided. TelegramGateway will not function.")
            self.app = None
            return

        self.app = ApplicationBuilder().token(token).build()

        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.handle_message))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Lucenta at your service. Send me a message or a task.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        text = update.message.text

        # Simple HIL simulation: if message is "OK" or "Yes", grant lease
        if text.upper() in ["OK", "YES", "Y"]:
            self.session_manager.grant_lease(user_id)
            await update.message.reply_text("✅ Session lease granted for 30 minutes.")
            return

        # Check if user is asking for a task that needs approval
        if not self.session_manager.is_authorized(user_id):
            await update.message.reply_text(
                f"⚠️ Action: '{text}' requires approval.\n"
                "Reply 'OK' to authorize all tasks for 30 minutes."
            )
            return

        # "Phase 1 Flow" simulation
        if "arxiv" in text.lower():
            await update.message.reply_text("🔍 Routing task to Arxiv plugin...")
            # Simulate Auditor check
            if hasattr(self, 'auditor'):
                await update.message.reply_text("🛡️ Auditing plugin: arxiv-mcp...")
                # Mock a scan of a tool file
                label = self.auditor.get_security_label([{"file": "arxiv_tool.py", "risk_score": 2, "is_safe": True, "findings": []}])
                await update.message.reply_text(f"📊 Security Label: {label['label']} (Risk: {label['overall_risk_score']})")

            await update.message.reply_text("⚙️ Executing Docling for PDF parsing...")
            # Simulate result storage
            if hasattr(self, 'memory'):
                project = "ArxivResearch"
                self.memory.store_result(project, "summary.md", "Found 3 papers on LLM security.")
                await update.message.reply_text(f"📂 Results saved to shared project folder: {project}")

            await update.message.reply_text("Done! Summary is in the shared folder.")
        else:
            # General triage
            response = self.triage_engine.generate(text)
            await update.message.reply_text(response)

    def run(self):
        if self.app:
            logging.info("Starting Telegram Bot...")
            self.app.run_polling()
        else:
            logging.error("Cannot run Telegram bot without a valid token.")

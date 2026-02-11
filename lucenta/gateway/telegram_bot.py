import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from typing import Dict, List

class TelegramGateway:
    """
    Telegram interface for Lucenta.
    Delegates reasoning and tool execution to the central Orchestrator.
    """
    def __init__(self, token: str, orchestrator):
        self.token = token
        self.orchestrator = orchestrator
        self.user_histories: Dict[str, List[str]] = {}

        if not token:
            logging.warning("Telegram Token not provided. TelegramGateway will not function.")
            self.app = None
            return

        self.app = ApplicationBuilder().token(token).build()

        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.handle_message))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Lucenta at your service. I'm connected to the Central Orchestrator. Send me any task!")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        text = update.message.text

        if user_id not in self.user_histories:
            self.user_histories[user_id] = []

        # Sink to relay status updates to Telegram
        async def sink(msg: str):
            # In a more advanced version, we could use 'edit_message_text' for a live progress bar.
            # For now, we'll send a simple follow-up for major milestones if needed.
            logging.info(f"Telegram [{user_id}] Progress: {msg}")

        try:
            # We use the Orchestrator to handle the core logic
            # Note: Orchestrator currently handles its own HIL for CLI. 
            # For Telegram, we'll need to adapt HIL later, but for now it runs auto-approved or via general reasoning.
            response = await self.orchestrator.process_message(
                text, 
                self.user_histories[user_id], 
                sink
            )

            await update.message.reply_text(response)
            
            # Update local history for this specific user
            self.user_histories[user_id].append(f"User: {text}")
            self.user_histories[user_id].append(f"Assistant: {response}")

            # Keep history manageable
            if len(self.user_histories[user_id]) > 20:
                self.user_histories[user_id] = self.user_histories[user_id][-20:]

        except Exception as e:
            logging.error(f"Telegram Error: {e}")
            await update.message.reply_text(f"❌ System Error: {e}")

    def run(self):
        if self.app:
            logging.info("Starting Telegram Bot...")
            self.app.run_polling()
        else:
            logging.error("Cannot run Telegram bot without a valid token.")

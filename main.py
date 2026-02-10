import os
import json
import logging
import asyncio
from dotenv import load_dotenv
from lucenta.core.triage import TriageEngine
from lucenta.gateway.session import SessionManager
from lucenta.gateway.telegram_bot import TelegramGateway
from lucenta.gateway.email_poller import EmailGateway
from lucenta.core.scheduler import TaskRunner
from lucenta.core.memory import ProjectMemory
from lucenta.audit.scanner import SecurityAuditor

async def async_main():
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Load settings.json if exists
    settings = {}
    if os.path.exists("settings.json"):
        try:
            with open("settings.json", "r") as f:
                settings = json.load(f)
            logging.info("Loaded configuration from settings.json")
        except Exception as e:
            logging.error(f"Failed to load settings.json: {e}")

    # Init components
    # Merge settings.json and environment variables
    # Priority: Env > Settings
    local_provider_type = os.getenv("LOCAL_PROVIDER") or settings.get("default_app", "local").lower()
    if local_provider_type == "ollama":
        ollama_settings = settings.get("providers", {}).get("Ollama", {})
        local_config = {
            "provider_type": "ollama",
            "model": os.getenv("OLLAMA_MODEL") or ollama_settings.get("model", "llama3"),
            "base_url": os.getenv("OLLAMA_BASE_URL") or ollama_settings.get("base_url", "http://localhost:11434")
        }
    elif local_provider_type == "llamacpp":
        local_config = {
            "provider_type": "llamacpp",
            "binary_path": os.getenv("LLAMACPP_BINARY", "llama-cli"),
            "model_path": os.getenv("LLAMACPP_MODEL_PATH", "")
        }
    else:
        local_config = {
            "provider_type": "local",
            "binary_path": os.getenv("LOCAL_MODEL_BINARY", "echo"),
            "args": os.getenv("LOCAL_MODEL_ARGS", "Local model placeholder").split()
        }

    external_provider = "openai" # Default
    openai_settings = settings.get("providers", {}).get("OpenAI", {})
    external_config = {
        "provider": external_provider,
        "kwargs": {
            "api_key": os.getenv("OPENAI_API_KEY") or openai_settings.get("api_key", "missing"),
            "model": os.getenv("OPENAI_MODEL") or settings.get("default_model") or openai_settings.get("model", "gpt-4o-mini")
        }
    }

    # Extract provider_type from local_config for TriageEngine
    t_local_type = local_config.pop("provider_type")
    triage = TriageEngine({"provider": t_local_type, "kwargs": local_config}, external_config)
    session = SessionManager()
    memory = ProjectMemory()
    scheduler = TaskRunner()
    scheduler.start_background()
    auditor = SecurityAuditor(triage)

    logging.info("Lucenta Phase 1 components initialized.")

    # Telegram Gateway
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if telegram_token:
        tg_gateway = TelegramGateway(telegram_token, session, triage)
        # In a more advanced implementation, we'd pass auditor/memory to the gateway
        tg_gateway.auditor = auditor
        tg_gateway.memory = memory

        await tg_gateway.app.initialize()
        await tg_gateway.app.start()
        await tg_gateway.app.updater.start_polling()
        logging.info("Telegram Bot is polling...")
    else:
        logging.warning("No TELEGRAM_BOT_TOKEN found. Skipping Telegram Gateway.")

    # Email Gateway
    email_user = os.getenv("EMAIL_USER")
    if email_user:
        email_gateway = EmailGateway(
            os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com"),
            os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com"),
            email_user,
            os.getenv("EMAIL_PASS", ""),
            session,
            triage
        )
        email_gateway.start_polling()
        logging.info("Email Gateway started.")
    else:
        logging.warning("No EMAIL_USER found. Skipping Email Gateway.")

    # Keep the main loop running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down...")

if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass

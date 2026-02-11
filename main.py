import os
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

    # Init components
    local_provider_type = os.getenv("LOCAL_PROVIDER", "local")
    if local_provider_type == "ollama":
        local_config = {
            "provider_type": "ollama",
            "model": os.getenv("OLLAMA_MODEL", "llama3"),
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
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

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and openai_key != "your-key-here":
        external_config = {
            "provider": "openai",
            "kwargs": {
                "api_key": openai_key,
                "model": "gpt-4o-mini"
            }
        }
    else:
        external_config = None

    # Thresholds from env or defaults
    cpu_threshold = float(os.getenv("CPU_THRESHOLD", 70.0))
    mem_threshold = float(os.getenv("MEM_THRESHOLD", 70.0))

    # Extract provider_type from local_config for TriageEngine
    t_local_type = local_config.pop("provider_type")
    triage = TriageEngine(
        {"provider": t_local_type, "kwargs": local_config}, 
        external_config,
        cpu_threshold=cpu_threshold,
        mem_threshold=mem_threshold
    )
    session = SessionManager()
    memory = ProjectMemory()
    scheduler = TaskRunner()
    scheduler.start_background()
    auditor = SecurityAuditor(triage)

    logging.info("Lucenta Phase 1 components initialized.")

    # Initialize MCP Server Manager
    from lucenta.plugins.mcp_manager import MCPServerManager
    mcp_manager = MCPServerManager()
    
    if mcp_manager.servers:
        logging.info(f"Initializing {len(mcp_manager.servers)} MCP servers...")
        await mcp_manager.initialize_all_servers()
        
        # Log available tools
        server_info = mcp_manager.get_server_info()
        total_tools = sum(s['tool_count'] for s in server_info)
        logging.info(f"MCP Ready: {len(server_info)} servers, {total_tools} tools available")
        
        for info in server_info:
            logging.info(f"  - {info['name']}: {info['tool_count']} tools - {info['description']}")
    else:
        logging.warning("No MCP servers configured. Check mcp-config.json")
        mcp_manager = None

    # CLI Gateway - Add interaction via CMD
    from lucenta.gateway.cli import CLIGateway
    cli_gateway = CLIGateway(triage, session, mcp_manager, memory, scheduler)
    cli_task = asyncio.create_task(cli_gateway.start())



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
        # Wait for CLI task to finish if it's running
        if cli_task:
            await cli_task
        else:
            while True:
                await asyncio.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down...")


if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass

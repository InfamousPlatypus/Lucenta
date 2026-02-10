# Lucenta Quick Startup

Lucenta is designed for resource-constrained hosts and prioritizes security and isolation.

## 🚀 Installation

```bash
# 1. Clone and enter the repo
git clone https://github.com/user/lucenta.git
cd lucenta

# 2. Run the setup script
# This sets up the 'lucenta-shared' group and udev rules for optional hardware.
chmod +x setup.sh
./setup.sh

# 3. Configure your API keys in settings.json or .env
# Fill in keys for OpenAI, Anthropic, or Gemini. settings.json is shared with LlamaHUD.
nano settings.json

# 4. Start Lucenta
python3 main.py
```

## 🛠 Basic Usage

- **Triage:** Lucenta automatically monitors system load (CPU/RAM). High-compute tasks are routed to external APIs if local resources are low.
- **Audit:** All plugins are scanned for security "smells" before execution.
- **Approval:** Check your Telegram (or CLI) for HIL (Human-in-the-Loop) approval requests for sensitive commands.
- **Shared Storage:** Results are stored in `./lucenta-shared/` for persistent access.

# Lucenta (v0.1-Alpha) - Phase 1: Legacy Guard

Lucenta is a security-first, hardware-agnostic AI orchestrator designed for resource-constrained hosts. It protects your system by auditing all external tools and routing tasks based on real-time system load.

## 🚀 Quick Startup

Get Lucenta up and running on your legacy hardware in minutes:

```bash
# 1. Clone and enter the repo
git clone https://github.com/user/lucenta.git
cd lucenta

# 2. Run the setup script (sets up groups, udev rules, and .env)
chmod +x setup.sh
./setup.sh

# 3. Configure your API keys in .env
nano .env

# 4. Start Lucenta
python3 main.py
```

## 🛠 Phase 1 Architecture

### 1. Universal Backend & Triage
Lucenta abstracts LLM providers (OpenAI, Anthropic, Gemini, **Ollama**, and **llama.cpp**). The **Triage Engine** monitors CPU and RAM. If the host is struggling, it automatically routes "Thought" tasks to a cheap external API (like GPT-4o-mini).

### 2. Security Smell Test
Before any plugin runs, Lucenta's **Security Auditor** performs a static analysis scan. It flags:
- **Unauthorized Egress**: Hardcoded IPs or network calls.
- **Filesystem Escapes**: Access to sensitive system directories.
- **Obfuscation**: Suspicious strings or `eval()` blocks.

### 3. Communications Gateway
Reach Lucenta via **Telegram** or **Email**.
- **HIL (Human-in-the-Loop)**: Sensitive actions require a "Yes" via chat.
- **Session Lease**: An approval grants a 30-minute window for similar tasks.

### 4. Docling & MCP Integration
Integrated **Docling** for OCR and document parsing. Lucenta acts as an **MCP Client**, running potentially risky plugins in sandboxed Docker containers.

### 5. Proactive Scheduler & Project Memory
- **Task Runner**: Persists tasks across reboots using SQLite.
- **Shared Memory**: Research results are saved to `./lucenta-shared/`, managed by the `lucenta-shared` Unix group for multi-user access.

## 📁 Project Structure
```text
lucenta/
├── audit/              # Static analysis & Security reporting
├── core/               # Triage engine, Scheduler, and Memory
├── gateway/            # Telegram and Email interfaces
├── plugins/            # MCP Client and Sandboxing logic
└── lucenta-shared/     # Project-based shared storage
```

## ⚖️ License
MIT

#!/bin/bash
# setup.sh - Lucenta Phase 1 Setup

echo "🚀 Setting up Lucenta..."

# 1. Create lucenta-shared group
if getent group lucenta-shared > /dev/null; then
    echo "✅ Group 'lucenta-shared' already exists."
else
    echo "Creating 'lucenta-shared' group (may require sudo)..."
    sudo groupadd lucenta-shared || echo "⚠️ Failed to create group. Please run: sudo groupadd lucenta-shared"
    sudo usermod -aG lucenta-shared $USER || echo "⚠️ Failed to add user to group."
    echo "Done. You may need to log out and back in for group changes to take effect."
fi

# 2. Configure udev rules for Intel NCS2 (Neural Compute Stick 2)
if [ -d "/etc/udev/rules.d" ]; then
    echo "Configuring udev rules for Intel NCS2..."
    echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"' | sudo tee /etc/udev/rules.d/97-ncs2.rules > /dev/null
    sudo udevadm control --reload-rules || true
    sudo udevadm trigger || true
    echo "✅ udev rules configured."
fi

# 3. Generate .env template
if [ ! -f .env ]; then
    echo "Generating .env template..."
    cat <<EOF > .env
# Lucenta Configuration
# Local LLM Provider - Using Ollama with smallest model
LOCAL_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5-coder:1.5b-base
OLLAMA_BASE_URL=http://localhost:11434

# llama.cpp Config (alternative)
# LLAMACPP_BINARY=llama-cli
# LLAMACPP_MODEL_PATH=/path/to/model.gguf

# External API fallback (optional - for when local resources are constrained)
# OPENAI_API_KEY=your-key-here
# ANTHROPIC_API_KEY=your-key-here
# GEMINI_API_KEY=your-key-here

# Communication Gateways (optional)
# TELEGRAM_BOT_TOKEN=your-telegram-token
# EMAIL_USER=your-email@example.com
# EMAIL_PASS=your-email-password
# EMAIL_IMAP_SERVER=imap.gmail.com
# EMAIL_SMTP_SERVER=smtp.gmail.com

# MCP Server Configuration
MCP_SERVERS_PATH=/path/to/mcp-servers
# Set to true to use Podman instead of Docker (default: false)
USE_PODMAN=false

# NASA API Key (optional)
# NASA_API_KEY=DEMO_KEY

# Hugging Face API Token (optional)
# HUGGING_FACE_API_TOKEN=hf_your_token_here
EOF
    echo "✅ .env template created. Please edit it with your configuration."
fi

# 4. Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "✨ Setup complete!"
echo "Run Lucenta with: python3 main.py"

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
# Model Providers
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=

# Local Model Config
# Options for LOCAL_PROVIDER: local, ollama, llamacpp
LOCAL_PROVIDER=local
LOCAL_MODEL_BINARY=echo
LOCAL_MODEL_ARGS="[Local Mode] System load low, using local echo."

# Ollama Config
OLLAMA_MODEL=llama3
OLLAMA_BASE_URL=http://localhost:11434

# llama.cpp Config
LLAMACPP_BINARY=llama-cli
LLAMACPP_MODEL_PATH=models/7b/ggml-model-f16.gguf

# Communications
TELEGRAM_BOT_TOKEN=
EMAIL_IMAP_SERVER=imap.gmail.com
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_USER=
EMAIL_PASS=

# System Triage
CPU_THRESHOLD=70
MEM_THRESHOLD=70
EOF
    echo "✅ .env template created. Please fill in your API keys."
fi

# 4. Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "✨ Setup complete!"
echo "Run Lucenta with: python3 main.py"

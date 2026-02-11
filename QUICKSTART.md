# 🚀 Lucenta with MCP Servers - Quick Start Guide

This guide will help you get Lucenta running with MCP servers using Ollama and Podman (or Docker).

## ✅ Prerequisites

- **Python 3.8+** installed
- **Node.js 18+** installed (for MCP servers)
- **Ollama** installed and running
- **Podman** or **Docker** (optional, for sandboxed MCP servers)

## 🎯 Quick Start

### Option 1: Cross-Platform Python Script (Recommended)

```bash
# Run the startup script - works on Windows, Linux, macOS
python start.py
```

### Option 2: Platform-Specific Scripts

**Windows (PowerShell):**
```powershell
.\start-lucenta.ps1
```

**Linux/macOS (Bash):**
```bash
chmod +x setup.sh
./setup.sh
python3 main.py
```

## 📋 What Gets Set Up

1. **Ollama Configuration**: Uses your smallest model (`qwen2.5-coder:1.5b-base`)
2. **MCP Servers**: 11 enabled servers with 50+ tools:
   - arXiv (academic papers)
   - Open Notify (ISS tracking)
   - Nominatim (geocoding)
   - Open Meteo (weather)
   - USGS Earthquake
   - PubMed (medical research)
   - NASA APOD & Asteroids
   - Open Elevation
   - Hugging Face
   - IBM Quantum

3. **Container Runtime**: Docker by default, Podman if `USE_PODMAN=true`

## ⚙️ Configuration

Edit `.env` to customize:

```bash
# Your smallest Ollama model (already configured)
OLLAMA_MODEL=qwen2.5-coder:1.5b-base

# Use Podman instead of Docker
USE_PODMAN=true

# MCP servers path (update if different)
MCP_SERVERS_PATH=C:\Users\mark\public-apis\mcp-servers

# Optional: Add external API fallback
# OPENAI_API_KEY=your-key-here
```

## 🧪 Testing MCP Integration

Test that MCP servers are working:

```bash
python test_mcp.py
```

This will:
- Load all enabled MCP servers
- List available tools
- Test a sample tool call

## 🛠️ Managing MCP Servers

### Enable/Disable Servers

Edit `mcp-config.json`:

```json
{
  "mcpServers": {
    "arxiv": {
      "enabled": true,  // Change to false to disable
      ...
    }
  }
}
```

### Add More Servers

1. Add server to `mcp-config.json`
2. Build the server: `cd mcp-servers/[name] && npm install && npm run build`
3. Restart Lucenta

## 📊 Current Setup

**Enabled Servers (11):**
- ✅ arxiv (5 tools)
- ✅ open-notify (4 tools)
- ✅ nominatim (6 tools)
- ✅ open-meteo (4 tools)
- ✅ usgs-earthquake (5 tools)
- ✅ pubmed (3 tools)
- ✅ nasa-apod (4 tools)
- ✅ nasa-asteroids (5 tools)
- ✅ open-elevation (2 tools)
- ✅ hugging-face (6 tools)
- ✅ ibm-quantum (3 tools)

**Disabled Servers (5):**
- ⏸️ gbif
- ⏸️ uk-carbon
- ⏸️ openaq
- ⏸️ geocode-xyz
- ⏸️ overpass
- ⏸️ roboflow

## 🔧 Troubleshooting

### Ollama Not Running
```bash
# Start Ollama
ollama serve

# Verify it's running
ollama list
```

### Model Not Found
```bash
# Pull your model
ollama pull qwen2.5-coder:1.5b-base

# List available models
ollama list
```

### MCP Servers Not Building
```bash
# Manually build a specific server
cd C:\Users\mark\public-apis\mcp-servers\arxiv
npm install
npm run build
```

### Podman vs Docker
```bash
# Test Podman
podman --version

# If using Docker instead, set in .env:
USE_PODMAN=false
```

## 🎮 Using Lucenta

Once started, Lucenta will:
1. Initialize with Ollama using your smallest model
2. Load all enabled MCP servers
3. Make 50+ tools available for use
4. Route tasks based on system load (local vs external API)

### Example Tool Usage

The MCP manager automatically routes tool calls:

```python
# In your code or via Telegram/Email gateway
await mcp_manager.smart_call_tool('search_arxiv', {
    'query': 'quantum computing',
    'max_results': 5
})
```

## 📁 Project Structure

```
Lucenta/
├── .env                    # Your configuration (not in git)
├── .env.sample            # Template configuration
├── .gitignore             # Excludes .env from git
├── mcp-config.json        # MCP server configuration
├── start.py               # Cross-platform startup (recommended)
├── start-lucenta.ps1      # Windows PowerShell startup
├── setup.sh               # Linux/macOS setup
├── test_mcp.py            # MCP integration test
├── main.py                # Lucenta main entry point
├── lucenta/
│   ├── core/              # Triage, scheduler, memory
│   ├── gateway/           # Telegram, email interfaces
│   ├── plugins/
│   │   ├── mcp_client.py  # Basic MCP client (Docker/Podman)
│   │   └── mcp_manager.py # Multi-server MCP manager
│   └── audit/             # Security auditor
```

## 🚦 Next Steps

1. **Test the setup**: `python test_mcp.py`
2. **Start Lucenta**: `python start.py`
3. **Configure gateways** (optional): Add Telegram/Email credentials to `.env`
4. **Enable more servers**: Edit `mcp-config.json` to enable additional APIs

## 📚 Additional Resources

- [MCP Servers Documentation](C:\Users\mark\public-apis\mcp-servers\README.md)
- [Lucenta Architecture](README.md)
- [MCP Protocol Docs](https://modelcontextprotocol.io)

## 💡 Tips

- **Start small**: The default 11 enabled servers is a good balance
- **Monitor resources**: Lucenta's triage engine will route to external APIs if local resources are constrained
- **Use the smallest model**: `qwen2.5-coder:1.5b-base` is already configured for you
- **Cross-platform**: Use `start.py` for consistent behavior across OS

---

**Ready to go!** Run `python start.py` to get started. 🎉

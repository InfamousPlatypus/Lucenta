#!/usr/bin/env python3
"""
Cross-platform startup script for Lucenta with MCP servers
Works on Windows, Linux, and macOS
"""
import os
import sys
import json
import subprocess
import shutil
from pathlib import Path
from dotenv import load_dotenv

def print_header(text):
    print("\n" + "=" * 50)
    print(f"  {text}")
    print("=" * 50 + "\n")

def check_env():
    """Check if .env exists, create from sample if not"""
    if not Path(".env").exists():
        print("⚠️  No .env file found!")
        if Path(".env.sample").exists():
            print("Creating .env from .env.sample...")
            shutil.copy(".env.sample", ".env")
            print("✅ Created .env - Please edit it with your configuration")
            print("\nPress Enter to continue or Ctrl+C to exit and configure .env...")
            input()
        else:
            print("❌ No .env.sample found! Cannot create .env")
            return False
    return True

def check_ollama():
    """Check if Ollama is running"""
    print("🔍 Checking Ollama...")
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            print("✅ Ollama is running")
            return True
    except:
        pass
    
    print("⚠️  Ollama is not running!")
    print("Please start Ollama manually: ollama serve")
    return False

def check_model(model_name):
    """Check if the specified model exists"""
    print(f"🤖 Checking model: {model_name}")
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            check=True
        )
        if model_name in result.stdout:
            print(f"✅ Model {model_name} is available")
            return True
        else:
            print(f"⚠️  Model {model_name} not found!")
            print("\nAvailable models:")
            print(result.stdout)
            print(f"\nPlease pull the model first: ollama pull {model_name}")
            return False
    except Exception as e:
        print(f"⚠️  Could not check Ollama models: {e}")
        return False

def build_mcp_servers(mcp_path, config_file="mcp-config.json"):
    """Build enabled MCP servers"""
    if not Path(mcp_path).exists():
        print(f"⚠️  MCP servers path not found: {mcp_path}")
        print("MCP servers will not be available.")
        return False
    
    print_header("Building MCP Servers")
    
    # Read config to find enabled servers
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        enabled_servers = [
            name for name, server in config.get('mcpServers', {}).items()
            if server.get('enabled', False)
        ]
        
        print(f"Building {len(enabled_servers)} enabled servers...")
        
        build_errors = []
        for server_name in enabled_servers:
            server_path = Path(mcp_path) / server_name
            if not server_path.exists():
                print(f"  ⚠️  {server_name} directory not found")
                continue
            
            print(f"  Building {server_name}...", end=" ")
            
            # Check if already built
            dist_file = server_path / "dist" / "index.js"
            if dist_file.exists():
                print("✅ Already built")
                continue
            
            # Install dependencies if needed
            if not (server_path / "node_modules").exists():
                subprocess.run(
                    "npm install",
                    cwd=server_path,
                    capture_output=True,
                    check=False,
                    shell=True
                )
            
            # Build
            result = subprocess.run(
                "npm run build",
                cwd=server_path,
                capture_output=True,
                check=False,
                shell=True
            )

            
            if result.returncode == 0:
                print("✅ Built")
            else:
                print("❌ Failed")
                build_errors.append(server_name)
        
        if build_errors:
            print(f"\n⚠️  Some servers failed to build: {', '.join(build_errors)}")
            print("Lucenta will continue with available servers.")
        else:
            print("\n✅ All MCP servers built successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Error building MCP servers: {e}")
        return False

def main():
    print_header("Lucenta Startup with MCP Servers")
    
    # Check .env
    if not check_env():
        return 1
    
    # Load environment
    load_dotenv()
    
    # Check Ollama
    if not check_ollama():
        print("\nContinuing anyway... Lucenta may fall back to external APIs")
    
    # Check model
    model_name = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:1.5b-base")
    if not check_model(model_name):
        print("\nContinuing anyway... Lucenta may encounter errors")
    
    # Build MCP servers
    mcp_path = os.getenv("MCP_SERVERS_PATH", "")
    if mcp_path and Path(mcp_path).exists():
        build_mcp_servers(mcp_path)
    else:
        print("\n⚠️  MCP_SERVERS_PATH not set or invalid")
        print("MCP servers will not be available.")
    
    # Start Lucenta
    print_header("Starting Lucenta")
    
    try:
        subprocess.run([sys.executable, "main.py"], check=True)
    except KeyboardInterrupt:
        print("\n\n✅ Lucenta stopped")
    except Exception as e:
        print(f"\n❌ Error running Lucenta: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

# Lucenta Startup Script with MCP Servers
# This script builds MCP servers and starts Lucenta

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Lucenta Startup with MCP Servers" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  No .env file found!" -ForegroundColor Yellow
    Write-Host "Creating .env from .env.sample..." -ForegroundColor Yellow
    Copy-Item ".env.sample" ".env"
    Write-Host "✅ Created .env - Please edit it with your configuration" -ForegroundColor Green
    Write-Host ""
    Write-Host "Press any key to continue or Ctrl+C to exit and configure .env..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

# Load environment variables
Write-Host "📋 Loading configuration..." -ForegroundColor Cyan
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^#][^=]+)=(.*)$') {
        $name = $matches[1].Trim()
        $value = $matches[2].Trim()
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

# Check if Ollama is running
Write-Host "🔍 Checking Ollama..." -ForegroundColor Cyan
try {
    $null = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -Method GET -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✅ Ollama is running" -ForegroundColor Green
}
catch {
    Write-Host "⚠️  Ollama is not running!" -ForegroundColor Yellow
    Write-Host "Starting Ollama..." -ForegroundColor Yellow
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

# Check if model exists
$ollamaModel = $env:OLLAMA_MODEL
if (-not $ollamaModel) {
    $ollamaModel = "qwen2.5-coder:1.5b-base"
}

Write-Host "🤖 Checking model: $ollamaModel" -ForegroundColor Cyan
$models = ollama list | Select-String -Pattern $ollamaModel
if (-not $models) {
    Write-Host "⚠️  Model $ollamaModel not found!" -ForegroundColor Yellow
    Write-Host "Available models:" -ForegroundColor Yellow
    ollama list
    Write-Host ""
    Write-Host "Please pull the model first: ollama pull $ollamaModel" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Model $ollamaModel is available" -ForegroundColor Green

# Build MCP servers
$mcpPath = $env:MCP_SERVERS_PATH
if (-not $mcpPath) {
    $mcpPath = "C:\Users\mark\public-apis\mcp-servers"
}

if (Test-Path $mcpPath) {
    Write-Host ""
    Write-Host "🔧 Building MCP servers..." -ForegroundColor Cyan
    
    # Read mcp-config.json to see which servers are enabled
    $mcpConfig = Get-Content "mcp-config.json" | ConvertFrom-Json
    $enabledServers = @()
    
    foreach ($serverName in $mcpConfig.mcpServers.PSObject.Properties.Name) {
        $server = $mcpConfig.mcpServers.$serverName
        if ($server.enabled -eq $true) {
            $enabledServers += $serverName
        }
    }
    
    Write-Host "Building $($enabledServers.Count) enabled servers..." -ForegroundColor Cyan
    
    $buildErrors = @()
    foreach ($serverName in $enabledServers) {
        $serverPath = Join-Path $mcpPath $serverName
        if (Test-Path $serverPath) {
            Write-Host "  Building $serverName..." -ForegroundColor Gray
            Push-Location $serverPath
            
            # Install dependencies if needed
            if (-not (Test-Path "node_modules")) {
                npm install --silent 2>&1 | Out-Null
            }
            
            # Build
            npm run build 2>&1 | Out-Null
            if ($LASTEXITCODE -ne 0) {
                $buildErrors += $serverName
                Write-Host "    ❌ Failed" -ForegroundColor Red
            }
            else {
                Write-Host "    ✅ Built" -ForegroundColor Green
            }
            
            Pop-Location
        }
    }
    
    if ($buildErrors.Count -gt 0) {
        Write-Host ""
        Write-Host "⚠️  Some servers failed to build: $($buildErrors -join ', ')" -ForegroundColor Yellow
        Write-Host "Lucenta will continue with available servers." -ForegroundColor Yellow
    }
    else {
        Write-Host "✅ All MCP servers built successfully" -ForegroundColor Green
    }
}
else {
    Write-Host "⚠️  MCP servers path not found: $mcpPath" -ForegroundColor Yellow
    Write-Host "MCP servers will not be available." -ForegroundColor Yellow
}

# Start Lucenta
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting Lucenta" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

python main.py

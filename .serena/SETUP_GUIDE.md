# Serena Setup Guide for FormatIQ_v3

## Quick Start

### Activating the Project

Once your Serena server is running, activate this project with:

```bash
# In any Serena-enabled IDE or terminal
> activate project /home/ajk/FormatIQ_v3
```

Or simply:
```bash
> activate project formatiq_v3
```

## Running Serena Server

### Option 1: Keep Current Server Running (RECOMMENDED)

Your Serena server is already running! You can:

1. **Check running instances:**
   ```bash
   ps aux | grep serena | grep -v grep
   ```

2. **Access the web dashboard:**
   - Open browser: http://localhost:24282/dashboard/
   - If port conflicts, try: http://localhost:24283/ or :24284

3. **View logs in real-time:**
   ```bash
   tail -f ~/.serena/logs/$(date +%Y-%m-%d)/mcp_*.txt
   ```

### Option 2: Start New Server Instance

If you need to restart or run in a different terminal:

```bash
# Navigate to Serena installation
cd /home/ajk/Serena/serena

# Start with default context
uv run serena start-mcp-server --context ide-assistant

# Or with custom config
uv run serena start-mcp-server --context ide-assistant --config /home/ajk/FormatIQ_v3/.serena/serena_config.yml
```

### Option 3: Run as Background Service

```bash
# Create a systemd service (one-time setup)
cat > ~/.config/systemd/user/serena.service << 'EOF'
[Unit]
Description=Serena Code Agent MCP Server
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/ajk/Serena/serena
ExecStart=/usr/bin/uv run serena start-mcp-server --context ide-assistant
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

# Enable and start the service
systemctl --user daemon-reload
systemctl --user enable serena.service
systemctl --user start serena.service

# Check status
systemctl --user status serena.service

# View logs
journalctl --user -u serena.service -f
```

### Useful Commands

```bash
# Stop running Serena instances
pkill -f "serena start-mcp-server"

# Restart Serena
pkill -f "serena start-mcp-server" && cd /home/ajk/Serena/serena && uv run serena start-mcp-server --context ide-assistant

# Check Serena version
cd /home/ajk/Serena/serena && uv run serena --version
```

## IDE Integration

### VS Code (Primary IDE)

#### 1. Install MCP Extension

```bash
# Install Claude Desktop or MCP-compatible extension
# Recommended: "Anthropic MCP" or "Claude Dev"
code --install-extension anthropic.claude-dev
```

#### 2. Configure MCP Settings

Create/edit: `~/.config/Code/User/settings.json`

```json
{
  "mcp.servers": {
    "serena": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/home/ajk/Serena/serena",
        "serena",
        "start-mcp-server",
        "--context",
        "ide-assistant"
      ],
      "env": {},
      "enabled": true
    }
  },
  
  "serena.projectPath": "/home/ajk/FormatIQ_v3",
  "serena.autoActivate": true,
  
  // Optional: Symbol navigation shortcuts
  "keyboard.shortcuts": [
    {
      "key": "ctrl+shift+s",
      "command": "serena.findSymbol"
    },
    {
      "key": "ctrl+shift+r",
      "command": "serena.findReferences"
    }
  ]
}
```

#### 3. Workspace Settings (Recommended)

Create: `.vscode/settings.json` in project root:

```json
{
  "serena.enabled": true,
  "serena.projectPath": "${workspaceFolder}",
  
  "python.analysis.extraPaths": [
    "${workspaceFolder}/apps/backend",
    "${workspaceFolder}/apps/backend/app"
  ],
  
  "typescript.tsdk": "apps/frontend/node_modules/typescript/lib",
  
  "files.watcherExclude": {
    "**/.git/objects/**": true,
    "**/.git/subtree-cache/**": true,
    "**/node_modules/**": true,
    "**/.venv/**": true,
    "**/__pycache__/**": true,
    "**/htmlcov/**": true
  }
}
```

### PyCharm / WebStorm (JetBrains IDEs)

#### 1. MCP Plugin Installation

```bash
# Wait for official Serena JetBrains plugin release
# Or use external tools integration
```

#### 2. External Tools Configuration

**Settings → Tools → External Tools → Add:**

**Tool 1: Serena Find Symbol**
- Name: `Serena Find Symbol`
- Program: `/usr/bin/python3`
- Arguments: `-m serena_tools find-symbol "$SelectedText$" --project /home/ajk/FormatIQ_v3`
- Working directory: `$ProjectFileDir$`

**Tool 2: Serena Get Overview**
- Name: `Serena Overview`
- Program: `/usr/bin/python3`
- Arguments: `-m serena_tools get-overview "$FilePath$" --project /home/ajk/FormatIQ_v3`
- Working directory: `$ProjectFileDir$`

#### 3. Keyboard Shortcuts

**Settings → Keymap → External Tools:**
- Serena Find Symbol: `Ctrl+Shift+Alt+S`
- Serena Overview: `Ctrl+Shift+Alt+O`

### Claude Desktop Integration

#### Configuration File

Create/edit: `~/.config/claude-desktop/config.json`

```json
{
  "mcpServers": {
    "serena": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/home/ajk/Serena/serena",
        "serena",
        "start-mcp-server",
        "--context",
        "ide-assistant"
      ],
      "env": {
        "SERENA_PROJECT": "/home/ajk/FormatIQ_v3"
      }
    }
  }
}
```

### Neovim Integration

Add to your `~/.config/nvim/init.lua` or `~/.vimrc`:

```lua
-- Serena MCP integration
vim.g.serena_project_path = '/home/ajk/FormatIQ_v3'

-- Keybindings
vim.keymap.set('n', '<leader>ss', ':!serena-cli find-symbol <cword><CR>')
vim.keymap.set('n', '<leader>so', ':!serena-cli get-overview %<CR>')
vim.keymap.set('n', '<leader>sr', ':!serena-cli find-references <cword> %<CR>')
```

## Best Practices for FormatIQ_v3

### 1. Project Activation Workflow

```bash
# Always activate project first in new Serena session
> activate project formatiq_v3

# Verify activation
> get_current_config
```

### 2. Efficient Code Navigation

**DO:**
```bash
# Start with overview
> get_symbols_overview apps/backend/app/main.py

# Then drill down
> find_symbol create_app --relative-path apps/backend/app/main.py --include-body true

# Find usages
> find_referencing_symbols create_app apps/backend/app/main.py
```

**DON'T:**
```bash
# Avoid reading entire files unnecessarily
> read_file apps/backend/app/main.py  # ❌ Use symbols instead!
```

### 3. Multi-Language Navigation

```bash
# Backend (Python)
> find_symbol OptimizationService --relative-path apps/backend

# Frontend (TypeScript)
> find_symbol useAppActions --relative-path apps/frontend

# Cross-reference search
> search_for_pattern "api/v1/resumes" --relative-path .
```

### 4. Memory Management

```bash
# Save important architecture notes
> write_memory architecture "FormatIQ uses FastAPI backend with Next.js frontend..."

# Read before starting features
> list_memories
> read_memory architecture
```

### 5. Testing Integration

```bash
# Find test files for a feature
> find_file "*test*.py" apps/backend/tests

# Get test structure
> get_symbols_overview apps/backend/tests/test_resume_service.py

# Find what's tested
> find_referencing_symbols ResumeService apps/backend/app/services/resume_service.py
```

## Performance Tips

### 1. Language Server Health

```bash
# Check if language servers are running properly
ps aux | grep -E "pylsp|typescript-language-server"

# Restart language servers if needed (from Serena)
> restart_language_server python
> restart_language_server typescript
```

### 2. Monitor Token Usage

With `record_tool_usage_stats: true` in config:
- Open dashboard: http://localhost:24282/dashboard/
- View "Token Usage" tab
- Optimize queries that use excessive tokens

### 3. Optimize Search Patterns

```bash
# ✅ Good: Specific patterns
> search_for_pattern "class.*Service" --paths-include-glob "**/*.py" --relative-path apps/backend/app/services

# ❌ Bad: Too broad
> search_for_pattern ".*" --relative-path apps/backend
```

## Troubleshooting

### Server Won't Start

```bash
# Check for port conflicts
lsof -i :24282

# Kill conflicting processes
pkill -f "serena start-mcp-server"

# Start fresh
cd /home/ajk/Serena/serena && uv run serena start-mcp-server --context ide-assistant
```

### Language Server Not Working

```bash
# Check language server logs
tail -f ~/.serena/logs/$(date +%Y-%m-%d)/*.txt

# Reinstall language servers
pip install --upgrade python-lsp-server
npm install -g typescript-language-server typescript
```

### Project Not Activating

```bash
# Verify project.yml exists
cat /home/ajk/FormatIQ_v3/.serena/project.yml

# Check global config
cat ~/.serena/serena_config.yml | grep -A 5 projects

# Force re-register
> activate project /home/ajk/FormatIQ_v3
```

## Environment Variables

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# Serena shortcuts
export SERENA_HOME="/home/ajk/Serena/serena"
export SERENA_PROJECT="/home/ajk/FormatIQ_v3"

alias serena-start='cd $SERENA_HOME && uv run serena start-mcp-server --context ide-assistant'
alias serena-stop='pkill -f "serena start-mcp-server"'
alias serena-restart='serena-stop && serena-start'
alias serena-logs='tail -f ~/.serena/logs/$(date +%Y-%m-%d)/mcp_*.txt'
alias serena-dashboard='xdg-open http://localhost:24282/dashboard/'
```

## Next Steps

1. **Activate the project** in your current Serena session
2. **Test navigation** with a simple query:
   ```bash
   > find_symbol main --relative-path apps/backend/app/main.py
   ```
3. **Create initial memories** for your architecture patterns
4. **Configure your primary IDE** (VS Code, PyCharm, etc.)
5. **Set up keyboard shortcuts** for frequent operations

---

**Dashboard:** http://localhost:24282/dashboard/  
**Logs:** `~/.serena/logs/`  
**Config:** `/home/ajk/FormatIQ_v3/.serena/`

# MCP Integration Guide - Serena for FormatIQ_v3

## Overview

This guide covers integrating Serena with various MCP-compatible clients using the configuration files provided.

**Configuration Files:**
- `mcp-config.json` - JSON format (FormatIQ_v3 specific)
- `mcp-config.toml` - TOML format (FormatIQ_v3 specific)
- `mcp-config-template.json` - Reusable template (JSON)
- `mcp-config-template.toml` - Reusable template (TOML)

---

## Quick Start for FormatIQ_v3

### Claude Desktop

**Step 1:** Copy the FormatIQ-specific config
```bash
mkdir -p ~/.config/claude-desktop
cp /home/ajk/FormatIQ_v3/.serena/mcp-config.json ~/.config/claude-desktop/config.json
```

**Step 2:** Restart Claude Desktop

**Step 3:** In Claude chat, activate the project:
```
> activate project formatiq_v3
```

---

### VS Code with MCP Extension

**Step 1:** Install MCP extension
```bash
code --install-extension anthropic.claude-dev
# OR
code --install-extension continue.continue
```

**Step 2:** Create workspace settings
```bash
mkdir -p /home/ajk/FormatIQ_v3/.vscode
cp /home/ajk/FormatIQ_v3/.serena/mcp-config.json /home/ajk/FormatIQ_v3/.vscode/mcp-settings.json
```

**Step 3:** Configure VS Code settings

Add to `.vscode/settings.json`:
```json
{
  "mcp.configPath": "${workspaceFolder}/.vscode/mcp-settings.json",
  "mcp.autoStart": true,
  "mcp.servers": {
    "serena": {
      "enabled": true
    }
  }
}
```

**Step 4:** Reload VS Code window
```
Ctrl+Shift+P → "Developer: Reload Window"
```

---

### Cursor IDE

**Step 1:** Copy configuration
```bash
mkdir -p /home/ajk/FormatIQ_v3/.cursor
cp /home/ajk/FormatIQ_v3/.serena/mcp-config.json /home/ajk/FormatIQ_v3/.cursor/mcp-config.json
```

**Step 2:** Cursor automatically loads `.cursor/mcp-config.json`

**Step 3:** Restart Cursor

---

### Windsurf IDE

**Step 1:** Navigate to Settings → Extensions → MCP

**Step 2:** Add new MCP server with these values:
- **Name:** Serena
- **Command:** `uv`
- **Args:** 
  ```
  run
  --directory
  /home/ajk/Serena/serena
  serena
  start-mcp-server
  --context
  ide-assistant
  ```
- **Environment Variables:**
  - `SERENA_PROJECT` = `/home/ajk/FormatIQ_v3`
  - `SERENA_AUTO_ACTIVATE` = `true`
  - `SERENA_LOG_LEVEL` = `20`

**Step 3:** Enable the server and restart Windsurf

---

### Zed Editor

**Step 1:** Edit Zed settings
```bash
nano ~/.config/zed/settings.json
```

**Step 2:** Add MCP configuration:
```json
{
  "language_servers": {
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
      "environment": {
        "SERENA_PROJECT": "/home/ajk/FormatIQ_v3",
        "SERENA_AUTO_ACTIVATE": "true"
      }
    }
  }
}
```

**Step 3:** Restart Zed

---

### Neovim with MCP Support

**Step 1:** Install MCP plugin (using lazy.nvim)

Add to `~/.config/nvim/lua/plugins/mcp.lua`:
```lua
return {
  "anthropics/mcp.nvim",
  config = function()
    require("mcp").setup({
      servers = {
        serena = {
          command = "uv",
          args = {
            "run",
            "--directory",
            "/home/ajk/Serena/serena",
            "serena",
            "start-mcp-server",
            "--context",
            "ide-assistant"
          },
          env = {
            SERENA_PROJECT = "/home/ajk/FormatIQ_v3",
            SERENA_AUTO_ACTIVATE = "true"
          }
        }
      }
    })
  end
}
```

**Step 2:** Add keybindings to `~/.config/nvim/lua/config/keymaps.lua`:
```lua
vim.keymap.set('n', '<leader>ss', ':SerenaFindSymbol<CR>')
vim.keymap.set('n', '<leader>so', ':SerenaGetOverview<CR>')
vim.keymap.set('n', '<leader>sr', ':SerenaFindReferences<CR>')
```

---

## Setting Up for Other Projects

### Using Templates

**Step 1:** Copy the template file
```bash
# For JSON
cp /home/ajk/FormatIQ_v3/.serena/mcp-config-template.json ~/my-new-project/.serena/mcp-config.json

# For TOML
cp /home/ajk/FormatIQ_v3/.serena/mcp-config-template.toml ~/my-new-project/.serena/mcp-config.toml
```

**Step 2:** Replace placeholders

Edit the copied file and replace:
- `{{SERENA_INSTALLATION_PATH}}` → `/home/ajk/Serena/serena` (or your Serena path)
- `{{PROJECT_ROOT_PATH}}` → `/home/ajk/my-new-project` (absolute path to project)
- `{{PROJECT_NAME}}` → `my-new-project` (project name)

**Step 3:** Create project.yml

Create `~/my-new-project/.serena/project.yml`:
```yaml
name: my-new-project
path: /home/ajk/my-new-project
language: python  # or typescript, javascript, etc.

paths:
  - src
  - lib

ignore:
  - "**/__pycache__"
  - "**/.venv"
  - "**/node_modules"
  - "**/dist"
```

**Step 4:** Deploy configuration

Follow the IDE-specific steps above, using your new config file.

---

## Configuration Options Explained

### Command & Args

```json
"command": "uv",
"args": [
  "run",                           // Run in uv environment
  "--directory",                   // Specify Serena directory
  "/home/ajk/Serena/serena",      // Path to Serena installation
  "serena",                        // Serena CLI command
  "start-mcp-server",             // Start MCP server mode
  "--context",                     // Specify context
  "ide-assistant"                  // Use IDE assistant context
]
```

**Alternative commands:**
```bash
# If serena is in PATH
"command": "serena"
"args": ["start-mcp-server", "--context", "ide-assistant"]

# Using Python directly
"command": "python"
"args": ["-m", "serena", "start-mcp-server", "--context", "ide-assistant"]

# Using specific Python version
"command": "/usr/bin/python3.11"
"args": ["-m", "serena", "start-mcp-server", "--context", "ide-assistant"]
```

---

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `SERENA_PROJECT` | None | Auto-activate this project on start |
| `SERENA_AUTO_ACTIVATE` | `false` | Enable auto-activation |
| `SERENA_LOG_LEVEL` | `20` | Logging level (10=DEBUG, 20=INFO, 30=WARNING, 40=ERROR) |
| `SERENA_WEB_DASHBOARD` | `true` | Enable web dashboard |
| `SERENA_WEB_DASHBOARD_OPEN` | `false` | Auto-open dashboard in browser |
| `SERENA_CONFIG` | `~/.serena/serena_config.yml` | Path to global config |

**Example with all options:**
```json
"env": {
  "SERENA_PROJECT": "/home/ajk/FormatIQ_v3",
  "SERENA_AUTO_ACTIVATE": "true",
  "SERENA_LOG_LEVEL": "10",
  "SERENA_WEB_DASHBOARD": "true",
  "SERENA_WEB_DASHBOARD_OPEN": "true",
  "SERENA_CONFIG": "/home/ajk/FormatIQ_v3/.serena/serena_config.yml",
  "PYTHONPATH": "/home/ajk/FormatIQ_v3/apps/backend"
}
```

---

### MCP Settings

```json
"mcpSettings": {
  "timeout": 240000,        // Tool execution timeout (milliseconds)
  "autoReconnect": true,    // Reconnect on disconnection
  "maxRetries": 3,          // Max reconnection attempts
  "logLevel": "info"        // MCP client log level
}
```

**Timeout values:**
- Default: `240000` (4 minutes)
- For complex queries: `600000` (10 minutes)
- For quick responses: `60000` (1 minute)

---

### Keyboard Shortcuts

```json
"globalShortcuts": {
  "serena.findSymbol": "Ctrl+Shift+S",
  "serena.getOverview": "Ctrl+Shift+O",
  "serena.findReferences": "Ctrl+Shift+R"
}
```

**Customization examples:**
```json
// macOS style
"serena.findSymbol": "Cmd+Shift+S"

// Vim style
"serena.findSymbol": "<leader>ss"

// Function keys
"serena.findSymbol": "F12"
```

---

## Multi-Project Setup

### Option 1: Separate Configs

Create individual configs for each project:
```
~/project1/.serena/mcp-config.json  (SERENA_PROJECT=/home/user/project1)
~/project2/.serena/mcp-config.json  (SERENA_PROJECT=/home/user/project2)
~/project3/.serena/mcp-config.json  (SERENA_PROJECT=/home/user/project3)
```

### Option 2: Single Config, Manual Activation

Use one global config without `SERENA_PROJECT`:
```json
{
  "mcpServers": {
    "serena": {
      "command": "uv",
      "args": ["run", "--directory", "/home/ajk/Serena/serena", "serena", "start-mcp-server", "--context", "ide-assistant"],
      "env": {
        "SERENA_AUTO_ACTIVATE": "false"
      }
    }
  }
}
```

Then manually activate in each session:
```
> activate project /home/user/project1
> activate project /home/user/project2
```

### Option 3: Multiple MCP Servers

Register Serena multiple times with different names:
```json
{
  "mcpServers": {
    "serena-formatiq": {
      "command": "uv",
      "args": ["run", "--directory", "/home/ajk/Serena/serena", "serena", "start-mcp-server", "--context", "ide-assistant"],
      "env": {
        "SERENA_PROJECT": "/home/ajk/FormatIQ_v3"
      }
    },
    "serena-other-project": {
      "command": "uv",
      "args": ["run", "--directory", "/home/ajk/Serena/serena", "serena", "start-mcp-server", "--context", "ide-assistant"],
      "env": {
        "SERENA_PROJECT": "/home/ajk/other-project"
      }
    }
  }
}
```

---

## Verification

### Test MCP Connection

**In Claude Desktop or VS Code:**
```
> get_current_config
```

Expected output:
```
Current configuration:
Serena version: 0.1.4-a317017f
Active project: FormatIQ_v3
...
```

### Test Basic Query

```
> get_symbols_overview apps/backend/app/main.py
```

Should return list of symbols in the file.

### Test Dashboard

```bash
# Open dashboard
xdg-open http://localhost:24282/dashboard/

# Or check if server is running
curl http://localhost:24282/dashboard/
```

---

## Troubleshooting

### MCP Server Not Starting

**Check logs:**
```bash
tail -f ~/.serena/logs/$(date +%Y-%m-%d)/mcp_*.txt
```

**Common issues:**
1. **Command not found:** Check `command` path in config
2. **Port conflict:** Another Serena instance running on port 24282
3. **Permission denied:** Check file permissions on Serena installation

**Solutions:**
```bash
# Kill existing instances
pkill -f "serena start-mcp-server"

# Check if serena command works
cd /home/ajk/Serena/serena && uv run serena --version

# Verify permissions
ls -la /home/ajk/Serena/serena
```

---

### IDE Not Recognizing Serena

**For VS Code:**
```
1. Check Developer Tools: Help → Toggle Developer Tools → Console
2. Look for MCP connection errors
3. Reload window: Ctrl+Shift+P → "Developer: Reload Window"
```

**For Claude Desktop:**
```
1. Check Claude Desktop logs (location varies by OS)
2. Verify config.json syntax with: jsonlint ~/.config/claude-desktop/config.json
3. Restart Claude Desktop completely
```

---

### Project Not Auto-Activating

**Check environment variable:**
```json
"env": {
  "SERENA_PROJECT": "/absolute/path/to/project",  // Must be absolute!
  "SERENA_AUTO_ACTIVATE": "true"                   // Must be string "true"
}
```

**Manual activation:**
```
> activate project /home/ajk/FormatIQ_v3
```

---

### Slow Response Times

**Increase timeout:**
```json
"mcpSettings": {
  "timeout": 600000  // 10 minutes
}
```

**Check language servers:**
```bash
# Verify language servers are installed
which pylsp
which typescript-language-server

# Install if missing
pip install python-lsp-server
npm install -g typescript-language-server typescript
```

---

## Platform-Specific Notes

### Linux

- Config directory: `~/.config/claude-desktop/`
- Logs: `~/.serena/logs/`
- Use `xdg-open` for dashboard

### macOS

- Config directory: `~/Library/Application Support/Claude/`
- Use `open` for dashboard
- May need to allow MCP server in Security & Privacy

### Windows (WSL)

- Use Linux paths in config
- Access dashboard via Windows browser: `http://localhost:24282/dashboard/`
- May need to configure WSL firewall

---

## Advanced Configuration

### Custom Context

Create custom context in `~/.serena/serena_config.yml`:
```yaml
contexts:
  my-custom-context:
    description: "Custom context for my workflow"
    excluded_tools:
      - create_text_file
      - execute_shell_command
    included_optional_tools:
      - restart_language_server
```

Use in MCP config:
```json
"args": ["start-mcp-server", "--context", "my-custom-context"]
```

### Multiple Language Servers

In `project.yml`:
```yaml
language: python

paths:
  - apps/backend
  - apps/frontend

ignore:
  - "**/__pycache__"
  - "**/node_modules"

# Let Serena handle TypeScript in frontend
additional_languages:
  - typescript:
      paths:
        - apps/frontend
```

---

## Security Considerations

### Environment Variables

**Never commit:**
- API keys in `env` section
- Absolute paths that expose system structure
- Credentials or tokens

**Use placeholders:**
```json
"env": {
  "SERENA_PROJECT": "${PROJECT_ROOT}",
  "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}"
}
```

### Network Access

Serena dashboard binds to `localhost:24282` by default. To restrict:

In `~/.serena/serena_config.yml`:
```yaml
web_dashboard: true
web_dashboard_port: 24282
web_dashboard_host: "127.0.0.1"  # Only localhost
```

---

## Migration Guide

### From Old Config to New

**Old format (deprecated):**
```json
{
  "serena": {
    "path": "/home/ajk/Serena/serena",
    "project": "/home/ajk/FormatIQ_v3"
  }
}
```

**New format:**
```json
{
  "mcpServers": {
    "serena": {
      "command": "uv",
      "args": ["run", "--directory", "/home/ajk/Serena/serena", "serena", "start-mcp-server", "--context", "ide-assistant"],
      "env": {
        "SERENA_PROJECT": "/home/ajk/FormatIQ_v3"
      }
    }
  }
}
```

---

## Resources

- **Serena Documentation:** https://github.com/serena/serena
- **MCP Protocol Spec:** https://modelcontextprotocol.io/
- **Claude Desktop Docs:** https://claude.ai/docs
- **Dashboard:** http://localhost:24282/dashboard/
- **Logs:** `~/.serena/logs/`

---

## Quick Reference

| Task | Command/Path |
|------|-------------|
| Claude Desktop Config | `~/.config/claude-desktop/config.json` |
| VS Code Config | `.vscode/mcp-settings.json` |
| Cursor Config | `.cursor/mcp-config.json` |
| Check Running Server | `ps aux \| grep serena` |
| View Logs | `tail -f ~/.serena/logs/$(date +%Y-%m-%d)/mcp_*.txt` |
| Open Dashboard | `xdg-open http://localhost:24282/dashboard/` |
| Stop Server | `pkill -f "serena start-mcp-server"` |
| Test Connection | `> get_current_config` |
| Activate Project | `> activate project formatiq_v3` |

---

**For FormatIQ_v3 specific commands, see:**
- [COMMANDS_CHEATSHEET.md](./COMMANDS_CHEATSHEET.md)
- [ALL_TOOLS_REFERENCE.md](./ALL_TOOLS_REFERENCE.md)
- [SETUP_GUIDE.md](./SETUP_GUIDE.md)

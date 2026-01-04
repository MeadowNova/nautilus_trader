# Serena IDE Configurations - Installed

This document tracks where Serena MCP configurations have been installed on your system.

## ✅ Installed Configurations

### 1. **Kilocode** (Factory IDE)
**Config File:** `/home/ajk/.vscode-server/data/User/globalStorage/kilocode.kilo-code/settings/mcp_settings.json`

**Status:** ✅ **FIXED AND READY**

**Configuration:**
```json
{
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
      "SERENA_PROJECT": "/home/ajk/FormatIQ_v3",
      "SERENA_AUTO_ACTIVATE": "true",
      "SERENA_LOG_LEVEL": "20",
      "SERENA_WEB_DASHBOARD": "true",
      "SERENA_WEB_DASHBOARD_OPEN": "false"
    },
    "alwaysAllow": [
      "get_symbols_overview",
      "find_symbol",
      "find_referencing_symbols",
      "search_for_pattern",
      "list_dir",
      "find_file"
    ],
    "disabled": false
  }
}
```

**Next Steps:**
1. Reload Kilocode window: `Ctrl+Shift+P` → "Developer: Reload Window"
2. Test connection: `> get_current_config`
3. Try command: `> get_symbols_overview apps/backend/app/main.py`

---

### 2. **Codex**
**Config File:** `/home/ajk/.codex/config.toml`

**Status:** ✅ **CONFIGURED**

**Configuration:**
```toml
[mcp_servers.serena]
command = "uv"
args = ["run", "--directory", "/home/ajk/Serena/serena", "serena", "start-mcp-server", "--context", "ide-assistant"]

[mcp_servers.serena.env]
SERENA_PROJECT = "/home/ajk/FormatIQ_v3"
SERENA_AUTO_ACTIVATE = "true"
SERENA_LOG_LEVEL = "20"
SERENA_WEB_DASHBOARD = "true"
SERENA_WEB_DASHBOARD_OPEN = "false"
```

**Next Steps:**
1. Restart Codex
2. Test connection in Codex chat
3. Try: `> activate project formatiq_v3`

---

### 3. **Gemini CLI**
**Config File:** `/home/ajk/.gemini/settings.json`

**Status:** ✅ **CONFIGURED**

**Configuration:**
```json
{
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
      "SERENA_PROJECT": "/home/ajk/FormatIQ_v3",
      "SERENA_AUTO_ACTIVATE": "true",
      "SERENA_LOG_LEVEL": "20",
      "SERENA_WEB_DASHBOARD": "true",
      "SERENA_WEB_DASHBOARD_OPEN": "false"
    },
    "trust": true,
    "alwaysAllow": [
      "get_symbols_overview",
      "find_symbol",
      "find_referencing_symbols",
      "search_for_pattern",
      "list_dir",
      "find_file",
      "write_memory",
      "read_memory",
      "list_memories"
    ]
  }
}
```

**Next Steps:**
1. Restart Gemini CLI
2. Test connection: `> get_current_config`
3. Try navigation: `> get_symbols_overview apps/backend/app/main.py`

---

## 📋 Available Configurations (Not Yet Installed)

### Claude Desktop
**Config File:** `~/.config/claude-desktop/config.json`

**To Install:**
```bash
cp /home/ajk/FormatIQ_v3/.serena/mcp-config.json ~/.config/claude-desktop/config.json
# OR merge into existing config
```

---

### VS Code (Standard)
**Config File:** `.vscode/settings.json` in project root

**To Install:**
```bash
mkdir -p /home/ajk/FormatIQ_v3/.vscode
cp /home/ajk/FormatIQ_v3/.serena/mcp-config.json /home/ajk/FormatIQ_v3/.vscode/mcp-settings.json
```

Then add to `.vscode/settings.json`:
```json
{
  "mcp.configPath": "${workspaceFolder}/.vscode/mcp-settings.json",
  "mcp.autoStart": true
}
```

---

### Cursor IDE
**Config File:** `.cursor/mcp-config.json` in project root

**To Install:**
```bash
mkdir -p /home/ajk/FormatIQ_v3/.cursor
cp /home/ajk/FormatIQ_v3/.serena/mcp-config.json /home/ajk/FormatIQ_v3/.cursor/mcp-config.json
```

Cursor will automatically detect it.

---

### Windsurf
**Config File:** Settings → Extensions → MCP (GUI)

**To Install:**
1. Open Windsurf Settings
2. Navigate to Extensions → MCP
3. Add new server with:
   - Name: `Serena`
   - Command: `uv`
   - Args: `run --directory /home/ajk/Serena/serena serena start-mcp-server --context ide-assistant`
   - Environment Variables:
     - `SERENA_PROJECT` = `/home/ajk/FormatIQ_v3`
     - `SERENA_AUTO_ACTIVATE` = `true`

---

### Zed Editor
**Config File:** `~/.config/zed/settings.json`

**To Install:**
Add to your Zed settings:
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

---

### Neovim
**Config File:** `~/.config/nvim/lua/plugins/mcp.lua`

**To Install:**
Create the file with:
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

---

## 🔍 Verification Steps

### Check if Serena is Running
```bash
ps aux | grep serena | grep -v grep
```

### Check Dashboard
```bash
xdg-open http://localhost:24282/dashboard/
```

### Check Logs
```bash
tail -f ~/.serena/logs/$(date +%Y-%m-%d)/mcp_*.txt
```

---

## 🐛 Troubleshooting

### Config Not Loading

**Kilocode:**
- Reload window: `Ctrl+Shift+P` → "Developer: Reload Window"
- Check Output panel: `Ctrl+Shift+U` → Select "MCP"

**Codex:**
- Restart Codex completely
- Check Codex logs for MCP errors

**Other IDEs:**
- Restart the IDE
- Check IDE-specific logs/developer console

---

### Serena Not Connecting

1. **Verify server is running:**
   ```bash
   ps aux | grep serena | grep -v grep
   ```

2. **Test command manually:**
   ```bash
   cd /home/ajk/Serena/serena && uv run serena start-mcp-server --context ide-assistant
   ```

3. **Check dashboard:**
   - Open: http://localhost:24282/dashboard/
   - Should show active connections

4. **Validate config syntax:**
   ```bash
   # For JSON configs
   python3 -m json.tool <config-file.json>
   
   # For TOML configs
   python3 -c "import tomli; tomli.load(open('<config-file.toml>', 'rb'))"
   ```

---

### Port Conflicts

If dashboard shows port conflict:

```bash
# Kill existing instances
pkill -f "serena start-mcp-server"

# Restart fresh
cd /home/ajk/Serena/serena && uv run serena start-mcp-server --context ide-assistant
```

---

## 📊 Configuration Summary

| IDE | Config Location | Status | Format |
|-----|----------------|--------|--------|
| **Kilocode** | `~/.vscode-server/.../mcp_settings.json` | ✅ Installed | JSON |
| **Codex** | `~/.codex/config.toml` | ✅ Installed | TOML |
| **Gemini CLI** | `~/.gemini/settings.json` | ✅ Installed | JSON |
| Claude Desktop | `~/.config/claude-desktop/config.json` | ⏳ Available | JSON |
| VS Code | `.vscode/mcp-settings.json` | ⏳ Available | JSON |
| Cursor | `.cursor/mcp-config.json` | ⏳ Available | JSON |
| Windsurf | Settings GUI | ⏳ Available | GUI |
| Zed | `~/.config/zed/settings.json` | ⏳ Available | JSON |
| Neovim | `~/.config/nvim/lua/plugins/mcp.lua` | ⏳ Available | Lua |

---

## 🎯 Quick Start Commands

Once Serena is connected in your IDE:

```bash
# Activate project
> activate project formatiq_v3

# Get file overview
> get_symbols_overview apps/backend/app/main.py

# Find symbol
> find_symbol ResumeService --relative-path apps/backend/app/services

# Find references
> find_referencing_symbols ResumeService apps/backend/app/services/resume_service.py

# Search pattern
> search_for_pattern "class.*Service" --relative-path apps/backend

# List directory
> list_dir apps/backend/app --recursive false

# Check config
> get_current_config
```

---

## 📚 More Information

- **Complete Tool Reference:** [.serena/ALL_TOOLS_REFERENCE.md](./ALL_TOOLS_REFERENCE.md)
- **Command Cheatsheet:** [.serena/COMMANDS_CHEATSHEET.md](./COMMANDS_CHEATSHEET.md)
- **Full IDE Integration Guide:** [.serena/MCP_INTEGRATION_GUIDE.md](./MCP_INTEGRATION_GUIDE.md)
- **Quick Start:** [.serena/README.md](./README.md)

---

## 🔄 Updates

**Last Updated:** 2025-10-03

**Changes:**
- ✅ Kilocode config fixed (path corrected from /home/user to /home/ajk)
- ✅ Codex config added with environment variables
- ✅ Gemini CLI config added with trust settings
- ✅ All 3 configs validated and ready to use

**Serena Server Status:**
- ✅ Running on http://localhost:24282/dashboard/
- ✅ Multiple instances detected (can be consolidated)
- ✅ Project FormatIQ_v3 activated

---

**For other projects:** Copy templates from:
- [mcp-config-template.json](./mcp-config-template.json)
- [mcp-config-template.toml](./mcp-config-template.toml)

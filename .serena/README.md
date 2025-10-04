# Serena Configuration for FormatIQ_v3

This directory contains Serena code agent configuration for intelligent codebase navigation and editing.

## 📁 Files Overview

### Configuration Files
- **`project.yml`** - Project structure and language configuration
- **`serena_config.yml`** - Runtime settings (logging, performance, tools)
- **`mcp-config.json`** - MCP integration config (JSON format) for FormatIQ_v3
- **`mcp-config.toml`** - MCP integration config (TOML format) for FormatIQ_v3
- **`mcp-config-template.json`** - Reusable JSON template for other projects
- **`mcp-config-template.toml`** - Reusable TOML template for other projects

### Documentation
- **`SETUP_GUIDE.md`** - Complete setup, IDE integration, and best practices (COMPREHENSIVE)
- **`COMMANDS_CHEATSHEET.md`** - Quick command reference with examples (QUICK REFERENCE)
- **`ALL_TOOLS_REFERENCE.md`** - Complete documentation of all 20 Serena tools (COMPLETE GUIDE)
- **`MCP_INTEGRATION_GUIDE.md`** - MCP setup for all IDEs and platforms (IDE SETUP)
- **`README.md`** - This file (OVERVIEW)

### Utilities
- **`quick-start.sh`** - Helper script to check status and get started
- **`memories/`** - Saved architecture knowledge (auto-created)

## 🚀 Quick Start

### 1. Check Server Status
```bash
./quick-start.sh
# OR
ps aux | grep serena | grep -v grep
```

### 2. Activate Project
```
> activate project formatiq_v3
```

### 3. Test Navigation
```
> get_symbols_overview apps/backend/app/main.py
> find_symbol ResumeService --relative-path apps/backend/app/services
```

### 4. Open Dashboard
http://localhost:24282/dashboard/

## 📚 Documentation Guide

**Start here depending on your goal:**

| Goal | Read This |
|------|-----------|
| First-time setup | [SETUP_GUIDE.md](./SETUP_GUIDE.md) |
| Quick commands | [COMMANDS_CHEATSHEET.md](./COMMANDS_CHEATSHEET.md) |
| Learn all tools | [ALL_TOOLS_REFERENCE.md](./ALL_TOOLS_REFERENCE.md) |
| IDE integration | [MCP_INTEGRATION_GUIDE.md](./MCP_INTEGRATION_GUIDE.md) |
| Reuse for other projects | `mcp-config-template.*` |

## 🎯 Common Commands

### Code Navigation
```bash
# Get file overview (always start here!)
> get_symbols_overview <file>

# Find specific symbol
> find_symbol <name_path> --relative-path <path> --include-body true

# Find all references
> find_referencing_symbols <symbol_name> <file>

# Find patterns
> search_for_pattern "<regex>" --relative-path <path>
```

### File Operations
```bash
# List directory
> list_dir <path> --recursive false

# Find files
> find_file "<pattern>" <directory>
```

### Memory Management
```bash
# List saved knowledge
> list_memories

# Save architecture notes
> write_memory <name> "<markdown content>"

# Read saved notes
> read_memory <name>

# Delete outdated notes
> delete_memory <name>
```

### Code Editing
```bash
# Replace entire function/class
> replace_symbol_body <name_path> <file> "<new_code>"

# Insert after symbol
> insert_after_symbol <name_path> <file> "<code>"

# Insert before symbol (imports, decorators)
> insert_before_symbol <name_path> <file> "<code>"
```

## 🔧 Server Management

```bash
# Check status
ps aux | grep serena | grep -v grep

# Start server
cd /home/ajk/Serena/serena && uv run serena start-mcp-server --context ide-assistant

# Stop server
pkill -f "serena start-mcp-server"

# View logs
tail -f ~/.serena/logs/$(date +%Y-%m-%d)/mcp_*.txt

# Open dashboard
xdg-open http://localhost:24282/dashboard/
```

## 🎓 Learn More

### All 20 Available Tools

1. `activate_project` - Activate project
2. `get_current_config` - Show configuration
3. `check_onboarding_performed` - Check onboarding status
4. `onboarding` - Start onboarding
5. `get_symbols_overview` - File overview
6. `find_symbol` - Find specific symbols
7. `find_referencing_symbols` - Find references
8. `list_dir` - List directories
9. `find_file` - Find files by pattern
10. `search_for_pattern` - Regex pattern search
11. `list_memories` - List saved memories
12. `write_memory` - Save knowledge
13. `read_memory` - Read saved knowledge
14. `delete_memory` - Delete memory
15. `replace_symbol_body` - Replace code
16. `insert_after_symbol` - Insert code after
17. `insert_before_symbol` - Insert code before
18. `think_about_collected_information` - Reflect on info
19. `think_about_task_adherence` - Check task alignment
20. `think_about_whether_you_are_done` - Evaluate completion

**Full documentation:** [ALL_TOOLS_REFERENCE.md](./ALL_TOOLS_REFERENCE.md)

## 🔗 Integration

### Claude Desktop
```bash
cp mcp-config.json ~/.config/claude-desktop/config.json
```

### VS Code
```bash
cp mcp-config.json .vscode/mcp-settings.json
```

### Cursor
```bash
cp mcp-config.json .cursor/mcp-config.json
```

**Full setup:** [MCP_INTEGRATION_GUIDE.md](./MCP_INTEGRATION_GUIDE.md)

## 💡 Best Practices

### ✅ Do This
- Start with `get_symbols_overview` before reading files
- Use `--relative-path` to narrow searches
- Set `--include-body false` initially, then read specific symbols
- Save architecture knowledge in memories
- Use `find_referencing_symbols` before refactoring

### ❌ Don't Do This
- Don't read entire files unless necessary
- Don't search entire codebase without filters
- Don't forget to activate project first
- Don't use overly broad patterns

## 📊 Dashboard

**URL:** http://localhost:24282/dashboard/

**Features:**
- Real-time log viewing
- Tool usage statistics
- Token consumption tracking
- Session management

## 🆘 Troubleshooting

```bash
# Server not starting
pkill -f "serena start-mcp-server"
cd /home/ajk/Serena/serena && uv run serena start-mcp-server --context ide-assistant

# Language server issues
> restart_language_server python
> restart_language_server typescript

# Project not activating
> activate project /home/ajk/FormatIQ_v3

# Check configuration
> get_current_config
```

## 📦 For Other Projects

1. Copy template: `cp mcp-config-template.json ~/my-project/.serena/mcp-config.json`
2. Replace placeholders:
   - `{{SERENA_INSTALLATION_PATH}}` → `/home/ajk/Serena/serena`
   - `{{PROJECT_ROOT_PATH}}` → `/home/ajk/my-project`
   - `{{PROJECT_NAME}}` → `my-project`
3. Create `project.yml` for your project
4. Follow [MCP_INTEGRATION_GUIDE.md](./MCP_INTEGRATION_GUIDE.md)

## 🔗 Resources

- **Dashboard:** http://localhost:24282/dashboard/
- **Logs:** `~/.serena/logs/`
- **Global Config:** `~/.serena/serena_config.yml`
- **Serena Docs:** https://github.com/serena/serena
- **MCP Protocol:** https://modelcontextprotocol.io/

## 📖 See Also

- [../AGENTS.md](../AGENTS.md) - Project-wide agent guidelines
- [SETUP_GUIDE.md](./SETUP_GUIDE.md) - Detailed setup instructions
- [COMMANDS_CHEATSHEET.md](./COMMANDS_CHEATSHEET.md) - Quick command reference
- [ALL_TOOLS_REFERENCE.md](./ALL_TOOLS_REFERENCE.md) - Complete tools documentation
- [MCP_INTEGRATION_GUIDE.md](./MCP_INTEGRATION_GUIDE.md) - IDE integration guide

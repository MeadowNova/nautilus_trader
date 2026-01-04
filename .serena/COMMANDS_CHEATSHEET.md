# Serena Commands Cheatsheet - FormatIQ_v3

## Server Management

```bash
# Check if running
ps aux | grep serena | grep -v grep

# Start Serena
cd /home/ajk/Serena/serena && uv run serena start-mcp-server --context ide-assistant

# Start in background
cd /home/ajk/Serena/serena && nohup uv run serena start-mcp-server --context ide-assistant > /tmp/serena.log 2>&1 &

# Stop Serena
pkill -f "serena start-mcp-server"

# Restart
pkill -f "serena start-mcp-server" && cd /home/ajk/Serena/serena && uv run serena start-mcp-server --context ide-assistant

# View logs
tail -f ~/.serena/logs/$(date +%Y-%m-%d)/mcp_*.txt

# Open dashboard
xdg-open http://localhost:24282/dashboard/
```

## Project Activation

```bash
# Activate this project (do this first in every session!)
> activate project formatiq_v3
# OR
> activate project /home/ajk/FormatIQ_v3

# Verify active project
> get_current_config
```

## Code Navigation

```bash
# Get file overview (always start here!)
> get_symbols_overview apps/backend/app/main.py

# Find specific symbol
> find_symbol create_app --relative-path apps/backend/app/main.py --include-body true

# Find symbol by pattern
> find_symbol "*Service" --relative-path apps/backend/app/services --substring-matching true

# Get class with methods
> find_symbol ResumeService --relative-path apps/backend/app/services/resume_service.py --depth 1 --include-body false

# Get specific method
> find_symbol ResumeService/upload_resume --relative-path apps/backend/app/services/resume_service.py --include-body true

# Find references
> find_referencing_symbols ResumeService apps/backend/app/services/resume_service.py
```

## File & Directory Operations

```bash
# List directory contents
> list_dir apps/backend/app --recursive false

# Find files by pattern
> find_file "*service*.py" apps/backend/app

# Search for code patterns
> search_for_pattern "class.*Service" --relative-path apps/backend --paths-include-glob "**/*.py"

# Search with context
> search_for_pattern "api/v1/resumes" --relative-path . --context-lines-before 3 --context-lines-after 3
```

## Memory Management

```bash
# List saved memories
> list_memories

# Save architecture knowledge
> write_memory architecture "FormatIQ uses FastAPI backend at apps/backend with Next.js frontend at apps/frontend. Key services: ResumeService, OptimizationService, ReconstructionService, JobService."

# Read memory
> read_memory architecture

# Delete outdated memory
> delete_memory old_architecture
```

## Editing Code

```bash
# Replace entire function/class
> replace_symbol_body OptimizationService/optimize apps/backend/app/services/optimization_service.py "def optimize(self, resume_id: int, job_id: int):\n    # New implementation\n    pass"

# Insert after a symbol (add new function)
> insert_after_symbol create_app apps/backend/app/main.py "\n\ndef health_check():\n    return {'status': 'healthy'}\n"

# Insert before first symbol (add import)
> insert_before_symbol create_app apps/backend/app/main.py "from typing import Optional\n"
```

## Symbol Kinds (LSP)

Use with `find_symbol --include-kinds` or `--exclude-kinds`:

```
1  = File
2  = Module  
5  = Class
6  = Method
7  = Property
8  = Field
9  = Constructor
12 = Function
13 = Variable
14 = Constant
```

**Example:**
```bash
# Find only classes
> find_symbol "*Service" --relative-path apps/backend --include-kinds [5]

# Find classes and functions
> find_symbol "*" --relative-path apps/backend/app/api --include-kinds [5,12]
```

## Advanced Searches

```bash
# Find all test files
> find_file "*test*.py" apps/backend/tests

# Find API endpoints
> search_for_pattern "@app\\.(get|post|put|delete)" --relative-path apps/backend/app/api

# Find all imports of a module
> search_for_pattern "from.*resume_service.*import|import.*resume_service" --relative-path apps/backend

# Find TODO comments
> search_for_pattern "TODO:|FIXME:" --relative-path .

# Find environment variable usage
> search_for_pattern "os\\.environ|getenv" --relative-path apps/backend
```

## FormatIQ-Specific Queries

```bash
# Backend Services
> find_symbol "*Service" --relative-path apps/backend/app/services --substring-matching true --depth 1

# API Endpoints
> get_symbols_overview apps/backend/app/api/router/v1/resume.py
> find_symbol upload_resume --relative-path apps/backend/app/api/router/v1 --include-body true

# Frontend Components
> find_symbol "useApp*" --relative-path apps/frontend/lib/hooks --substring-matching true
> find_symbol FileUpload --relative-path apps/frontend/components/common --include-body true

# Database Models
> find_symbol "*" --relative-path apps/backend/app/models --include-kinds [5]

# Celery Tasks
> get_symbols_overview apps/backend/app/tasks.py
```

## Workflow Examples

### Understanding a New Feature

```bash
# 1. Activate project
> activate project formatiq_v3

# 2. Find the main entry point
> get_symbols_overview apps/backend/app/api/router/v1/resume.py

# 3. Dive into specific function
> find_symbol upload_resume --relative-path apps/backend/app/api/router/v1/resume.py --include-body true

# 4. Find what it calls
> find_referencing_symbols upload_resume apps/backend/app/api/router/v1/resume.py

# 5. Check the service
> find_symbol ResumeService/upload_resume --relative-path apps/backend/app/services/resume_service.py --include-body true
```

### Adding a New Endpoint

```bash
# 1. Find similar endpoints
> search_for_pattern "@router\\.(post|get)" --relative-path apps/backend/app/api/router/v1

# 2. Get structure of existing file
> get_symbols_overview apps/backend/app/api/router/v1/resume.py

# 3. Find what you need to import
> search_for_pattern "from.*services.*import" --relative-path apps/backend/app/api/router/v1

# 4. Insert new endpoint after last function
> insert_after_symbol delete_resume apps/backend/app/api/router/v1/resume.py "\n\n@router.get('/resumes/search')\nasync def search_resumes(query: str):\n    pass\n"
```

### Refactoring a Service

```bash
# 1. Find all usages
> find_referencing_symbols OptimizationService apps/backend/app/services/optimization_service.py

# 2. Review the service methods
> find_symbol OptimizationService --relative-path apps/backend/app/services/optimization_service.py --depth 1

# 3. Replace specific method
> replace_symbol_body OptimizationService/optimize apps/backend/app/services/optimization_service.py "<new implementation>"

# 4. Verify no syntax errors (check dashboard logs)
```

## Performance Tips

1. **Always start with overview**, not full file reads
2. **Use `--relative-path`** to narrow searches
3. **Use `--include-kinds`** to filter by symbol type
4. **Read `--include-body true`** only when needed
5. **Use `find_file`** for file discovery before `search_for_pattern`
6. **Monitor token usage** in dashboard

## Troubleshooting

```bash
# Language server not responding
> restart_language_server python
> restart_language_server typescript

# Check active project
> get_current_config

# Verify file exists before querying
> find_file "main.py" apps/backend/app

# Check if pattern works (test on small directory first)
> search_for_pattern "test" --relative-path apps/backend/app/api --max-answer-chars 1000
```

## Keyboard Shortcuts (if configured)

- **Ctrl+Shift+S**: Find symbol under cursor
- **Ctrl+Shift+R**: Find references to symbol
- **Ctrl+Shift+O**: Get file overview
- **Ctrl+Shift+Alt+S**: Serena custom command

---

**See also:**
- [SETUP_GUIDE.md](./SETUP_GUIDE.md) - Full setup instructions
- [README.md](./README.md) - Quick reference
- Dashboard: http://localhost:24282/dashboard/

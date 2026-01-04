# Complete Serena Tools Reference - FormatIQ_v3

## All Available Tools (20 Active)

### 📁 Project Management

#### `activate_project`
**Purpose:** Activate a project to enable all other tools  
**Usage:**
```
> activate project formatiq_v3
> activate project /home/ajk/FormatIQ_v3
```
**Parameters:**
- `project` (string): Project name or absolute path

**Notes:** Must be called first in every new Serena session

---

#### `get_current_config`
**Purpose:** Show active project, tools, modes, and configuration  
**Usage:**
```
> get_current_config
```
**Returns:** 
- Serena version
- Active project details
- Active/inactive tools list
- Active/inactive modes
- Log level settings

---

#### `check_onboarding_performed`
**Purpose:** Check if project onboarding was completed  
**Usage:**
```
> check_onboarding_performed
```
**Returns:** Boolean indicating onboarding status

---

#### `onboarding`
**Purpose:** Start interactive onboarding for new project  
**Usage:**
```
> onboarding
```
**Notes:** Only needed once per project, helps establish architecture understanding

---

### 🔍 Code Navigation & Reading

#### `get_symbols_overview`
**Purpose:** Get high-level overview of all symbols in a file  
**Usage:**
```
> get_symbols_overview apps/backend/app/main.py
> get_symbols_overview apps/frontend/components/FileUpload.tsx
```
**Parameters:**
- `relative_path` (string): Path to file from project root
- `max_answer_chars` (int, optional): Limit output size (default: 150000)

**Returns:** List of top-level symbols with:
- `name_path`: Full path to symbol
- `kind`: Symbol type (Class=5, Function=12, Variable=13, etc.)

**Best Practice:** ALWAYS start here before reading file contents

---

#### `find_symbol`
**Purpose:** Find and retrieve specific symbols with precise control  
**Usage:**
```
# Find specific class
> find_symbol ResumeService --relative-path apps/backend/app/services/resume_service.py --include-body true

# Find with pattern matching
> find_symbol "*Service" --relative-path apps/backend/app/services --substring-matching true

# Get class with methods (depth=1)
> find_symbol ResumeService --relative-path apps/backend/app/services/resume_service.py --depth 1 --include-body false

# Get specific method
> find_symbol ResumeService/upload_resume --relative-path apps/backend/app/services/resume_service.py --include-body true

# Find only classes
> find_symbol "*" --relative-path apps/backend/app/models --include-kinds [5]

# Find classes and functions
> find_symbol "*" --relative-path apps/backend/app/api --include-kinds [5,12]
```

**Parameters:**
- `name_path` (string): Symbol name or pattern
  - Simple: `create_app` (matches any symbol with this name)
  - Relative: `ResumeService/upload_resume` (matches method in class)
  - Absolute: `/ResumeService` (matches only top-level symbols)
  - Pattern: `*Service` (wildcard matching)
- `relative_path` (string, optional): Restrict to file or directory
- `substring_matching` (bool): Enable fuzzy matching (default: false)
- `include_body` (bool): Include source code (default: false)
- `depth` (int): Include children (0=none, 1=direct children, etc.)
- `include_kinds` (list[int], optional): Filter by LSP symbol kinds
- `exclude_kinds` (list[int], optional): Exclude specific symbol kinds
- `max_answer_chars` (int, optional): Limit output size

**LSP Symbol Kinds:**
```
1  = File          9  = Constructor    17 = Boolean
2  = Module        10 = Enum           18 = Array
3  = Namespace     11 = Interface      19 = Object
4  = Package       12 = Function       20 = Key
5  = Class         13 = Variable       21 = Null
6  = Method        14 = Constant       22 = Enum Member
7  = Property      15 = String         23 = Struct
8  = Field         16 = Number         24 = Event
25 = Operator      26 = Type Parameter
```

**Returns:** List of symbols with:
- `name_path`: Full symbol path
- `kind`: Symbol type
- `location`: Line and column
- `body_location`: Start/end lines
- `body`: Source code (if `include_body=true`)
- `children`: Nested symbols (if `depth > 0`)

**Name Path Matching Rules:**
- `method` → matches `method`, `class/method`, `class/nested/method`
- `class/method` → matches `class/method`, `nested/class/method`, NOT `method`
- `/class` → matches only top-level `class`, NOT `nested/class`
- `/class/method` → matches `class/method`, NOT `nested/class/method`

---

#### `find_referencing_symbols`
**Purpose:** Find all locations that reference a specific symbol  
**Usage:**
```
> find_referencing_symbols ResumeService apps/backend/app/services/resume_service.py
> find_referencing_symbols OptimizationService apps/backend/app/services/optimization_service.py
```

**Parameters:**
- `name_path` (string): Symbol to find references for
- `relative_path` (string): File containing the symbol (must be file, not directory)
- `include_kinds` (list[int], optional): Filter referencing symbols by kind
- `exclude_kinds` (list[int], optional): Exclude referencing symbols by kind
- `max_answer_chars` (int, optional): Limit output size

**Returns:** List of referencing symbols with:
- Symbol metadata (name, kind, location)
- Code snippet showing the reference
- Context lines around reference

**Use Cases:**
- Understanding symbol usage
- Refactoring impact analysis
- Finding integration points

---

### 🔎 File & Pattern Search

#### `list_dir`
**Purpose:** List files and directories  
**Usage:**
```
> list_dir apps/backend/app --recursive false
> list_dir apps/frontend/components --recursive true
> list_dir . --recursive false
```

**Parameters:**
- `relative_path` (string): Directory to list
- `recursive` (bool): Include subdirectories
- `skip_ignored_files` (bool, optional): Skip .gitignore patterns (default: false)
- `max_answer_chars` (int, optional): Limit output size

**Returns:** JSON with:
- `dirs`: List of subdirectories
- `files`: List of files

---

#### `find_file`
**Purpose:** Find files matching a pattern  
**Usage:**
```
> find_file "*service*.py" apps/backend/app
> find_file "*.test.ts" apps/frontend
> find_file "main.py" .
```

**Parameters:**
- `file_mask` (string): Filename pattern (* and ? wildcards)
- `relative_path` (string): Directory to search in

**Returns:** JSON with:
- `files`: List of matching file paths

---

#### `search_for_pattern`
**Purpose:** Flexible regex pattern search in code  
**Usage:**
```
# Find class definitions
> search_for_pattern "class.*Service" --relative-path apps/backend --paths-include-glob "**/*.py"

# Find API decorators
> search_for_pattern "@app\\.(get|post|put|delete)" --relative-path apps/backend/app/api

# Find imports
> search_for_pattern "from.*resume_service.*import|import.*resume_service" --relative-path apps/backend

# Find TODOs
> search_for_pattern "TODO:|FIXME:" --relative-path .

# With context
> search_for_pattern "api/v1/resumes" --relative-path . --context-lines-before 3 --context-lines-after 3

# Restrict to code files only
> search_for_pattern "class.*Service" --relative-path apps/backend --restrict-search-to-code-files true

# Exclude test files
> search_for_pattern "def test_" --relative-path apps/backend --paths-exclude-glob "**/tests/**"
```

**Parameters:**
- `substring_pattern` (string): Regular expression (DOTALL mode, `.` matches newlines)
- `relative_path` (string, optional): File or directory to search in
- `paths_include_glob` (string, optional): Include only matching paths (e.g., "**/*.py")
- `paths_exclude_glob` (string, optional): Exclude matching paths (e.g., "**/tests/**")
- `restrict_search_to_code_files` (bool): Search only analyzable code files (default: false)
- `context_lines_before` (int): Lines before match (default: 0)
- `context_lines_after` (int): Lines after match (default: 0)
- `max_answer_chars` (int, optional): Limit output size

**Returns:** Dictionary mapping file paths to lists of matched lines

**Pattern Tips:**
- Use `.*?` (non-greedy) instead of `.*` (greedy)
- Escape special regex chars: `\\.`, `\\(`, `\\[`
- Use `|` for alternation: `get|post|put`
- Don't use `.*` at start/end (redundant with line matching)

---

### 💾 Memory Management

#### `list_memories`
**Purpose:** List all saved memory files  
**Usage:**
```
> list_memories
```

**Returns:** List of memory names/descriptions

**Use Cases:**
- See what architecture knowledge is saved
- Find relevant context before starting work

---

#### `write_memory`
**Purpose:** Save architecture/pattern knowledge for future sessions  
**Usage:**
```
> write_memory architecture "FormatIQ v3 Architecture:
- Backend: FastAPI at apps/backend (Python 3.x)
- Frontend: Next.js at apps/frontend (TypeScript/React)
- Key Services: ResumeService, OptimizationService, ReconstructionService, JobService
- API: Versioned under /api/v1/ with routers for job, optimization, reconstruction, resume
- Database: SQLAlchemy with async support
- Background Tasks: Celery with Redis
- Testing: pytest (backend), Playwright (E2E)
"

> write_memory coding_patterns "Common Patterns:
- Services use dependency injection via __init__(db_session)
- API routes use FastAPI routers with versioning
- All async operations use asyncio
- Error handling via custom exceptions in app.core.exceptions
"

> write_memory testing_strategy "Testing Approach:
- Unit tests: tests/<module>/test_<file>.py
- Integration tests: tests/integration/
- E2E tests: Playwright in tests/ directory
- Run backend tests: pytest apps/backend/tests
- Run E2E tests: playwright test
"
```

**Parameters:**
- `memory_name` (string): Unique identifier for the memory
- `content` (string): Markdown-formatted content
- `max_answer_chars` (int, optional): Limit storage size

**Best Practices:**
- Use descriptive names: `architecture`, `api_patterns`, `database_schema`
- Write in Markdown for readability
- Include examples and code snippets
- Update memories when architecture changes

---

#### `read_memory`
**Purpose:** Retrieve saved memory content  
**Usage:**
```
> read_memory architecture
> read_memory coding_patterns
> read_memory testing_strategy
```

**Parameters:**
- `memory_file_name` (string): Name of the memory to read
- `max_answer_chars` (int, optional): Limit output size

**Returns:** Markdown content of the memory

---

#### `delete_memory`
**Purpose:** Remove outdated memory  
**Usage:**
```
> delete_memory old_architecture
> delete_memory deprecated_patterns
```

**Parameters:**
- `memory_file_name` (string): Name of memory to delete

---

### ✏️ Code Editing

#### `replace_symbol_body`
**Purpose:** Replace entire symbol definition (class, function, method)  
**Usage:**
```
> replace_symbol_body OptimizationService/optimize apps/backend/app/services/optimization_service.py "async def optimize(self, resume_id: int, job_id: int) -> dict:
    '''Optimize resume for job description.'''
    # New implementation
    result = await self._run_optimization(resume_id, job_id)
    return result
"
```

**Parameters:**
- `name_path` (string): Symbol to replace (e.g., `ClassName/method_name`)
- `relative_path` (string): File containing the symbol
- `body` (string): Complete new symbol definition including signature

**Important:** 
- `body` must include the complete definition (e.g., `def func():` line)
- Does NOT include docstrings or imports above the symbol
- Preserves indentation based on symbol location

---

#### `insert_after_symbol`
**Purpose:** Insert code after a symbol definition  
**Usage:**
```
# Add new function after existing one
> insert_after_symbol create_app apps/backend/app/main.py "

def health_check():
    '''Health check endpoint.'''
    return {'status': 'healthy'}
"

# Add new method to class
> insert_after_symbol ResumeService/get_resume_status apps/backend/app/services/resume_service.py "

    async def delete_resume(self, resume_id: int) -> None:
        '''Delete a resume.'''
        await self.db.delete(resume_id)
"
```

**Parameters:**
- `name_path` (string): Symbol after which to insert
- `relative_path` (string): File containing the symbol
- `body` (string): Code to insert

**Use Cases:**
- Adding new functions/methods
- Adding new endpoints
- Adding new classes

---

#### `insert_before_symbol`
**Purpose:** Insert code before a symbol definition  
**Usage:**
```
# Add import before first symbol
> insert_before_symbol create_app apps/backend/app/main.py "from typing import Optional
"

# Add decorator before function
> insert_before_symbol upload_resume apps/backend/app/api/router/v1/resume.py "@rate_limit(max_calls=10, period=60)
"
```

**Parameters:**
- `name_path` (string): Symbol before which to insert
- `relative_path` (string): File containing the symbol
- `body` (string): Code to insert

**Use Cases:**
- Adding imports
- Adding decorators
- Inserting helper functions before main code

---

### 🤔 Reflection Tools

#### `think_about_collected_information`
**Purpose:** Reflect on gathered information and determine next steps  
**Usage:**
```
> think_about_collected_information
```

**When to use:**
- After completing a sequence of searches
- Before making code changes
- When unsure about next steps

---

#### `think_about_task_adherence`
**Purpose:** Verify you're still on track with the original task  
**Usage:**
```
> think_about_task_adherence
```

**When to use:**
- ALWAYS before editing code
- After long conversation threads
- When task scope seems to be expanding

---

#### `think_about_whether_you_are_done`
**Purpose:** Evaluate if task is complete  
**Usage:**
```
> think_about_whether_you_are_done
```

**When to use:**
- After completing implementation
- Before reporting back to user
- To catch missed requirements

---

## Inactive Tools (Available but Not Active)

These tools exist but are not active in the current `ide-assistant` context:

- `create_text_file` - Create new files (use Factory's Create tool instead)
- `read_file` - Read full files (prefer symbolic tools)
- `execute_shell_command` - Run shell commands (use Factory's Execute)
- `replace_regex` - Regex-based editing (use Factory's Edit)
- `replace_lines` - Line-based editing
- `delete_lines` - Remove lines
- `insert_at_line` - Insert at specific line
- `restart_language_server` - Restart LSP servers
- `remove_project` - Remove project from registry
- `switch_modes` - Change operational modes
- `initial_instructions` - Get system instructions
- `prepare_for_new_conversation` - Session cleanup
- `summarize_changes` - Summarize edits made
- `jet_brains_*` - JetBrains IDE integration (requires plugin)

---

## Tool Usage Patterns

### Pattern 1: Understanding New Code
```
1. > activate project formatiq_v3
2. > get_symbols_overview apps/backend/app/services/resume_service.py
3. > find_symbol ResumeService --relative-path apps/backend/app/services/resume_service.py --depth 1 --include-body false
4. > find_symbol ResumeService/upload_resume --relative-path apps/backend/app/services/resume_service.py --include-body true
5. > find_referencing_symbols ResumeService apps/backend/app/services/resume_service.py
```

### Pattern 2: Finding Patterns Across Codebase
```
1. > search_for_pattern "class.*Service" --relative-path apps/backend --paths-include-glob "**/*.py"
2. > find_file "*service*.py" apps/backend/app
3. > get_symbols_overview apps/backend/app/services/<found_file>
```

### Pattern 3: Refactoring Safety
```
1. > find_referencing_symbols <SymbolToChange> <file>
2. > think_about_collected_information
3. (Review all references)
4. > replace_symbol_body <SymbolToChange> <file> "<new_implementation>"
5. > think_about_whether_you_are_done
```

### Pattern 4: Adding New Feature
```
1. > read_memory architecture
2. > search_for_pattern "<similar_pattern>" --relative-path <relevant_area>
3. > get_symbols_overview <similar_file>
4. > insert_after_symbol <existing_symbol> <file> "<new_code>"
5. > write_memory <feature_name> "<document what you added>"
```

---

## Performance Best Practices

### ✅ Do This
```
# Start with overview
> get_symbols_overview apps/backend/app/main.py

# Then drill down with symbol queries
> find_symbol create_app --relative-path apps/backend/app/main.py --include-body true

# Use relative_path to narrow searches
> find_symbol "*Service" --relative-path apps/backend/app/services

# Use include_kinds to filter
> find_symbol "*" --relative-path apps/backend/app/models --include-kinds [5]
```

### ❌ Don't Do This
```
# Don't read entire files unless necessary
> read_file apps/backend/app/main.py  # ❌

# Don't search entire codebase without filters
> search_for_pattern ".*" --relative-path .  # ❌

# Don't use greedy wildcards
> search_for_pattern "class.*Service.*def.*"  # ❌ Too broad
```

---

## Advanced Usage

### Combining Tools for Complex Queries

**Find all FastAPI routes and their implementations:**
```
> search_for_pattern "@router\\.(get|post|put|delete)\\(.*\\)" --relative-path apps/backend/app/api --context-lines-after 5
```

**Find all database models:**
```
> find_symbol "*" --relative-path apps/backend/app/models --include-kinds [5] --depth 1
```

**Find all services and their public methods:**
```
> find_symbol "*Service" --relative-path apps/backend/app/services --substring-matching true --depth 1 --exclude-kinds [6]
```

**Find all Celery tasks:**
```
> search_for_pattern "@celery_app\\.task|@shared_task" --relative-path apps/backend --paths-include-glob "**/*.py"
```

---

## Token Optimization

### Efficient Querying
1. **Start specific:** Use `--relative-path` to target files/directories
2. **Filter early:** Use `--include-kinds` or `--exclude-kinds`
3. **Body on demand:** Set `--include-body false` initially
4. **Depth control:** Use `depth=0` for classes, `depth=1` for methods list
5. **Context limits:** Only add context lines when needed

### Memory Management
```
# Good: Structured, reusable knowledge
> write_memory api_structure "API endpoints organized under /api/v1/..."

# Bad: Dumping entire files
> write_memory resume_service "<entire 400-line file>"  # ❌
```

---

## Integration with Factory Tools

**When to use Serena vs Factory tools:**

| Task | Use | Reason |
|------|-----|--------|
| Navigate code structure | Serena `find_symbol` | Token-efficient symbolic navigation |
| Read specific function | Serena `find_symbol --include-body` | Targeted reading |
| Read entire file | Factory `Read` | Sometimes necessary |
| Search patterns | Serena `search_for_pattern` | Flexible regex with context |
| Create new files | Factory `Create` | Serena doesn't create files |
| Edit few lines | Factory `Edit` | Line-based editing |
| Replace entire function | Serena `replace_symbol_body` | Symbol-aware editing |
| Run tests | Factory `Execute` | Shell commands |
| Commit changes | Factory `Execute` | Git operations |

---

## Common Workflows

### Debug an Issue
1. `search_for_pattern` to find error message or relevant code
2. `get_symbols_overview` of files with matches
3. `find_symbol` with `--include-body` to read specific functions
4. `find_referencing_symbols` to understand dependencies
5. `think_about_collected_information`

### Add New Endpoint
1. `search_for_pattern` to find similar endpoints
2. `get_symbols_overview` of router file
3. `find_symbol` to get last endpoint in file
4. `insert_after_symbol` to add new endpoint
5. Find service file with `find_file`
6. `insert_after_symbol` to add service method

### Refactor Service
1. `find_referencing_symbols` to find all usages
2. `read_memory` to check architecture patterns
3. `find_symbol` with `depth=1` to see all methods
4. `replace_symbol_body` for methods that need changes
5. `write_memory` to document changes
6. `think_about_whether_you_are_done`

---

**See Also:**
- [COMMANDS_CHEATSHEET.md](./COMMANDS_CHEATSHEET.md) - Quick command reference
- [SETUP_GUIDE.md](./SETUP_GUIDE.md) - Setup and IDE integration
- Dashboard: http://localhost:24282/dashboard/

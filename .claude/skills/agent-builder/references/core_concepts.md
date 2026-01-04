# Claude-Agent-Sdk - Core Concepts

**Pages:** 16

---

## Agent SDK reference - Python

**URL:** https://docs.claude.com/en/api/agent-sdk/python

**Contents:**
- Agent SDK reference - Python
- ​Installation
- ​Choosing Between query() and ClaudeSDKClient
  - ​Quick Comparison
  - ​When to Use query() (New Session Each Time)
  - ​When to Use ClaudeSDKClient (Continuous Conversation)
- ​Functions
  - ​query()
    - ​Parameters
    - ​Returns

Complete API reference for the Python Agent SDK, including all functions, types, and classes.

Was this page helpful?

**Examples:**

Example 1 (unknown):
```unknown
pip install claude-agent-sdk
```

Example 2 (python):
```python
async def query(
    *,
    prompt: str | AsyncIterable[dict[str, Any]],
    options: ClaudeAgentOptions | None = None
) -> AsyncIterator[Message]
```

Example 3 (python):
```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    options = ClaudeAgentOptions(
        system_prompt="You are an expert Python developer",
        permission_mode='acceptEdits',
        cwd="/home/user/project"
    )

    async for message in query(
        prompt="Create a Python web server",
        options=options
    ):
        print(message)


asyncio.run(main())
```

Example 4 (python):
```python
def tool(
    name: str,
    description: str,
    input_schema: type | dict[str, Any]
) -> Callable[[Callable[[Any], Awaitable[dict[str, Any]]]], SdkMcpTool[Any]]
```

---

## Modifying system prompts

**URL:** https://docs.claude.com/en/api/agent-sdk/modifying-system-prompts

**Contents:**
- Modifying system prompts
- ​Understanding system prompts
- ​Methods of modification
  - ​Method 1: CLAUDE.md files (project-level instructions)
    - ​How CLAUDE.md works with the SDK
    - ​Example CLAUDE.md
    - ​Using CLAUDE.md with the SDK
    - ​When to use CLAUDE.md
  - ​Method 2: Output styles (persistent configurations)
    - ​Creating an output style

Learn how to customize Claude’s behavior by modifying system prompts using three approaches - output styles, systemPrompt with append, and custom system prompts.

Was this page helpful?

**Examples:**

Example 1 (unknown):
```unknown
# Project Guidelines

## Code Style

- Use TypeScript strict mode
- Prefer functional components in React
- Always include JSDoc comments for public APIs

## Testing

- Run `npm test` before committing
- Maintain >80% code coverage
- Use jest for unit tests, playwright for E2E

## Commands

- Build: `npm run build`
- Dev server: `npm run dev`
- Type check: `npm run typecheck`
```

Example 2 (python):
```python
import { query } from "@anthropic-ai/claude-agent-sdk";

// IMPORTANT: You must specify settingSources to load CLAUDE.md
// The claude_code preset alone does NOT load CLAUDE.md files
const messages = [];

for await (const message of query({
  prompt: "Add a new React component for user profiles",
  options: {
    systemPrompt: {
      type: "preset",
      preset: "claude_code", // Use Claude Code's system prompt
    },
    settingSources: ["project"], // Required to load CLAUDE.md from project
  },
})) {
  messages.push(message);
}

// Now Claude has access to your project guidelines from CLA
...
```

Example 3 (python):
```python
import { writeFile, mkdir } from "fs/promises";
import { join } from "path";
import { homedir } from "os";

async function createOutputStyle(
  name: string,
  description: string,
  prompt: string
) {
  // User-level: ~/.claude/output-styles
  // Project-level: .claude/output-styles
  const outputStylesDir = join(homedir(), ".claude", "output-styles");

  await mkdir(outputStylesDir, { recursive: true });

  const content = `---
name: ${name}
description: ${description}
---

${prompt}`;

  const filePath = join(
    outputStylesDir,
    `${name.toLowerCase().replace(/\s+/g, "-")}.md`
  );
  a
...
```

Example 4 (python):
```python
import { query } from "@anthropic-ai/claude-agent-sdk";

const messages = [];

for await (const message of query({
  prompt: "Help me write a Python function to calculate fibonacci numbers",
  options: {
    systemPrompt: {
      type: "preset",
      preset: "claude_code",
      append:
        "Always include detailed docstrings and type hints in Python code.",
    },
  },
})) {
  messages.push(message);
  if (message.type === "assistant") {
    console.log(message.message.content);
  }
}
```

---

## Custom Tools

**URL:** https://docs.claude.com/en/api/agent-sdk/custom-tools

**Contents:**
- Custom Tools
- ​Creating Custom Tools
- ​Using Custom Tools
  - ​Tool Name Format
  - ​Configuring Allowed Tools
  - ​Multiple Tools Example
- ​Type Safety with Python
- ​Error Handling
- ​Example Tools
  - ​Database Query Tool

Build and integrate custom tools to extend Claude Agent SDK functionality

Was this page helpful?

**Examples:**

Example 1 (python):
```python
import { query, tool, createSdkMcpServer } from "@anthropic-ai/claude-agent-sdk";
import { z } from "zod";

// Create an SDK MCP server with custom tools
const customServer = createSdkMcpServer({
  name: "my-custom-tools",
  version: "1.0.0",
  tools: [
    tool(
      "get_weather",
      "Get current weather for a location",
      {
        location: z.string().describe("City name or coordinates"),
        units: z.enum(["celsius", "fahrenheit"]).default("celsius").describe("Temperature units")
      },
      async (args) => {
        // Call weather API
        const response = await fetch(
...
```

Example 2 (python):
```python
import { query } from "@anthropic-ai/claude-code";

// Use the custom tools in your query with streaming input
async function* generateMessages() {
  yield {
    type: "user" as const,
    message: {
      role: "user" as const,
      content: "What's the weather in San Francisco?"
    }
  };
}

for await (const message of query({
  prompt: generateMessages(),  // Use async generator for streaming input
  options: {
    mcpServers: {
      "my-custom-tools": customServer  // Pass as object/dictionary, not array
    },
    // Optionally specify which tools Claude can use
    allowedTools: [
   
...
```

Example 3 (javascript):
```javascript
const multiToolServer = createSdkMcpServer({
  name: "utilities",
  version: "1.0.0",
  tools: [
    tool("calculate", "Perform calculations", { /* ... */ }, async (args) => { /* ... */ }),
    tool("translate", "Translate text", { /* ... */ }, async (args) => { /* ... */ }),
    tool("search_web", "Search the web", { /* ... */ }, async (args) => { /* ... */ })
  ]
});

// Allow only specific tools with streaming input
async function* generateMessages() {
  yield {
    type: "user" as const,
    message: {
      role: "user" as const,
      content: "Calculate 5 + 3 and translate 'hello' to Sp
...
```

Example 4 (python):
```python
import { z } from "zod";

tool(
  "process_data",
  "Process structured data with type safety",
  {
    // Zod schema defines both runtime validation and TypeScript types
    data: z.object({
      name: z.string(),
      age: z.number().min(0).max(150),
      email: z.string().email(),
      preferences: z.array(z.string()).optional()
    }),
    format: z.enum(["json", "csv", "xml"]).default("json")
  },
  async (args) => {
    // args is fully typed based on the schema
    // TypeScript knows: args.data.name is string, args.data.age is number, etc.
    console.log(`Processing ${args.data.na
...
```

---

## Session Management

**URL:** https://docs.claude.com/en/api/agent-sdk/sessions

**Contents:**
- Session Management
- ​Session Management
- ​How Sessions Work
  - ​Getting the Session ID
- ​Resuming Sessions
- ​Forking Sessions
  - ​When to Fork a Session
  - ​Forking vs Continuing
  - ​Example: Forking a Session

Understanding how the Claude Agent SDK handles sessions and session resumption

Was this page helpful?

**Examples:**

Example 1 (python):
```python
import { query } from "@anthropic-ai/claude-agent-sdk"

let sessionId: string | undefined

const response = query({
  prompt: "Help me build a web application",
  options: {
    model: "claude-sonnet-4-5"
  }
})

for await (const message of response) {
  // The first message is a system init message with the session ID
  if (message.type === 'system' && message.subtype === 'init') {
    sessionId = message.session_id
    console.log(`Session started with ID: ${sessionId}`)
    // You can save this ID for later resumption
  }

  // Process other messages...
  console.log(message)
}

// Later, y
...
```

Example 2 (python):
```python
import { query } from "@anthropic-ai/claude-agent-sdk"

// Resume a previous session using its ID
const response = query({
  prompt: "Continue implementing the authentication system from where we left off",
  options: {
    resume: "session-xyz", // Session ID from previous conversation
    model: "claude-sonnet-4-5",
    allowedTools: ["Read", "Edit", "Write", "Glob", "Grep", "Bash"]
  }
})

// The conversation continues with full context from the previous session
for await (const message of response) {
  console.log(message)
}
```

Example 3 (python):
```python
import { query } from "@anthropic-ai/claude-agent-sdk"

// First, capture the session ID
let sessionId: string | undefined

const response = query({
  prompt: "Help me design a REST API",
  options: { model: "claude-sonnet-4-5" }
})

for await (const message of response) {
  if (message.type === 'system' && message.subtype === 'init') {
    sessionId = message.session_id
    console.log(`Original session: ${sessionId}`)
  }
}

// Fork the session to try a different approach
const forkedResponse = query({
  prompt: "Now let's redesign this as a GraphQL API instead",
  options: {
    resume: ses
...
```

---

## Agent Skills in the SDK

**URL:** https://docs.claude.com/en/api/agent-sdk/skills

**Contents:**
- Agent Skills in the SDK
- ​Overview
- ​How Skills Work with the SDK
- ​Using Skills with the SDK
- ​Skill Locations
- ​Creating Skills
- ​Tool Restrictions
- ​Discovering Available Skills
- ​Testing Skills
- ​Troubleshooting

Extend Claude with specialized capabilities using Agent Skills in the Claude Agent SDK

Was this page helpful?

**Examples:**

Example 1 (python):
```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    options = ClaudeAgentOptions(
        cwd="/path/to/project",  # Project with .claude/skills/
        setting_sources=["user", "project"],  # Load Skills from filesystem
        allowed_tools=["Skill", "Read", "Write", "Bash"]  # Enable Skill tool
    )

    async for message in query(
        prompt="Help me process this PDF document",
        options=options
    ):
        print(message)

asyncio.run(main())
```

Example 2 (unknown):
```unknown
.claude/skills/processing-pdfs/
└── SKILL.md
```

Example 3 (unknown):
```unknown
options = ClaudeAgentOptions(
    setting_sources=["user", "project"],  # Load Skills from filesystem
    allowed_tools=["Skill", "Read", "Grep", "Glob"]  # Restricted toolset
)

async for message in query(
    prompt="Analyze the codebase structure",
    options=options
):
    print(message)
```

Example 4 (unknown):
```unknown
options = ClaudeAgentOptions(
    setting_sources=["user", "project"],  # Load Skills from filesystem
    allowed_tools=["Skill"]
)

async for message in query(
    prompt="What Skills are available?",
    options=options
):
    print(message)
```

---

## Plugins in the SDK

**URL:** https://docs.claude.com/en/api/agent-sdk/plugins

**Contents:**
- Plugins in the SDK
- ​What are plugins?
- ​Loading plugins
  - ​Path specifications
- ​Verifying plugin installation
- ​Using plugin commands
- ​Complete example
- ​Plugin structure reference
- ​Common use cases
  - ​Development and testing

Load custom plugins to extend Claude Code with commands, agents, skills, and hooks through the Agent SDK

Was this page helpful?

**Examples:**

Example 1 (python):
```python
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Hello",
  options: {
    plugins: [
      { type: "local", path: "./my-plugin" },
      { type: "local", path: "/absolute/path/to/another-plugin" }
    ]
  }
})) {
  // Plugin commands, agents, and other features are now available
}
```

Example 2 (python):
```python
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Hello",
  options: {
    plugins: [{ type: "local", path: "./my-plugin" }]
  }
})) {
  if (message.type === "system" && message.subtype === "init") {
    // Check loaded plugins
    console.log("Plugins:", message.plugins);
    // Example: [{ name: "my-plugin", path: "./my-plugin" }]

    // Check available commands from plugins
    console.log("Commands:", message.slash_commands);
    // Example: ["/help", "/compact", "my-plugin:custom-command"]
  }
}
```

Example 3 (python):
```python
import { query } from "@anthropic-ai/claude-agent-sdk";

// Load a plugin with a custom /greet command
for await (const message of query({
  prompt: "/my-plugin:greet",  // Use plugin command with namespace
  options: {
    plugins: [{ type: "local", path: "./my-plugin" }]
  }
})) {
  // Claude executes the custom greeting command from the plugin
  if (message.type === "assistant") {
    console.log(message.content);
  }
}
```

Example 4 (python):
```python
import { query } from "@anthropic-ai/claude-agent-sdk";
import * as path from "path";

async function runWithPlugin() {
  const pluginPath = path.join(__dirname, "plugins", "my-plugin");

  console.log("Loading plugin from:", pluginPath);

  for await (const message of query({
    prompt: "What custom commands do you have available?",
    options: {
      plugins: [
        { type: "local", path: pluginPath }
      ],
      maxTurns: 3
    }
  })) {
    if (message.type === "system" && message.subtype === "init") {
      console.log("Loaded plugins:", message.plugins);
      console.log("Avail
...
```

---

## Handling Permissions

**URL:** https://docs.claude.com/en/api/agent-sdk/permissions

**Contents:**
- Handling Permissions
- ​SDK Permissions
- ​Overview
- ​Permission Flow Diagram
- ​Permission Modes
  - ​Available Modes
  - ​Setting Permission Mode
    - ​1. Initial Configuration
    - ​2. Dynamic Mode Changes (Streaming Only)
  - ​Mode-Specific Behaviors

Control tool usage and permissions in the Claude Agent SDK

Was this page helpful?

**Examples:**

Example 1 (python):
```python
import { query } from "@anthropic-ai/claude-agent-sdk";

const result = await query({
  prompt: "Help me refactor this code",
  options: {
    permissionMode: 'default'  // Standard permission mode
  }
});
```

Example 2 (python):
```python
import { query } from "@anthropic-ai/claude-agent-sdk";

// Create an async generator for streaming input
async function* streamInput() {
  yield { 
    type: 'user',
    message: { 
      role: 'user', 
      content: "Let's start with default permissions" 
    }
  };
  
  // Later in the conversation...
  yield {
    type: 'user',
    message: {
      role: 'user',
      content: "Now let's speed up development"
    }
  };
}

const q = query({
  prompt: streamInput(),
  options: {
    permissionMode: 'default'  // Start in default mode
  }
});

// Change mode dynamically
await q.setPermissio
...
```

Example 3 (unknown):
```unknown
// Start in default mode for controlled execution
permissionMode: 'default'

// Switch to acceptEdits for rapid iteration
await q.setPermissionMode('acceptEdits')
```

Example 4 (python):
```python
import { query } from "@anthropic-ai/claude-agent-sdk";

async function promptForToolApproval(toolName: string, input: any) {
  console.log("\n🔧 Tool Request:");
  console.log(`   Tool: ${toolName}`);
  
  // Display tool parameters
  if (input && Object.keys(input).length > 0) {
    console.log("   Parameters:");
    for (const [key, value] of Object.entries(input)) {
      let displayValue = value;
      if (typeof value === 'string' && value.length > 100) {
        displayValue = value.substring(0, 100) + "...";
      } else if (typeof value === 'object') {
        displayValue = JSON.strin
...
```

---

## Todo Lists

**URL:** https://docs.claude.com/en/api/agent-sdk/todo-tracking

**Contents:**
- Todo Lists
  - ​Todo Lifecycle
  - ​When Todos Are Used
- ​Examples
  - ​Monitoring Todo Changes
  - ​Real-time Progress Display
- ​Related Documentation

Track and display todos using the Claude Agent SDK for organized task management

Was this page helpful?

**Examples:**

Example 1 (python):
```python
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Optimize my React app performance and track progress with todos",
  options: { maxTurns: 15 }
})) {
  // Todo updates are reflected in the message stream
  if (message.type === "assistant") {
    for (const block of message.message.content) {
      if (block.type === "tool_use" && block.name === "TodoWrite") {
        const todos = block.input.todos;

        console.log("Todo Status Update:");
        todos.forEach((todo, index) => {
          const status = todo.status === "completed" ? "✅
...
```

Example 2 (python):
```python
import { query } from "@anthropic-ai/claude-agent-sdk";

class TodoTracker {
  private todos: any[] = [];
  
  displayProgress() {
    if (this.todos.length === 0) return;
    
    const completed = this.todos.filter(t => t.status === "completed").length;
    const inProgress = this.todos.filter(t => t.status === "in_progress").length;
    const total = this.todos.length;
    
    console.log(`\nProgress: ${completed}/${total} completed`);
    console.log(`Currently working on: ${inProgress} task(s)\n`);
    
    this.todos.forEach((todo, index) => {
      const icon = todo.status === "complet
...
```

---

## Hosting the Agent SDK

**URL:** https://docs.claude.com/en/api/agent-sdk/hosting

**Contents:**
- Hosting the Agent SDK
- ​Hosting Requirements
  - ​Container-Based Sandboxing
  - ​System Requirements
- ​Understanding the SDK Architecture
- ​Sandbox Provider Options
- ​Production Deployment Patterns
  - ​Pattern 1: Ephemeral Sessions
  - ​Pattern 2: Long-Running Sessions
  - ​Pattern 3: Hybrid Sessions

Deploy and host Claude Agent SDK in production environments

Was this page helpful?

---

## Agent SDK reference - TypeScript

**URL:** https://docs.claude.com/en/api/agent-sdk/typescript

**Contents:**
- Agent SDK reference - TypeScript
- ​Installation
- ​Functions
  - ​query()
    - ​Parameters
    - ​Returns
  - ​tool()
    - ​Parameters
  - ​createSdkMcpServer()
    - ​Parameters

Complete API reference for the TypeScript Agent SDK, including all functions, types, and interfaces.

Was this page helpful?

**Examples:**

Example 1 (unknown):
```unknown
npm install @anthropic-ai/claude-agent-sdk
```

Example 2 (unknown):
```unknown
function query({
  prompt,
  options
}: {
  prompt: string | AsyncIterable<SDKUserMessage>;
  options?: Options;
}): Query
```

Example 3 (javascript):
```javascript
function tool<Schema extends ZodRawShape>(
  name: string,
  description: string,
  inputSchema: Schema,
  handler: (args: z.infer<ZodObject<Schema>>, extra: unknown) => Promise<CallToolResult>
): SdkMcpToolDefinition<Schema>
```

Example 4 (unknown):
```unknown
function createSdkMcpServer(options: {
  name: string;
  version?: string;
  tools?: Array<SdkMcpToolDefinition<any>>;
}): McpSdkServerConfigWithInstance
```

---

## Slash Commands in the SDK

**URL:** https://docs.claude.com/en/api/agent-sdk/slash-commands

**Contents:**
- Slash Commands in the SDK
- ​Discovering Available Slash Commands
- ​Sending Slash Commands
- ​Common Slash Commands
  - ​/compact - Compact Conversation History
  - ​/clear - Clear Conversation
- ​Creating Custom Slash Commands
  - ​File Locations
  - ​File Format
    - ​Basic Example

Learn how to use slash commands to control Claude Code sessions through the SDK

Was this page helpful?

**Examples:**

Example 1 (python):
```python
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Hello Claude",
  options: { maxTurns: 1 }
})) {
  if (message.type === "system" && message.subtype === "init") {
    console.log("Available slash commands:", message.slash_commands);
    // Example output: ["/compact", "/clear", "/help"]
  }
}
```

Example 2 (python):
```python
import { query } from "@anthropic-ai/claude-agent-sdk";

// Send a slash command
for await (const message of query({
  prompt: "/compact",
  options: { maxTurns: 1 }
})) {
  if (message.type === "result") {
    console.log("Command executed:", message.result);
  }
}
```

Example 3 (python):
```python
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "/compact",
  options: { maxTurns: 1 }
})) {
  if (message.type === "system" && message.subtype === "compact_boundary") {
    console.log("Compaction completed");
    console.log("Pre-compaction tokens:", message.compact_metadata.pre_tokens);
    console.log("Trigger:", message.compact_metadata.trigger);
  }
}
```

Example 4 (python):
```python
import { query } from "@anthropic-ai/claude-agent-sdk";

// Clear conversation and start fresh
for await (const message of query({
  prompt: "/clear",
  options: { maxTurns: 1 }
})) {
  if (message.type === "system" && message.subtype === "init") {
    console.log("Conversation cleared, new session started");
    console.log("Session ID:", message.session_id);
  }
}
```

---

## MCP in the SDK

**URL:** https://docs.claude.com/en/api/agent-sdk/mcp

**Contents:**
- MCP in the SDK
- ​Overview
- ​Configuration
  - ​Basic Configuration
  - ​Using MCP Servers in SDK
- ​Transport Types
  - ​stdio Servers
  - ​HTTP/SSE Servers
  - ​SDK MCP Servers
- ​Resource Management

Extend Claude Code with custom tools using Model Context Protocol servers

Was this page helpful?

**Examples:**

Example 1 (unknown):
```unknown
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem"],
      "env": {
        "ALLOWED_PATHS": "/Users/me/projects"
      }
    }
  }
}
```

Example 2 (python):
```python
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "List files in my project",
  options: {
    mcpServers: {
      "filesystem": {
        command: "npx",
        args: ["@modelcontextprotocol/server-filesystem"],
        env: {
          ALLOWED_PATHS: "/Users/me/projects"
        }
      }
    },
    allowedTools: ["mcp__filesystem__list_files"]
  }
})) {
  if (message.type === "result" && message.subtype === "success") {
    console.log(message.result);
  }
}
```

Example 3 (unknown):
```unknown
// .mcp.json configuration
{
  "mcpServers": {
    "my-tool": {
      "command": "node",
      "args": ["./my-mcp-server.js"],
      "env": {
        "DEBUG": "${DEBUG:-false}"
      }
    }
  }
}
```

Example 4 (unknown):
```unknown
// SSE server configuration
{
  "mcpServers": {
    "remote-api": {
      "type": "sse",
      "url": "https://api.example.com/mcp/sse",
      "headers": {
        "Authorization": "Bearer ${API_TOKEN}"
      }
    }
  }
}

// HTTP server configuration
{
  "mcpServers": {
    "http-service": {
      "type": "http",
      "url": "https://api.example.com/mcp",
      "headers": {
        "X-API-Key": "${API_KEY}"
      }
    }
  }
}
```

---

## Page Not Found

**URL:** https://docs.claude.com/en/api/agent-sdk/sdk-permissions

**Contents:**
- Page Not Found

---

## Tracking Costs and Usage

**URL:** https://docs.claude.com/en/api/agent-sdk/cost-tracking

**Contents:**
- Tracking Costs and Usage
- ​SDK Cost Tracking
- ​Understanding Token Usage
  - ​Key Concepts
- ​Usage Reporting Structure
  - ​Single vs Parallel Tool Use
  - ​Message Flow Example
- ​Important Usage Rules
  - ​1. Same ID = Same Usage
  - ​2. Charge Once Per Step

Understand and track token usage for billing in the Claude Agent SDK

Was this page helpful?

**Examples:**

Example 1 (python):
```python
import { query } from "@anthropic-ai/claude-agent-sdk";

// Example: Tracking usage in a conversation
const result = await query({
  prompt: "Analyze this codebase and run tests",
  options: {
    onMessage: (message) => {
      if (message.type === 'assistant' && message.usage) {
        console.log(`Message ID: ${message.id}`);
        console.log(`Usage:`, message.usage);
      }
    }
  }
});
```

Example 2 (unknown):
```unknown
<!-- Step 1: Initial request with parallel tool uses -->
assistant (text)      { id: "msg_1", usage: { output_tokens: 100, ... } }
assistant (tool_use)  { id: "msg_1", usage: { output_tokens: 100, ... } }
assistant (tool_use)  { id: "msg_1", usage: { output_tokens: 100, ... } }
assistant (tool_use)  { id: "msg_1", usage: { output_tokens: 100, ... } }
user (tool_result)
user (tool_result)
user (tool_result)

<!-- Step 2: Follow-up response -->
assistant (text)      { id: "msg_2", usage: { output_tokens: 98, ... } }
```

Example 3 (javascript):
```javascript
// All these messages have the same ID and usage
const messages = [
  { type: 'assistant', id: 'msg_123', usage: { output_tokens: 100 } },
  { type: 'assistant', id: 'msg_123', usage: { output_tokens: 100 } },
  { type: 'assistant', id: 'msg_123', usage: { output_tokens: 100 } }
];

// Charge only once per unique message ID
const uniqueUsage = messages[0].usage; // Same for all messages with this ID
```

Example 4 (javascript):
```javascript
// Final result includes total usage
const result = await query({
  prompt: "Multi-step task",
  options: { /* ... */ }
});

console.log("Total usage:", result.usage);
console.log("Total cost:", result.usage.total_cost_usd);
```

---

## Subagents in the SDK

**URL:** https://docs.claude.com/en/api/agent-sdk/subagents

**Contents:**
- Subagents in the SDK
- ​Overview
- ​Benefits of Using Subagents
  - ​Context Management
  - ​Parallelization
  - ​Specialized Instructions and Knowledge
  - ​Tool Restrictions
- ​Creating Subagents
  - ​Programmatic Definition (Recommended)
  - ​AgentDefinition Configuration

Working with subagents in the Claude Agent SDK

Was this page helpful?

**Examples:**

Example 1 (python):
```python
import { query } from '@anthropic-ai/claude-agent-sdk';

const result = query({
  prompt: "Review the authentication module for security issues",
  options: {
    agents: {
      'code-reviewer': {
        description: 'Expert code review specialist. Use for quality, security, and maintainability reviews.',
        prompt: `You are a code review specialist with expertise in security, performance, and best practices.

When reviewing code:
- Identify security vulnerabilities
- Check for performance issues
- Verify adherence to coding standards
- Suggest specific improvements

Be thorough but con
...
```

Example 2 (unknown):
```unknown
---
name: code-reviewer
description: Expert code review specialist. Use for quality, security, and maintainability reviews.
tools: Read, Grep, Glob, Bash
---

Your subagent's system prompt goes here. This defines the subagent's
role, capabilities, and approach to solving problems.
```

Example 3 (javascript):
```javascript
const result = query({
  prompt: "Optimize the database queries in the API layer",
  options: {
    agents: {
      'performance-optimizer': {
        description: 'Use PROACTIVELY when code changes might impact performance. MUST BE USED for optimization tasks.',
        prompt: 'You are a performance optimization specialist...',
        tools: ['Read', 'Edit', 'Bash', 'Grep'],
        model: 'sonnet'
      }
    }
  }
});
```

Example 4 (javascript):
```javascript
const result = query({
  prompt: "Use the code-reviewer agent to check the authentication module",
  options: {
    agents: {
      'code-reviewer': {
        description: 'Expert code review specialist',
        prompt: 'You are a security-focused code reviewer...',
        tools: ['Read', 'Grep', 'Glob']
      }
    }
  }
});
```

---

## Streaming Input

**URL:** https://docs.claude.com/en/api/agent-sdk/streaming-vs-single-mode

**Contents:**
- Streaming Input
- ​Overview
- ​Streaming Input Mode (Recommended)
  - ​How It Works
  - ​Benefits
- Image Uploads
- Queued Messages
- Tool Integration
- Hooks Support
- Real-time Feedback

Understanding the two input modes for Claude Agent SDK and when to use each

Was this page helpful?

**Examples:**

Example 1 (python):
```python
import { query } from "@anthropic-ai/claude-agent-sdk";
import { readFileSync } from "fs";

async function* generateMessages() {
  // First message
  yield {
    type: "user" as const,
    message: {
      role: "user" as const,
      content: "Analyze this codebase for security issues"
    }
  };
  
  // Wait for conditions or user input
  await new Promise(resolve => setTimeout(resolve, 2000));
  
  // Follow-up with image
  yield {
    type: "user" as const,
    message: {
      role: "user" as const,
      content: [
        {
          type: "text",
          text: "Review this architectu
...
```

Example 2 (python):
```python
import { query } from "@anthropic-ai/claude-agent-sdk";

// Simple one-shot query
for await (const message of query({
  prompt: "Explain the authentication flow",
  options: {
    maxTurns: 1,
    allowedTools: ["Read", "Grep"]
  }
})) {
  if (message.type === "result") {
    console.log(message.result);
  }
}

// Continue conversation with session management
for await (const message of query({
  prompt: "Now explain the authorization process",
  options: {
    continue: true,
    maxTurns: 1
  }
})) {
  if (message.type === "result") {
    console.log(message.result);
  }
}
```

---

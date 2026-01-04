---
name: agent-builder
description: Claude Agent SDK for Python and TypeScript. Use for building AI agents with automatic context management, tool integration, and API interactions. Includes guides on setting up agents, defining tools, handling responses, and best practices.
---

# Claude Agent SDK Skill

Comprehensive assistance with Claude Agent SDK development, generated from official documentation.

## When to Use This Skill

This skill should be triggered when:
- Working with claude-agent-sdk in Python or TypeScript
- Building AI agents with Claude Code integration
- Implementing custom tools and MCP servers
- Managing sessions, permissions, and streaming input
- Setting up system prompts and subagents
- Debugging claude-agent-sdk code or understanding API responses
- Learning claude-agent-sdk best practices and patterns

## Quick Reference

### Basic Query (Python)
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

### Basic Query (TypeScript)
```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Help me write a Python function to calculate fibonacci numbers",
  options: {
    systemPrompt: {
      type: "preset",
      preset: "claude_code",
      append: "Always include detailed docstrings and type hints in Python code.",
    },
  },
})) {
  if (message.type === "assistant") {
    console.log(message.message.content);
  }
}
```

### Custom Tools with MCP Server
```python
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool("calculate", "Perform mathematical calculations", {"expression": str})
async def calculate(args: dict[str, Any]) -> dict[str, Any]:
    try:
        result = eval(args["expression"], {"__builtins__": {}})
        return {
            "content": [{"type": "text", "text": f"Result: {result}"}]
        }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
            "is_error": True
        }

# Create server with tools
calculator = create_sdk_mcp_server(
    name="calculator",
    version="1.0.0",
    tools=[calculate]
)
```

### Session Management and Resumption
```typescript
import { query } from "@anthropic-ai/claude-agent-sdk"

let sessionId: string | undefined

// Start new session
const response = query({
  prompt: "Help me build a web application",
  options: { model: "claude-sonnet-4-5" }
})

for await (const message of response) {
  if (message.type === 'system' && message.subtype === 'init') {
    sessionId = message.session_id
    console.log(`Session started: ${sessionId}`)
  }
}

// Resume later
const resumedResponse = query({
  prompt: "Continue from where we left off",
  options: {
    resume: sessionId,
    model: "claude-sonnet-4-5"
  }
})
```

### Continuous Conversation with ClaudeSDKClient
```python
import asyncio
from claude_agent_sdk import ClaudeSDKClient

async def main():
    async with ClaudeSDKClient() as client:
        # First question
        await client.query("What's the capital of France?")
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                print(f"Claude: {message.content[0].text}")

        # Follow-up - Claude remembers context
        await client.query("What's the population of that city?")
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                print(f"Claude: {message.content[0].text}")

asyncio.run(main())
```

### Permission Handling
```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

const result = await query({
  prompt: "Help me refactor this code",
  options: {
    permissionMode: 'acceptEdits',  // Auto-approve file edits
    canUseTool: async (toolName, input) => {
      // Custom permission logic
      if (toolName === "Bash" && input.command.includes("rm -rf")) {
        return { behavior: "deny", message: "Dangerous command blocked" };
      }
      return { behavior: "allow", updatedInput: input };
    }
  }
});
```

### Streaming Input Mode
```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

async function* generateMessages() {
  yield {
    type: "user" as const,
    message: {
      role: "user" as const,
      content: "Analyze this codebase for security issues"
    }
  };
  
  // Dynamic follow-up
  await new Promise(resolve => setTimeout(resolve, 2000));
  
  yield {
    type: "user" as const,
    message: {
      role: "user" as const,
      content: "Focus on authentication vulnerabilities"
    }
  };
}

for await (const message of query({
  prompt: generateMessages(),
  options: { maxTurns: 5 }
})) {
  console.log(message);
}
```

### Subagents Configuration
```typescript
import { query } from '@anthropic-ai/claude-agent-sdk';

const result = query({
  prompt: "Review the authentication module for security issues",
  options: {
    agents: {
      'code-reviewer': {
        description: 'Expert code review specialist for security and quality reviews.',
        prompt: `You are a security-focused code reviewer. Check for:
- Security vulnerabilities
- Performance issues  
- Best practices adherence`,
        tools: ['Read', 'Grep', 'Glob'],
        model: 'sonnet'
      }
    }
  }
});
```

## Key Concepts

### Sessions and Continuity
- **query()** function creates new sessions each time (Python) or manages single sessions (TypeScript)
- **ClaudeSDKClient** (Python) maintains conversation context across multiple exchanges
- Sessions can be resumed using session IDs for long-running conversations

### Tool Integration
- Built-in tools: Read, Write, Edit, Bash, Grep, Glob, WebSearch, etc.
- Custom tools via MCP servers using `@tool` decorator and `createSdkMcpServer`
- Tool permissions controlled via `permission_mode` and `canUseTool` callbacks

### System Prompts
- Default: Empty system prompt for flexibility
- Claude Code preset: `systemPrompt: { type: "preset", preset: "claude_code" }`
- Custom prompts: Direct string or append to presets
- CLAUDE.md files: Project-level instructions (requires `settingSources`)

### Input Modes
- **Single mode**: Simple string prompts for one-off queries
- **Streaming mode**: Async generators for dynamic, multi-turn conversations
- Streaming required for MCP tools and advanced features

## Reference Files

### api_reference.md
Contains complete API documentation including:
- Error handling patterns and HTTP status codes
- Stop reason handling for message completion
- Request/response structures and limits
- Authentication and headers

### core_concepts.md
Comprehensive coverage of SDK features:
- **Python SDK Reference**: Complete API with ClaudeSDKClient, query(), tool decorators
- **TypeScript SDK Reference**: Functions, types, and interfaces
- **System Prompts**: CLAUDE.md files, output styles, custom prompts
- **Custom Tools**: MCP server creation and tool integration
- **Session Management**: Resuming, forking, and session lifecycle
- **Permissions**: Permission modes, canUseTool callbacks, security controls
- **Subagents**: Specialized agents for different tasks
- **Streaming Input**: Dynamic conversation patterns
- **Slash Commands**: Built-in and custom command creation
- **MCP Integration**: Model Context Protocol server configuration
- **Cost Tracking**: Token usage and billing information
- **Hosting**: Production deployment patterns

### getting_started.md
Basic setup and overview:
- Installation instructions for both Python and TypeScript
- Core concepts and authentication
- Why use the Agent SDK and what you can build
- Basic examples to get started

## Working with This Skill

### For Beginners
1. Start with `view getting_started.md` for installation and basic concepts
2. Review the Quick Reference examples above for common patterns
3. Use `view core_concepts.md` and search for specific topics like "Python SDK" or "Custom Tools"

### For Specific Features
- **Custom Tools**: Look for "Custom Tools" and "MCP" sections in core_concepts.md
- **Session Management**: Search for "Session Management" and "ClaudeSDKClient" 
- **Permissions**: Find "Handling Permissions" for security controls
- **System Prompts**: Check "Modifying system prompts" for behavior customization

### For Troubleshooting
- **Error Handling**: Check api_reference.md for HTTP errors and stop reasons
- **Permissions Issues**: Review permission modes and canUseTool patterns
- **Tool Integration**: Verify MCP server configuration and tool name formats

### Language-Specific Help
- **Python**: Focus on ClaudeSDKClient, async/await patterns, and type hints
- **TypeScript**: Use query() function, async generators, and Zod schemas
- Both languages share similar concepts but different implementation patterns

## Notes

- This skill covers both Python and TypeScript SDKs with unified concepts
- Examples preserve the exact syntax and patterns from official documentation
- MCP (Model Context Protocol) is key for custom tool integration
- Permission handling is crucial for production deployments
- Session management enables sophisticated multi-turn conversations
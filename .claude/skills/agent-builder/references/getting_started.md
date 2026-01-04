# Claude-Agent-Sdk - Getting Started

**Pages:** 2

---

## Overview

**URL:** https://docs.claude.com/en/api/overview

**Contents:**
- Overview
- ​Accessing the API
- ​Authentication
- ​Content types
- ​Request size limits
- ​Response Headers
- ​Examples

Was this page helpful?

**Examples:**

Example 1 (unknown):
```unknown
curl https://api.anthropic.com/v1/messages \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01" \
     --header "content-type: application/json" \
     --data \
'{
    "model": "claude-sonnet-4-5",
    "max_tokens": 1024,
    "messages": [
        {"role": "user", "content": "Hello, world"}
    ]
}'
```

---

## Agent SDK overview

**URL:** https://docs.claude.com/en/api/agent-sdk/overview

**Contents:**
- Agent SDK overview
- ​Installation
- ​SDK Options
- ​Why use the Claude Agent SDK?
- ​What can you build with the SDK?
- ​Core Concepts
  - ​Authentication
  - ​Full Claude Code Feature Support
  - ​System Prompts
  - ​Tool Permissions

Build custom AI agents with the Claude Agent SDK

Was this page helpful?

**Examples:**

Example 1 (unknown):
```unknown
npm install @anthropic-ai/claude-agent-sdk
```

---

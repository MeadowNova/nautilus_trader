# Claude-Agent-Sdk - Api Reference

**Pages:** 2

---

## Errors

**URL:** https://docs.claude.com/en/api/errors

**Contents:**
- Errors
- ​HTTP errors
- ​Request size limits
- ​Error shapes
- ​Request id
- ​Long requests

Was this page helpful?

**Examples:**

Example 1 (unknown):
```unknown
{
  "type": "error",
  "error": {
    "type": "not_found_error",
    "message": "The requested resource could not be found."
  },
  "request_id": "req_011CSHoEeqs5C35K2UUqR7Fy"
}
```

Example 2 (unknown):
```unknown
import anthropic

client = anthropic.Anthropic()

message = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello, Claude"}
    ]
)
print(f"Request ID: {message._request_id}")
```

---

## Handling stop reasons

**URL:** https://docs.claude.com/en/api/handling-stop-reasons

**Contents:**
- Handling stop reasons
- ​What is stop_reason?
- ​Stop reason values
  - ​end_turn
    - ​Empty responses with end_turn
  - ​max_tokens
  - ​stop_sequence
  - ​tool_use
  - ​pause_turn
  - ​refusal

Was this page helpful?

**Examples:**

Example 1 (unknown):
```unknown
{
  "id": "msg_01234",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "Here's the answer to your question..."
    }
  ],
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 100,
    "output_tokens": 50
  }
}
```

Example 2 (unknown):
```unknown
if response.stop_reason == "end_turn":
    # Process the complete response
    print(response.content[0].text)
```

Example 3 (python):
```python
# INCORRECT: Adding text immediately after tool_result
messages = [
    {"role": "user", "content": "Calculate the sum of 1234 and 5678"},
    {"role": "assistant", "content": [
        {
            "type": "tool_use",
            "id": "toolu_123",
            "name": "calculator",
            "input": {"operation": "add", "a": 1234, "b": 5678}
        }
    ]},
    {"role": "user", "content": [
        {
            "type": "tool_result",
            "tool_use_id": "toolu_123",
            "content": "6912"
        },
        {
            "type": "text",
            "text": "Here's the res
...
```

Example 4 (unknown):
```unknown
# Request with limited tokens
response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=10,
    messages=[{"role": "user", "content": "Explain quantum physics"}]
)

if response.stop_reason == "max_tokens":
    # Response was truncated
    print("Response was cut off at token limit")
    # Consider making another request to continue
```

---

"""
Sefaria MCP Chainlit Chatbot - Proof of Concept

A chatbot that integrates with the Sefaria MCP server for Jewish text exploration.
Supports RTL (Hebrew) text rendering and multiple AI personas.

DISCLAIMER: This is a prototype/testing environment.
Do NOT rely on this for halachic or religious decision-making.
"""

import os
import json
import asyncio
import socket
from typing import Optional
from pathlib import Path

import chainlit as cl
from openai import AsyncOpenAI
from dotenv import load_dotenv, set_key
import httpx

from personas import PERSONAS, DEFAULT_PERSONA, get_persona, list_personas

load_dotenv()

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPEN_ROUTER_API")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Sefaria MCP SSE endpoint
SEFARIA_MCP_URL = "https://mcp.sefaria.org/sse"

# Path to .env file
ENV_FILE = Path(__file__).parent / ".env"


def get_openai_client(api_key: Optional[str] = None) -> AsyncOpenAI:
    """Create an OpenRouter client with the given or default API key."""
    key = api_key or OPENROUTER_API_KEY
    return AsyncOpenAI(
        api_key=key,
        base_url=OPENROUTER_BASE_URL,
    )


async def validate_api_key(api_key: str) -> tuple[bool, str]:
    """Validate an OpenRouter API key by making a test request."""
    if not api_key:
        return False, "No API key provided"

    if not api_key.startswith("sk-or-"):
        return False, "Invalid key format (should start with 'sk-or-')"

    try:
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            resp = await http_client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "anthropic/claude-sonnet-4",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5
                }
            )
            if resp.status_code == 200:
                return True, "API key is valid"
            elif resp.status_code == 401:
                return False, "Invalid API key (authentication failed)"
            elif resp.status_code == 402:
                return False, "API key has no credits remaining"
            else:
                return False, f"API error: {resp.status_code} - {resp.text[:100]}"
    except httpx.TimeoutException:
        return False, "Connection timeout - check your internet connection"
    except Exception as e:
        return False, f"Connection error: {str(e)}"


def save_api_key_to_env(api_key: str) -> bool:
    """Save the API key to the .env file."""
    try:
        # Create .env if it doesn't exist
        if not ENV_FILE.exists():
            ENV_FILE.write_text("# Sefaria MCP Testing Environment Variables\n")

        set_key(str(ENV_FILE), "OPEN_ROUTER_API", api_key)

        # Update the global variable
        global OPENROUTER_API_KEY
        OPENROUTER_API_KEY = api_key
        os.environ["OPEN_ROUTER_API"] = api_key

        return True
    except Exception as e:
        print(f"Error saving API key: {e}")
        return False


# Initialize OpenRouter client (will be recreated if key changes)
client = get_openai_client()

# Available Sefaria MCP tools (based on the MCP server capabilities)
SEFARIA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_text",
            "description": "Retrieves the actual text content from a specific reference in the Jewish library. Args: reference (e.g. 'Genesis 1:1', 'Berakhot 2a'), version_language ('source', 'english', 'both', or omit for all).",
            "parameters": {
                "type": "object",
                "properties": {
                    "reference": {
                        "type": "string",
                        "description": "Specific text reference (e.g. 'Genesis 1:1', 'Berakhot 2a')"
                    },
                    "version_language": {
                        "type": "string",
                        "description": "Which language version to retrieve - 'source', 'english', 'both', or omit for all",
                        "enum": ["source", "english", "both"]
                    }
                },
                "required": ["reference"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "text_search",
            "description": "Searches across the entire Jewish library for passages containing specific terms. Hebrew/Aramaic searches are more reliable than English translations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search terms (Hebrew/Aramaic preferred for best results)"
                    },
                    "size": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "english_semantic_search",
            "description": "Performs semantic similarity search on English embeddings of texts from Sefaria. Works well only with English queries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find semantically similar text chunks"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_links_between_texts",
            "description": "Finds all cross-references and connections to a specific text passage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reference": {
                        "type": "string",
                        "description": "Specific text reference (e.g. 'Genesis 1:1', 'Berakhot 2a')"
                    },
                    "with_text": {
                        "type": "string",
                        "description": "Whether to include the actual text content ('0' or '1')",
                        "default": "0"
                    }
                },
                "required": ["reference"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_topic_details",
            "description": "Retrieves detailed information about specific topics in Jewish thought and texts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic_slug": {
                        "type": "string",
                        "description": "Topic identifier slug (e.g. 'moses', 'sabbath')"
                    },
                    "with_links": {
                        "type": "boolean",
                        "description": "Include links to related topics",
                        "default": False
                    },
                    "with_refs": {
                        "type": "boolean",
                        "description": "Include text references tagged with this topic",
                        "default": False
                    }
                },
                "required": ["topic_slug"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clarify_name_argument",
            "description": "Validates and autocompletes text names, book titles, references, topic slugs, author names, and categories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Partial or complete name to validate/complete"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of suggestions to return"
                    }
                },
                "required": ["name"]
            }
        }
    }
]


async def call_sefaria_mcp(tool_name: str, arguments: dict) -> str:
    """
    Call the Sefaria MCP server via SSE.

    This is a simplified implementation that makes direct API calls.
    For production, you'd want proper MCP client handling.
    """
    base_url = "https://www.sefaria.org/api"

    try:
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            if tool_name == "get_text":
                reference = arguments.get("reference", "")
                version_language = arguments.get("version_language")
                url = f"{base_url}/v3/texts/{reference}"
                if version_language:
                    url += f"?version={version_language}"
                response = await http_client.get(url)
                return response.text

            elif tool_name == "text_search":
                query = arguments.get("query", "")
                size = arguments.get("size", 10)
                url = f"{base_url}/search-wrapper/text/{query}"
                params = {"size": size}
                response = await http_client.get(url, params=params)
                return response.text

            elif tool_name == "english_semantic_search":
                query = arguments.get("query", "")
                url = f"{base_url}/search/text/{query}"
                response = await http_client.get(url)
                return response.text

            elif tool_name == "get_links_between_texts":
                reference = arguments.get("reference", "")
                with_text = arguments.get("with_text", "0")
                url = f"{base_url}/links/{reference}?with_text={with_text}"
                response = await http_client.get(url)
                return response.text

            elif tool_name == "get_topic_details":
                topic_slug = arguments.get("topic_slug", "")
                url = f"{base_url}/topics/{topic_slug}"
                params = {}
                if arguments.get("with_links"):
                    params["with_links"] = "1"
                if arguments.get("with_refs"):
                    params["with_refs"] = "1"
                response = await http_client.get(url, params=params)
                return response.text

            elif tool_name == "clarify_name_argument":
                name = arguments.get("name", "")
                limit = arguments.get("limit", 10)
                url = f"{base_url}/name/{name}?limit={limit}"
                response = await http_client.get(url)
                return response.text

            else:
                return json.dumps({"error": f"Unknown tool: {tool_name}"})

    except Exception as e:
        return json.dumps({"error": str(e)})


def format_hebrew_text(text: str) -> str:
    """
    Format text with RTL support for Hebrew content.
    Wraps Hebrew text in appropriate HTML/markdown for RTL display.
    """
    if any('\u0590' <= char <= '\u05FF' for char in text):
        return f'<div dir="rtl" style="text-align: right; font-family: \'David\', \'Noto Sans Hebrew\', serif;">{text}</div>'
    return text


def get_disclaimer_banner() -> str:
    """Return the prototype disclaimer banner."""
    return """
---

**IMPORTANT DISCLAIMER**

This is a **prototype/testing environment** for exploring the Sefaria MCP integration.

- Do **NOT** rely on this information for **halachic (Jewish legal) decisions**
- Do **NOT** use this for **religious decision-making**
- Information provided may be **incomplete or incorrect**
- Always consult **qualified rabbinical authorities** for practical guidance

<div dir="rtl" style="text-align: right; font-size: 0.9em; color: #666;">
זוהי סביבת בדיקות בלבד. אין לסמוך על מידע זה להלכה למעשה.
</div>

---
"""


@cl.on_chat_start
async def on_chat_start():
    """Initialize the chat session with API key validation and persona selection."""

    # Check if API key is configured
    api_key = OPENROUTER_API_KEY

    if not api_key:
        # No API key - prompt user to enter one
        await show_api_key_setup("No API key found. Please enter your OpenRouter API key to continue.")
        return

    # Validate the API key
    status_msg = await cl.Message(content="🔄 Validating API key...").send()

    is_valid, message = await validate_api_key(api_key)

    if not is_valid:
        await status_msg.remove()
        await show_api_key_setup(f"⚠️ API key validation failed: {message}\n\nPlease enter a valid OpenRouter API key.")
        return

    # API key is valid - show success and proceed to persona selection
    await status_msg.remove()
    await cl.Message(content="✅ API key validated successfully!").send()

    # Show persona selection
    await show_persona_selection()


async def show_api_key_setup(message: str):
    """Show the API key setup interface."""
    setup_message = f"""# Sefaria Explorer - Setup Required

{message}

## How to get an OpenRouter API key:
1. Go to [OpenRouter](https://openrouter.ai/)
2. Sign up or log in
3. Navigate to your [API Keys](https://openrouter.ai/keys)
4. Create a new key (starts with `sk-or-`)

Enter your API key below, or click the Settings button to configure it.
"""

    actions = [
        cl.Action(
            name="open_settings",
            payload={},
            label="⚙️ Open Settings",
            description="Configure your API key"
        ),
    ]

    await cl.Message(content=setup_message, actions=actions).send()

    # Store that we need API key setup
    cl.user_session.set("needs_api_key", True)


async def show_persona_selection():
    """Show the persona selection interface."""
    # Create persona selection buttons
    actions = [
        cl.Action(
            name="select_persona",
            payload={"persona": "generalist"},
            label="General Explorer",
            description="Neutral AI assistant for Jewish text exploration"
        ),
        cl.Action(
            name="select_persona",
            payload={"persona": "ashkenazi"},
            label="Ashkenazi Rabbi",
            description="Orthodox Rabbi preferring Ashkenazic sources"
        ),
        cl.Action(
            name="select_persona",
            payload={"persona": "sephardi"},
            label="Sephardi Rabbi",
            description="Orthodox Rabbi preferring Sephardic sources"
        ),
        cl.Action(
            name="select_persona",
            payload={"persona": "halacha"},
            label="Halacha Specialist",
            description="Focus on Jewish law and its sources"
        ),
        cl.Action(
            name="select_persona",
            payload={"persona": "tanakh"},
            label="Tanakh Explorer",
            description="Specialist in finding biblical sources"
        ),
        cl.Action(
            name="open_settings",
            payload={},
            label="⚙️ Settings",
            description="Configure API key and other settings"
        ),
    ]

    welcome_message = f"""# Welcome to Sefaria Explorer

{get_disclaimer_banner()}

**Select an AI persona to begin:**

Each persona has different expertise and perspectives for exploring Jewish texts.
"""

    await cl.Message(
        content=welcome_message,
        actions=actions
    ).send()


@cl.action_callback("open_settings")
async def on_open_settings(action: cl.Action):
    """Show the settings panel."""
    current_key = OPENROUTER_API_KEY
    masked_key = f"{current_key[:15]}...{current_key[-4:]}" if current_key and len(current_key) > 20 else "Not configured"

    settings_message = f"""# ⚙️ Settings

## Current Configuration

**OpenRouter API Key:** `{masked_key}`

---

## Update API Key

To update your API key, type it in the chat below in this format:

```
/setkey sk-or-v1-your-new-key-here
```

The key will be validated and saved to your `.env` file.

---

## Get an API Key

1. Visit [OpenRouter](https://openrouter.ai/)
2. Create an account or sign in
3. Go to [API Keys](https://openrouter.ai/keys)
4. Generate a new key (starts with `sk-or-`)

---
"""

    actions = [
        cl.Action(
            name="close_settings",
            payload={},
            label="← Back",
            description="Return to persona selection"
        ),
        cl.Action(
            name="validate_current_key",
            payload={},
            label="🔄 Re-validate Current Key",
            description="Test if the current API key is working"
        ),
    ]

    await cl.Message(content=settings_message, actions=actions).send()


@cl.action_callback("close_settings")
async def on_close_settings(action: cl.Action):
    """Return to persona selection."""
    await show_persona_selection()


@cl.action_callback("validate_current_key")
async def on_validate_key(action: cl.Action):
    """Re-validate the current API key."""
    status_msg = await cl.Message(content="🔄 Validating API key...").send()

    is_valid, message = await validate_api_key(OPENROUTER_API_KEY)

    await status_msg.remove()

    if is_valid:
        await cl.Message(content=f"✅ {message}").send()
    else:
        await cl.Message(content=f"❌ {message}").send()


async def handle_setkey_command(content: str):
    """Handle the /setkey command to update the API key."""
    global client, OPENROUTER_API_KEY

    # Extract the key from the command
    parts = content.strip().split(maxsplit=1)
    if len(parts) < 2:
        await cl.Message(content="❌ Please provide an API key: `/setkey sk-or-v1-your-key-here`").send()
        return

    new_key = parts[1].strip()

    # Validate the new key
    status_msg = await cl.Message(content="🔄 Validating new API key...").send()

    is_valid, message = await validate_api_key(new_key)

    await status_msg.remove()

    if not is_valid:
        await cl.Message(content=f"❌ Invalid API key: {message}").send()
        return

    # Save the key
    if save_api_key_to_env(new_key):
        # Update the client
        OPENROUTER_API_KEY = new_key
        client = get_openai_client(new_key)

        # Clear the needs_api_key flag
        cl.user_session.set("needs_api_key", False)

        masked_key = f"{new_key[:15]}...{new_key[-4:]}"
        await cl.Message(content=f"✅ API key saved successfully!\n\n**Key:** `{masked_key}`\n\nYou can now select a persona to begin.").send()

        # Show persona selection
        await show_persona_selection()
    else:
        await cl.Message(content="❌ Failed to save API key to .env file. Check file permissions.").send()


@cl.action_callback("select_persona")
async def on_persona_select(action: cl.Action):
    """Handle persona selection."""
    persona_key = action.payload.get("persona", DEFAULT_PERSONA)
    persona = get_persona(persona_key)

    # Recreate client with current API key (in case it was updated)
    global client
    client = get_openai_client()

    # Store persona in session
    cl.user_session.set("persona", persona_key)
    cl.user_session.set("message_history", [
        {
            "role": "system",
            "content": persona["system_prompt"]
        }
    ])

    # Send confirmation with persona-specific welcome
    persona_welcome = f"""## {persona['name']} is ready!

*{persona['description']}*

{get_disclaimer_banner()}

You can now explore Jewish texts. Try:

- **Look up specific texts**: "Show me Genesis 1:1" or "Get Berakhot 2a"
- **Search for topics**: "Find texts about Shabbat"
- **Explore connections**: "What texts are linked to Exodus 20:1?"
- **Learn about concepts**: "Tell me about the topic of teshuvah"

<div dir="rtl" style="text-align: right;">
ברוכים הבאים! אני יכול לעזור לך לחקור טקסטים יהודיים.
</div>

How can I help you explore today?"""

    await cl.Message(content=persona_welcome).send()

    # Remove the action buttons from the original message
    await action.remove()


@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming messages."""

    # Handle /setkey command
    if message.content.strip().startswith("/setkey "):
        await handle_setkey_command(message.content)
        return

    # Handle direct API key input when setup is needed
    needs_api_key = cl.user_session.get("needs_api_key")
    if needs_api_key and message.content.strip().startswith("sk-or-"):
        await handle_setkey_command(f"/setkey {message.content.strip()}")
        return

    message_history = cl.user_session.get("message_history")

    # Check if persona was selected
    if message_history is None:
        await cl.Message(
            content="Please select a persona first by clicking one of the buttons above."
        ).send()
        return

    message_history.append({"role": "user", "content": message.content})

    # Create initial response message
    response_msg = cl.Message(content="")
    await response_msg.send()

    try:
        # Call OpenRouter with tools
        response = await client.chat.completions.create(
            model="anthropic/claude-sonnet-4",
            messages=message_history,
            tools=SEFARIA_TOOLS,
            tool_choice="auto",
            max_tokens=4096,
        )

        assistant_message = response.choices[0].message

        # Handle tool calls if any
        if assistant_message.tool_calls:
            # Add assistant message with tool calls to history
            message_history.append({
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in assistant_message.tool_calls
                ]
            })

            # Process each tool call
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                # Show user what we're doing
                await cl.Message(
                    content=f"Searching Sefaria: {tool_name}\n`{json.dumps(arguments, ensure_ascii=False)}`",
                    author="System"
                ).send()

                # Call the Sefaria API
                result = await call_sefaria_mcp(tool_name, arguments)

                # Add tool result to history
                message_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

            # Get final response after tool calls
            final_response = await client.chat.completions.create(
                model="anthropic/claude-sonnet-4",
                messages=message_history,
                max_tokens=4096,
            )

            final_content = final_response.choices[0].message.content or ""

            # Format any Hebrew content
            formatted_content = format_hebrew_text(final_content)

            response_msg.content = formatted_content
            await response_msg.update()

            # Add to history
            message_history.append({
                "role": "assistant",
                "content": final_content
            })
        else:
            # No tool calls, just respond directly
            content = assistant_message.content or ""
            formatted_content = format_hebrew_text(content)

            response_msg.content = formatted_content
            await response_msg.update()

            message_history.append({
                "role": "assistant",
                "content": content
            })

        # Update session history
        cl.user_session.set("message_history", message_history)

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        response_msg.content = error_msg
        await response_msg.update()


def find_available_port(start_port: int = 8000, max_attempts: int = 10) -> int:
    """
    Find an available port starting from start_port.
    Tries sequential ports until one is available.
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find an available port in range {start_port}-{start_port + max_attempts - 1}")


if __name__ == "__main__":
    import sys
    from chainlit.cli import run_chainlit

    # Find available port
    port = find_available_port(9101)
    print(f"Starting Sefaria Explorer on port {port}...")

    # Inject port into sys.argv for chainlit
    sys.argv = [sys.argv[0], "app.py", "--host", "0.0.0.0", "--port", str(port)]
    run_chainlit(__file__)

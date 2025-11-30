# Sefaria MCP Testing

Test prompts and responses using [Sefaria Texts MCP](https://github.com/Sefaria/Sefaria-MCP) and [HebCal](https://www.hebcal.com/) integrations.

## Purpose

This repository contains example prompts and their outputs for testing:

- **Sefaria MCP**: Access to Jewish texts, commentaries, and scholarly resources
- **HebCal**: Jewish calendar data, holidays, and zmanim

## Setup

### MCP Configuration

Add the following to your `.mcp.json` (or Claude Code MCP settings):

```json
{
  "mcpServers": {
    "sefaria": {
      "type": "sse",
      "url": "https://mcp.sefaria.org/sse"
    },
    "hebcal": {
      "type": "sse",
      "url": "https://www.hebcal.com/mcp"
    }
  }
}
```

Both MCPs use public SSE endpoints—no API keys required.

### Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Configure the following:

| Variable | Required | Description |
|----------|----------|-------------|
| `OPEN_ROUTER_API` | Yes | Your [OpenRouter](https://openrouter.ai/) API key |

The Sefaria and HebCal MCPs use public endpoints—no additional keys needed.

## Contents

Test cases demonstrating various queries and responses from these MCPs.

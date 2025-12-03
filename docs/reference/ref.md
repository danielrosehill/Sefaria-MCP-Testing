# Jewish MCP Reference

Remote hosted MCP servers — no local installation required.

## Available Endpoints

| MCP | URL | Purpose |
|-----|-----|---------|
| Sefaria Texts | `https://mcp.sefaria.org/sse` | Search and retrieve Jewish texts with precise citations |
| Sefaria Developers | `https://developers.sefaria.org/mcp` | Sefaria API interaction for code generation and data queries |
| Hebcal | `https://www.hebcal.com/mcp` | Jewish calendar: date conversions, holidays, Torah portions, yahrzeits, Daf Yomi |

## Configuration

Add to `.mcp.json`:

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

## Resources

### Sefaria
- [Official Documentation](https://developers.sefaria.org/docs/the-sefaria-mcp)
- [Self-hosted option (GitHub)](https://github.com/Sefaria/sefaria-mcp)

### Hebcal
- [Official Documentation](https://www.hebcal.com/home/5027/jewish-calendar-model-context-protocol-mcp)
- [GitHub](https://github.com/hebcal/hebcal-mcp)

### Other
- [Jewish Interest MCP Projects](https://github.com/danielrosehill/Jewish-Interest-MCP-Projects)

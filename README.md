# td-mcp

MCP (Model Context Protocol) server for controlling TouchDesigner from AI coding agents like Claude Code and Codex CLI.

## Setup

### 1. TouchDesigner Side

1. Install the callbacks file into your TD project:
   ```bash
   cd /path/to/your-td-project
   uvx td-mcp install
   ```
2. Create a WebServer DAT in TouchDesigner
3. Set Port to `9980`
4. Set the WebServer DAT's callbacks File parameter to `td_mcp_callbacks.py`
5. Toggle Active ON

### 2. Agent Side

#### Claude Code (`.mcp.json`)

```json
{
  "mcpServers": {
    "touchdesigner": {
      "command": "uvx",
      "args": ["td-mcp"],
      "env": {
        "TD_HOST": "127.0.0.1",
        "TD_PORT": "9980"
      }
    }
  }
}
```

#### Codex CLI

```bash
codex mcp add touchdesigner \
  --env TD_HOST=127.0.0.1 \
  --env TD_PORT=9980 \
  -- uvx td-mcp
```

## Tools

| Tool | Description |
|---|---|
| `td_get_root` | Get project root path (call first) |
| `td_create_op` | Create an operator |
| `td_delete_op` | Delete an operator |
| `td_list_ops` | List child operators |
| `td_get_op_info` | Get operator info |
| `td_set_params` | Set parameters (batch) |
| `td_get_params` | Get parameters (with schema discovery) |
| `td_connect` | Connect operators |
| `td_disconnect` | Disconnect operators |
| `td_find_empty_space` | Find empty space in network editor |
| `td_execute` | Execute Python code in TD |
| `td_get_screenshot` | Capture TOP screenshot |

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `TD_HOST` | `127.0.0.1` | TouchDesigner host |
| `TD_PORT` | `9980` | WebServer DAT port |
| `TD_TIMEOUT` | `10.0` | Request timeout (seconds) |

## Architecture

```
AI Agent → MCP Server (stdio) → HTTP Client → TouchDesigner WebServer DAT
```

## Security Note

`td_execute` allows arbitrary Python execution inside TouchDesigner. Use only in trusted local environments.

## License

MIT

"""FastMCP server instance and tool registration."""

from mcp.server.fastmcp import FastMCP

from .tools import connections, execute, operators, parameters

mcp = FastMCP(
    "TouchDesigner",
    instructions=(
        "MCP server for controlling TouchDesigner. "
        "Provides tools to create/delete/query operators, set parameters, "
        "manage connections, execute Python code, and capture screenshots. "
        "Optimized for minimal token usage — use default field sets unless you need more detail. "
        "IMPORTANT: Always call td_get_root first to discover the actual project path before using "
        "any tool that requires a path. Never assume the project path is '/project1'."
    ),
)

# Register all tool modules
operators.register(mcp)
parameters.register(mcp)
connections.register(mcp)
execute.register(mcp)

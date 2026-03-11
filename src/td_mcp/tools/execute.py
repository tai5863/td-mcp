"""Code execution and screenshot tools."""

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..td_client import td


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def td_execute(
        code: str,
        return_expression: str | None = None,
    ) -> dict:
        """Execute Python code inside TouchDesigner.

        Args:
            code: Python code to execute in TD's main thread
            return_expression: Optional expression to evaluate and return after execution
        """
        p: dict[str, Any] = {"code": code}
        if return_expression:
            p["return_expression"] = return_expression
        return await td.request("execute", p)

    @mcp.tool()
    async def td_get_screenshot(
        path: str,
        width: int = 640,
        format: str = "jpeg",
    ) -> dict:
        """Get a screenshot of a TOP operator as base64 image.

        Args:
            path: Path to a TOP operator
            width: Output width in pixels (default 640, height auto-scaled)
            format: Image format — "jpeg" (default, smaller) or "png"
        """
        return await td.request("get_screenshot", {
            "path": path,
            "width": width,
            "format": format,
        })

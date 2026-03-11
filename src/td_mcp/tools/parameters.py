"""Parameter get/set tools."""

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..td_client import td


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def td_set_params(
        path: str,
        params: dict[str, Any],
    ) -> dict:
        """Set multiple parameters on an operator in a single batch call.

        Args:
            path: Operator path
            params: Dict of parameter names to values (e.g. {"roughness": 0.5, "seed": 42})
        """
        return await td.request("set_params", {"path": path, "params": params})

    @mcp.tool()
    async def td_get_params(
        path: str,
        names: list[str] | None = None,
        pattern: str | None = None,
        discover: bool = False,
        page: int = 0,
    ) -> dict:
        """Get parameters from an operator. Returns only non-default values by default for token efficiency.

        Args:
            path: Operator path
            names: Specific parameter names to retrieve (returns all values including defaults)
            pattern: Glob pattern to filter parameter names (e.g. "noise*")
            discover: If true, returns rich schema per parameter (value, default, type, min, max, page, menuNames). Use this to discover available parameter names and their types for an unfamiliar operator.
            page: Page number for paginated results (50 params per page)
        """
        p: dict[str, Any] = {"path": path, "page": page}
        if names:
            p["names"] = names
        if pattern:
            p["pattern"] = pattern
        if discover:
            p["discover"] = True
        return await td.request("get_params", p)

"""Operator CRUD tools."""

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..td_client import td


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def td_get_root() -> dict:
        """Get the actual project root path. Call this FIRST before using any other tool that requires a path.

        Returns the path of the top-level project COMP (e.g. "/project1" or whatever the user named it).
        Do not assume "/project1" — always discover the real path with this tool.
        """
        result = await td.request("list_ops", {"path": "/", "fields": ["name", "path", "type"], "limit": 10})
        ops = result.get("ops", []) if isinstance(result, dict) else result
        # Return the first Base COMP child of root (the project container)
        for op in ops:
            if op.get("type") in ("baseCOMP", "Base"):
                return {"root": op.get("path"), "ops": ops}
        return {"root": ops[0].get("path") if ops else "/project1", "ops": ops}

    @mcp.tool()
    async def td_create_op(
        parent: str,
        op_type: str,
        name: str | None = None,
        params: dict[str, Any] | None = None,
        nodeX: int | None = None,
        nodeY: int | None = None,
    ) -> dict:
        """Create a new operator in TouchDesigner.

        Args:
            parent: Parent path (e.g. "/project1")
            op_type: TD operator class name (e.g. "noiseCHOP", "constantTOP", "textDAT")
            name: Optional name for the new operator
            params: Optional dict of parameters to set immediately after creation
            nodeX: Optional X position in the network editor. Use td_find_empty_space to get a non-overlapping position.
            nodeY: Optional Y position in the network editor. Use td_find_empty_space to get a non-overlapping position.
        """
        p: dict[str, Any] = {"parent": parent, "op_type": op_type}
        if name:
            p["name"] = name
        if params:
            p["params"] = params
        if nodeX is not None:
            p["nodeX"] = nodeX
        if nodeY is not None:
            p["nodeY"] = nodeY
        return await td.request("create_op", p)

    @mcp.tool()
    async def td_delete_op(path: str) -> dict:
        """Delete an operator.

        Args:
            path: Full path of the operator to delete (e.g. "/project1/noise1")
        """
        return await td.request("delete_op", {"path": path})

    @mcp.tool()
    async def td_list_ops(
        path: str,
        family: str | None = None,
        type_filter: str | None = None,
        fields: list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """List child operators with optional filtering and pagination.

        Args:
            path: Parent path to list children of
            family: Filter by family (CHOP, TOP, SOP, DAT, COMP, MAT)
            type_filter: Filter by specific type name
            fields: Fields to return per op (default: name, type, family)
            limit: Max results (default 50)
            offset: Skip first N results
        """
        p: dict[str, Any] = {"path": path, "limit": limit, "offset": offset}
        if family:
            p["family"] = family
        if type_filter:
            p["type_filter"] = type_filter
        if fields:
            p["fields"] = fields
        return await td.request("list_ops", p)

    @mcp.tool()
    async def td_get_op_info(
        path: str,
        fields: list[str] | None = None,
    ) -> dict:
        """Get info about an operator. Returns minimal fields by default for token efficiency.

        Args:
            path: Operator path
            fields: Fields to return (default: name, type, family). Available: name, type, family, path, inputs, outputs, numChildren, comment, storage, tags, nodeX, nodeY
        """
        p: dict[str, Any] = {"path": path}
        if fields:
            p["fields"] = fields
        return await td.request("get_op_info", p)

    @mcp.tool()
    async def td_find_empty_space(
        parent: str,
        width: int = 200,
        height: int = 200,
        direction: str = "right",
        padding: int = 50,
    ) -> dict:
        """Find an empty (non-overlapping) position for a new operator in the network editor.

        Returns nodeX, nodeY coordinates that can be passed directly to td_create_op.

        Args:
            parent: Parent path to search in (e.g. "/project1")
            width: Estimated width of the new operator (default 200)
            height: Estimated height of the new operator (default 200)
            direction: Placement strategy — "right" (next to rightmost op), "below" (under bottommost op), or "grid" (find first free slot in grid scan)
            padding: Minimum gap between operators (default 50)
        """
        return await td.request("find_empty_space", {
            "parent": parent,
            "width": width,
            "height": height,
            "direction": direction,
            "padding": padding,
        })

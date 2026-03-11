"""HTTP client for communicating with TouchDesigner's WebServer DAT."""

from typing import Any

import httpx

from .config import settings


class TDError(Exception):
    """Error returned from TouchDesigner."""

    def __init__(self, message: str, code: str = "UNKNOWN", suggestions: list[str] | None = None):
        self.code = code
        self.suggestions = suggestions
        msg = f"[{code}] {message}"
        if suggestions:
            msg += f" Did you mean: {', '.join(suggestions)}?"
        super().__init__(msg)


class TDClient:
    """Async HTTP client that talks to the TD WebServer DAT."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.td_base_url,
            timeout=settings.td_timeout,
        )

    async def request(self, action: str, params: dict[str, Any] | None = None) -> Any:
        """Send an action to TD and return the data payload."""
        payload = {"action": action}
        if params:
            payload["params"] = params

        try:
            resp = await self._client.post("/api", json=payload)
        except httpx.ConnectError:
            raise TDError(
                f"Cannot connect to TouchDesigner at {settings.td_base_url}. "
                "Ensure WebServer DAT is running on the correct port.",
                code="CONNECTION_REFUSED",
            )
        except httpx.TimeoutException:
            raise TDError(
                f"Request to TouchDesigner timed out after {settings.td_timeout}s.",
                code="TIMEOUT",
            )

        body = resp.json()
        if not body.get("ok"):
            raise TDError(
                body.get("error", "Unknown error from TouchDesigner"),
                code=body.get("code", "INTERNAL"),
                suggestions=body.get("suggestions"),
            )
        return body.get("data")

    async def close(self) -> None:
        await self._client.aclose()


# Module-level singleton
td = TDClient()

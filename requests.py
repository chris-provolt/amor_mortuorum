"""Minimal stand-in for the ``requests`` library used in tests."""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, Optional

Dispatcher = Callable[["Session", str, str, Dict[str, Any]], "Response"]

_mock_dispatcher: Optional[Dispatcher] = None


class RequestException(Exception):
    """Base exception raised for network errors."""


class Response:
    def __init__(
        self,
        status_code: int,
        *,
        json_data: Any | None = None,
        text: str | None = None,
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data
        self.text = text or ""

    def json(self) -> Any:
        if self._json_data is not None:
            return self._json_data
        if self.text:
            return json.loads(self.text)
        return {}


class Session:
    def __init__(self) -> None:
        self.headers: Dict[str, str] = {}

    def request(
        self, method: str, url: str, timeout: float | None = None, **kwargs: Any
    ) -> Response:
        if _mock_dispatcher is None:
            raise RequestException("No HTTP dispatcher configured for stubbed requests")
        return _mock_dispatcher(self, method.upper(), url, kwargs)

    def get(self, url: str, timeout: float | None = None, **kwargs: Any) -> Response:
        return self.request("GET", url, timeout=timeout, **kwargs)

    def post(self, url: str, timeout: float | None = None, **kwargs: Any) -> Response:
        return self.request("POST", url, timeout=timeout, **kwargs)

    def patch(self, url: str, timeout: float | None = None, **kwargs: Any) -> Response:
        return self.request("PATCH", url, timeout=timeout, **kwargs)


def _set_mock_dispatcher(dispatcher: Optional[Dispatcher]) -> None:
    global _mock_dispatcher
    _mock_dispatcher = dispatcher

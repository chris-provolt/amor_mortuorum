"""Minimal subset of the ``responses`` HTTP mocking API for tests."""
from __future__ import annotations

from contextlib import ContextDecorator
from dataclasses import dataclass
from functools import wraps
from typing import Any, Dict, List, Optional

import requests

GET = "GET"
POST = "POST"
PATCH = "PATCH"
DELETE = "DELETE"


@dataclass
class _Mock:
    method: str
    url: str
    status: int
    body: Optional[str]
    json_data: Any


_active: List["RequestsMock"] = []


class RequestsMock(ContextDecorator):
    def __init__(self) -> None:
        self._mocks: List[_Mock] = []
        self.calls: List[Dict[str, Any]] = []

    def add(
        self,
        method: str,
        url: str,
        *,
        body: str | None = None,
        json: Any | None = None,
        status: int = 200,
    ) -> None:
        self._mocks.append(_Mock(method.upper(), url, status, body, json))

    def _dispatch(
        self,
        session: requests.Session,
        method: str,
        url: str,
        kwargs: Dict[str, Any],
    ) -> requests.Response:
        for idx, mock in enumerate(self._mocks):
            if mock.method == method and mock.url == url:
                self.calls.append({"method": method, "url": url, "kwargs": kwargs})
                self._mocks.pop(idx)
                return requests.Response(
                    mock.status, json_data=mock.json_data, text=mock.body
                )
        raise requests.RequestException(
            f"No mock registered for {method} {url}"
        )

    def __enter__(self) -> "RequestsMock":
        self.calls.clear()
        _active.append(self)
        requests._set_mock_dispatcher(self._dispatch)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if _active and _active[-1] is self:
            _active.pop()
        requests._set_mock_dispatcher(_active[-1]._dispatch if _active else None)


def add(
    method: str,
    url: str,
    *,
    body: str | None = None,
    json: Any | None = None,
    status: int = 200,
) -> None:
    if not _active:
        raise RuntimeError("responses.add must be called within an active context")
    _active[-1].add(method, url, body=body, json=json, status=status)


def activate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with RequestsMock():
            return func(*args, **kwargs)

    return wrapper

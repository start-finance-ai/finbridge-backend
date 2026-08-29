from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.config import DEFAULT_BIZINFO_SNAPSHOT
from app.main import create_app


class ASGITestClient:
    def __init__(self, application: FastAPI) -> None:
        self._application = application

    def get(self, path: str) -> httpx.Response:
        return self.request("GET", path)

    def post(self, path: str, *, json: Any) -> httpx.Response:
        return self.request("POST", path, json=json)

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        async def send() -> httpx.Response:
            transport = httpx.ASGITransport(app=self._application)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as client:
                return await client.request(method, path, **kwargs)

        return asyncio.run(send())


@pytest.fixture
def snapshot_path() -> Path:
    return DEFAULT_BIZINFO_SNAPSHOT


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch, snapshot_path: Path
) -> ASGITestClient:
    monkeypatch.setenv("FINBRIDGE_BIZINFO_SNAPSHOT", str(snapshot_path))
    return ASGITestClient(create_app())

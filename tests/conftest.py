from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.main import create_app


TEST_BIZINFO_SNAPSHOT = (
    Path(__file__).resolve().parent / "fixtures" / "bizinfo_startup_sample_20.json"
)


class ASGITestClient:
    def __init__(self, application: FastAPI) -> None:
        self._application = application

    def get(self, path: str) -> httpx.Response:
        return self.request("GET", path)

    def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", path, **kwargs)

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
    return TEST_BIZINFO_SNAPSHOT


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch, snapshot_path: Path
) -> ASGITestClient:
    monkeypatch.setenv("FINBRIDGE_BIZINFO_SNAPSHOT", str(snapshot_path))
    return ASGITestClient(create_app())

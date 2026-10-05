from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.config import BIZINFO_BOOTSTRAP_SNAPSHOT
from app.main import create_app


TEST_BIZINFO_SNAPSHOT = (
    Path(os.environ["FINBRIDGE_TEST_SNAPSHOT"]).expanduser().resolve()
    if os.environ.get("FINBRIDGE_TEST_SNAPSHOT")
    else Path(__file__).resolve().parents[1] / "data" / "private" / "bizinfo_startup_sample_20.json"
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
    if not TEST_BIZINFO_SNAPSHOT.is_file():
        if os.environ.get("FINBRIDGE_TEST_SNAPSHOT"):
            pytest.fail("Explicit FINBRIDGE_TEST_SNAPSHOT file does not exist")
        pytest.skip("Private 20-record Bizinfo fixture is not bundled; set FINBRIDGE_TEST_SNAPSHOT")
    return TEST_BIZINFO_SNAPSHOT


@pytest.fixture
def real_bootstrap_path() -> Path:
    configured = os.environ.get("FINBRIDGE_TEST_BOOTSTRAP")
    path = (
        Path(configured).expanduser().resolve() if configured else
        Path(__file__).resolve().parents[1] / "data" / "private" / "bizinfo_startup_bootstrap.json"
    )
    if not path.is_file():
        if configured:
            pytest.fail("Explicit FINBRIDGE_TEST_BOOTSTRAP file does not exist")
        pytest.skip("Private 69-record Bizinfo bootstrap is not bundled; set FINBRIDGE_TEST_BOOTSTRAP")
    return path


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch,
) -> ASGITestClient:
    monkeypatch.setenv("FINBRIDGE_BIZINFO_SNAPSHOT", str(BIZINFO_BOOTSTRAP_SNAPSHOT))
    return ASGITestClient(create_app())


@pytest.fixture
def private_client(
    monkeypatch: pytest.MonkeyPatch, snapshot_path: Path
) -> ASGITestClient:
    monkeypatch.setenv("FINBRIDGE_BIZINFO_SNAPSHOT", str(snapshot_path))
    return ASGITestClient(create_app())

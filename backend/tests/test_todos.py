from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import init_db
from app.settings import get_settings
from app.main import create_app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_todo_crud(tmp_path: Path, monkeypatch) -> None:
    get_settings.cache_clear()
    db_path = tmp_path / "todo.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    init_db()

    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/healthz")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        response = await client.post("/api/todos", json={"title": "Write tutorial"})
        assert response.status_code == 201
        todo = response.json()
        assert todo["title"] == "Write tutorial"
        assert todo["completed"] is False

        response = await client.patch(f"/api/todos/{todo['id']}", json={"completed": True})
        assert response.status_code == 200
        assert response.json()["completed"] is True

        response = await client.get("/api/todos")
        assert response.status_code == 200
        assert len(response.json()) == 1

        response = await client.delete(f"/api/todos/{todo['id']}")
        assert response.status_code == 204

        response = await client.get("/api/todos")
        assert response.status_code == 200
        assert response.json() == []

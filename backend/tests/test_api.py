"""
Integration API tests using AsyncClient against FastAPI application.
"""

from pathlib import Path
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.database import init_db
from app.main import app


@pytest_asyncio.fixture(autouse=True, loop_scope="function")
async def setup_database():
    await init_db()


@pytest.mark.asyncio
async def test_root_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "AI Code Intelligence" in data["name"]
        assert "$0" in data["cost"]


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "services" in data
        assert "backend" in data["services"]
        assert data["services"]["backend"]["status"] == "ok"


@pytest.mark.asyncio
async def test_models_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/models")
        assert resp.status_code == 200
        data = resp.json()
        assert "current_model" in data


@pytest.mark.asyncio
async def test_repository_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        repo_path = str(Path("/Users/aanandd/coding/AI-Projects/ai-code-intelligence").resolve())

        # 1. Create or get repo
        list_resp = await client.get("/api/repositories")
        assert list_resp.status_code == 200
        existing = [r for r in list_resp.json()["repositories"] if r["path"] == repo_path]

        if existing:
            repo_id = existing[0]["id"]
        else:
            create_resp = await client.post(
                "/api/repositories",
                json={"path": repo_path, "name": "AI Code Intelligence"},
            )
            assert create_resp.status_code == 201
            repo_id = create_resp.json()["id"]

        # 2. Get repository details
        get_resp = await client.get(f"/api/repositories/{repo_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == repo_id

        # 3. List files
        files_resp = await client.get(f"/api/repositories/{repo_id}/files")
        assert files_resp.status_code == 200
        files = files_resp.json()
        assert len(files) > 0

        # 4. Get file tree
        tree_resp = await client.get(f"/api/repositories/{repo_id}/tree")
        assert tree_resp.status_code == 200
        assert isinstance(tree_resp.json(), list)

        # 5. Read a specific file
        file_resp = await client.get(
            f"/api/repositories/{repo_id}/file",
            params={"path": "backend/app/main.py"},
        )
        assert file_resp.status_code == 200
        assert "FastAPI" in file_resp.json()["content"]

        # 6. Index repository
        idx_resp = await client.post(f"/api/repositories/{repo_id}/index")
        assert idx_resp.status_code == 200
        assert idx_resp.json()["status"] in ("completed", "running")

        # 7. Semantic search
        search_resp = await client.post(
            f"/api/repositories/{repo_id}/semantic-search",
            json={"query": "FastAPI uvicorn startup configuration", "top_k": 3},
        )
        assert search_resp.status_code == 200
        results = search_resp.json()["results"]
        assert len(results) > 0

        # 8. Code Review
        review_resp = await client.post(
            f"/api/repositories/{repo_id}/review",
            json={
                "code": "import os\nsecret = 'sk-1234567890abcdef123456'\n",
                "review_type": "security",
            },
        )
        assert review_resp.status_code == 200
        assert len(review_resp.json()["findings"]) > 0

        # 9. Git status
        git_resp = await client.get(f"/api/repositories/{repo_id}/git/status")
        assert git_resp.status_code == 200
        assert "branch" in git_resp.json()

        # 10. Patch preview
        patch_resp = await client.post(
            f"/api/repositories/{repo_id}/patch/preview",
            json={
                "description": "API Test patch",
                "files": [{
                    "file_path": "backend/app/main.py",
                    "after": "# header comment\n" + file_resp.json()["content"],
                }],
            },
        )
        assert patch_resp.status_code == 200
        assert len(patch_resp.json()["files"]) == 1
        assert "diff" in patch_resp.json()["files"][0]

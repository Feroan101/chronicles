from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from chronicle.api import create_app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def client(tmp_path: Path):
    """A migrated Chronicle store on a temp file, served through the REST app."""
    db_path = tmp_path / "chronicle.db"
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(cfg, "head")
    db = create_engine(f"sqlite:///{db_path}")
    app = create_app(sessionmaker(bind=db))
    return TestClient(app)


@pytest.fixture()
def project_id(client) -> str:
    response = client.post("/projects", json={"name": "demo"})
    assert response.status_code == 201
    return response.json()["id"]


def _create_memory(client, project_id, content, **kwargs):
    return client.post("/memories", json={"project_id": project_id, "content": content, **kwargs})


def test_application_startup_serves_docs_and_schema(client):
    docs = client.get("/docs")
    assert docs.status_code == 200

    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    paths = schema.json()["paths"]
    assert set(paths) == {
        "/projects",
        "/projects/{project_id}",
        "/memories",
        "/memories/{memory_id}",
        "/projects/{project_id}/memories",
        "/memories/{memory_id}/versions",
        "/memories/{memory_id}/versions/{sequence}/evidence",
        "/search",
        "/projects/{project_id}/observations",
        "/observations/{observation_id}/process",
        "/projects/{project_id}/relationships",
        "/memories/{memory_id}/relationships",
        "/relationships/{relationship_id}",
        "/projects/{project_id}/snapshots",
        "/snapshots/{snapshot_id}",
    }


def test_create_project(client):
    response = client.post("/projects", json={"name": "demo", "description": "x"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "demo"
    assert body["description"] == "x"
    assert body["id"]
    assert body["created_at"]


def test_get_project(client, project_id):
    response = client.get(f"/projects/{project_id}")
    assert response.status_code == 200
    assert response.json()["id"] == project_id


def test_get_unknown_project_returns_404(client):
    response = client.get("/projects/missing")
    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found: missing"}


def test_create_memory_creates_first_version(client, project_id):
    response = _create_memory(client, project_id, "first", type="fact", context="ctx")
    assert response.status_code == 201
    body = response.json()
    assert body["project_id"] == project_id
    assert body["type"] == "fact"
    assert len(body["versions"]) == 1
    version = body["versions"][0]
    assert version["sequence"] == 1
    assert version["content"] == "first"
    assert version["context"] == "ctx"


def test_create_memory_unknown_project_returns_404(client):
    response = _create_memory(client, "missing", "first")
    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found: missing"}


def test_get_memory(client, project_id):
    memory_id = _create_memory(client, project_id, "first").json()["id"]
    response = client.get(f"/memories/{memory_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == memory_id
    assert body["project_id"] == project_id
    assert len(body["versions"]) == 1


def test_get_unknown_memory_returns_404(client):
    response = client.get("/memories/missing")
    assert response.status_code == 404
    assert response.json() == {"detail": "Memory not found: missing"}


def test_list_memories_orders_by_creation(client, project_id):
    first = _create_memory(client, project_id, "a").json()["id"]
    second = _create_memory(client, project_id, "b").json()["id"]

    response = client.get(f"/projects/{project_id}/memories")
    assert response.status_code == 200
    assert [m["id"] for m in response.json()] == [first, second]


def test_update_memory_attribute(client, project_id):
    memory_id = _create_memory(client, project_id, "v1", type="fact").json()["id"]

    response = client.patch(f"/memories/{memory_id}", json={"type": "decision"})
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "decision"
    assert len(body["versions"]) == 1


def test_update_memory_empty_body_is_noop(client, project_id):
    memory_id = _create_memory(client, project_id, "v1", type="fact").json()["id"]

    response = client.patch(f"/memories/{memory_id}", json={})
    assert response.status_code == 200
    assert response.json()["type"] == "fact"


def test_update_memory_unknown_memory_returns_404(client):
    response = client.patch("/memories/missing", json={"type": "decision"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Memory not found: missing"}


def test_create_version_appends_history(client, project_id):
    memory_id = _create_memory(client, project_id, "v1").json()["id"]

    response = client.post(
        f"/memories/{memory_id}/versions",
        json={"content": "v2", "context": "new"},
    )
    assert response.status_code == 201
    version = response.json()
    assert version["sequence"] == 2
    assert version["content"] == "v2"
    assert version["context"] == "new"

    body = client.get(f"/memories/{memory_id}").json()
    assert [v["sequence"] for v in body["versions"]] == [1, 2]


def test_create_version_unknown_memory_returns_404(client):
    response = client.post("/memories/missing/versions", json={"content": "v2"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Memory not found: missing"}


def test_search_returns_current_version(client, project_id):
    memory_id = _create_memory(client, project_id, "Uses Flask").json()["id"]
    client.post(f"/memories/{memory_id}/versions", json={"content": "Uses FastAPI"})

    response = client.get("/search", params={"query": "FastAPI"})
    assert response.status_code == 200
    hits = response.json()
    assert len(hits) == 1
    hit = hits[0]
    assert hit["memory"]["id"] == memory_id
    assert hit["version"]["sequence"] == 2
    assert hit["version"]["content"] == "Uses FastAPI"


def test_search_project_filter(client, project_id):
    other = client.post("/projects", json={"name": "other"}).json()["id"]
    _create_memory(client, project_id, "database schema notes")
    _create_memory(client, other, "database schema notes")

    in_project = client.get("/search", params={"query": "schema", "project_id": project_id})
    assert in_project.status_code == 200
    assert len(in_project.json()) == 1
    assert in_project.json()[0]["memory"]["project_id"] == project_id


def test_search_across_projects_without_filter(client, project_id):
    other = client.post("/projects", json={"name": "other"}).json()["id"]
    _create_memory(client, project_id, "database schema notes")
    _create_memory(client, other, "database schema notes")

    response = client.get("/search", params={"query": "schema"})
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_search_empty_query_returns_400(client):
    for query in ("", "   ", "\t"):
        response = client.get("/search", params={"query": query})
        assert response.status_code == 400
        assert response.json()["detail"].startswith("Invalid search query")


def test_search_invalid_query_returns_400(client):
    response = client.get("/search", params={"query": '"unterminated'})
    assert response.status_code == 400
    assert response.json()["detail"].startswith("Invalid search query")


def test_search_missing_query_returns_422(client):
    response = client.get("/search")
    assert response.status_code == 422


def test_request_validation_errors(client):
    missing_name = client.post("/projects", json={})
    assert missing_name.status_code == 422

    missing_content = client.post("/memories", json={"project_id": "p"})
    assert missing_content.status_code == 422

    wrong_type = client.post("/projects", json={"name": "demo", "description": 1})
    assert wrong_type.status_code == 422


def test_error_responses_are_fastapi_native(client):
    response = client.get("/projects/missing")
    assert response.status_code == 404
    assert set(response.json()) == {"detail"}

    response = client.get("/memories/missing")
    assert response.status_code == 404
    assert set(response.json()) == {"detail"}

    response = client.get("/search", params={"query": ""})
    assert response.status_code == 400
    assert set(response.json()) == {"detail"}


# ------------------------------------------------------------------
# Observation API tests
# ------------------------------------------------------------------


def test_create_observation(client, project_id):
    response = client.post(
        f"/projects/{project_id}/observations",
        json={"content": "something observed"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["project_id"] == project_id
    assert body["content"] == "something observed"
    assert body["status"] == "pending"
    assert body["processed_at"] is None


def test_create_observation_unknown_project_returns_404(client):
    response = client.post(
        "/projects/missing/observations",
        json={"content": "x"},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found: missing"}


def test_list_observations(client, project_id):
    first = client.post(
        f"/projects/{project_id}/observations",
        json={"content": "a"},
    ).json()["id"]
    second = client.post(
        f"/projects/{project_id}/observations",
        json={"content": "b"},
    ).json()["id"]

    response = client.get(f"/projects/{project_id}/observations")
    assert response.status_code == 200
    assert [o["id"] for o in response.json()] == [first, second]


def test_process_observation_create_memory(client, project_id):
    obs = client.post(
        f"/projects/{project_id}/observations",
        json={"content": "new knowledge"},
    ).json()

    response = client.post(
        f"/observations/{obs['id']}/process",
        json={"action": "create_memory"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "processed"

    memories = client.get(f"/projects/{project_id}/memories").json()
    assert len(memories) == 1
    assert memories[0]["versions"][0]["content"] == "new knowledge"


def test_process_observation_update_memory(client, project_id):
    mem = _create_memory(client, project_id, "original").json()
    obs = client.post(
        f"/projects/{project_id}/observations",
        json={"content": "updated"},
    ).json()

    response = client.post(
        f"/observations/{obs['id']}/process",
        json={"action": "update_memory", "memory_id": mem["id"]},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "processed"

    fetched = client.get(f"/memories/{mem['id']}").json()
    assert len(fetched["versions"]) == 2
    assert fetched["versions"][1]["content"] == "updated"


def test_process_observation_discard(client, project_id):
    obs = client.post(
        f"/projects/{project_id}/observations",
        json={"content": "not useful"},
    ).json()

    response = client.post(
        f"/observations/{obs['id']}/process",
        json={"action": "discard"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "discarded"


def test_process_observation_already_processed_returns_400(client, project_id):
    obs = client.post(
        f"/projects/{project_id}/observations",
        json={"content": "x"},
    ).json()
    client.post(
        f"/observations/{obs['id']}/process",
        json={"action": "discard"},
    )

    response = client.post(
        f"/observations/{obs['id']}/process",
        json={"action": "discard"},
    )
    assert response.status_code == 400
    assert "already" in response.json()["detail"]


def test_process_observation_unknown_observation_returns_404(client):
    response = client.post(
        "/observations/missing/process",
        json={"action": "discard"},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Observation not found: missing"}


def test_process_observation_invalid_action_returns_400(client, project_id):
    obs = client.post(
        f"/projects/{project_id}/observations",
        json={"content": "x"},
    ).json()

    response = client.post(
        f"/observations/{obs['id']}/process",
        json={"action": "invalid_action"},
    )
    assert response.status_code == 400
    assert "Invalid observation action" in response.json()["detail"]


# ------------------------------------------------------------------
# Relationship API tests
# ------------------------------------------------------------------


def test_create_relationship(client, project_id):
    mem_a = _create_memory(client, project_id, "a").json()
    mem_b = _create_memory(client, project_id, "b").json()

    response = client.post(
        f"/projects/{project_id}/relationships",
        json={
            "from_memory_id": mem_a["id"],
            "to_memory_id": mem_b["id"],
            "type": "caused_by",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["project_id"] == project_id
    assert body["from_memory_id"] == mem_a["id"]
    assert body["to_memory_id"] == mem_b["id"]
    assert body["type"] == "caused_by"


def test_create_relationship_self_returns_400(client, project_id):
    mem = _create_memory(client, project_id, "a").json()

    response = client.post(
        f"/projects/{project_id}/relationships",
        json={
            "from_memory_id": mem["id"],
            "to_memory_id": mem["id"],
            "type": "related_to",
        },
    )
    assert response.status_code == 400
    assert "cannot connect a Memory to itself" in response.json()["detail"]


def test_list_relationships(client, project_id):
    mem_a = _create_memory(client, project_id, "a").json()
    mem_b = _create_memory(client, project_id, "b").json()
    first = client.post(
        f"/projects/{project_id}/relationships",
        json={"from_memory_id": mem_a["id"], "to_memory_id": mem_b["id"], "type": "caused_by"},
    ).json()["id"]
    mem_c = _create_memory(client, project_id, "c").json()
    second = client.post(
        f"/projects/{project_id}/relationships",
        json={"from_memory_id": mem_b["id"], "to_memory_id": mem_c["id"], "type": "resolved_by"},
    ).json()["id"]

    response = client.get(f"/projects/{project_id}/relationships")
    assert response.status_code == 200
    assert [r["id"] for r in response.json()] == [first, second]


def test_get_relationships_for_memory(client, project_id):
    mem_a = _create_memory(client, project_id, "a").json()
    mem_b = _create_memory(client, project_id, "b").json()
    mem_c = _create_memory(client, project_id, "c").json()
    rel_ab = client.post(
        f"/projects/{project_id}/relationships",
        json={"from_memory_id": mem_a["id"], "to_memory_id": mem_b["id"], "type": "caused_by"},
    ).json()
    rel_bc = client.post(
        f"/projects/{project_id}/relationships",
        json={"from_memory_id": mem_b["id"], "to_memory_id": mem_c["id"], "type": "resolved_by"},
    ).json()

    response = client.get(f"/memories/{mem_b['id']}/relationships")
    assert response.status_code == 200
    rel_ids = {r["id"] for r in response.json()}
    assert rel_ab["id"] in rel_ids
    assert rel_bc["id"] in rel_ids


def test_get_relationships_for_memory_empty(client, project_id):
    mem = _create_memory(client, project_id, "isolated").json()

    response = client.get(f"/memories/{mem['id']}/relationships")
    assert response.status_code == 200
    assert response.json() == []


def test_remove_relationship(client, project_id):
    mem_a = _create_memory(client, project_id, "a").json()
    mem_b = _create_memory(client, project_id, "b").json()
    rel = client.post(
        f"/projects/{project_id}/relationships",
        json={"from_memory_id": mem_a["id"], "to_memory_id": mem_b["id"], "type": "related_to"},
    ).json()

    response = client.delete(f"/relationships/{rel['id']}")
    assert response.status_code == 204

    verify = client.get(f"/projects/{project_id}/relationships")
    assert verify.json() == []


def test_remove_relationship_unknown_returns_404(client):
    response = client.delete("/relationships/missing")
    assert response.status_code == 404
    assert response.json() == {"detail": "Relationship not found: missing"}


# ------------------------------------------------------------------
# Snapshot API tests
# ------------------------------------------------------------------


def test_create_snapshot(client, project_id):
    response = client.post(
        f"/projects/{project_id}/snapshots",
        json={"message": "initial state"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["project_id"] == project_id
    assert body["message"] == "initial state"
    assert body["id"]
    assert body["created_at"]
    assert body["members"] == []
    assert body["snapshot_relationships"] == []


def test_create_snapshot_captures_versions(client, project_id):
    memory = _create_memory(client, project_id, "v1").json()

    response = client.post(
        f"/projects/{project_id}/snapshots",
        json={"message": "snapshot"},
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body["members"]) == 1
    assert body["members"][0]["memory_version_id"] == memory["versions"][0]["id"]


def test_create_snapshot_captures_relationships(client, project_id):
    mem_a = _create_memory(client, project_id, "a").json()
    mem_b = _create_memory(client, project_id, "b").json()
    client.post(
        f"/projects/{project_id}/relationships",
        json={
            "from_memory_id": mem_a["id"],
            "to_memory_id": mem_b["id"],
            "type": "caused_by",
        },
    )

    response = client.post(
        f"/projects/{project_id}/snapshots",
        json={"message": "with relationships"},
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body["snapshot_relationships"]) == 1
    assert body["snapshot_relationships"][0]["type"] == "caused_by"


def test_create_snapshot_unknown_project_returns_404(client):
    response = client.post(
        "/projects/missing/snapshots",
        json={"message": "x"},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found: missing"}


def test_list_snapshots(client, project_id):
    first = client.post(
        f"/projects/{project_id}/snapshots",
        json={"message": "first"},
    ).json()["id"]
    second = client.post(
        f"/projects/{project_id}/snapshots",
        json={"message": "second"},
    ).json()["id"]

    response = client.get(f"/projects/{project_id}/snapshots")
    assert response.status_code == 200
    assert [s["id"] for s in response.json()] == [first, second]


def test_get_snapshot(client, project_id):
    snapshot_id = client.post(
        f"/projects/{project_id}/snapshots",
        json={"message": "test"},
    ).json()["id"]

    response = client.get(f"/snapshots/{snapshot_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == snapshot_id
    assert body["message"] == "test"


def test_get_snapshot_unknown_returns_404(client):
    response = client.get("/snapshots/missing")
    assert response.status_code == 404
    assert response.json() == {"detail": "Snapshot not found: missing"}


def test_snapshot_immutable_after_creation(client, project_id):
    memory = _create_memory(client, project_id, "v1").json()
    snapshot_id = client.post(
        f"/projects/{project_id}/snapshots",
        json={"message": "before update"},
    ).json()["id"]

    client.post(
        f"/memories/{memory['id']}/versions",
        json={"content": "v2"},
    )

    response = client.get(f"/snapshots/{snapshot_id}")
    body = response.json()
    assert len(body["members"]) == 1
    assert body["members"][0]["memory_version_id"] == memory["versions"][0]["id"]

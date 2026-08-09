import subprocess
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
        "/projects/{project_id}/branches",
        "/branches/{branch_id}",
        "/projects/{project_id}/branches/current",
        "/branches/{branch_id}/knowledge",
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
        "/memories/{memory_id}/versions/{sequence}/confidence",
        "/memories/{memory_id}/versions/{sequence}/confidence/history",
        "/projects/{project_id}/verify",
        "/memories/{memory_id}/verify",
        "/memories/{memory_id}/versions/{sequence}/verify",
        "/snapshots/{snapshot_id}/verify",
        "/projects/{project_id}/drift",
        "/projects/{project_id}/decay",
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


# ------------------------------------------------------------------
# Confidence API tests
# ------------------------------------------------------------------


def test_record_confidence(client, project_id):
    memory = _create_memory(client, project_id, "knowledge").json()

    response = client.post(
        f"/memories/{memory['id']}/versions/1/confidence",
        json={"score": 0.8, "reason": "well supported"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["score"] == 0.8
    assert body["reason"] == "well supported"
    assert body["memory_version_id"] == memory["versions"][0]["id"]


def test_record_confidence_without_reason(client, project_id):
    memory = _create_memory(client, project_id, "knowledge").json()

    response = client.post(
        f"/memories/{memory['id']}/versions/1/confidence",
        json={"score": 0.5},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["score"] == 0.5
    assert body["reason"] is None


def test_record_confidence_out_of_range_returns_400(client, project_id):
    memory = _create_memory(client, project_id, "knowledge").json()

    response = client.post(
        f"/memories/{memory['id']}/versions/1/confidence",
        json={"score": 1.5},
    )
    assert response.status_code == 400
    assert "between 0.0 and 1.0" in response.json()["detail"]


def test_record_confidence_unknown_memory_returns_404(client):
    response = client.post(
        "/memories/missing/versions/1/confidence",
        json={"score": 0.5},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Memory not found: missing"}


def test_record_confidence_unknown_version_returns_404(client, project_id):
    memory = _create_memory(client, project_id, "knowledge").json()

    response = client.post(
        f"/memories/{memory['id']}/versions/99/confidence",
        json={"score": 0.5},
    )
    assert response.status_code == 404
    assert "Memory version not found" in response.json()["detail"]


def test_get_confidence(client, project_id):
    memory = _create_memory(client, project_id, "knowledge").json()
    client.post(
        f"/memories/{memory['id']}/versions/1/confidence",
        json={"score": 0.7},
    )

    response = client.get(f"/memories/{memory['id']}/versions/1/confidence")
    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 0.7


def test_get_confidence_no_records(client, project_id):
    memory = _create_memory(client, project_id, "knowledge").json()

    response = client.get(f"/memories/{memory['id']}/versions/1/confidence")
    assert response.status_code == 200
    assert response.json() is None


def test_get_confidence_history(client, project_id):
    memory = _create_memory(client, project_id, "knowledge").json()
    client.post(
        f"/memories/{memory['id']}/versions/1/confidence",
        json={"score": 0.3, "reason": "initial"},
    )
    client.post(
        f"/memories/{memory['id']}/versions/1/confidence",
        json={"score": 0.9, "reason": "updated"},
    )

    response = client.get(f"/memories/{memory['id']}/versions/1/confidence/history")
    assert response.status_code == 200
    history = response.json()
    assert len(history) == 2
    assert [s["score"] for s in history] == [0.3, 0.9]


def test_get_confidence_history_empty(client, project_id):
    memory = _create_memory(client, project_id, "knowledge").json()

    response = client.get(f"/memories/{memory['id']}/versions/1/confidence/history")
    assert response.status_code == 200
    assert response.json() == []


# ------------------------------------------------------------------
# Verification API tests
# ------------------------------------------------------------------


def test_verify_project(client, project_id):
    _create_memory(client, project_id, "knowledge", type="fact")

    response = client.post(f"/projects/{project_id}/verify")
    assert response.status_code == 200
    body = response.json()
    assert body["scope"] == "project"
    assert body["scope_id"] == project_id
    assert body["passed"] is True
    assert body["has_failures"] is False
    assert len(body["results"]) > 0


def test_verify_project_unknown_project_returns_404(client):
    response = client.post("/projects/missing/verify")
    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found: missing"}


def test_verify_project_inconclusive_without_evidence(client, project_id):
    _create_memory(client, project_id, "knowledge")

    response = client.post(f"/projects/{project_id}/verify")
    body = response.json()
    trace_checks = [r for r in body["results"] if r["check"] == "traceability"]
    assert len(trace_checks) == 1
    assert trace_checks[0]["outcome"] == "inconclusive"


def test_verify_memory(client, project_id):
    memory = _create_memory(client, project_id, "knowledge", type="fact").json()

    response = client.post(f"/memories/{memory['id']}/verify")
    assert response.status_code == 200
    body = response.json()
    assert body["scope"] == "memory"
    assert body["scope_id"] == memory["id"]
    assert body["passed"] is True


def test_verify_memory_unknown_returns_404(client):
    response = client.post("/memories/missing/verify")
    assert response.status_code == 404
    assert response.json() == {"detail": "Memory not found: missing"}


def test_verify_version(client, project_id):
    memory = _create_memory(client, project_id, "knowledge", context="ctx").json()

    response = client.post(f"/memories/{memory['id']}/versions/1/verify")
    assert response.status_code == 200
    body = response.json()
    assert body["scope"] == "version"
    assert body["scope_id"] == f"{memory['id']}:1"
    assert body["passed"] is True
    checks = {r["check"]: r["outcome"] for r in body["results"]}
    assert checks["version_sequence_order"] == "verified"
    assert checks["traceability"] == "verified"


def test_verify_version_unknown_memory_returns_404(client):
    response = client.post("/memories/missing/versions/1/verify")
    assert response.status_code == 404
    assert response.json() == {"detail": "Memory not found: missing"}


def test_verify_version_unknown_sequence_returns_404(client, project_id):
    memory = _create_memory(client, project_id, "knowledge").json()

    response = client.post(f"/memories/{memory['id']}/versions/99/verify")
    assert response.status_code == 404
    assert "Memory version not found" in response.json()["detail"]


def test_verify_snapshot(client, project_id):
    _create_memory(client, project_id, "knowledge")
    snapshot = client.post(
        f"/projects/{project_id}/snapshots",
        json={"message": "s"},
    ).json()

    response = client.post(f"/snapshots/{snapshot['id']}/verify")
    assert response.status_code == 200
    body = response.json()
    assert body["scope"] == "snapshot"
    assert body["scope_id"] == snapshot["id"]
    assert body["passed"] is True


def test_verify_snapshot_unknown_returns_404(client):
    response = client.post("/snapshots/missing/verify")
    assert response.status_code == 404
    assert response.json() == {"detail": "Snapshot not found: missing"}


def test_verify_does_not_modify_confidence(client, project_id):
    memory = _create_memory(client, project_id, "knowledge").json()
    client.post(
        f"/memories/{memory['id']}/versions/1/confidence",
        json={"score": 0.7},
    )

    response = client.post(f"/projects/{project_id}/verify")
    assert response.status_code == 200

    confidence = client.get(f"/memories/{memory['id']}/versions/1/confidence")
    assert confidence.json()["score"] == 0.7


# ------------------------------------------------------------------
# Drift detection API tests
# ------------------------------------------------------------------


def _git(repo: Path, *args: str):
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )


def _init_repo(repo: Path) -> Path:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Chronicle Test")
    (repo / "src").mkdir(exist_ok=True)
    (repo / "src" / "main.py").write_text("print('hi')\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "initial")
    return repo


def _head(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def _branch(repo: Path) -> str:
    return _git(repo, "branch", "--show-current").stdout.strip()


def test_detect_drift_clean(client, project_id, tmp_path):
    repo = _init_repo(tmp_path / "repo")
    _create_memory(
        client,
        project_id,
        "knowledge",
        git_context={"commit": _head(repo), "branch": _branch(repo)},
    )

    response = client.post(f"/projects/{project_id}/drift", params={"repo_path": str(repo)})
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == project_id
    assert body["state"] == "clean"
    assert body["changed_artifacts"] == []
    assert body["affected_knowledge"] == []


def test_detect_drift_dirty(client, project_id, tmp_path):
    repo = _init_repo(tmp_path / "repo")
    _create_memory(client, project_id, "knowledge", git_context={"commit": "deadbeef"})

    response = client.post(f"/projects/{project_id}/drift", params={"repo_path": str(repo)})
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "dirty"
    assert len(body["affected_knowledge"]) == 1
    assert "recorded commit" in body["affected_knowledge"][0]["reason"]


def test_detect_drift_unknown_project_returns_404(client):
    response = client.post("/projects/missing/drift")
    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found: missing"}


def test_detect_drift_read_only(client, project_id, tmp_path):
    repo = _init_repo(tmp_path / "repo")
    memory = _create_memory(
        client,
        project_id,
        "knowledge",
        git_context={"commit": _head(repo)},
    ).json()
    client.post(
        f"/memories/{memory['id']}/versions/1/confidence",
        json={"score": 0.7},
    )

    (repo / "README.md").write_text("readme")
    response = client.post(f"/projects/{project_id}/drift", params={"repo_path": str(repo)})
    assert response.status_code == 200
    assert response.json()["state"] == "dirty"

    fetched = client.get(f"/memories/{memory['id']}").json()
    assert fetched["versions"][0]["content"] == "knowledge"
    confidence = client.get(f"/memories/{memory['id']}/versions/1/confidence").json()
    assert confidence["score"] == 0.7


# --- decay endpoint ----------------------------------------------------------


def test_assess_decay_fresh(client, project_id):
    _create_memory(client, project_id, "knowledge")

    response = client.post(f"/projects/{project_id}/decay")
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == project_id
    assert body["fresh_days"] == 30
    assert body["stale_days"] == 180
    assert body["stale_count"] == 0
    assert len(body["assessments"]) == 1
    assessment = body["assessments"][0]
    assert assessment["state"] == "fresh"
    assert assessment["freshness"] == pytest.approx(1.0)
    assert assessment["age_days"] == pytest.approx(0.0, abs=1e-6)
    assert assessment["sequence"] == 1
    assert assessment["content"] == "knowledge"


def test_assess_decay_unknown_project_returns_404(client):
    response = client.post("/projects/missing/decay")
    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found: missing"}


def test_assess_decay_empty_project(client, project_id):
    response = client.post(f"/projects/{project_id}/decay")
    assert response.status_code == 200
    body = response.json()
    assert body["assessments"] == []
    assert body["stale_count"] == 0


def test_assess_decay_read_only(client, project_id):
    memory = _create_memory(client, project_id, "knowledge", type="fact").json()
    client.post(
        f"/memories/{memory['id']}/versions/1/confidence",
        json={"score": 0.7},
    )

    response = client.post(f"/projects/{project_id}/decay")
    assert response.status_code == 200

    fetched = client.get(f"/memories/{memory['id']}").json()
    assert fetched["type"] == "fact"
    assert fetched["versions"][0]["content"] == "knowledge"
    confidence = client.get(f"/memories/{memory['id']}/versions/1/confidence").json()
    assert confidence["score"] == 0.7


# ----------------------------------------------------------------------
# Branch endpoints
# ----------------------------------------------------------------------


def test_create_and_list_branches(client, project_id):
    branches = client.get(f"/projects/{project_id}/branches").json()
    assert len(branches) == 1
    assert branches[0]["is_default"] is True

    response = client.post(
        f"/projects/{project_id}/branches", json={"name": "experimental"}
    )
    assert response.status_code == 201
    branch = response.json()
    assert branch["name"] == "experimental"
    assert branch["is_default"] is False

    names = {b["name"] for b in client.get(f"/projects/{project_id}/branches").json()}
    assert names == {"main", "experimental"}


def test_create_branch_duplicate_name_returns_409(client, project_id):
    client.post(f"/projects/{project_id}/branches", json={"name": "experimental"})
    response = client.post(
        f"/projects/{project_id}/branches", json={"name": "experimental"}
    )
    assert response.status_code == 409


def test_get_and_switch_current_branch(client, project_id):
    current = client.get(f"/projects/{project_id}/branches/current")
    assert current.status_code == 200
    assert current.json()["is_default"] is True

    client.post(f"/projects/{project_id}/branches", json={"name": "feature"})
    switched = client.post(f"/projects/{project_id}/branches/current", json={"name": "feature"})
    assert switched.status_code == 200
    assert switched.json()["name"] == "feature"

    new_current = client.get(f"/projects/{project_id}/branches/current").json()
    assert new_current["name"] == "feature"


def test_switch_branch_unknown_name_returns_404(client, project_id):
    response = client.post(f"/projects/{project_id}/branches/current", json={"name": "missing"})
    assert response.status_code == 404


def test_get_branch_knowledge_is_branch_scoped(client, project_id):
    main = client.get(f"/projects/{project_id}/branches/current").json()
    client.post(f"/projects/{project_id}/branches", json={"name": "feature"})
    client.post(f"/projects/{project_id}/branches/current", json={"name": "feature"})

    _create_memory(client, project_id, "only on feature")

    feature = client.get(f"/projects/{project_id}/branches/current").json()
    knowledge = client.get(f"/branches/{feature['id']}/knowledge").json()
    assert [item["version"]["content"] for item in knowledge] == ["only on feature"]

    main_knowledge = client.get(f"/branches/{main['id']}/knowledge").json()
    assert main_knowledge == []


def test_get_branch_by_id(client, project_id):
    branch = client.get(f"/projects/{project_id}/branches/current").json()
    response = client.get(f"/branches/{branch['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == branch["id"]

    assert client.get("/branches/missing").status_code == 404


def test_create_snapshot_with_branch(client, project_id):
    _create_memory(client, project_id, "on main")
    main = client.get(f"/projects/{project_id}/branches/current").json()

    client.post(f"/projects/{project_id}/branches", json={"name": "feature"})
    client.post(f"/projects/{project_id}/branches/current", json={"name": "feature"})
    _create_memory(client, project_id, "on feature")

    feature = client.get(f"/projects/{project_id}/branches/current").json()
    response = client.post(
        f"/projects/{project_id}/snapshots",
        json={"branch_id": feature["id"], "message": "feature state"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["branch_id"] == feature["id"]
    assert len(body["members"]) == 2

    main_snapshot = client.post(
        f"/projects/{project_id}/snapshots", json={"branch_id": main["id"]}
    ).json()
    assert len(main_snapshot["members"]) == 1

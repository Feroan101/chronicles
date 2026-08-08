import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from mcp.client.stdio import stdio_client

from mcp import ClientSession, StdioServerParameters

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def server_dir(tmp_path: Path):
    """A migrated Chronicle store on a temp file, served by a real MCP server process."""
    chronicle_dir = tmp_path / ".chronicle"
    chronicle_dir.mkdir()
    db_path = chronicle_dir / "chronicle.db"
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(cfg, "head")
    return tmp_path


@asynccontextmanager
async def _session(server_dir: Path):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "chronicle.mcp"],
        cwd=str(server_dir),
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        yield session


async def _ok(session, name, args):
    result = await session.call_tool(name, args)
    assert not result.isError, result.content
    return json.loads(result.content[0].text)


async def _ok_list(session, name, args):
    result = await session.call_tool(name, args)
    assert not result.isError, result.content
    return [json.loads(content.text) for content in result.content]


async def _err(session, name, args) -> str:
    result = await session.call_tool(name, args)
    assert result.isError
    return result.content[0].text


@pytest.mark.anyio
async def test_server_initializes_and_exposes_contract_tools(server_dir):
    async with _session(server_dir) as session:
        tools = await session.list_tools()

        assert {tool.name for tool in tools.tools} == {
            "create_project",
            "get_project",
            "create_memory",
            "get_memory",
            "list_memories",
            "update_memory",
            "create_version",
            "search",
            "get_evidence",
            "create_observation",
            "list_observations",
            "process_observation",
            "create_relationship",
            "list_relationships",
            "get_relationships_for_memory",
            "remove_relationship",
            "create_snapshot",
            "get_snapshot",
            "list_snapshots",
            "record_confidence",
            "get_confidence",
            "get_confidence_history",
        }


@pytest.mark.anyio
async def test_tool_input_schemas(server_dir):
    async with _session(server_dir) as session:
        tools = {tool.name: tool.inputSchema for tool in (await session.list_tools()).tools}

        assert set(tools["create_project"]["required"]) == {"name"}
        assert set(tools["create_memory"]["required"]) == {"project_id", "content"}
        assert set(tools["get_project"]["required"]) == {"project_id"}
        assert set(tools["search"]["required"]) == {"query"}


@pytest.mark.anyio
async def test_create_project(server_dir):
    async with _session(server_dir) as session:
        project = await _ok(session, "create_project", {"name": "demo", "description": "x"})

        assert project["name"] == "demo"
        assert project["description"] == "x"
        assert project["id"]
        assert project["created_at"]


@pytest.mark.anyio
async def test_create_project_without_description(server_dir):
    async with _session(server_dir) as session:
        project = await _ok(session, "create_project", {"name": "demo"})

        assert project["name"] == "demo"
        assert project["description"] is None


@pytest.mark.anyio
async def test_get_project(server_dir):
    async with _session(server_dir) as session:
        project = await _ok(session, "create_project", {"name": "demo"})

        fetched = await _ok(session, "get_project", {"project_id": project["id"]})

        assert fetched["id"] == project["id"]
        assert fetched["name"] == "demo"


@pytest.mark.anyio
async def test_get_unknown_project_errors(server_dir):
    async with _session(server_dir) as session:
        message = await _err(session, "get_project", {"project_id": "missing"})

        assert "Project not found: missing" in message


@pytest.mark.anyio
async def test_create_memory_creates_first_version(server_dir):
    async with _session(server_dir) as session:
        project = await _ok(session, "create_project", {"name": "demo"})

        memory = await _ok(
            session,
            "create_memory",
            {
                "project_id": project["id"],
                "content": "first",
                "type": "fact",
                "context": "ctx",
            },
        )

        assert memory["project_id"] == project["id"]
        assert memory["type"] == "fact"
        assert len(memory["versions"]) == 1
        version = memory["versions"][0]
        assert version["sequence"] == 1
        assert version["content"] == "first"
        assert version["context"] == "ctx"


@pytest.mark.anyio
async def test_create_memory_unknown_project_errors(server_dir):
    async with _session(server_dir) as session:
        message = await _err(session, "create_memory", {"project_id": "missing", "content": "x"})

        assert "Project not found: missing" in message


@pytest.mark.anyio
async def test_get_memory(server_dir):
    async with _session(server_dir) as session:
        project = await _ok(session, "create_project", {"name": "demo"})
        memory = await _ok(session, "create_memory", {"project_id": project["id"], "content": "x"})

        fetched = await _ok(session, "get_memory", {"memory_id": memory["id"]})

        assert fetched["id"] == memory["id"]
        assert fetched["project_id"] == project["id"]
        assert len(fetched["versions"]) == 1


@pytest.mark.anyio
async def test_get_unknown_memory_errors(server_dir):
    async with _session(server_dir) as session:
        message = await _err(session, "get_memory", {"memory_id": "missing"})

        assert "Memory not found: missing" in message


@pytest.mark.anyio
async def test_list_memories_orders_by_creation(server_dir):
    async with _session(server_dir) as session:
        project = await _ok(session, "create_project", {"name": "demo"})
        first = await _ok(session, "create_memory", {"project_id": project["id"], "content": "a"})
        second = await _ok(session, "create_memory", {"project_id": project["id"], "content": "b"})

        memories = await _ok_list(session, "list_memories", {"project_id": project["id"]})

        assert [memory["id"] for memory in memories] == [first["id"], second["id"]]


@pytest.mark.anyio
async def test_update_memory_type(server_dir):
    async with _session(server_dir) as session:
        project = await _ok(session, "create_project", {"name": "demo"})
        memory = await _ok(
            session,
            "create_memory",
            {"project_id": project["id"], "content": "v1", "type": "fact"},
        )

        updated = await _ok(
            session, "update_memory", {"memory_id": memory["id"], "type": "decision"}
        )

        assert updated["type"] == "decision"
        assert len(updated["versions"]) == 1


@pytest.mark.anyio
async def test_update_memory_null_type_is_noop(server_dir):
    async with _session(server_dir) as session:
        project = await _ok(session, "create_project", {"name": "demo"})
        memory = await _ok(
            session,
            "create_memory",
            {"project_id": project["id"], "content": "v1", "type": "fact"},
        )

        updated = await _ok(session, "update_memory", {"memory_id": memory["id"], "type": None})

        assert updated["type"] == "fact"


@pytest.mark.anyio
async def test_update_memory_omitted_type_is_noop(server_dir):
    async with _session(server_dir) as session:
        project = await _ok(session, "create_project", {"name": "demo"})
        memory = await _ok(
            session,
            "create_memory",
            {"project_id": project["id"], "content": "v1", "type": "fact"},
        )

        updated = await _ok(session, "update_memory", {"memory_id": memory["id"]})

        assert updated["type"] == "fact"


@pytest.mark.anyio
async def test_update_memory_unknown_memory_errors(server_dir):
    async with _session(server_dir) as session:
        message = await _err(session, "update_memory", {"memory_id": "missing", "type": "x"})

        assert "Memory not found: missing" in message


@pytest.mark.anyio
async def test_create_version_appends_history(server_dir):
    async with _session(server_dir) as session:
        project = await _ok(session, "create_project", {"name": "demo"})
        memory = await _ok(session, "create_memory", {"project_id": project["id"], "content": "v1"})

        version = await _ok(
            session,
            "create_version",
            {"memory_id": memory["id"], "content": "v2", "context": "new"},
        )

        assert version["sequence"] == 2
        assert version["content"] == "v2"
        assert version["context"] == "new"

        fetched = await _ok(session, "get_memory", {"memory_id": memory["id"]})
        assert [v["sequence"] for v in fetched["versions"]] == [1, 2]


@pytest.mark.anyio
async def test_create_version_unknown_memory_errors(server_dir):
    async with _session(server_dir) as session:
        message = await _err(session, "create_version", {"memory_id": "missing", "content": "v2"})

        assert "Memory not found: missing" in message


@pytest.mark.anyio
async def test_search_returns_current_version(server_dir):
    async with _session(server_dir) as session:
        project = await _ok(session, "create_project", {"name": "demo"})
        memory = await _ok(
            session, "create_memory", {"project_id": project["id"], "content": "Uses Flask"}
        )
        await _ok(session, "create_version", {"memory_id": memory["id"], "content": "Uses FastAPI"})

        hits = await _ok_list(session, "search", {"query": "FastAPI"})

        assert len(hits) == 1
        hit = hits[0]
        assert hit["memory"]["id"] == memory["id"]
        assert hit["version"]["sequence"] == 2
        assert hit["version"]["content"] == "Uses FastAPI"
        assert "rank" in hit


@pytest.mark.anyio
async def test_search_project_filter(server_dir):
    async with _session(server_dir) as session:
        project = await _ok(session, "create_project", {"name": "demo"})
        other = await _ok(session, "create_project", {"name": "other"})
        await _ok(
            session, "create_memory", {"project_id": project["id"], "content": "schema notes"}
        )
        await _ok(session, "create_memory", {"project_id": other["id"], "content": "schema notes"})

        in_project = await _ok_list(
            session,
            "search",
            {"query": "schema", "project_id": project["id"]},
        )
        all_projects = await _ok_list(session, "search", {"query": "schema"})

        assert len(in_project) == 1
        assert in_project[0]["memory"]["project_id"] == project["id"]
        assert len(all_projects) == 2


@pytest.mark.anyio
async def test_search_empty_query_errors(server_dir):
    async with _session(server_dir) as session:
        for query in ("", "   ", "\t"):
            message = await _err(session, "search", {"query": query})
            assert "Invalid search query" in message


@pytest.mark.anyio
async def test_search_invalid_query_errors(server_dir):
    async with _session(server_dir) as session:
        message = await _err(session, "search", {"query": '"unterminated'})
        assert "Invalid search query" in message


@pytest.mark.anyio
async def test_missing_required_argument_errors(server_dir):
    async with _session(server_dir) as session:
        result = await session.call_tool("create_project", {})
        assert result.isError


@pytest.mark.anyio
async def test_create_snapshot(server_dir):
    async with _session(server_dir) as session:
        project = await _ok(session, "create_project", {"name": "demo"})
        memory = await _ok(
            session, "create_memory", {"project_id": project["id"], "content": "knowledge"}
        )

        snapshot = await _ok(
            session,
            "create_snapshot",
            {"project_id": project["id"], "message": "initial state"},
        )

        assert snapshot["project_id"] == project["id"]
        assert snapshot["message"] == "initial state"
        assert len(snapshot["members"]) == 1
        assert snapshot["members"][0]["memory_version_id"] == memory["versions"][0]["id"]


@pytest.mark.anyio
async def test_get_snapshot(server_dir):
    async with _session(server_dir) as session:
        project = await _ok(session, "create_project", {"name": "demo"})
        created = await _ok(
            session, "create_snapshot", {"project_id": project["id"], "message": "test"}
        )

        fetched = await _ok(session, "get_snapshot", {"snapshot_id": created["id"]})

        assert fetched["id"] == created["id"]
        assert fetched["message"] == "test"


@pytest.mark.anyio
async def test_get_snapshot_unknown_errors(server_dir):
    async with _session(server_dir) as session:
        message = await _err(session, "get_snapshot", {"snapshot_id": "missing"})
        assert "Snapshot not found: missing" in message


@pytest.mark.anyio
async def test_list_snapshots(server_dir):
    async with _session(server_dir) as session:
        project = await _ok(session, "create_project", {"name": "demo"})
        first = await _ok(
            session, "create_snapshot", {"project_id": project["id"], "message": "first"}
        )
        second = await _ok(
            session, "create_snapshot", {"project_id": project["id"], "message": "second"}
        )

        snapshots = await _ok_list(session, "list_snapshots", {"project_id": project["id"]})

        assert [s["id"] for s in snapshots] == [first["id"], second["id"]]


@pytest.mark.anyio
async def test_snapshot_immutable_after_creation(server_dir):
    async with _session(server_dir) as session:
        project = await _ok(session, "create_project", {"name": "demo"})
        memory = await _ok(session, "create_memory", {"project_id": project["id"], "content": "v1"})
        snapshot = await _ok(session, "create_snapshot", {"project_id": project["id"]})

        await _ok(
            session,
            "create_version",
            {"memory_id": memory["id"], "content": "v2"},
        )

        fetched = await _ok(session, "get_snapshot", {"snapshot_id": snapshot["id"]})
        assert len(fetched["members"]) == 1
        assert fetched["members"][0]["memory_version_id"] == memory["versions"][0]["id"]


@pytest.mark.anyio
async def test_record_confidence(server_dir):
    async with _session(server_dir) as session:
        project = await _ok(session, "create_project", {"name": "demo"})
        memory = await _ok(
            session, "create_memory", {"project_id": project["id"], "content": "knowledge"}
        )

        record = await _ok(
            session,
            "record_confidence",
            {"memory_id": memory["id"], "sequence": 1, "score": 0.8, "reason": "well supported"},
        )

        assert record["score"] == 0.8
        assert record["reason"] == "well supported"
        assert record["memory_version_id"] == memory["versions"][0]["id"]


@pytest.mark.anyio
async def test_get_confidence(server_dir):
    async with _session(server_dir) as session:
        project = await _ok(session, "create_project", {"name": "demo"})
        memory = await _ok(
            session, "create_memory", {"project_id": project["id"], "content": "knowledge"}
        )
        await _ok(
            session,
            "record_confidence",
            {"memory_id": memory["id"], "sequence": 1, "score": 0.7},
        )

        result = await _ok(session, "get_confidence", {"memory_id": memory["id"], "sequence": 1})

        assert result["score"] == 0.7


@pytest.mark.anyio
async def test_get_confidence_no_records(server_dir):
    async with _session(server_dir) as session:
        project = await _ok(session, "create_project", {"name": "demo"})
        memory = await _ok(
            session, "create_memory", {"project_id": project["id"], "content": "knowledge"}
        )

        result = await _ok(session, "get_confidence", {"memory_id": memory["id"], "sequence": 1})
        assert result == {}


@pytest.mark.anyio
async def test_get_confidence_history(server_dir):
    async with _session(server_dir) as session:
        project = await _ok(session, "create_project", {"name": "demo"})
        memory = await _ok(
            session, "create_memory", {"project_id": project["id"], "content": "knowledge"}
        )
        await _ok(
            session,
            "record_confidence",
            {"memory_id": memory["id"], "sequence": 1, "score": 0.3},
        )
        await _ok(
            session,
            "record_confidence",
            {"memory_id": memory["id"], "sequence": 1, "score": 0.9},
        )

        history = await _ok_list(
            session,
            "get_confidence_history",
            {"memory_id": memory["id"], "sequence": 1},
        )

        assert len(history) == 2
        assert [s["score"] for s in history] == [0.3, 0.9]


@pytest.mark.anyio
async def test_record_confidence_out_of_range_errors(server_dir):
    async with _session(server_dir) as session:
        project = await _ok(session, "create_project", {"name": "demo"})
        memory = await _ok(
            session, "create_memory", {"project_id": project["id"], "content": "knowledge"}
        )

        result = await session.call_tool(
            "record_confidence",
            {"memory_id": memory["id"], "sequence": 1, "score": 1.5},
        )
        assert result.isError
        assert "between 0.0 and 1.0" in result.content[0].text

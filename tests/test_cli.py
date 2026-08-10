import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from chronicle.cli import context
from chronicle.cli.main import app
from typer.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parent.parent
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
runner = CliRunner()


@pytest.fixture()
def project_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An empty project directory where Chronicle is initialized."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture()
def project_dir_with_alembic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A project directory that happens to contain an ``alembic.ini``."""
    shutil.copy2(REPO_ROOT / "alembic.ini", tmp_path / "alembic.ini")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _first_uuid(text: str) -> str:
    return UUID_RE.search(text).group()


def _init(project_dir: Path) -> None:
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0, result.output


def _migration_heads(db_path: Path) -> set[str]:
    import sqlite3

    con = sqlite3.connect(db_path)
    try:
        rows = con.execute("SELECT version_num FROM alembic_version").fetchall()
    finally:
        con.close()
    return {row[0] for row in rows}


def test_init_creates_dir_db_and_config(project_dir: Path):
    _init(project_dir)
    assert context.chronicle_dir().is_dir()
    assert context.db_path().is_file()
    assert context.config_path().is_file()
    config = json.loads(context.config_path().read_text())
    assert config["db"] == "chronicle.db"


def test_init_applies_migrations_in_an_empty_directory(project_dir: Path):
    assert not next(project_dir.iterdir(), None)
    _init(project_dir)
    assert _migration_heads(context.db_path()) == {"620fffbacf7c"}


def test_init_works_when_project_contains_alembic_ini(project_dir_with_alembic: Path):
    _init(project_dir_with_alembic)
    assert context.db_path().is_file()
    assert _migration_heads(context.db_path()) == {"620fffbacf7c"}


def test_init_is_idempotent(project_dir: Path):
    _init(project_dir)
    heads = _migration_heads(context.db_path())
    config_before = context.config_path().read_text()

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0, result.output
    assert _migration_heads(context.db_path()) == heads
    assert context.config_path().read_text() == config_before


def test_init_does_not_create_files_in_project_root(project_dir: Path):
    _init(project_dir)
    assert (project_dir / ".chronicle").is_dir()
    assert not (project_dir / "alembic.ini").exists()
    assert not (project_dir / "alembic").exists()


def test_command_without_init_fails(project_dir: Path):
    result = runner.invoke(app, ["project", "create", "demo"])
    assert result.exit_code == 1
    assert "not initialized" in result.output


def test_project_create(project_dir: Path):
    _init(project_dir)
    result = runner.invoke(app, ["project", "create", "demo", "--description", "x"])
    assert result.exit_code == 0, result.output
    assert "demo" in result.output
    assert _first_uuid(result.output)


def test_memory_workflow(project_dir: Path):
    _init(project_dir)
    project_id = _first_uuid(runner.invoke(app, ["project", "create", "demo"]).output)

    created = runner.invoke(
        app,
        [
            "memory",
            "create",
            "--project-id",
            project_id,
            "--content",
            "first",
            "--type",
            "fact",
        ],
    )
    assert created.exit_code == 0, created.output
    memory_id = _first_uuid(created.output)
    assert "current version: 1" in created.output

    listed = runner.invoke(app, ["memory", "list", "--project-id", project_id])
    assert listed.exit_code == 0
    assert "seq 1" in listed.output

    shown = runner.invoke(app, ["memory", "show", "--memory-id", memory_id])
    assert shown.exit_code == 0, shown.output
    assert "first" in shown.output
    assert "Current version (sequence 1)" in shown.output


def test_version_create_appends_history(project_dir: Path):
    _init(project_dir)
    project_id = _first_uuid(runner.invoke(app, ["project", "create", "demo"]).output)
    memory_id = _first_uuid(
        runner.invoke(
            app,
            [
                "memory",
                "create",
                "--project-id",
                project_id,
                "--content",
                "v1",
            ],
        ).output
    )

    result = runner.invoke(
        app,
        ["version", "create", "--memory-id", memory_id, "--content", "v2"],
    )
    assert result.exit_code == 0, result.output
    assert "sequence: 2" in result.output

    shown = runner.invoke(app, ["memory", "show", "--memory-id", memory_id])
    assert "Current version (sequence 2)" in shown.output
    assert "v2" in shown.output


def test_unknown_project_and_memory_errors(project_dir: Path):
    _init(project_dir)

    bad_project = runner.invoke(
        app, ["memory", "create", "--project-id", "bad-id", "--content", "x"]
    )
    assert bad_project.exit_code == 1
    assert "Project not found" in bad_project.output

    bad_memory = runner.invoke(
        app, ["version", "create", "--memory-id", "bad-id", "--content", "x"]
    )
    assert bad_memory.exit_code == 1
    assert "Memory not found" in bad_memory.output


def test_search_command(project_dir: Path):
    _init(project_dir)
    project_id = _first_uuid(runner.invoke(app, ["project", "create", "demo"]).output)
    memory_id = _first_uuid(
        runner.invoke(
            app,
            [
                "memory",
                "create",
                "--project-id",
                project_id,
                "--content",
                "Uses Flask for the web layer",
                "--type",
                "decision",
            ],
        ).output
    )

    found = runner.invoke(app, ["search", "Flask"])
    assert found.exit_code == 0, found.output
    assert memory_id in found.output
    assert "decision" in found.output
    assert "current version: 1" in found.output
    assert "Uses Flask for the web layer" in found.output

    missed = runner.invoke(app, ["search", "FastAPI"])
    assert missed.exit_code == 0
    assert "No matches." in missed.output

    filtered = runner.invoke(app, ["search", "Flask", "--project-id", project_id])
    assert filtered.exit_code == 0, filtered.output
    assert memory_id in filtered.output

    unknown_project = runner.invoke(app, ["search", "Flask", "--project-id", "unknown"])
    assert unknown_project.exit_code == 0
    assert "No matches." in unknown_project.output


def test_search_command_invalid_query(project_dir: Path):
    _init(project_dir)
    result = runner.invoke(app, ["search", '"unterminated'])
    assert result.exit_code == 1
    assert "Invalid search query" in result.output


def test_verify_workflow(project_dir: Path):
    _init(project_dir)
    project_id = _first_uuid(runner.invoke(app, ["project", "create", "demo"]).output)
    memory_id = _first_uuid(
        runner.invoke(
            app,
            [
                "memory",
                "create",
                "--project-id",
                project_id,
                "--content",
                "knowledge",
                "--type",
                "fact",
            ],
        ).output
    )

    project = runner.invoke(app, ["verify", "project", "--project-id", project_id])
    assert project.exit_code == 0, project.output
    assert "PASSED" in project.output
    assert "[+]" in project.output

    memory = runner.invoke(app, ["verify", "memory", "--memory-id", memory_id])
    assert memory.exit_code == 0, memory.output
    assert "PASSED" in memory.output

    version = runner.invoke(app, ["verify", "version", "--memory-id", memory_id, "--sequence", "1"])
    assert version.exit_code == 0, version.output
    assert "PASSED" in version.output


def test_verify_unknown_errors(project_dir: Path):
    _init(project_dir)

    bad_project = runner.invoke(app, ["verify", "project", "--project-id", "bad-id"])
    assert bad_project.exit_code == 1
    assert "Project not found" in bad_project.output

    bad_memory = runner.invoke(app, ["verify", "memory", "--memory-id", "bad-id"])
    assert bad_memory.exit_code == 1
    assert "Memory not found" in bad_memory.output

    bad_version = runner.invoke(
        app, ["verify", "version", "--memory-id", "bad-id", "--sequence", "1"]
    )
    assert bad_version.exit_code == 1
    assert "Memory not found" in bad_version.output


# --- drift command --------------------------------------------------------


def _git(repo: Path, *args: str):
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )


def _init_repo(repo: Path) -> Path:
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


def test_drift_command(project_dir: Path):
    _init(project_dir)
    (project_dir / ".gitignore").write_text(".chronicle/\n")
    _init_repo(project_dir)
    project_id = _first_uuid(runner.invoke(app, ["project", "create", "demo"]).output)
    _first_uuid(
        runner.invoke(
            app,
            [
                "memory",
                "create",
                "--project-id",
                project_id,
                "--content",
                "knowledge",
                "--git-commit",
                _head(project_dir),
                "--git-branch",
                _branch(project_dir),
            ],
        ).output
    )

    clean = runner.invoke(app, ["drift", "--project-id", project_id])
    assert clean.exit_code == 0, clean.output
    assert "CLEAN" in clean.output

    (project_dir / "README.md").write_text("readme")
    dirty = runner.invoke(app, ["drift", "--project-id", project_id])
    assert dirty.exit_code == 0, dirty.output
    assert "DIRTY" in dirty.output


def test_drift_unknown_project_errors(project_dir: Path):
    _init(project_dir)

    result = runner.invoke(app, ["drift", "--project-id", "bad-id"])
    assert result.exit_code == 1
    assert "Project not found" in result.output


# --- decay command -----------------------------------------------------------


def test_decay_command(project_dir: Path):
    _init(project_dir)
    project_id = _first_uuid(runner.invoke(app, ["project", "create", "demo"]).output)
    _first_uuid(
        runner.invoke(
            app,
            [
                "memory",
                "create",
                "--project-id",
                project_id,
                "--content",
                "knowledge",
            ],
        ).output
    )

    result = runner.invoke(app, ["decay", "--project-id", project_id])
    assert result.exit_code == 0, result.output
    assert "Decay · demo" in result.output
    assert project_id not in result.output
    assert "FRESH" in result.output
    assert "stale: 0" in result.output


def test_decay_empty_project(project_dir: Path):
    _init(project_dir)
    project_id = _first_uuid(runner.invoke(app, ["project", "create", "demo"]).output)

    result = runner.invoke(app, ["decay", "--project-id", project_id])
    assert result.exit_code == 0, result.output
    assert "0 assessment(s)" in result.output


def test_decay_unknown_project_errors(project_dir: Path):
    _init(project_dir)

    result = runner.invoke(app, ["decay", "--project-id", "bad-id"])
    assert result.exit_code == 1
    assert "Project not found" in result.output


# ------------------------------------------------------------------
# Human-readable identity layer
# ------------------------------------------------------------------


def _init_demo_project(project_dir: Path) -> None:
    _init(project_dir)
    result = runner.invoke(app, ["project", "create", "demo", "--description", "demo project"])
    assert result.exit_code == 0, result.output


def _create_named_memory(
    project_dir: Path, name: str, content: str, type: str | None = None
) -> None:
    args = ["memory", "create", "--project", "demo", "--name", name, "--content", content]
    if type:
        args += ["--type", type]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output


def test_project_list_and_show_by_name(project_dir: Path):
    _init_demo_project(project_dir)

    listed = runner.invoke(app, ["project", "list"])
    assert listed.exit_code == 0, listed.output
    assert "demo" in listed.output

    shown = runner.invoke(app, ["project", "show", "--name", "demo"])
    assert shown.exit_code == 0, shown.output
    assert 'Project "demo"' in shown.output
    assert "demo project" in shown.output


def test_project_show_unknown_name_errors(project_dir: Path):
    _init_demo_project(project_dir)
    result = runner.invoke(app, ["project", "show", "--name", "missing"])
    assert result.exit_code == 1
    assert "Project not found" in result.output


def test_project_show_conflicting_options_errors(project_dir: Path):
    _init_demo_project(project_dir)
    project_id = _first_uuid(runner.invoke(app, ["project", "show", "--name", "demo"]).output)
    result = runner.invoke(app, ["project", "show", "--name", "demo", "--project-id", project_id])
    assert result.exit_code == 1
    assert "not both" in result.output


def test_project_duplicate_name_rejected(project_dir: Path):
    _init(project_dir)
    first = runner.invoke(app, ["project", "create", "demo"])
    assert first.exit_code == 0, first.output
    second = runner.invoke(app, ["project", "create", "demo"])
    assert second.exit_code == 1
    assert "Project name already exists" in second.output


def test_memory_create_with_project_and_name(project_dir: Path):
    _init_demo_project(project_dir)
    result = runner.invoke(
        app,
        [
            "memory",
            "create",
            "--project",
            "demo",
            "--name",
            "authentication",
            "--content",
            "JWT middleware protects routes.",
            "--type",
            "decision",
        ],
    )
    assert result.exit_code == 0, result.output
    assert 'Created memory "authentication"' in result.output
    assert "current version: 1" in result.output
    assert "decision" in result.output


def test_memory_create_missing_project_errors(project_dir: Path):
    _init(project_dir)
    result = runner.invoke(app, ["memory", "create", "--content", "x", "--project-id", "missing"])
    assert result.exit_code == 1
    assert "Project not found" in result.output


def test_memory_create_duplicate_name_rejected(project_dir: Path):
    _init_demo_project(project_dir)
    _create_named_memory(project_dir, "auth", "first")
    result = runner.invoke(
        app, ["memory", "create", "--project", "demo", "--name", "auth", "--content", "dup"]
    )
    assert result.exit_code == 1
    assert "Memory name already exists" in result.output


def test_memory_list_by_project_name(project_dir: Path):
    _init_demo_project(project_dir)
    _create_named_memory(project_dir, "auth", "content a")
    _create_named_memory(project_dir, "tokens", "content b")

    result = runner.invoke(app, ["memory", "list", "--project", "demo"])
    assert result.exit_code == 0, result.output
    assert "auth" in result.output
    assert "tokens" in result.output
    assert "seq 1" in result.output


def test_memory_show_by_name(project_dir: Path):
    _init_demo_project(project_dir)
    _create_named_memory(project_dir, "auth", "JWT middleware")

    result = runner.invoke(app, ["memory", "show", "--project", "demo", "--name", "auth"])
    assert result.exit_code == 0, result.output
    assert 'Memory "auth"' in result.output
    assert "JWT middleware" in result.output
    assert "Current version (sequence 1)" in result.output


def test_memory_show_unknown_name_errors(project_dir: Path):
    _init_demo_project(project_dir)
    result = runner.invoke(app, ["memory", "show", "--project", "demo", "--name", "missing"])
    assert result.exit_code == 1
    assert "Memory not found" in result.output


def test_memory_name_and_id_conflict_errors(project_dir: Path):
    _init_demo_project(project_dir)
    created = runner.invoke(
        app, ["memory", "create", "--project", "demo", "--name", "auth", "--content", "x"]
    )
    assert created.exit_code == 0, created.output
    memory_id = _first_uuid(created.output)
    result = runner.invoke(
        app,
        ["memory", "show", "--project", "demo", "--name", "auth", "--memory-id", memory_id],
    )
    assert result.exit_code == 1
    assert "not both" in result.output


def test_memory_workflow_still_supports_uuids(project_dir: Path):
    _init_demo_project(project_dir)
    project_id = _first_uuid(runner.invoke(app, ["project", "show", "--name", "demo"]).output)
    created = runner.invoke(
        app,
        [
            "memory",
            "create",
            "--project-id",
            project_id,
            "--name",
            "uuid-mem",
            "--content",
            "x",
        ],
    )
    assert created.exit_code == 0, created.output
    memory_id = _first_uuid(created.output)

    shown = runner.invoke(app, ["memory", "show", "--memory-id", memory_id])
    assert shown.exit_code == 0, shown.output
    assert 'Memory "uuid-mem"' in shown.output


def test_version_operations_with_memory_name(project_dir: Path):
    _init_demo_project(project_dir)
    _create_named_memory(project_dir, "auth", "v1")

    created = runner.invoke(app, ["version", "create", "--memory", "auth", "--content", "v2"])
    assert created.exit_code == 0, created.output
    assert "sequence: 2" in created.output

    for sequence, content in [("1", "v1"), ("2", "v2")]:
        shown = runner.invoke(app, ["version", "show", "--memory", "auth", "--sequence", sequence])
        assert shown.exit_code == 0, shown.output
        assert shown.output.startswith(f'Version v{sequence} of "auth"')
        assert f"  sequence: {sequence}" in shown.output
        assert content in shown.output
        assert "id:" not in shown.output


def test_version_with_memory_name_and_id_conflict(project_dir: Path):
    _init_demo_project(project_dir)
    _create_named_memory(project_dir, "auth", "v1")
    result = runner.invoke(
        app, ["version", "show", "--memory", "auth", "--memory-id", "any-id", "--sequence", "1"]
    )
    assert result.exit_code == 1
    assert "not both" in result.output


def test_branch_operations_with_project_name(project_dir: Path):
    _init_demo_project(project_dir)
    created = runner.invoke(
        app, ["branch", "create", "--project", "demo", "--name", "auth-refactor"]
    )
    assert created.exit_code == 0, created.output
    assert "Created branch auth-refactor" in created.output

    listed = runner.invoke(app, ["branch", "list", "--project", "demo"])
    assert listed.exit_code == 0, listed.output
    assert "auth-refactor" in listed.output
    assert "main" in listed.output

    switched = runner.invoke(
        app, ["branch", "switch", "--project", "demo", "--name", "auth-refactor"]
    )
    assert switched.exit_code == 0, switched.output

    current = runner.invoke(app, ["branch", "current", "--project", "demo"])
    assert current.exit_code == 0, current.output
    assert "auth-refactor" in current.output


def test_branch_operations_unknown_project_errors(project_dir: Path):
    _init(project_dir)
    result = runner.invoke(app, ["branch", "list", "--project", "missing"])
    assert result.exit_code == 1
    assert "Project not found" in result.output


def test_relationship_operations_with_names(project_dir: Path):
    _init_demo_project(project_dir)
    _create_named_memory(project_dir, "authentication", "JWT")
    _create_named_memory(project_dir, "token-lifecycle", "one hour")
    _create_named_memory(project_dir, "user-identity", "from JWT")

    created = runner.invoke(
        app,
        [
            "relationship",
            "create",
            "--project",
            "demo",
            "--from-memory",
            "authentication",
            "--to-memory",
            "token-lifecycle",
            "--type",
            "depends_on",
        ],
    )
    assert created.exit_code == 0, created.output
    assert "authentication -> token-lifecycle" in created.output
    assert "depends_on" in created.output

    second = runner.invoke(
        app,
        [
            "relationship",
            "create",
            "--project",
            "demo",
            "--from-memory",
            "authentication",
            "--to-memory",
            "user-identity",
            "--type",
            "depends_on",
        ],
    )
    assert second.exit_code == 0, second.output

    listed = runner.invoke(app, ["relationship", "list", "--project", "demo"])
    assert listed.exit_code == 0, listed.output
    assert "authentication -> token-lifecycle" in listed.output

    for_memory = runner.invoke(
        app,
        ["relationship", "for-memory", "--project", "demo", "--memory", "authentication"],
    )
    assert for_memory.exit_code == 0, for_memory.output
    assert "authentication -> token-lifecycle" in for_memory.output
    assert "authentication -> user-identity" in for_memory.output


def test_relationship_unknown_memory_name_errors(project_dir: Path):
    _init_demo_project(project_dir)
    result = runner.invoke(
        app,
        [
            "relationship",
            "create",
            "--project",
            "demo",
            "--from-memory",
            "missing",
            "--to-memory",
            "also-missing",
            "--type",
            "depends_on",
        ],
    )
    assert result.exit_code == 1
    assert "Memory not found" in result.output


def test_snapshot_operations_with_names(project_dir: Path):
    _init_demo_project(project_dir)
    _create_named_memory(project_dir, "auth", "x")

    created = runner.invoke(
        app, ["snapshot", "create", "--project", "demo", "--name", "initial-auth"]
    )
    assert created.exit_code == 0, created.output
    assert 'Created snapshot "initial-auth"' in created.output

    listed = runner.invoke(app, ["snapshot", "list", "--project", "demo"])
    assert listed.exit_code == 0, listed.output
    assert "initial-auth" in listed.output

    got = runner.invoke(app, ["snapshot", "get", "--project", "demo", "--name", "initial-auth"])
    assert got.exit_code == 0, got.output
    assert 'Snapshot "initial-auth"' in got.output


def test_snapshot_duplicate_name_rejected(project_dir: Path):
    _init_demo_project(project_dir)
    runner.invoke(app, ["snapshot", "create", "--project", "demo", "--name", "snap"])
    result = runner.invoke(app, ["snapshot", "create", "--project", "demo", "--name", "snap"])
    assert result.exit_code == 1
    assert "Snapshot name already exists" in result.output


def test_snapshot_unknown_name_errors(project_dir: Path):
    _init_demo_project(project_dir)
    result = runner.invoke(app, ["snapshot", "get", "--project", "demo", "--name", "missing"])
    assert result.exit_code == 1
    assert "Snapshot not found" in result.output


def test_confidence_operations_with_memory_name(project_dir: Path):
    _init_demo_project(project_dir)
    _create_named_memory(project_dir, "auth", "x")

    recorded = runner.invoke(
        app,
        ["confidence", "record", "--memory", "auth", "--sequence", "1", "--score", "0.9"],
    )
    assert recorded.exit_code == 0, recorded.output

    shown = runner.invoke(app, ["confidence", "show", "--memory", "auth", "--sequence", "1"])
    assert shown.exit_code == 0, shown.output
    assert "0.9" in shown.output


def test_verify_operations_with_names(project_dir: Path):
    _init_demo_project(project_dir)
    _create_named_memory(project_dir, "auth", "JWT", type="fact")

    project_report = runner.invoke(app, ["verify", "project", "--project", "demo"])
    assert project_report.exit_code == 0, project_report.output
    assert "PASSED" in project_report.output

    memory_report = runner.invoke(
        app, ["verify", "memory", "--project", "demo", "--memory", "auth"]
    )
    assert memory_report.exit_code == 0, memory_report.output
    assert "PASSED" in memory_report.output


def test_drift_and_decay_with_project_name(project_dir: Path):
    _init_demo_project(project_dir)
    _create_named_memory(project_dir, "auth", "JWT", type="fact")

    decay_result = runner.invoke(app, ["decay", "--project", "demo"])
    assert decay_result.exit_code == 0, decay_result.output
    assert "Decay · demo" in decay_result.output
    assert "1 assessment(s)" in decay_result.output

    drift_result = runner.invoke(app, ["drift", "--project", "demo"])
    assert drift_result.exit_code == 0, drift_result.output
    assert "Drift · demo" in drift_result.output


def test_drift_renders_project_name_not_uuid(project_dir: Path):
    _init_demo_project(project_dir)
    _create_named_memory(project_dir, "auth", "JWT", type="fact")
    project_id = _first_uuid(runner.invoke(app, ["project", "show", "--name", "demo"]).output)

    result = runner.invoke(app, ["drift", "--project", "demo"])
    assert result.exit_code == 0, result.output
    assert "Drift · demo: CLEAN" in result.output
    assert project_id not in result.output


def test_drift_with_project_id_still_renders_name(project_dir: Path):
    _init_demo_project(project_dir)
    _create_named_memory(project_dir, "auth", "JWT", type="fact")
    project_id = _first_uuid(runner.invoke(app, ["project", "show", "--name", "demo"]).output)

    result = runner.invoke(app, ["drift", "--project-id", project_id])
    assert result.exit_code == 0, result.output
    assert "Drift · demo: CLEAN" in result.output
    assert project_id not in result.output


def test_drift_ignores_chronicle_internal_state(project_dir: Path):
    _init_demo_project(project_dir)
    _init_repo(project_dir)
    created = runner.invoke(
        app,
        [
            "memory",
            "create",
            "--project",
            "demo",
            "--name",
            "auth",
            "--type",
            "fact",
            "--content",
            "JWT middleware",
            "--git-commit",
            _head(project_dir),
            "--git-branch",
            _branch(project_dir),
        ],
    )
    assert created.exit_code == 0, created.output
    (project_dir / "auth.md").write_text("auth design")

    result = runner.invoke(app, ["drift", "--project", "demo"])
    assert result.exit_code == 0, result.output
    assert "DIRTY" in result.output
    assert "changed artifact: auth.md" in result.output
    assert ".chronicle" not in result.output


def test_drift_renders_named_memory_instead_of_uuid(project_dir: Path):
    _init_demo_project(project_dir)
    _init_repo(project_dir)
    created = runner.invoke(
        app,
        [
            "memory",
            "create",
            "--project",
            "demo",
            "--name",
            "tokens",
            "--type",
            "fact",
            "--content",
            "JWT expires in 15 minutes",
            "--git-commit",
            "deadbeef",
        ],
    )
    assert created.exit_code == 0, created.output
    memory_id = _first_uuid(created.output)

    result = runner.invoke(app, ["drift", "--project", "demo"])
    assert result.exit_code == 0, result.output
    assert "affected knowledge: tokens v1" in result.output
    assert "recorded commit differs from current HEAD" in result.output
    assert memory_id not in result.output


def test_search_with_project_name(project_dir: Path):
    _init_demo_project(project_dir)
    _create_named_memory(project_dir, "auth", "JWT middleware protects routes", type="decision")

    result = runner.invoke(app, ["search", "JWT", "--project", "demo"])
    assert result.exit_code == 0, result.output
    assert '"auth"' in result.output
    assert "project: demo" in result.output

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
    shutil.copy2(REPO_ROOT / "alembic.ini", tmp_path / "alembic.ini")
    shutil.copytree(REPO_ROOT / "alembic", tmp_path / "alembic")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _first_uuid(text: str) -> str:
    return UUID_RE.search(text).group()


def _init(project_dir: Path) -> None:
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0, result.output


def test_init_creates_dir_db_and_config(project_dir: Path):
    _init(project_dir)
    assert context.chronicle_dir().is_dir()
    assert context.db_path().is_file()
    assert context.config_path().is_file()
    config = json.loads(context.config_path().read_text())
    assert config["db"] == "chronicle.db"


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
    assert f"Decay [project {project_id}]" in result.output
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

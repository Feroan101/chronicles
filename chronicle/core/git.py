"""Git context: an optional reference attached to a Memory Version.

The reference is provided by the user or agent when creating or updating
knowledge. Values are opaque strings; Version 1 validates only that supplied
fields are non-empty and non-whitespace.

The module also reads the current state of a Git working tree for drift
detection. Reading is read-only and is only performed when the user or agent
explicitly invokes a drift check.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from chronicle.core.errors import GitContextError

#: Chronicle's own state directory. Files under it are internal state, not
#: project content, so a dirty ``.chronicle/`` tree never counts as drift.
INTERNAL_STATE_DIR = ".chronicle"

#: The two conventional names for Git's default branch across repos. Knowledge
#: recorded against one of these names is treated as referring to the default
#: development line, so a pure main<->master rename is not reported as drift.
DEFAULT_BRANCH_ALIASES: tuple[str, str] = ("main", "master")


@dataclass(frozen=True)
class GitContext:
    """A Git context reference: branch, commit, and change description.

    All fields are optional; at least one must be supplied.
    """

    branch: str | None = None
    commit: str | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        fields = {
            "branch": self.branch,
            "commit": self.commit,
            "description": self.description,
        }
        if not any(value is not None for value in fields.values()):
            raise GitContextError()
        for name, value in fields.items():
            if value is not None and not value.strip():
                raise GitContextError(name)


@dataclass(frozen=True)
class GitTree:
    """A read-only snapshot of a Git working tree.

    ``current_branch`` is None when HEAD is detached. ``default_branch`` is the
    repository's default branch name when it can be determined (from the origin
    HEAD ref, or the sole local branch), otherwise None. ``head_commit`` is
    None when the repository has no commits yet. ``changed_files`` lists paths
    with uncommitted modifications, including untracked files, excluding
    Chronicle's own ``.chronicle/`` state directory.
    """

    is_repo: bool
    current_branch: str | None = None
    default_branch: str | None = None
    head_commit: str | None = None
    changed_files: list[str] = field(default_factory=list)


def _is_internal_state(path: str) -> bool:
    """True when ``path`` lives inside Chronicle's own state directory."""
    return path.split("/", 1)[0] == INTERNAL_STATE_DIR


def _git(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(path),
        capture_output=True,
        text=True,
        check=False,
    )


def read_git_tree(path: Path | str | None = None) -> GitTree:
    """Read the current state of a Git working tree.

    The operation is read-only and never modifies the repository. When ``path``
    is not inside a Git work tree, or when Git is unavailable, an empty tree
    with ``is_repo=False`` is returned.
    """
    target = Path(path) if path is not None else Path.cwd()
    try:
        probe = _git(target, "rev-parse", "--is-inside-work-tree")
    except FileNotFoundError:
        return GitTree(is_repo=False)
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        return GitTree(is_repo=False)

    branch_result = _git(target, "branch", "--show-current")
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None

    head_result = _git(target, "rev-parse", "HEAD")
    head = head_result.stdout.strip() if head_result.returncode == 0 else None

    status_result = _git(target, "status", "--porcelain", "--untracked-files=all")
    changed: list[str] = []
    for line in status_result.stdout.splitlines():
        if len(line) > 3:
            path = line[3:].strip()
            if not _is_internal_state(path):
                changed.append(path)

    return GitTree(
        is_repo=True,
        current_branch=branch or None,
        default_branch=_default_branch(target),
        head_commit=head or None,
        changed_files=changed,
    )


def _default_branch(path: Path) -> str | None:
    """Return the repository's default branch name when determinable.

    Reads the local tracking ref that mirrors the default upstream branch, or,
    for repositories with no remote, falls back to the single local branch.
    The operation is read-only.
    """
    symbolic = _git(path, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    if symbolic.returncode == 0 and symbolic.stdout.strip():
        return symbolic.stdout.strip()

    branches = _git(path, "for-each-ref", "--format=%(refname:short)", "refs/heads")
    if branches.returncode == 0:
        names = [line.strip() for line in branches.stdout.splitlines() if line.strip()]
        if len(names) == 1:
            return names[0]
    return None

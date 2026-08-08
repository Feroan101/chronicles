"""Git context: an optional reference attached to a Memory Version.

The reference is provided by the user or agent when creating or updating
knowledge. Values are opaque strings; Version 1 validates only that supplied
fields are non-empty and non-whitespace.
"""

from __future__ import annotations

from dataclasses import dataclass

from chronicle.core.errors import GitContextError


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

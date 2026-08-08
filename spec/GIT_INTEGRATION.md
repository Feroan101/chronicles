# Chronicle Git Integration Specification

Version: 1.0

Status: Draft

---

# 1. Purpose

This specification defines how Chronicle connects project knowledge with source code history.

Git manages changes to source code.

Chronicle manages changes to project understanding.

The Git Bridge provides context between code changes and knowledge changes without replacing either system.

This document defines the requirements, behavior, constraints, and invariants of the Git Integration.

---

# 2. Definition

The Git Integration is the connection between Chronicle knowledge and a Git repository.

It allows knowledge to reference the source code context in which it was created or discovered, while remaining fully functional without that context.

---

# 3. Requirements

The Git Integration MUST:

* Operate within exactly one Project.
* Remain optional for all Chronicle operations.
* Preserve Chronicle's independence from Git.
* Preserve all Chronicle invariants.

The Git Integration MUST NOT:

* Modify source code.
* Create Git commits.
* Run Git commands automatically.
* Replace Git functionality.
* Analyze source code.
* Operate across multiple Projects.
* Rewrite Version history.

---

# 4. Knowledge Association

A Memory Version MAY reference a Git context.

A Git context reference includes:

* The branch name, where available.
* The commit identifier, where available.
* A description of the associated change.

The reference is provided by the user or agent when creating or updating knowledge.

A Git context reference is attached to the Version created by the operation that carries it. It never changes Memory ownership or content.

The concrete shape and placement of Git context in Version 1 are defined by the Version 1 Contract (see §14).

---

# 5. Manual Operation

The Git Integration is manual in Version 1.

Git context is associated with knowledge only when a user or agent explicitly provides it through a Chronicle interface.

Chronicle MUST NOT trigger knowledge operations automatically in response to Git events.

No Git hooks are installed or invoked by Chronicle.

---

# 6. Optional Connection

Chronicle knowledge MUST remain meaningful without Git history.

All core operations — creating Memories, creating Versions, Snapshots, Merge, Search, Verification — MUST function in a repository with no Git history.

The absence of Git context MUST NOT prevent any Chronicle operation.

---

# 7. Historical Context

Git history explains what changed in the code.

Chronicle history explains why project understanding changed.

The Git Integration allows these two histories to be connected:

* A code change references the knowledge it produced.
* A Memory references the code change it relates to.

Either history remains valid and complete without the other.

---

# 8. Separation of Responsibilities

Git manages source code history.

Chronicle manages knowledge history.

The Git Integration never:

* Reads Chronicle storage on Git's behalf.
* Writes knowledge on Git's behalf.
* Depends on a specific Git implementation.
* Requires a Git repository to exist.

---

# 9. Evidence

A Git context reference MAY be recorded as Evidence for a Memory Version.

When recorded as Evidence, the reference follows the Evidence model.

Each field of the Git context is recorded as its own Evidence row on the target Version:

* `commit` → `evidence_type="commit"`, `ref` is the commit identifier.
* `branch` → `evidence_type="branch"`, `ref` is the branch name.
* `description` → `evidence_type="description"`, `ref` is the change description.

Only the fields supplied by the user or agent are recorded. Evidence rows are
immutable and remain attached to the Version they were recorded for.

When read back, the Evidence rows are presented both as a grouped Git context
reference (branch, commit, description) and as individual Evidence rows.

Recording Git context as Evidence never makes the knowledge depend on Git.

---

# 10. Consistency

The Git Integration MUST expose the same behavior through:

* CLI Interface
* REST Interface
* MCP Interface
* SDK Interface

Changing interfaces MUST NOT change Git Integration semantics.

---

# 11. Version 1 Contract

This section is the authoritative contract for the Git Integration as
implemented in Version 1. Behavior is defined only where this section or the
sections above require it; the specification does not invent behavior that is
not described.

## 11.1 Git Context Shape

A Git context is a reference with three optional fields:

* `branch` — the branch name, where available.
* `commit` — the commit identifier, where available.
* `description` — a description of the associated change, where available.

At least one field MAY be supplied; the fields that are not supplied are
omitted. A Git context with no fields supplied is not a valid reference and is
rejected.

## 11.2 Operations

The `git_context` reference is accepted by the knowledge operations that create
a Memory Version:

* `create_memory` — records the Git context against the Memory's initial
  Version (sequence 1).
* `create_version` — records the Git context against the appended Version.

The Git context is attached to the exact Version created by the operation. It is
recorded in the same transaction as the Version; an invalid Git context fails
the whole operation, so no Version is created and no partial modification
occurs.

`update_memory` does not accept a Git context: it changes a Memory attribute and
creates no Version to attach Evidence to.

## 11.3 One Context per Operation

An operation accepts at most one Git context. A single Version therefore
carries at most one grouped Git context reference.

## 11.4 Validation

Git context field values are opaque strings. Version 1 applies only
presence/non-empty validation:

* A field value MUST be a non-empty string.
* A field value consisting only of whitespace is treated as empty and is
  rejected.
* No format validation is applied: branch names and commit identifiers are not
  checked against Git naming or hash rules.

An invalid Git context raises a `GitContextError` (a `ChronicleError`) and
fails the operation without side effects.

## 11.5 Evidence Mapping

Each supplied field is recorded as its own Evidence row on the target Version,
as defined in §9:

* `branch` → `evidence_type="branch"`, `ref` = branch name.
* `commit` → `evidence_type="commit"`, `ref` = commit identifier.
* `description` → `evidence_type="description"`, `ref` = change description.

Only the fields supplied by the caller are recorded. Evidence rows are
immutable and never move between Versions.

## 11.6 Read Representation

Recorded Git context is readable through every interface:

* A grouped read representation exposes the Git context of a Version as
  `branch`, `commit`, and `description` fields, assembled from that Version's
  Evidence rows.
* A raw Evidence read exposes the individual Evidence rows attached to a
  Version, including their `evidence_type` and `ref` values.

Both representations reflect the same stored data.

## 11.7 Interface Parity

The Git Integration behavior is identical through the CLI, REST, MCP, and SDK
interfaces, per §10. All four interfaces accept the same Git context shape,
apply the same validation, record the same Evidence, and expose the same
grouped and raw read representations.

---

# 12. Invariants

The following conditions MUST always remain true.

* Every operation operates within exactly one Project.
* Knowledge never depends on Git.
* Chronicle never modifies source code.
* Chronicle never runs Git commands automatically.
* Git context references never change Memory ownership.
* All core operations function without Git history.
* Chronicle Core remains the single authority for knowledge behavior.

---

# 13. Compliance

A Chronicle implementation is compliant with this specification if it:

* Preserves Chronicle's independence from Git.
* Associates knowledge with Git context only by explicit user or agent action.
* Functions fully without Git history.
* Never modifies source code.
* Preserves Project boundaries and Version history.

---

# 14. Out of Scope

This specification does not define:

* Git commands.
* Repository management.
* Commit automation.
* Git hooks.
* Source code analysis.
* Automatic synchronization.
* Version control implementation.

These concerns are implementation-specific or belong to future versions.

In Version 1 the Git Integration additionally does NOT include:

* Execution of Git subprocesses or Git commands.
* Inspection of a Git repository, its branches, or its working tree.
* Automatic detection of the current branch or commit.
* Branch tracking, branch-aware knowledge, or the `branches` model.
* Snapshot integration.
* Automatic knowledge operations in response to Git events.

None of these behaviors may be added without an approved specification change.

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

A reference records where the knowledge came from. It never changes Memory ownership or content.

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

# 11. Invariants

The following conditions MUST always remain true.

* Every operation operates within exactly one Project.
* Knowledge never depends on Git.
* Chronicle never modifies source code.
* Chronicle never runs Git commands automatically.
* Git context references never change Memory ownership.
* All core operations function without Git history.
* Chronicle Core remains the single authority for knowledge behavior.

---

# 12. Compliance

A Chronicle implementation is compliant with this specification if it:

* Preserves Chronicle's independence from Git.
* Associates knowledge with Git context only by explicit user or agent action.
* Functions fully without Git history.
* Never modifies source code.
* Preserves Project boundaries and Version history.

---

# 13. Out of Scope

This specification does not define:

* Git commands.
* Repository management.
* Commit automation.
* Git hooks.
* Source code analysis.
* Automatic synchronization.
* Version control implementation.

These concerns are implementation-specific or belong to future versions.

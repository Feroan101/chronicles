# Chronicle Snapshots Specification

Version: 1.0

Status: Draft

---

# 1. Purpose

This specification defines the Snapshot model within Chronicle.

A Snapshot preserves the state of a Project's knowledge at a specific point in time. It provides a historical reference that allows previous states of project understanding to be examined without modifying the current state.

---

# 2. Definition

A Snapshot is an immutable representation of a Project's knowledge at the moment it is created.

A Snapshot captures the current state of the Project's Memories and their Current Versions.

A Snapshot is not a backup of source code, files, or repositories.

---

# 3. Requirements

A Snapshot MUST:

* Belong to exactly one Project.
* Represent a single point in time.
* Be immutable after creation.
* Preserve the Project's knowledge state.
* Maintain its identity throughout its lifetime.

A Snapshot MUST NOT:

* Belong to multiple Projects.
* Modify Project knowledge.
* Replace Memory history.
* Contain source code.

---

# 4. Snapshot Creation

A Snapshot is created from the current state of a Project.

The creation process follows:

Project

↓

Current Memories

↓

Current Versions

↓

Snapshot

The Snapshot records the Project's knowledge exactly as it exists at that moment.

---

# 5. Snapshot Contents

A Snapshot includes:

* The Project it belongs to.
* The Memories present at the time of creation.
* The Current Version of each Memory.
* The relationships between those Memories.

A Snapshot does not alter or duplicate ownership.

---

# 6. Immutability

Once created, a Snapshot MUST NOT change.

Subsequent changes to Project knowledge MUST NOT modify existing Snapshots.

Creating additional Memories or Versions after a Snapshot has been created does not affect previously created Snapshots.

---

# 7. Relationship with Versioning

Snapshots and Versions serve different purposes.

Versions preserve the history of an individual Memory.

Snapshots preserve the overall state of Project knowledge.

Both mechanisms work together to provide historical understanding.

---

# 8. Retrieval

Chronicle implementations SHOULD support retrieving:

* A specific Snapshot.
* The latest Snapshot.
* Multiple Snapshots belonging to the same Project.

Retrieving a Snapshot MUST NOT modify it.

---

# 9. Persistence

Snapshots MUST persist independently of:

* AI agent sessions.
* CLI sessions.
* REST requests.
* SDK instances.
* MCP connections.

Snapshots remain available until explicitly removed according to implementation policy.

---

# 10. Invariants

The following conditions MUST always remain true.

* Every Snapshot belongs to exactly one Project.
* Every Snapshot represents one point in time.
* Snapshots are immutable.
* A Snapshot never changes after creation.
* A Snapshot does not modify Project knowledge.

---

# 11. Compliance

A Chronicle implementation is compliant with this specification if it:

* Preserves Snapshot immutability.
* Maintains Project ownership.
* Captures the current Project knowledge state.
* Prevents modification of existing Snapshots.
* Preserves Snapshot persistence independently of user or agent sessions.

---

# 12. Out of Scope

This specification does not define:

* Snapshot storage format.
* Snapshot compression.
* Snapshot scheduling.
* Snapshot comparison algorithms.
* Source code versioning.
* Backup or recovery mechanisms.

These concerns are implementation-specific or defined by other specifications.

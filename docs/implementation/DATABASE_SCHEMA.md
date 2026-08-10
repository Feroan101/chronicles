# Chronicle Database Schema

## 1. Overview

This document defines the persistent data model for Chronicle Version 1.

The schema implements the object model defined by the Chronicle specifications:

* Project
* Memory
* Memory Version
* Evidence
* Relationship
* Observation
* Confidence
* Configuration

The schema preserves every invariant defined by the specifications. In particular:

* Every Project has exactly one identity.
* Every Memory belongs to exactly one Project.
* Every Memory has at least one Version.
* Every Version belongs to exactly one Memory.
* Versions are immutable after creation.
* Every Memory has exactly one Current Version.
* Evidence is immutable after insertion.
* Relationships never cross Project boundaries.
* Observations never modify stored knowledge directly.

---

## 2. Storage Model

Chronicle Version 1 stores all data in a single SQLite database located at `.chronicle/chronicle.db`.

The schema is defined using portable types (TEXT, INTEGER, REAL, BLOB) so that the same logical model can be mapped onto a relational server database (such as PostgreSQL) behind the storage abstraction in a future version.

The schema does not rely on machine-specific paths, absolute filesystem locations, or user identities. This allows a `.chronicle/` directory to be shared between machines or committed to a repository by explicit user choice.

---

## 3. Conventions

* Primary keys are generated as unique identifiers (UUID strings) by the Core Engine.
* Timestamps are stored in UTC.
* `created_at` marks the moment a row was inserted.
* Immutable rows MUST NOT be updated or deleted after insertion.
* Foreign keys are enforced.
* Constraints are enforced at the database level where possible, and MUST be enforced at the Core Engine boundary in every case.

---

## 4. Tables

### 4.1 config

Stores Chronicle store-level configuration.

| Column    | Type      | Constraints            | Description                    |
|-----------|-----------|------------------------|--------------------------------|
| key       | TEXT      | PRIMARY KEY            | Configuration key.             |
| value     | TEXT      | NOT NULL               | Configuration value.           |

Example keys:

* `schema_version` — current schema version for migrations.
* `current_branch` — the active branch name.

---

### 4.2 projects

Stores Project objects. A Project is the ownership boundary for all knowledge.

| Column        | Type      | Constraints            | Description                              |
|---------------|-----------|------------------------|------------------------------------------|
| id            | TEXT      | PRIMARY KEY            | Stable Project identity (UUID).          |
| name          | TEXT      | NOT NULL               | Project name.                            |
| description   | TEXT      |                        | Project description (optional).          |
| created_at    | TIMESTAMP | NOT NULL               | Creation time (UTC).                     |

Constraints:

* Project identity never changes.
* One Project per Chronicle store in the standard layout.

---

### 4.3 memories

Stores Memory objects. A Memory is a unit of reusable project knowledge.

| Column        | Type      | Constraints            | Description                              |
|---------------|-----------|------------------------|------------------------------------------|
| id            | TEXT      | PRIMARY KEY            | Stable Memory identity (UUID).           |
| project_id    | TEXT      | NOT NULL, FK projects  | Owning Project.                          |
| type          | TEXT      |                        | Optional knowledge type label.           |
| created_at    | TIMESTAMP | NOT NULL               | Creation time (UTC).                     |

Constraints:

* Every Memory belongs to exactly one Project.
* `UNIQUE(project_id, id)` prevents cross-Project identity reuse.
* A Memory identity never changes.

---

### 4.4 memory_versions

Stores Memory Version objects. Versions are immutable historical states of a Memory.

| Column        | Type      | Constraints            | Description                              |
|---------------|-----------|------------------------|------------------------------------------|
| id            | TEXT      | PRIMARY KEY            | Version identity (UUID).                 |
| memory_id     | TEXT      | NOT NULL, FK memories  | Parent Memory.                           |
| sequence      | INTEGER   | NOT NULL               | Position in the Memory's ordered history.|
| content       | TEXT      | NOT NULL               | The stored knowledge.                    |
| context       | TEXT      |                        | Where the knowledge applies (optional).  |
| metadata      | TEXT      |                        | JSON metadata (optional).                |
| created_at    | TIMESTAMP | NOT NULL               | Creation time (UTC).                     |

Constraints:

* `UNIQUE(memory_id, sequence)` — exactly one position per Memory history.
* `CHECK (sequence >= 1)` — the first Version is numbered 1.
* The first Version of a Memory is created with the Memory.
* Every subsequent update creates a new Version row; existing rows are never modified.
* The Current Version of a Memory is the Version with the highest `sequence` for that Memory.
* The ordering of Versions never changes.

---

### 4.5 observations

Stores unprocessed Observations before they are incorporated into project knowledge.

| Column         | Type      | Constraints              | Description                       |
|----------------|-----------|--------------------------|-----------------------------------|
| id             | TEXT      | PRIMARY KEY              | Observation identity (UUID).      |
| project_id     | TEXT      | NOT NULL, FK projects    | Owning Project.                   |
| content        | TEXT      | NOT NULL                 | The observed information.         |
| status         | TEXT      | NOT NULL                 | pending, processed, discarded.    |
| created_at     | TIMESTAMP | NOT NULL                 | Creation time (UTC).              |
| processed_at   | TIMESTAMP |                          | Processing time (UTC).            |

Constraints:

* An Observation belongs to exactly one Project.
* An Observation never modifies stored knowledge directly.
* Knowledge changes only through Memory creation or Version creation.
* `CHECK (status IN ('pending', 'processed', 'discarded'))`.

---

### 4.6 relationships

Stores Relationships between Memories within a Project.

| Column          | Type      | Constraints              | Description                     |
|-----------------|-----------|--------------------------|---------------------------------|
| id              | TEXT      | PRIMARY KEY              | Relationship identity (UUID).   |
| project_id      | TEXT      | NOT NULL, FK projects    | Owning Project.                 |
| from_memory_id  | TEXT      | NOT NULL, FK memories    | Source Memory.                  |
| to_memory_id    | TEXT      | NOT NULL, FK memories    | Target Memory.                  |
| type            | TEXT      | NOT NULL                 | Relationship type.              |
| created_at      | TIMESTAMP | NOT NULL                 | Creation time (UTC).            |

Constraints:

* Both Memories belong to the same Project.
* `CHECK (from_memory_id <> to_memory_id)` — a Relationship never connects a Memory to itself.
* A Relationship never transfers Memory ownership.
* A Relationship never modifies the Memories it connects.

---

### 4.7 confidence_history

Stores confidence scores as an append-only time series.

| Column            | Type      | Constraints                | Description                           |
|-------------------|-----------|----------------------------|---------------------------------------|
| id                | TEXT      | PRIMARY KEY                | Record identity (UUID).               |
| memory_version_id | TEXT      | NOT NULL, FK memory_versions | Version this score applies to.      |
| score             | REAL      | NOT NULL                   | Confidence value.                     |
| reason            | TEXT      |                            | Why the score was recorded (optional).|
| recorded_at       | TIMESTAMP | NOT NULL                   | When the score was recorded (UTC).    |

Constraints:

* `CHECK (score >= 0.0 AND score <= 1.0)`.
* The current confidence of a Version is the most recent `recorded_at` value.
* Historical scores remain available.
* A confidence change never modifies previous rows.

---

### 4.8 evidence

Stores Evidence records attached to Memory Versions.

| Column            | Type      | Constraints                | Description                           |
|-------------------|-----------|----------------------------|---------------------------------------|
| id                | TEXT      | PRIMARY KEY                | Evidence identity (UUID).             |
| memory_version_id | TEXT      | NOT NULL, FK memory_versions | Version this evidence supports.     |
| evidence_type     | TEXT      | NOT NULL                   | commit, branch, description, pull_request, documentation, source_code, human_confirmation, ai_observation. |
| ref               | TEXT      | NOT NULL                   | Reference to the evidence (commit SHA, file path, etc.). |
| recorded_at       | TIMESTAMP | NOT NULL                   | When the evidence was recorded (UTC). |

Constraints:

* Evidence is immutable after insertion.
* Evidence attaches to a specific Memory Version and never moves.
* Evidence never changes Memory ownership.

---

## 5. Search Index

Knowledge search requires an index over Memory Version content.

In the SQLite implementation, search is provided through a full-text search virtual table:

```sql
CREATE VIRTUAL TABLE search_index USING fts5(
    memory_id UNINDEXED,
    memory_version_id UNINDEXED,
    content
)
```

The `content` column is full-text indexed. The two ID columns are stored but not indexed (UNINDEXED), used only for associating search results back to their owning objects.

A trigger keeps the search index synchronized with the `memory_versions` table:

```sql
CREATE TRIGGER trg_search_index_insert
AFTER INSERT ON memory_versions
BEGIN
    INSERT INTO search_index (memory_id, memory_version_id, content)
    VALUES (NEW.memory_id, NEW.id, NEW.content);
END
```

The search index is derived data. It MUST be kept consistent with the `memory_versions` table and MUST be maintained whenever a new Version is created.

Search behavior is defined by the Search Specification.

---

## 6. Implemented V1 Tables

The following tables are implemented and shipped:

### 6.1 snapshots

Stores Snapshot objects. Snapshots are immutable captures of Project knowledge state.

| Column        | Type      | Constraints            | Description                              |
|---------------|-----------|------------------------|------------------------------------------|
| id            | TEXT      | PRIMARY KEY            | Snapshot identity (UUID).                |
| project_id    | TEXT      | NOT NULL, FK projects  | Owning Project.                          |
| parent_id     | TEXT      | FK snapshots           | Parent snapshot (single-parent history). |
| message       | TEXT      |                        | Snapshot message.                        |
| created_at    | TIMESTAMP | NOT NULL               | Creation time (UTC).                     |

Constraints:

* A Snapshot belongs to exactly one Project.
* A Snapshot represents one point in time.
* A Snapshot is immutable; its rows are never modified.
* A Snapshot does not contain source code.
* Snapshot history forms a chain through `parent_id`.

---

### 6.2 snapshot_members

Captures the knowledge state recorded by each Snapshot.

| Column             | Type      | Constraints                | Description                      |
|--------------------|-----------|----------------------------|----------------------------------|
| snapshot_id        | TEXT      | NOT NULL, FK snapshots     | Owning Snapshot.                 |
| memory_version_id  | TEXT      | NOT NULL, FK memory_versions | Version captured by Snapshot.  |

Constraints:

* `PRIMARY KEY (snapshot_id, memory_version_id)`.
* A Snapshot captures each Memory through its Current Version at creation time.
* A Snapshot captures only one Version per Memory.
* Changes made after a Snapshot is created never modify existing `snapshot_members` rows.

---

### 6.3 snapshot_relationships

Captures the relationships present in each Snapshot.

| Column             | Type      | Constraints                | Description                     |
|--------------------|-----------|----------------------------|---------------------------------|
| snapshot_id        | TEXT      | NOT NULL, FK snapshots     | Owning Snapshot.                |
| relationship_id    | TEXT      | NOT NULL, FK relationships | Relationship captured.          |
| from_memory_id     | TEXT      | NOT NULL                   | Source Memory at capture time.  |
| to_memory_id       | TEXT      | NOT NULL                   | Target Memory at capture time.  |
| type               | TEXT      | NOT NULL                   | Type at capture time.           |

Constraints:

* `PRIMARY KEY (snapshot_id, relationship_id)`.
* Captures the state of each relationship exactly as it existed at creation time.
* Snapshots therefore preserve relationship history without rewriting past states.

---

### 6.4 branches

Stores Project branches. Knowledge follows Git-style branches.

| Column            | Type      | Constraints                | Description                                 |
|-------------------|-----------|----------------------------|---------------------------------------------|
| id                | TEXT      | PRIMARY KEY                | Branch identity (UUID).                     |
| project_id        | TEXT      | NOT NULL, FK projects      | Owning Project.                             |
| name              | TEXT      | NOT NULL                   | Branch name.                                |
| is_default        | BOOLEAN   | NOT NULL                   | Whether this is the Project's default branch |
| created_at        | TIMESTAMP | NOT NULL                   | Creation time (UTC).                        |

Constraints:

* `UNIQUE (project_id, name)` — a branch name is unique within a Project.
* `projects.default_branch_id` and `projects.current_branch_id` point at a `branches` row.
* `snapshots.branch_id` links a Snapshot to the branch it was captured on.

---

### 6.5 branch_members

Records which Memory Version is visible on each Branch.

| Column             | Type      | Constraints                 | Description                         |
|--------------------|-----------|-----------------------------|-------------------------------------|
| branch_id          | TEXT      | NOT NULL, FK branches       | Owning Branch.                      |
| memory_id          | TEXT      | NOT NULL, FK memories       | Memory in the Branch.               |
| memory_version_id  | TEXT      | NOT NULL, FK memory_versions | Version visible on the Branch.     |
| created_at         | TIMESTAMP | NOT NULL                    | Creation time (UTC).                |

Constraints:

* `PRIMARY KEY (branch_id, memory_id)`.
* A Branch shows exactly one Version per Memory.
* Adding a new Version updates the `branch_members` row for that branch.

---

## 7. Storage Abstraction

The schema is accessed exclusively through the Storage Engine.

The Storage Engine exposes a storage abstraction so that the SQLite implementation can be replaced by a server database (such as PostgreSQL) without changing Core Engine behavior.

The Storage Engine is the only component that executes schema-level operations.

---

## 8. Scope Boundaries

This document defines the persistent data model for Version 1.

It does not define:

* Storage engine internals.
* Query optimization.
* Full-text search technology.
* Migration tooling.
* Deployment configuration.

These concerns belong to implementation work.

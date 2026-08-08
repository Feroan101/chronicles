# Chronicle SDK Interface

## 1. Overview

The Chronicle SDK Interface defines how developers integrate Chronicle functionality directly into applications and AI agent systems.

The SDK provides a programmatic way to interact with Chronicle without requiring direct communication through lower-level interfaces.

---

## 2. Purpose

The purpose of the SDK is to make Chronicle functionality accessible inside software applications.

The SDK allows developers to:

* Connect applications with Chronicle
* Store project knowledge
* Retrieve memories
* Access project context
* Work with Chronicle through code

---

## 3. SDK Role

The SDK acts as a developer-facing interface.

Flow:

Application

↓

Chronicle SDK

↓

Chronicle Core

↓

Project Knowledge

The SDK provides convenient access while keeping Chronicle's internal architecture separate.

---

## 4. Core Capabilities

The SDK provides access to Chronicle's main knowledge operations.

### Project Interaction

Applications can work with Chronicle projects.

Examples:

* Access project context
* Connect to stored knowledge

---

### Memory Interaction

Applications can interact with memories.

Examples:

* Create memories
* Retrieve memories
* Update knowledge
* Access memory history

---

### Context Access

Applications can request stored project understanding.

Examples:

* Retrieve relevant knowledge
* Access previous decisions
* Understand project history

---

## 5. Agent Integration

The SDK allows AI agent systems to interact with Chronicle directly.

Example:

Agent Application

↓

Chronicle SDK

↓

Stored Project Memory

Agents can use Chronicle as a persistent knowledge layer while keeping their own execution logic separate.

---

## 6. Design Principles

### Developer Friendly

The SDK should provide a simple way to integrate Chronicle.

---

### Consistent Access

SDK operations should follow the same knowledge model as other Chronicle interfaces.

---

### Abstraction

Developers should interact with Chronicle without needing to understand internal storage.

---

### Reusable Integration

The SDK should allow Chronicle to be embedded into different applications and agent systems.

---

## 7. Implementation

The SDK is implemented as the Python package `chronicle/sdk`, exposing a
synchronous `Chronicle` client. It is a thin adapter over `ChronicleEngine`:
every method delegates to Core, and the SDK contains no SQLAlchemy queries and
no business logic.

### Client

```python
from chronicle.sdk import Chronicle
```

The client is also re-exported from the top-level package for convenience:

```python
from chronicle import Chronicle
```

A `Chronicle` instance connects to a store that must already exist and be
migrated. The SDK never creates or migrates the database automatically.

```python
Chronicle()  # .chronicle/chronicle.db (CWD-relative)
Chronicle(db_path=".chronicle/chronicle.db")
Chronicle(session_factory=sessionmaker(bind=engine))
```

`session_factory` wins over `db_path` when both are given. Each instance holds
its own store connection; multiple connections may be open at once. All
operations take an explicit `project_id` / `memory_id`; there is no active
project state.

### Methods

The method set mirrors the Core, REST, and MCP operations:

| Method | Description |
| --- | --- |
| `create_project(name, description=None)` | Create a project, returning `ProjectRead`. |
| `get_project(project_id)` | Get a project by ID. Raises `ProjectNotFoundError` when missing. |
| `create_memory(project_id, content, type=None, context=None)` | Store a memory with its initial version, returning `MemoryRead`. |
| `get_memory(memory_id)` | Get a memory and its version history. Raises `MemoryNotFoundError` when missing. |
| `list_memories(project_id)` | List a project's memories, ordered by creation, returning `list[MemoryRead]`. |
| `update_memory(memory_id, type=UNSET)` | Update a memory's type, returning `MemoryRead`. |
| `create_version(memory_id, content, context=None)` | Append a memory version, returning `MemoryVersionRead`. |
| `search(query, project_id=None)` | Search project knowledge, returning `list[SearchHitRead]` of current versions. |

Methods return the shared Pydantic read models (`ProjectRead`, `MemoryRead`,
`MemoryVersionRead`, `SearchHitRead`) also used by the REST and MCP interfaces;
SQLAlchemy ORM objects are never exposed.

### update_memory semantics

The `UNSET` sentinel (exported from `chronicle.sdk`) distinguishes "argument
not provided" from an explicit null:

* `update_memory(memory_id)` — `type` omitted (defaults to `UNSET`), type unchanged.
* `update_memory(memory_id, type="decision")` — type set to `"decision"`.
* `update_memory(memory_id, type=None)` — type cleared.

### Errors

SDK methods surface the Core domain errors directly: `ProjectNotFoundError`,
`MemoryNotFoundError`, and `SearchQueryError` (all subclasses of
`ChronicleError`). The SDK adds no error layer of its own.

---

## 8. Scope Boundaries

This document defines the SDK interface concept and its implementation.

It does not define:

* Agent architectures
* Model behavior
* Authentication systems

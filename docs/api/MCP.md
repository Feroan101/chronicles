# Chronicle MCP Interface

## 1. Overview

The Chronicle MCP Interface defines how AI agents communicate with Chronicle through the Model Context Protocol (MCP).

MCP provides a standard communication layer that allows agents to access Chronicle's memory system.

Chronicle uses MCP as an interface between AI agents and stored project knowledge.

---

## 2. Purpose

The purpose of the MCP interface is to allow AI agents to:

* Store project knowledge
* Retrieve existing memories
* Access project context
* Maintain continuity across sessions

The MCP layer allows agents to interact with Chronicle without directly accessing internal storage.

---

## 3. MCP Role

The MCP interface acts as a communication bridge.

Flow:

AI Agent

↓

MCP Interface

↓

Chronicle Core

↓

Project Knowledge

The MCP layer handles communication while Chronicle manages memory and knowledge.

---

## 4. Agent Interaction

Through MCP, agents can interact with Chronicle's knowledge system.

Examples:

### Store Knowledge

An agent provides important project information.

Chronicle stores it as project memory.

---

### Retrieve Knowledge

An agent requests relevant project context.

Chronicle returns stored knowledge.

---

### Access History

An agent requests previous knowledge states.

Chronicle provides memory history.

---

## 5. Knowledge Operations

The MCP interface exposes Chronicle's core knowledge operations.

These include:

* Memory creation
* Memory retrieval
* Memory updates
* Memory history access
* Project context access

---

## 6. Context Sharing

MCP allows multiple agents to use the same Chronicle project knowledge.

Example:

Agent A:

Discovers an architecture decision.

↓

Chronicle

↓

Agent B:

Retrieves the decision later.

This creates shared understanding between agents.

---

## 7. Design Principles

### Standard Communication

Agents should communicate with Chronicle through a consistent interface.

---

### Separation of Systems

Agents interact with Chronicle without depending on internal implementation details.

---

### Shared Knowledge

Multiple agents should be able to access the same project memory.

---

### Persistent Context

Agent sessions should not determine whether knowledge is available.

---

## 8. Implementation

The MCP interface is implemented as an MCP server in `chronicle/mcp/server.py`
using the official Python MCP SDK (`mcp>=1.0,<2.0`). The server is a thin
adapter over `ChronicleEngine`: tool handlers never touch SQLAlchemy directly,
they delegate exclusively to Core business operations.

### Transport

The server runs over `stdio` (`mcp run`, the default `FastMCP` transport). It
is launched as a subprocess by the agent:

```json
{
  "mcpServers": {
    "chronicle": {
      "command": "chronicle-mcp"
    }
  }
}
```

The entry point `chronicle-mcp` is registered as a console script and runs the
module-level server over stdio. The server opens the same default store as the
CLI and REST interfaces (`.chronicle/chronicle.db` relative to the working
directory), and can be constructed programmatically with
`create_mcp_server(session_factory=None)` for custom stores.

### Tools

The tool set mirrors the Chronicle REST API:

| Tool | Description |
| --- | --- |
| `create_project` | Create a new project (`name`, optional `description`). |
| `get_project` | Get a project by ID. |
| `create_memory` | Store a memory in a project (`project_id`, `content`, optional `type`, `context`). Creates the initial version. |
| `get_memory` | Get a memory and its version history by ID. |
| `list_memories` | List all memories in a project, ordered by creation. |
| `update_memory` | Update a memory's `type`. Passing null or omitting `type` leaves the memory unchanged. |
| `create_version` | Append a new version of a memory (`memory_id`, `content`, optional `context`). |
| `search` | Search project knowledge (`query`, optional `project_id` filter). Returns current-version hits with rank. |

Tool outputs are the same JSON shapes as the REST API responses. Errors from
Core (e.g. `ProjectNotFoundError`, `MemoryNotFoundError`, `SearchQueryError`)
surface as MCP tool errors (`isError` results) carrying the domain message.

### Design Principles

The MCP layer follows the same principles as the REST interface:

- Agents communicate with Chronicle through a consistent, documented tool set.
- Agents interact with Chronicle without depending on internal storage details.
- Multiple agents can access the same project memory through a shared store.
- Agent sessions do not determine whether knowledge is available.

---

## 9. Scope Boundaries

This document defines the MCP interface concept and its implementation.

It does not define:

* Agent architectures
* Model behavior
* External integrations

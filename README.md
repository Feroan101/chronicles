<div align="center">

# Chronicle

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![Status](https://img.shields.io/badge/status-V1%20Development-blue)
![Python](https://img.shields.io/badge/python-3.13+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Local First](https://img.shields.io/badge/local--first-yes-success)

### The Shared Memory Layer for AI Software Engineering

**Chronicle** is a local-first infrastructure platform that enables AI coding agents to share persistent engineering knowledge across sessions, branches, and tools.

Instead of every AI maintaining isolated chat history, Chronicle builds a versioned understanding of your project, allowing every agent to reason from the same source of truth.

Git tracks **source code**.

Chronicle tracks **project understanding**.

<br>

> [!NOTE]
> Chronicle v0.1.0 has been released and tagged. The project is now in active V1 development.
> The documentation below describes both the current foundation and the V1 target architecture.

<p align="center">
  <a href="#overview"><strong>Overview</strong></a> •
  <a href="#the-problem"><strong>Problem</strong></a> •
  <a href="#core-features"><strong>Features</strong></a> •
  <a href="#architecture"><strong>Architecture</strong></a> •
  <a href="#quick-start"><strong>Quick Start</strong></a> •
  <a href="#documentation"><strong>Documentation</strong></a> •
  <a href="#roadmap"><strong>Roadmap</strong></a>
</p>

</div>

---

## Overview

Chronicle is a standalone infrastructure platform that enables AI coding agents to share persistent engineering knowledge across sessions, branches, and tools.

Instead of treating every AI conversation as isolated context, Chronicle creates a versioned understanding of a software project that evolves alongside its source code.

Rather than storing conversations, Chronicle stores structured engineering knowledge, including architecture decisions, project constraints, business rules, design rationale, dependencies, conventions, and implementation history.

Chronicle is designed to become the project's single source of truth for engineering knowledge.

---

## The Problem

Modern AI coding assistants have exceptional reasoning capabilities but poor long-term memory.

As projects grow, agents gradually lose important context:

- Architectural decisions
- Project constraints
- Coding conventions
- Business rules
- API contracts
- Previously rejected solutions
- Design rationale

This causes repeated mistakes, inconsistent implementations, duplicated discussions, and architectural drift.

Although the codebase evolves through version control, the knowledge behind those changes is often lost inside conversations.

---

## The Solution

Chronicle versions engineering knowledge in the same way Git versions source code.

As a project evolves, Chronicle observes meaningful changes and proposes knowledge snapshots that capture what was learned, why decisions were made, and how different parts of the system relate to one another.

Every connected AI agent works from the same evolving understanding of the project instead of rebuilding context from scratch.

Knowledge becomes searchable, verifiable, branch-aware, and versioned.

---

## Architecture

```text
                        AI Coding Agents

 Claude Code   Cursor   Codex   OpenCode   Aider   Custom Agents

                               │
                               ▼

                      Chronicle Core Engine

                               │

        ┌──────────────────────┴──────────────────────┐
        │                                             │
 Knowledge Graph                             Snapshot Store
 Relationships                               Version History
 Evidence                                    Search
 Observations
```

Chronicle acts as the shared knowledge layer between AI coding agents and the software project.

It continuously builds an understanding of the project while allowing every connected tool to read from and contribute to the same knowledge base.

---

## Core Features

### Implemented

| Feature | Description |
|----------|-------------|
| Versioned Knowledge | Engineering knowledge evolves through immutable versions. |
| Knowledge Graph | Connects architecture, constraints, dependencies, and decisions via Relationships. |
| Evidence | Every knowledge object records why it exists. |
| Observations | Capture information before incorporating into project knowledge. |
| Snapshots | Capture project knowledge state at a point in time. |
| Local First | Every repository owns its own Chronicle repository. |

### Planned for V1

| Feature | Description |
|----------|-------------|
| Branch-Aware Memory | Project knowledge follows Git branches. |
| Confidence | Track the reliability of stored knowledge. |
| Verification | Validate stored knowledge against the current project. |
| Drift Detection | Detect when implementation and stored knowledge diverge. |

Detailed documentation for every feature is available in the documentation sections below.

---

## Repository Layout

Every Chronicle project lives alongside its Git repository.

```text
project/
├── .git/
└── .chronicle/
```

The `.chronicle` directory stores the project's versioned engineering knowledge, snapshots, metadata, indexes, and configuration.

Source code remains owned by Git.

Engineering knowledge is owned by Chronicle.

## Quick Start

> [!WARNING]
> The following commands represent the planned V1 CLI and may change during development.

```bash
chronicle init

chronicle snapshot

chronicle status

chronicle search "authentication"

chronicle verify

chronicle history
```

## Documentation

Chronicle's documentation is organized by responsibility.

### Design

| Document | Description |
|----------|-------------|
| [`VISION.md`](docs/design/VISION.md) | Why Chronicle exists and its long-term vision |
| [`PHILOSOPHY.md`](docs/design/PHILOSOPHY.md) | Core engineering principles and design philosophy |
| [`DESIGN.md`](docs/design/DESIGN.md) | Product decisions and the locked V1 specification |

### Architecture

| Document | Description |
|----------|-------------|
| [`SYSTEM_ARCHITECTURE.md`](docs/architecture/SYSTEM_ARCHITECTURE.md) | High-level system architecture |
| [`OBJECT_MODEL.md`](docs/architecture/OBJECT_MODEL.md) | Chronicle object model |
| [`SNAPSHOTS.md`](docs/architecture/SNAPSHOTS.md) | Snapshot and versioning model |
| [`STORAGE.md`](docs/architecture/STORAGE.md) | Storage architecture |
| [`GRAPH.md`](docs/architecture/GRAPH.md) | Knowledge graph |
| [`OBSERVATION.md`](docs/architecture/OBSERVATION.md) | Observation pipeline |
| [`VERIFICATION.md`](docs/architecture/VERIFICATION.md) | Verification pipeline |
| [`DRIFT_DETECTION.md`](docs/architecture/DRIFT_DETECTION.md) | Drift detection |
| [`MERGE.md`](docs/architecture/MERGE.md) | Merge strategy |

### APIs

| Document | Description |
|----------|-------------|
| [`CLI.md`](docs/api/CLI.md) | Command-line interface |
| [`REST.md`](docs/api/REST.md) | REST API |
| [`SDK.md`](docs/api/SDK.md) | Python SDK |
| [`MCP.md`](docs/api/MCP.md) | MCP integration |

### Implementation

| Document | Description |
|----------|-------------|
| [`CORE_ENGINE.md`](docs/implementation/CORE_ENGINE.md) | Internal engine architecture |
| [`STORAGE_ENGINE.md`](docs/implementation/STORAGE_ENGINE.md) | Persistence layer |
| [`GIT_BRIDGE.md`](docs/implementation/GIT_BRIDGE.md) | Git integration |
| [`DATABASE_SCHEMA.md`](docs/implementation/DATABASE_SCHEMA.md) | Database schema |
| [`ROADMAP.md`](docs/implementation/ROADMAP.md) | V1 implementation roadmap |

## Roadmap

Chronicle is currently focused on delivering a stable Version 1.

See the full implementation roadmap in [`docs/implementation/ROADMAP.md`](docs/implementation/ROADMAP.md).

## Contributing

Contributions, bug reports, feature discussions, and documentation improvements are welcome.

Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening an issue or pull request.

---

## License

Chronicle is released under the MIT License.

See the [LICENSE](LICENSE) file for more information.
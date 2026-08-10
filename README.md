<div align="center">

# Chronicle

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![Python](https://img.shields.io/badge/python-3.13+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Local First](https://img.shields.io/badge/local--first-yes-success)

### The Shared Memory Layer for AI Software Engineering

**Chronicle** is a local-first infrastructure platform that enables AI coding agents to share persistent engineering knowledge across sessions, branches, and tools.

Instead of every AI maintaining isolated chat history, Chronicle builds a versioned understanding of your project, allowing every agent to reason from the same source of truth.

Git tracks **source code**.

Chronicle tracks **project understanding**.

<br>

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
> [!NOTE]
> This is a test note.

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

As a project evolves, Chronicle allows users and agents to record knowledge with optional Git context (branch, commit, description) that connects code changes to project understanding.

Every connected AI agent works from the same evolving understanding of the project instead of rebuilding context from scratch.

Knowledge becomes searchable, verifiable, and versioned.

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
   Knowledge Store                            Evidence Tracking
   Memory Versions                            Git Context
   FTS5 Search                                 Version History
```

Chronicle acts as the shared knowledge layer between AI coding agents and the software project.

It builds an understanding of the project while allowing every connected tool to read from and contribute to the same knowledge base.

---

## Core Features

| Feature | Description |
|----------|-------------|
| Versioned Knowledge | Engineering knowledge evolves through immutable versions. |
| Evidence Tracking | Every knowledge object records why it exists. |
| Git Context | Optional association of knowledge with Git branch, commit, and description. |
| FTS5 Search | Full-text search across project knowledge. |
| Local First | Every repository owns its own Chronicle repository. |

Detailed documentation for every feature is available in the documentation sections below.

---

## Repository Layout

Every Chronicle project lives alongside its Git repository.

```text
project/
├── .git/
└── .chronicle/
```

The `.chronicle` directory stores the project's versioned engineering knowledge, metadata, indexes, and configuration.

Source code remains owned by Git.

Engineering knowledge is owned by Chronicle.

## Quick Start

```bash
# Initialize Chronicle in your project
chronicle init

# Create a project
chronicle project create "my-project"

# Store knowledge with optional Git context
chronicle memory create \
  --project-id <project-id> \
  --content "We use FastAPI for the REST layer" \
  --type decision \
  --git-branch main \
  --git-commit abc123

# Search your knowledge
chronicle search "FastAPI"

# View a memory
chronicle show --memory-id <memory-id>

# View version history with Git context
chronicle version show --memory-id <memory-id> --sequence 1
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
| [`STORAGE.md`](docs/architecture/STORAGE.md) | Storage architecture |

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

## Roadmap

Chronicle Version 1 focuses on establishing the core foundation: persistent knowledge, versioning, evidence tracking, and search.

See the full implementation roadmap in [`docs/implementation/ROADMAP.md`](docs/implementation/ROADMAP.md).

## Contributing

Contributions, bug reports, feature discussions, and documentation improvements are welcome.

Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening an issue or pull request.

---

## License

Chronicle is released under the MIT License.

See the [LICENSE](LICENSE) file for more information.

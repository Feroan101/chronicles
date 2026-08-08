# Chronicle Technology Stack

Version: 1.0

Status: Approved

---

# Purpose

This document defines the official technology stack for Chronicle.

Unless otherwise specified, all implementation decisions MUST follow this document.

Technology choices are intended to maximize:

* Industry relevance
* Long-term maintainability
* Simplicity
* Developer experience
* AI ecosystem compatibility

Implementations MUST NOT introduce additional technologies unless they provide a clear architectural benefit or solve an identified requirement.

---

# Core Language

## Python 3.13+

Python is the primary implementation language for Chronicle.

All core components, services, APIs, and integrations MUST be implemented in Python unless an approved architecture decision specifies otherwise.

---

# Package Management

## uv

Chronicle uses **uv** for:

* Dependency management
* Virtual environments
* Package installation
* Project execution

Other package managers SHOULD NOT be used for development.

---

# Command Line Interface

## Typer

The Chronicle CLI MUST be implemented using **Typer**.

Typer provides:

* Type-safe commands
* Automatic help generation
* Excellent developer experience
* Strong FastAPI ecosystem compatibility

---

# REST API

## FastAPI

The REST interface MUST be implemented using **FastAPI**.

FastAPI is responsible for:

* HTTP endpoints
* Request handling
* Response generation
* API documentation

Business logic MUST remain inside the Chronicle Core.

---

# Data Validation

## Pydantic v2

Pydantic is the standard model validation library.

It MUST be used for:

* Request validation
* Response validation
* Configuration models
* Internal data models where appropriate

---

# Database

## SQLite

SQLite is the storage engine for Chronicle Version 1.

It provides:

* Local-first operation
* Zero configuration
* Reliable persistence
* Full-text search (FTS5)

PostgreSQL may be used in future versions for multi-user or server deployments.

---

# Object Relational Mapping

## SQLAlchemy 2

Chronicle uses SQLAlchemy as its Object Relational Mapper (ORM).

SQLAlchemy is responsible for:

* Database models
* Query construction
* Relationships
* Database sessions

Raw SQL MAY be used when justified by performance or functionality.

---

# Database Migrations

## Alembic

Alembic is the official migration tool.

Database schema changes MUST be managed through migrations.

Manual schema modifications SHOULD be avoided.

---

# AI Communication

## Model Context Protocol (MCP)

Chronicle uses MCP for communication with AI agents.

The MCP server acts as an interface between AI systems and the Chronicle Core.

The Chronicle Core MUST NOT depend on MCP.

---

# Testing

## pytest

pytest is the official testing framework.

All tests SHOULD be written using pytest.

Testing SHOULD include:

* Unit tests
* Integration tests
* API tests

---

# Code Quality

## Ruff

Ruff is the official tool for:

* Linting
* Formatting

All code SHOULD pass Ruff checks before being committed.

---

# Architecture Principles

Technology choices MUST support the following architecture.

Interfaces:

* CLI
* REST API
* MCP
* SDK

↓

Chronicle Core

↓

Storage Layer

↓

SQLite

The Chronicle Core is the heart of the system.

All interfaces MUST communicate with the Chronicle Core.

Interfaces MUST NOT implement Chronicle business logic.

---

# Dependency Rules

The Chronicle Core:

* MUST remain framework-independent.
* MUST NOT depend on FastAPI.
* MUST NOT depend on LangChain.
* MUST NOT depend on LangGraph.
* MUST NOT depend on MCP.
* MUST NOT contain interface-specific logic.

Interfaces depend on the Core.

The Core does not depend on interfaces.

---

# Future Technologies

Additional technologies MAY be introduced only when:

* They solve a demonstrated problem.
* They do not unnecessarily increase complexity.
* They align with Chronicle's architecture.

Technology choices MUST prioritize simplicity over novelty.

---

# Approved Technology Stack

| Category               | Technology     |
| ---------------------- | -------------- |
| Language               | Python 3.13+   |
| Package Management     | uv             |
| CLI                    | Typer          |
| REST API               | FastAPI        |
| Data Validation        | Pydantic v2    |
| Database               | SQLite         |
| ORM                    | SQLAlchemy 2   |
| Database Migrations    | Alembic        |
| AI Communication       | MCP            |
| Testing                | pytest         |
| Linting & Formatting   | Ruff           |

This document serves as the authoritative reference for Chronicle's implementation stack.

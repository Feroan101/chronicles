# Chronicle REST Interface

## 1. Overview

The Chronicle REST Interface defines how external applications communicate with Chronicle through HTTP-based requests.

The REST interface provides a way for applications and services to interact with Chronicle's memory system without directly accessing internal components.

---

## 2. Purpose

The purpose of the REST interface is to expose Chronicle functionality through a standard communication layer.

It allows applications to:

* Access project knowledge
* Manage memories
* Retrieve stored context
* Interact with Chronicle programmatically

---

## 3. REST Role

The REST interface acts as an external communication layer.

Flow:

Application

↓

REST Interface

↓

Chronicle Core

↓

Project Knowledge

The REST layer handles requests and responses while Chronicle manages the underlying knowledge system.

---

## 4. Core Operations

The REST interface provides access to Chronicle's primary operations.

### Project Operations

Applications can interact with project context.

Examples:

* Access project information
* Work within a project boundary

---

### Memory Operations

Applications can interact with stored memories.

Examples:

* Create memories
* Retrieve memories
* Update knowledge
* Access memory history

---

### Knowledge Access

Applications can request project understanding from Chronicle.

Examples:

* Retrieve relevant memories
* View knowledge relationships
* Inspect previous states

---

## 5. Git Context

The REST interface exposes the same Git Integration behavior as the CLI, MCP,
and SDK interfaces, per the Git Integration Specification.

Requests that create a Memory Version — creating a Memory and creating a
Version — MAY carry an optional Git context reference with three fields:
`branch`, `commit`, and `description` (at least one required). The Git context
is recorded as Evidence on the exact Version created by the request, in the
same transaction.

Values are opaque strings; only non-empty (non-whitespace) values are accepted,
with no format validation. An invalid Git context fails the request without
creating anything and is reported as a `GitContextError`.

Responses reflect the recorded context in two forms:

* A grouped `git_context` representation on Version responses.
* A raw Evidence representation exposing the individual Evidence rows for a
  Version.

Updating a Memory attribute does not accept a Git context.

---

## 6. Request Flow

A typical REST interaction follows:

Application Request

↓

REST Interface

↓

Chronicle Processing

↓

Knowledge Operation

↓

Response

The interface provides access to Chronicle without exposing internal architecture.

---

## 7. Agent and Application Access

The REST interface allows different types of clients to interact with Chronicle.

Examples:

* AI agents
* Developer tools
* External applications

All clients interact through the same Chronicle knowledge model.

---

## 8. Design Principles

### Clear Interface

Communication with Chronicle should be predictable and understandable.

---

### Separation of Concerns

External clients should not depend on internal Chronicle implementation.

---

### Consistent Knowledge Model

All interfaces should interact with the same project memory system.

---

### Accessible Integration

Applications should be able to use Chronicle through a standard interface.

---

## 9. Scope Boundaries

This document defines the REST interface concept.

It does not define:

* Specific API endpoints
* Request formats
* Response schemas
* Authentication
* Server implementation

Those details belong to future implementation decisions.

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

## 8. Scope Boundaries

This document defines the MCP interface concept.

It does not define:

* MCP server implementation
* Specific MCP tool definitions
* Agent architectures
* Model behavior
* External integrations

Those details belong to future implementation decisions.

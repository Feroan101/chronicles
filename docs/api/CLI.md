# Chronicle CLI

## 1. Overview

The Chronicle CLI defines the command-line interface used to interact with Chronicle.

The CLI provides a direct way for users and developers to manage Chronicle projects, memories, and knowledge history.

It acts as an entry point for interacting with the Chronicle system from the terminal.

---

## 2. Purpose

The purpose of the CLI is to provide simple access to Chronicle functionality.

The CLI allows users to:

* Work with Chronicle projects
* View stored knowledge
* Manage memories
* Inspect knowledge history
* Interact with Chronicle without requiring another interface

---

## 3. CLI Role

The CLI acts as a client of Chronicle.

Flow:

User

↓

Chronicle CLI

↓

Chronicle Core

↓

Project Knowledge

The CLI does not contain the memory system itself. It communicates with Chronicle's underlying components.

---

## 4. Core Operations

The CLI provides access to Chronicle's main operations.

### Project Management

Allows users to interact with Chronicle projects.

Examples:

* Create a project context
* View project information
* Access project knowledge

---

### Memory Management

Allows users to work with stored memories.

Examples:

* Add knowledge
* View memories
* Update project knowledge
* Review memory history

---

### Knowledge Inspection

Allows users to understand stored project context.

Examples:

* View related knowledge
* Inspect previous versions
* Review changes over time

---

## 5. Memory Interaction

The CLI provides access to Chronicle memory operations.

Example workflow:

User provides knowledge

↓

Chronicle stores memory

↓

Memory becomes available to agents

Another workflow:

User requests context

↓

Chronicle retrieves knowledge

↓

Information is displayed

---

## 6. Version Awareness

The CLI allows users to interact with Chronicle's versioned knowledge.

Users can inspect:

* Current memory state
* Previous memory versions
* Knowledge evolution

This preserves the Git-like history concept of Chronicle.

---

## 7. Design Principles

### Simple Interface

The CLI should provide direct access to Chronicle capabilities.

---

### Human Accessible

Users should be able to understand and inspect stored knowledge.

---

### Project Focused

Operations should be performed within a project context.

---

### History Aware

The CLI should expose Chronicle's versioned knowledge model.

---

## 8. Scope Boundaries

This document defines the CLI interface concept.

It does not define:

* Exact command syntax
* CLI framework
* Terminal implementation
* Internal execution logic
* Authentication systems

Those details belong to implementation decisions.

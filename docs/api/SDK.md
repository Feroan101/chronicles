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

## 7. Scope Boundaries

This document defines the SDK interface concept.

It does not define:

* Programming language implementation
* SDK libraries
* Package structure
* Internal APIs
* Authentication systems

Those details belong to future implementation decisions.

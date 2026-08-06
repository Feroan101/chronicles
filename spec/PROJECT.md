# Chronicle Project Specification

Version: 1.0

Status: Draft

---

# 1. Purpose

This specification defines the Project object within Chronicle.

A Project is the top-level container for all knowledge managed by Chronicle. Every Chronicle object exists within the context of exactly one Project.

This document defines the requirements, lifecycle, constraints, and invariants of a Project.

---

# 2. Definition

A Project represents a single software project, repository, or development effort.

A Project establishes the boundary within which Chronicle stores and manages knowledge.

---

# 3. Requirements

A Project MUST:

* Have exactly one unique identity.
* Define the ownership boundary for all Memories.
* Persist independently of AI agent sessions.
* Support multiple Memories.
* Maintain its associated knowledge throughout its lifetime.

A Project MUST NOT:

* Exist without a unique identity.
* Share Memories with another Project.
* Depend on any specific AI model or interface.

---

# 4. Ownership

A Project owns every Memory that belongs to it.

Every Memory MUST belong to exactly one Project.

A Memory MUST NOT belong to multiple Projects.

Deleting or removing a Project affects every Memory owned by that Project according to the implementation's data retention policy.

---

# 5. Identity

A Project MUST have a stable identity.

The identity MUST remain unchanged throughout the lifetime of the Project.

The identity MUST uniquely distinguish one Project from another.

---

# 6. Lifecycle

A Project progresses through the following lifecycle.

Created

↓

Active

↓

Archived or Removed

A Project MAY exist without Memories.

A Project MUST exist before any Memory can be created.

---

# 7. Relationships

A Project MAY contain zero or more Memories.

A Project MUST NOT directly own Memory Versions.

Memory Versions belong to Memories.

The ownership hierarchy is therefore:

Project

↓

Memory

↓

Memory Version

---

# 8. Persistence

A Project MUST persist independently of:

* AI agent sessions
* CLI sessions
* REST requests
* SDK instances
* MCP connections

Loss of a session MUST NOT imply loss of a Project.

---

# 9. Invariants

The following conditions MUST always remain true.

* Every Project has exactly one identity.
* Every Memory belongs to one Project.
* Every Memory within a Project shares the same Project context.
* A Project remains the ownership boundary for all contained knowledge.
* Project identity never changes after creation.

---

# 10. Compliance

A Chronicle implementation is compliant with this specification if it:

* Creates Projects according to this document.
* Maintains Project ownership.
* Preserves Project identity.
* Prevents cross-project Memory ownership.
* Preserves Project persistence independently of user or agent sessions.

---

# 11. Out of Scope

This specification does not define:

* Project storage format
* Database implementation
* Project metadata
* Authentication
* Repository integration
* User permissions

These concerns are specified elsewhere.

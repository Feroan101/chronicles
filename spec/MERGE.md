# Chronicle Merge Specification

Version: 1.0

Status: Draft

---

# 1. Purpose

This specification defines how Chronicle combines changes to project knowledge.

A Merge incorporates new knowledge into an existing Project while preserving the integrity and history of previously stored knowledge.

Merge operations affect project knowledge only. They do not merge source code or repository history.

---

# 2. Definition

A Merge is the process of incorporating one or more knowledge changes into a Project.

The result of a Merge is an updated Project knowledge state that preserves both current understanding and historical context.

---

# 3. Requirements

A Merge MUST:

* Operate within exactly one Project.
* Preserve Project ownership.
* Preserve Memory identities.
* Preserve Version history.
* Produce a consistent Project knowledge state.

A Merge MUST NOT:

* Transfer Memories between Projects.
* Remove historical Versions.
* Modify existing Versions.
* Rewrite Project history.

---

# 4. Merge Sources

A Merge MAY include knowledge originating from:

* Newly created Memories.
* Updated Memories.
* Agent Observations.
* Existing Project knowledge.

All merged knowledge MUST belong to the same Project.

---

# 5. Merge Outcomes

A Merge MAY produce one or more of the following outcomes.

### New Memory

The incoming knowledge represents information that does not already exist within the Project.

A new Memory is created.

---

### Memory Update

The incoming knowledge extends or changes an existing Memory.

A new Version is created for that Memory.

---

### No Change

The incoming knowledge does not alter the current Project understanding.

The existing knowledge remains unchanged.

---

# 6. Version Preservation

When a Merge updates existing knowledge:

Current Version

↓

Historical Version

↓

New Current Version

Previous Versions MUST remain preserved according to the Versioning Specification.

A Merge MUST NOT overwrite existing Versions.

---

# 7. Project Integrity

A Merge MUST preserve the consistency of the Project.

After completion:

* Every Memory belongs to the same Project.
* Every Memory has at least one Version.
* Every Version belongs to exactly one Memory.
* Project ownership remains unchanged.

---

# 8. Relationships

A Merge MAY introduce or update relationships between Memories.

Relationship changes MUST NOT modify Memory ownership.

Relationship changes MUST preserve Project boundaries.

---

# 9. Persistence

The result of a successful Merge MUST become part of the Project's persistent knowledge.

Merged knowledge persists independently of:

* AI agent sessions.
* CLI sessions.
* REST requests.
* SDK instances.
* MCP connections.

---

# 10. Invariants

The following conditions MUST always remain true.

* A Merge operates within exactly one Project.
* Project ownership never changes.
* Memory identities remain stable.
* Existing Versions remain immutable.
* Historical knowledge is preserved.
* Every successful Merge produces a consistent Project knowledge state.

---

# 11. Compliance

A Chronicle implementation is compliant with this specification if it:

* Preserves Project boundaries.
* Maintains Memory identities.
* Preserves Version history.
* Prevents history rewriting.
* Produces a consistent Project knowledge state after every successful Merge.

---

# 12. Out of Scope

This specification does not define:

* Merge algorithms.
* Conflict resolution strategies.
* AI decision making.
* Merge prioritization.
* User interaction during merges.
* Source code merging.

These concerns are implementation-specific or defined elsewhere.

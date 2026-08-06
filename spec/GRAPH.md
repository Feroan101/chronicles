# Chronicle Knowledge Graph Specification

Version: 1.0

Status: Draft

---

# 1. Purpose

This specification defines the relationship model within Chronicle.

Chronicle knowledge is not isolated. A Memory may depend on, explain, supersede, or provide context for other Memories inside the same Project. The knowledge graph represents these connections so Chronicle can preserve the context and reasoning behind stored knowledge.

This document defines the requirements, ownership, lifecycle, constraints, and invariants of Memory relationships.

---

# 2. Definition

A Relationship is a directed, typed connection between exactly two Memories belonging to the same Project.

A Relationship expresses how one piece of project knowledge relates to another.

Examples:

* An Architecture Decision may relate to the Constraint that caused it.
* A Bug Memory may relate to the Solution Memory that resolved it.
* A project pattern may relate to the component knowledge where it is applied.

A Relationship is not a Memory and does not store knowledge content itself.

---

# 3. Requirements

A Relationship MUST:

* Connect exactly two Memories.
* Connect only Memories belonging to the same Project.
* Have exactly one direction.
* Have exactly one relationship type.
* Persist independently of AI agent sessions.
* Maintain its identity throughout its lifetime.

A Relationship MUST NOT:

* Connect Memories belonging to different Projects.
* Transfer Memory ownership.
* Replace Memory content.
* Modify the Memories it connects.

---

# 4. Ownership

A Relationship is owned by the Project that owns both connected Memories.

Every Relationship MUST belong to exactly one Project.

A Relationship MUST NOT connect Memories from different Projects.

Relationships do not create new ownership. The connected Memories remain owned by their Project.

---

# 5. Identity

Every Relationship MUST have a stable identity.

The identity uniquely distinguishes the Relationship within its Project.

A Relationship identity MUST remain unchanged throughout the lifetime of the Relationship.

---

# 6. Relationship Type

Every Relationship MUST have exactly one relationship type.

The type describes the nature of the connection between the two Memories.

Examples of relationship types described by the Chronicle architecture include:

* Caused by
* Resolved by
* Applied to
* Updates
* Provides context for
* Supersedes
* Related to

The set of relationship types is defined by the implementation.

An implementation MUST NOT create a Relationship without a type.

---

# 7. Direction

Every Relationship MUST have exactly one source Memory and one target Memory.

The direction is significant.

"A caused B" is not the same as "B caused A."

The direction MUST remain stable for the lifetime of the Relationship.

---

# 8. Versioning

A Relationship is part of the Project's knowledge state.

A change to the set of Relationships within a Project MUST be captured as part of the Project's knowledge history.

Creating, altering, or removing a Relationship MUST NOT modify the Memories it connects.

The history of a Relationship MUST remain accessible.

---

# 9. Relationship to Snapshots

A Snapshot captures the Relationships present in a Project at the time the Snapshot is created.

A Snapshot includes:

* The source and target Memories of each Relationship.
* The relationship type.
* The direction.

Creating, altering, or removing a Relationship after a Snapshot is created MUST NOT modify that Snapshot.

---

# 10. Relationship to Merge

A Merge MAY introduce new Relationships or update existing Relationships.

Relationship changes during a Merge MUST:

* Preserve Project boundaries.
* Preserve Memory ownership.
* Preserve Version history.
* Preserve the invariants defined by this specification.

---

# 11. Relationship to Observations

An Observation MAY relate to existing Memories within the same Project.

When an Observation is processed, relationships MAY be created between new or updated Memories and existing Memories.

Observation-related relationships MUST follow the invariants defined by this specification.

---

# 12. Lifecycle

A Relationship progresses through the following lifecycle.

Created

↓

Included in Snapshots

↓

Altered or Removed (creating history)

A Relationship MAY exist for any number of Snapshots.

A Relationship MUST NOT be modified in place. Changes MUST preserve previous states.

---

# 13. Persistence

A Relationship MUST persist independently of:

* AI agent sessions.
* CLI sessions.
* REST requests.
* SDK instances.
* MCP connections.

The loss of a session MUST NOT imply the loss of a Relationship.

---

# 14. Invariants

The following conditions MUST always remain true.

* Every Relationship connects exactly two Memories.
* Both connected Memories belong to the same Project.
* Every Relationship belongs to exactly one Project.
* Every Relationship has exactly one identity.
* Every Relationship has exactly one type.
* Every Relationship has exactly one direction.
* No Relationship transfers Memory ownership.
* No Relationship replaces Memory content.
* Historical Relationship states remain available.
* No existing Snapshot changes when Relationships change.

---

# 15. Compliance

A Chronicle implementation is compliant with this specification if it:

* Preserves Project boundaries.
* Preserves Memory ownership.
* Maintains Relationship identity.
* Captures Relationships in Snapshots.
* Preserves Relationship history.
* Prevents cross-Project Relationships.
* Prevents direct modification of connected Memories through Relationships.

---

# 16. Out of Scope

This specification does not define:

* Graph database technology.
* Relationship storage format.
* Graph traversal algorithms.
* Automated relationship generation.
* Semantic or LLM-based relationship discovery.
* Graph visualization.

These concerns are implementation-specific or defined by other specifications.

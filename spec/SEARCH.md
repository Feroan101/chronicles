# Chronicle Search Specification

Version: 1.0

Status: Draft

---

# 1. Purpose

This specification defines the behavior of knowledge search within Chronicle.

Chronicle stores reusable project knowledge. Search provides a way for users and AI agents to retrieve stored project understanding without knowing the exact identity of any Memory.

This document defines the requirements, behavior, constraints, and invariants of Search.

---

# 2. Definition

Search is a read-only operation that finds Memories relevant to a query.

Search operates on the stored knowledge of a single Project and returns the Memories that match the query, based on the current knowledge state of that Project.

---

# 3. Requirements

Search MUST:

* Operate within exactly one Project.
* Return Memories belonging to that Project.
* Return the Current Version of each returned Memory.
* Leave stored knowledge unchanged.
* Produce consistent results for identical queries against unchanged knowledge.
* Be exposed through every Chronicle interface with the same behavior.

Search MUST NOT:

* Operate across multiple Projects.
* Modify Memory content.
* Create or delete Memories.
* Create or modify Versions.
* Rewrite history.
* Return knowledge outside the Project boundary.

---

# 4. Project Context

Every search request MUST execute within the context of exactly one Project.

The active Project is determined by the interface context in which the search is invoked.

Search MUST NOT return knowledge belonging to another Project.

---

# 5. Query

A search request contains:

* The query text.
* The Project context.

A query MAY additionally restrict results through:

* Memory type.
* Relationship to a specified Memory.
* Version history constraints.

Query options MUST NOT relax Project boundaries.

---

# 6. Result Behavior

A search returns the Memories that match the query.

Each result MUST include:

* The Memory identity.
* The Memory type.
* The Current Version content.
* The Context of the Current Version.
* Confidence, where available.
* Related Memories, where available.

Search results reflect the current knowledge state of the Project at the time the search is executed.

---

# 7. Matching

Matching is based on the content of Memory Versions.

The exact matching algorithm is implementation-specific.

A compliant implementation MUST:

* Match queries against Memory content.
* Match within the active Project.
* Rank results deterministically.
* Treat identical queries against unchanged knowledge as equivalent.

Matching MUST NOT depend on AI models unless explicitly enabled by the user.

---

# 8. Read-Only Behavior

Search MUST NOT modify stored knowledge.

Search MUST NOT create or destroy any Chronicle object.

Repeated searches against unchanged knowledge MUST produce equivalent results.

---

# 9. Relationship Awareness

Search MAY use relationships to enrich results.

A result MAY include other Memories related to the matched Memory.

Relationship-aware results MUST remain within the Project boundary.

---

# 10. Error Handling

When a search cannot be completed:

* The operation MUST report failure.
* Stored knowledge MUST remain unchanged.
* Chronicle MUST remain in a consistent state.

---

# 11. Consistency

Search MUST expose the same behavior through:

* CLI Interface
* REST Interface
* MCP Interface
* SDK Interface

Changing interfaces MUST NOT change search semantics.

---

# 12. Invariants

The following conditions MUST always remain true.

* Every search operates within exactly one Project.
* Search never modifies stored knowledge.
* Search never violates Project boundaries.
* Search returns the Current Version of matched Memories.
* Identical queries against unchanged knowledge produce equivalent results.
* Chronicle Core remains the single authority for search behavior.

---

# 13. Compliance

A Chronicle implementation is compliant with this specification if it:

* Preserves Project boundaries.
* Leaves stored knowledge unchanged.
* Returns Current Versions.
* Produces deterministic results.
* Implements search behavior consistently across all interfaces.

---

# 14. Out of Scope

This specification does not define:

* Search technology or index implementation.
* Matching algorithms.
* Ranking algorithms.
* Relevance scoring.
* Semantic or vector search.
* Cross-Project search.
* AI-based query understanding.

These concerns are implementation-specific or belong to future versions.

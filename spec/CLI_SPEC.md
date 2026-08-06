# Chronicle Command Line Interface Specification

Version: 1.0

Status: Draft

---

# 1. Purpose

This specification defines the behavior of the Chronicle Command Line Interface (CLI).

The CLI provides a terminal-based interface for interacting with Chronicle Projects and their associated knowledge.

The CLI is one of several interfaces to Chronicle and MUST expose the same underlying behavior as other interfaces.

---

# 2. Definition

The CLI is a human-facing interface that allows users to perform Chronicle operations from a command-line environment.

The CLI communicates with the Chronicle Core and does not directly manage Project storage.

---

# 3. Requirements

A compliant CLI implementation MUST:

* Operate on Chronicle Projects.
* Allow interaction with Chronicle Memories.
* Allow retrieval of stored knowledge.
* Preserve Chronicle's versioned knowledge model.
* Produce deterministic results for identical operations.

A CLI implementation MUST NOT:

* Bypass Chronicle Core.
* Modify storage directly.
* Circumvent Project boundaries.
* Rewrite Version history.

---

# 4. Project Context

Every operation that affects Project knowledge MUST execute within the context of exactly one Project.

The CLI MUST prevent operations that would violate Project ownership.

---

# 5. Memory Operations

The CLI MUST provide access to Chronicle's Memory model.

Supported operations include:

* Creating knowledge.
* Retrieving knowledge.
* Updating knowledge.
* Inspecting historical knowledge.

The CLI MUST preserve the Memory and Versioning specifications during every operation.

---

# 6. Read Operations

Read operations MUST NOT modify Project knowledge.

Repeated retrieval of the same information MUST produce consistent results unless Project knowledge has changed.

---

# 7. Write Operations

Write operations MUST preserve Chronicle invariants.

When updating existing knowledge:

* Existing Versions MUST remain unchanged.
* New knowledge MUST create a new Version when required.
* Project ownership MUST remain unchanged.

---

# 8. Error Handling

When an operation cannot be completed, the CLI MUST:

* Report that the operation failed.
* Preserve existing Project knowledge.
* Leave Chronicle in a consistent state.

Partial modification of Project knowledge MUST NOT occur.

---

# 9. Consistency

The CLI MUST expose the same Chronicle behavior as:

* REST Interface
* MCP Interface
* SDK Interface

Changing interfaces MUST NOT change Chronicle semantics.

---

# 10. Invariants

The following conditions MUST always remain true.

* CLI operations occur within Project boundaries.
* Read operations never modify stored knowledge.
* Write operations preserve Version history.
* Failed operations do not corrupt Project knowledge.
* Chronicle Core remains the single authority for Project behavior.

---

# 11. Compliance

A CLI implementation is compliant with this specification if it:

* Preserves Project ownership.
* Preserves Memory identity.
* Preserves Version history.
* Prevents inconsistent Project states.
* Implements Chronicle behavior consistently with other interfaces.

---

# 12. Out of Scope

This specification does not define:

* Command names.
* Command syntax.
* Command-line flags.
* Output formatting.
* Terminal user experience.
* Shell compatibility.

These concerns are implementation-specific.

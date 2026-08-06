# Chronicle MCP Interface Specification

Version: 1.0

Status: Draft

---

# 1. Purpose

This specification defines the behavior of the Chronicle Model Context Protocol (MCP) Interface.

The MCP Interface enables AI agents to interact with Chronicle's persistent knowledge system through a standardized communication layer.

It provides a consistent mechanism for accessing Project knowledge while preserving Chronicle's core semantics.

---

# 2. Definition

The MCP Interface is the communication layer between AI agents and the Chronicle Core.

It allows agents to retrieve Project knowledge and contribute new knowledge without directly interacting with Chronicle's storage layer.

The MCP Interface is an interface only and does not implement Chronicle's knowledge model.

---

# 3. Requirements

A compliant MCP implementation MUST:

* Operate within the context of exactly one Project.
* Allow retrieval of Project knowledge.
* Allow creation and evolution of Project knowledge.
* Preserve Chronicle Version history.
* Preserve all Project invariants.

An MCP implementation MUST NOT:

* Access storage directly.
* Bypass the Chronicle Core.
* Rewrite Project history.
* Modify existing Versions.
* Violate Project ownership.

---

# 4. Agent Context

Every MCP interaction MUST occur within a single Project.

An AI agent MUST NOT access or modify knowledge belonging to another Project unless explicitly operating within that Project's context.

Project boundaries MUST always be preserved.

---

# 5. Knowledge Retrieval

The MCP Interface MUST allow AI agents to retrieve Project knowledge.

Retrieval operations MUST:

* Leave Project knowledge unchanged.
* Preserve Version history.
* Return knowledge consistent with the current Project state.

Repeated retrieval of unchanged knowledge SHOULD produce equivalent results.

---

# 6. Knowledge Contribution

The MCP Interface MUST allow AI agents to contribute Project knowledge.

Knowledge contribution MAY result in:

* Creation of a new Memory.
* Creation of a new Version for an existing Memory.
* No change to Project knowledge.

Knowledge contributions MUST follow the Memory, Observation, Merge, and Versioning specifications.

---

# 7. Error Handling

If an MCP operation cannot be completed:

* Existing Project knowledge MUST remain unchanged.
* Partial updates MUST NOT occur.
* Chronicle MUST remain in a consistent state.

The failure of one operation MUST NOT compromise subsequent operations.

---

# 8. Consistency

The MCP Interface MUST expose the same Chronicle behavior as:

* CLI Interface
* REST Interface
* SDK Interface

Changing interfaces MUST NOT change Chronicle semantics.

All interfaces operate on the same underlying Project knowledge model.

---

# 9. Invariants

The following conditions MUST always remain true.

* Every MCP operation occurs within a single Project.
* Retrieval operations never modify Project knowledge.
* Knowledge updates preserve Version history.
* Existing Versions remain immutable.
* Failed operations leave Project knowledge unchanged.
* Chronicle Core remains the single authority for Project behavior.

---

# 10. Compliance

An MCP implementation is compliant with this specification if it:

* Preserves Project ownership.
* Preserves Memory identity.
* Preserves Version history.
* Maintains Project consistency.
* Implements Chronicle behavior consistently with all other interfaces.

---

# 11. Out of Scope

This specification does not define:

* MCP tool names.
* MCP message formats.
* MCP transport protocols.
* AI model behavior.
* Prompt design.
* Agent orchestration.
* Authentication or authorization.

These concerns are implementation-specific or defined by the Model Context Protocol itself.

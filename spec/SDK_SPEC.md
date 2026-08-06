# Chronicle SDK Specification

Version: 1.0

Status: Draft

---

# 1. Purpose

This specification defines the behavior of the Chronicle Software Development Kit (SDK).

The SDK provides a programmatic interface for applications and AI systems to interact with Chronicle.

It enables developers to integrate Chronicle into software while preserving the behavior defined by the Chronicle specifications.

---

# 2. Definition

The SDK is a developer-facing interface to the Chronicle Core.

It exposes Chronicle functionality through a programming interface without exposing internal implementation details.

The SDK is an interface only and does not implement Chronicle's knowledge model.

---

# 3. Requirements

A compliant SDK implementation MUST:

* Operate within the context of exactly one Project.
* Allow retrieval of Project knowledge.
* Allow creation and evolution of Project knowledge.
* Preserve Chronicle Version history.
* Preserve all Chronicle invariants.

An SDK implementation MUST NOT:

* Access storage directly.
* Bypass the Chronicle Core.
* Rewrite Project history.
* Modify existing Versions.
* Violate Project ownership.

---

# 4. Project Context

Every SDK operation MUST execute within the context of exactly one Project.

Operations attempting to access knowledge outside the active Project MUST be rejected.

Project ownership MUST always be preserved.

---

# 5. Knowledge Retrieval

The SDK MUST provide access to Project knowledge.

Retrieval operations MUST:

* Leave Project knowledge unchanged.
* Preserve Version history.
* Return knowledge consistent with the current Project state.

Repeated retrieval of unchanged knowledge SHOULD produce equivalent results.

---

# 6. Knowledge Modification

The SDK MUST support operations that contribute to Project knowledge.

Knowledge modification MAY result in:

* Creation of a new Memory.
* Creation of a new Version.
* No change to the Project.

All modifications MUST comply with the Memory, Observation, Merge, and Versioning specifications.

---

# 7. Error Handling

If an SDK operation fails:

* Existing Project knowledge MUST remain unchanged.
* Partial modifications MUST NOT occur.
* Chronicle MUST remain in a consistent state.

Errors MUST NOT compromise future operations.

---

# 8. Consistency

The SDK MUST expose the same Chronicle behavior as:

* CLI Interface
* REST Interface
* MCP Interface

Changing interfaces MUST NOT change Chronicle semantics.

All interfaces interact with the same Chronicle Core and Project knowledge model.

---

# 9. Invariants

The following conditions MUST always remain true.

* Every SDK operation occurs within a single Project.
* Retrieval operations never modify Project knowledge.
* Knowledge updates preserve Version history.
* Existing Versions remain immutable.
* Failed operations leave Project knowledge unchanged.
* Chronicle Core remains the single authority for Project behavior.

---

# 10. Compliance

An SDK implementation is compliant with this specification if it:

* Preserves Project ownership.
* Preserves Memory identity.
* Preserves Version history.
* Maintains Project consistency.
* Implements Chronicle behavior consistently with all other Chronicle interfaces.

---

# 11. Out of Scope

This specification does not define:

* Programming languages.
* Public class or function names.
* Package structure.
* Dependency management.
* Language-specific APIs.
* Authentication or authorization.
* Distribution mechanisms.

These concerns are implementation-specific.

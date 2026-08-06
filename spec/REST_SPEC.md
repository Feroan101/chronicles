# Chronicle REST Interface Specification

Version: 1.0

Status: Draft

---

# 1. Purpose

This specification defines the behavior of the Chronicle REST Interface.

The REST Interface provides HTTP-based access to Chronicle Projects and their associated knowledge.

It enables applications and services to interact with Chronicle using a consistent request and response model.

---

# 2. Definition

The REST Interface is an external communication layer for Chronicle.

It forwards requests to the Chronicle Core and returns the resulting responses.

The REST Interface does not implement Chronicle's knowledge model.

---

# 3. Requirements

A compliant REST implementation MUST:

* Operate on Chronicle Projects.
* Provide access to Chronicle Memories.
* Preserve Chronicle Version history.
* Return deterministic results for identical requests.
* Preserve Chronicle invariants.

A REST implementation MUST NOT:

* Modify storage directly.
* Bypass Chronicle Core.
* Rewrite Version history.
* Violate Project ownership.

---

# 4. Resource Context

Every request affecting Chronicle knowledge MUST execute within the context of exactly one Project.

Requests attempting to operate across multiple Projects MUST be rejected.

---

# 5. Read Operations

Read operations MUST:

* Retrieve existing Project knowledge.
* Preserve Version history.
* Leave stored knowledge unchanged.

Repeated requests for unchanged knowledge SHOULD return equivalent results.

---

# 6. Write Operations

Write operations MAY:

* Create new Memories.
* Create new Versions.
* Update Project knowledge.

Write operations MUST:

* Preserve Project ownership.
* Preserve Version history.
* Maintain Project consistency.

---

# 7. Responses

Every completed request MUST produce exactly one response.

A response MUST represent either:

* Successful completion.
* Failed execution.

Responses MUST accurately reflect the resulting Project state.

---

# 8. Error Handling

When a request fails:

* Existing Project knowledge MUST remain unchanged.
* Partial updates MUST NOT occur.
* Chronicle MUST remain in a consistent state.

---

# 9. Consistency

The REST Interface MUST expose the same Chronicle behavior as:

* CLI Interface
* MCP Interface
* SDK Interface

Changing interfaces MUST NOT change Chronicle semantics.

---

# 10. Invariants

The following conditions MUST always remain true.

* Requests operate within Project boundaries.
* Read requests never modify Project knowledge.
* Write requests preserve Version history.
* Failed requests do not corrupt Project knowledge.
* Chronicle Core remains the single authority for Project behavior.

---

# 11. Compliance

A REST implementation is compliant with this specification if it:

* Preserves Project ownership.
* Preserves Memory identity.
* Preserves Version history.
* Maintains Project consistency.
* Implements Chronicle behavior consistently with all other interfaces.

---

# 12. Out of Scope

This specification does not define:

* HTTP endpoints.
* HTTP methods.
* JSON schemas.
* Authentication.
* Authorization.
* Rate limiting.
* Transport security.

These concerns are implementation-specific or defined by deployment requirements.

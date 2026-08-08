# Contributing to Chronicle

Thank you for contributing to Chronicle.

Chronicle is a local-first shared memory layer for AI software engineering. The project prioritizes a simple architecture, explicit behavior, and maintainable components over unnecessary complexity.

## Before Contributing

Please read the project documentation before making architectural changes.

The authoritative project documents are:

* `docs/`
* `spec/`
* `TECH_STACK.md`

These documents define the intended behavior and architecture of Chronicle.

The `.idea/` directory is not authoritative for implementation decisions.

If the specifications and implementation disagree, do not silently choose an implementation. Open an issue or discussion describing the conflict before making architectural changes.

## Development Setup

Chronicle uses Python 3.13+ and `uv`.

Clone the repository and install the development environment:

```text
uv sync
```

Run the test suite:

```text
uv run pytest
```

Run linting:

```text
uv run ruff check .
```

Check formatting:

```text
uv run ruff format --check .
```

Apply formatting:

```text
uv run ruff format .
```

Run all checks before submitting a change:

```text
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Project Architecture

Chronicle follows a layered architecture:

```text
Interfaces
    ↓
Chronicle Core
    ↓
Repositories
    ↓
SQLAlchemy
    ↓
SQLite
```

Interfaces such as the CLI, REST API, and MCP layer should remain thin adapters.

Business behavior belongs in Chronicle Core.

Database access belongs in repositories.

Do not place business logic inside CLI commands, REST handlers, MCP handlers, or database models.

## Making Changes

Before implementing a new capability:

1. Check the existing specifications.
2. Check whether the capability already has an approved design.
3. Determine which architectural layer owns the behavior.
4. Add or update tests.
5. Implement the smallest solution that satisfies the specification.
6. Run the full verification suite.

Do not introduce new dependencies unless they provide clear value and are consistent with `TECH_STACK.md`.

Avoid adding abstractions solely for theoretical future requirements.

## Specifications Come First

Chronicle is intentionally spec-driven.

If an implementation requires a behavior that is not defined by the specifications and the decision materially affects the architecture or public behavior, stop and ask for clarification rather than inventing a new rule.

Small implementation details may use reasonable engineering judgment when they do not alter public behavior or architectural boundaries.

## Database Changes

Database schema changes must use Alembic migrations.

Do not modify an existing migration after it has been applied or released.

Create a new migration for schema changes.

Verify migrations with:

```text
uv run alembic upgrade head
uv run alembic check
```

SQLite remains the V1 storage engine.

## Tests

Every behavioral change should include appropriate tests.

Tests should:

* be deterministic
* avoid depending on the developer's local database
* use isolated temporary databases where appropriate
* cover both successful and failure paths
* preserve existing behavior

Do not weaken or remove existing tests merely to make a change pass.

## Code Quality

Chronicle uses Ruff for linting and formatting.

Keep code readable and explicit.

Prefer the simplest implementation that satisfies the specification.

Avoid unnecessary frameworks, dependencies, abstractions, and indirection.

## Pull Requests

Pull requests should clearly explain:

* what changed
* why it changed
* which specification or requirement it implements
* how it was tested
* any architectural decisions or assumptions

Keep pull requests focused.

Do not combine unrelated refactors with feature work unless the refactor is required for the feature.

If a change intentionally deviates from an existing specification, explain why and obtain approval before implementation.

## Commit Messages

Use concise commit messages that describe the change.

Examples:

```text
feat: add memory search
fix: handle invalid search queries
test: cover version ordering
docs: clarify memory lifecycle
refactor: simplify repository transaction handling
```

Do not use commits to hide unrelated changes.

## Reporting Issues

When reporting a bug, include:

* what you expected
* what actually happened
* steps to reproduce
* relevant command output
* Python version
* Chronicle version or commit
* operating system, when relevant

For architectural or specification questions, explain the ambiguity rather than proposing an implementation as though it were already approved.

## Pull Request Checklist

Before opening a pull request, verify:

* [ ] The change follows the authoritative specifications.
* [ ] Tests have been added or updated where necessary.
* [ ] `uv run pytest` passes.
* [ ] `uv run ruff check .` passes.
* [ ] `uv run ruff format --check .` passes.
* [ ] Database changes have an Alembic migration.
* [ ] No unrelated changes are included.
* [ ] Documentation has been updated when behavior or architecture changes.
* [ ] Assumptions and specification gaps are documented.

## Code of Conduct

Please be respectful and constructive when participating in the project.

Technical disagreement is expected and welcome. Keep discussions focused on the problem, evidence, and proposed solution.

## License

By contributing to Chronicle, you agree that your contributions will be licensed under the MIT License included in this repository.


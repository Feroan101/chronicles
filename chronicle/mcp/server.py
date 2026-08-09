from pathlib import Path

from mcp.server.fastmcp import FastMCP
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from chronicle.api.schemas import (
    BranchKnowledgeRead,
    BranchRead,
    ConfidenceRead,
    DecayAssessmentRead,
    DecayReportRead,
    DriftAffectedKnowledgeRead,
    DriftReportRead,
    EvidenceRead,
    MemoryRead,
    MemorySummaryRead,
    MemoryVersionRead,
    ObservationRead,
    ProjectRead,
    RelationshipRead,
    SearchHitRead,
    SnapshotRead,
    VerificationReportRead,
    VerificationResultRead,
)
from chronicle.core import (
    BranchNotFoundError,
    ChronicleEngine,
    GitContext,
    MemoryNotFoundError,
    ProjectNotFoundError,
    SnapshotNotFoundError,
)

DEFAULT_DB_PATH = Path(".chronicle") / "chronicle.db"


def default_session_factory() -> sessionmaker[Session]:
    database = create_engine(f"sqlite:///{DEFAULT_DB_PATH}")
    return sessionmaker(bind=database)


def _project(project) -> dict:
    return ProjectRead.model_validate(project).model_dump(mode="json")


def _branch(branch) -> dict:
    return BranchRead.model_validate(branch).model_dump(mode="json")


def _memory(memory) -> dict:
    return MemoryRead.model_validate(memory).model_dump(mode="json")


def _version(version) -> dict:
    return MemoryVersionRead.model_validate(version).model_dump(mode="json")


def _search_hit(result) -> dict:
    return SearchHitRead(
        memory=MemorySummaryRead.model_validate(result.memory),
        version=MemoryVersionRead.model_validate(result.version),
        rank=result.rank,
    ).model_dump(mode="json")


def _observation(observation) -> dict:
    return ObservationRead.model_validate(observation).model_dump(mode="json")


def _relationship(relationship) -> dict:
    return RelationshipRead.model_validate(relationship).model_dump(mode="json")


def _snapshot(snapshot) -> dict:
    return SnapshotRead.model_validate(snapshot).model_dump(mode="json")


def _branch_knowledge(item) -> dict:
    return BranchKnowledgeRead(
        memory=MemorySummaryRead.model_validate(item.memory),
        version=MemoryVersionRead.model_validate(item.version),
    ).model_dump(mode="json")


def _confidence(score) -> dict | None:
    if score is None:
        return None
    return ConfidenceRead.model_validate(score).model_dump(mode="json")


def create_mcp_server(session_factory: sessionmaker[Session] | None = None) -> FastMCP:
    """Build a Chronicle MCP server.

    The engine is constructed once from a session factory and captured by the
    registered tools. Tool handlers never touch SQLAlchemy directly; they
    delegate exclusively to ``ChronicleEngine``. The tool set and output
    shapes mirror the Chronicle REST API.
    """
    engine = ChronicleEngine(session_factory or default_session_factory())
    server = FastMCP(
        "chronicle",
        instructions=(
            "Chronicle is a shared memory layer for AI software engineering. "
            "Use projects to group related knowledge, memories to hold "
            "knowledge that evolves over time, and versions to track each "
            "knowledge change. Search retrieves the current knowledge across "
            "projects."
        ),
    )

    @server.tool()
    def create_project(name: str, description: str | None = None) -> dict:
        """Create a new project.

        Args:
            name: The project name.
            description: An optional project description.
        """
        return _project(engine.create_project(name=name, description=description))

    @server.tool()
    def get_project(project_id: str) -> dict:
        """Get a project by ID.

        Args:
            project_id: The project ID.
        """
        project = engine.get_project(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)
        return _project(project)

    # ------------------------------------------------------------------
    # Branch tools
    # ------------------------------------------------------------------

    @server.tool()
    def create_branch(
        project_id: str, name: str, source_branch_id: str | None = None
    ) -> dict:
        """Create a new branch in a project.

        Branches hold independent lines of knowledge. New branches start from
        the project's current branch unless ``source_branch_id`` is given.

        Args:
            project_id: The project ID.
            name: The branch name (a valid identifier).
            source_branch_id: Optional branch ID to fork from.
        """
        return _branch(
            engine.create_branch(
                project_id=project_id, name=name, source_branch_id=source_branch_id
            )
        )

    @server.tool()
    def list_branches(project_id: str) -> list:
        """List all branches in a project.

        Args:
            project_id: The project ID.
        """
        return [_branch(branch) for branch in engine.list_branches(project_id)]

    @server.tool()
    def get_branch(branch_id: str) -> dict:
        """Get a branch by ID.

        Args:
            branch_id: The branch ID.
        """
        branch = engine.get_branch(branch_id)
        if branch is None:
            raise BranchNotFoundError(branch_id)
        return _branch(branch)

    @server.tool()
    def get_current_branch(project_id: str) -> dict:
        """Get the currently active branch of a project.

        Args:
            project_id: The project ID.
        """
        return _branch(engine.get_current_branch(project_id))

    @server.tool()
    def switch_branch(project_id: str, name: str) -> dict:
        """Activate a branch in a project.

        All subsequent writes and reads for the project use the active branch.

        Args:
            project_id: The project ID.
            name: The branch name to activate.
        """
        return _branch(engine.switch_branch(project_id=project_id, name=name))

    @server.tool()
    def get_branch_knowledge(branch_id: str) -> list:
        """Get the knowledge visible from a branch.

        Returns the current version of every memory that belongs to the branch
        or was created before the branch forked.

        Args:
            branch_id: The branch ID.
        """
        return [_branch_knowledge(item) for item in engine.get_branch_knowledge(branch_id)]

    @server.tool()
    def create_memory(
        project_id: str,
        content: str,
        type: str | None = None,
        context: str | None = None,
        git_branch: str | None = None,
        git_commit: str | None = None,
        git_description: str | None = None,
        branch_id: str | None = None,
    ) -> dict:
        """Store a new memory in a project.

        The initial version holds ``content``.

        Args:
            project_id: The project ID the memory belongs to.
            content: The knowledge to store.
            type: An optional memory type, e.g. "decision".
            context: Optional context about when this knowledge applies.
            git_branch: Optional Git branch name.
            git_commit: Optional Git commit hash.
            git_description: Optional description of the Git change.
            branch_id: Optional chronicle branch ID to write to; defaults to
                the project's current branch.
        """
        git_ctx = None
        if any([git_branch, git_commit, git_description]):
            git_ctx = GitContext(branch=git_branch, commit=git_commit, description=git_description)
        return _memory(
            engine.create_memory(
                project_id=project_id,
                content=content,
                type=type,
                context=context,
                git_context=git_ctx,
                branch_id=branch_id,
            )
        )

    @server.tool()
    def get_memory(memory_id: str) -> dict:
        """Get a memory and its version history by ID.

        Args:
            memory_id: The memory ID.
        """
        memory = engine.get_memory(memory_id)
        if memory is None:
            raise MemoryNotFoundError(memory_id)
        return _memory(memory)

    @server.tool()
    def list_memories(project_id: str, branch_id: str | None = None) -> list:
        """List all memories in a project, ordered by creation.

        Args:
            project_id: The project ID.
            branch_id: Optional branch ID to scope the list to; defaults to
                the project's current branch.
        """
        return [_memory(memory) for memory in engine.list_memories(project_id, branch_id=branch_id)]

    @server.tool()
    def update_memory(memory_id: str, type: str | None = None) -> dict:
        """Update the type of a memory.

        Passing ``type`` as null or omitting it leaves the memory unchanged.

        Args:
            memory_id: The memory ID.
            type: The new memory type, or null to keep the current type.
        """
        if type is None:
            memory = engine.get_memory(memory_id)
            if memory is None:
                raise MemoryNotFoundError(memory_id)
            return _memory(memory)
        return _memory(engine.update_memory(memory_id=memory_id, type=type))

    @server.tool()
    def create_version(
        memory_id: str,
        content: str,
        context: str | None = None,
        git_branch: str | None = None,
        git_commit: str | None = None,
        git_description: str | None = None,
        branch_id: str | None = None,
    ) -> dict:
        """Append a new version of a memory.

        Args:
            memory_id: The memory ID to extend.
            content: The updated knowledge.
            context: Optional context about when this knowledge applies.
            git_branch: Optional Git branch name.
            git_commit: Optional Git commit hash.
            git_description: Optional description of the Git change.
            branch_id: Optional chronicle branch ID to write to; defaults to
                the branch the memory is currently on.
        """
        git_ctx = None
        if any([git_branch, git_commit, git_description]):
            git_ctx = GitContext(branch=git_branch, commit=git_commit, description=git_description)
        return _version(
            engine.create_version(
                memory_id=memory_id,
                content=content,
                context=context,
                git_context=git_ctx,
                branch_id=branch_id,
            )
        )

    @server.tool()
    def get_evidence(memory_id: str, sequence: int) -> list:
        """Get evidence attached to a specific version.

        Args:
            memory_id: The memory ID.
            sequence: The version sequence number.
        """
        evidence = engine.get_evidence(memory_id=memory_id, sequence=sequence)
        return [EvidenceRead.model_validate(e).model_dump(mode="json") for e in evidence]

    @server.tool()
    def search(
        query: str, project_id: str | None = None, branch_id: str | None = None
    ) -> list:
        """Search project knowledge.

        Only the current version of each memory is returned, and each memory
        appears at most once.

        Args:
            query: The search terms.
            project_id: Restrict results to a project, or null to search all.
            branch_id: Restrict results to a branch, or null to search the
                project's current branch.
        """
        return [
            _search_hit(result)
            for result in engine.search(query=query, project_id=project_id, branch_id=branch_id)
        ]

    # ------------------------------------------------------------------
    # Observation tools
    # ------------------------------------------------------------------

    @server.tool()
    def create_observation(project_id: str, content: str) -> dict:
        """Create a pending observation in a project.

        Args:
            project_id: The project ID.
            content: The observed information.
        """
        return _observation(engine.create_observation(project_id=project_id, content=content))

    @server.tool()
    def list_observations(project_id: str) -> list:
        """List all observations in a project, ordered by creation.

        Args:
            project_id: The project ID.
        """
        return [_observation(obs) for obs in engine.list_observations(project_id)]

    @server.tool()
    def process_observation(observation_id: str, action: str, memory_id: str | None = None) -> dict:
        """Process an observation into knowledge or discard it.

        Actions:
        - "create_memory": creates a new memory from the observation content.
        - "update_memory": appends a new version to an existing memory
          (memory_id is required).
        - "discard": marks the observation as discarded with no knowledge change.

        Args:
            observation_id: The observation ID.
            action: The processing action.
            memory_id: Required for "update_memory" action.
        """
        return _observation(
            engine.process_observation(
                observation_id=observation_id,
                action=action,
                memory_id=memory_id,
            )
        )

    # ------------------------------------------------------------------
    # Relationship tools
    # ------------------------------------------------------------------

    @server.tool()
    def create_relationship(
        project_id: str, from_memory_id: str, to_memory_id: str, type: str
    ) -> dict:
        """Create a directed relationship between two memories.

        Args:
            project_id: The project ID.
            from_memory_id: The source memory ID.
            to_memory_id: The target memory ID.
            type: The relationship type (e.g. "caused_by", "resolved_by").
        """
        return _relationship(
            engine.create_relationship(
                project_id=project_id,
                from_memory_id=from_memory_id,
                to_memory_id=to_memory_id,
                type=type,
            )
        )

    @server.tool()
    def list_relationships(project_id: str) -> list:
        """List all relationships in a project, ordered by creation.

        Args:
            project_id: The project ID.
        """
        return [_relationship(rel) for rel in engine.list_relationships(project_id)]

    @server.tool()
    def get_relationships_for_memory(memory_id: str) -> list:
        """Get all relationships where a memory is source or target.

        Args:
            memory_id: The memory ID.
        """
        return [_relationship(rel) for rel in engine.get_relationships_for_memory(memory_id)]

    @server.tool()
    def remove_relationship(relationship_id: str) -> None:
        """Remove a relationship.

        Args:
            relationship_id: The relationship ID.
        """
        engine.remove_relationship(relationship_id)

    # ------------------------------------------------------------------
    # Snapshot tools
    # ------------------------------------------------------------------

    @server.tool()
    def create_snapshot(
        project_id: str, message: str | None = None, branch_id: str | None = None
    ) -> dict:
        """Create a snapshot of the project's current knowledge state.

        Args:
            project_id: The project ID to snapshot.
            message: An optional message describing the snapshot.
            branch_id: Optional branch ID to snapshot; defaults to the
                project's current branch.
        """
        return _snapshot(
            engine.create_snapshot(project_id=project_id, message=message, branch_id=branch_id)
        )

    @server.tool()
    def get_snapshot(snapshot_id: str) -> dict:
        """Get a snapshot by ID.

        Args:
            snapshot_id: The snapshot ID.
        """
        snapshot = engine.get_snapshot(snapshot_id)
        if snapshot is None:
            raise SnapshotNotFoundError(snapshot_id)
        return _snapshot(snapshot)

    @server.tool()
    def list_snapshots(project_id: str, branch_id: str | None = None) -> list:
        """List all snapshots for a project.

        Args:
            project_id: The project ID.
            branch_id: Optional branch ID to scope the list to; defaults to
                the project's current branch.
        """
        return [
            _snapshot(snapshot)
            for snapshot in engine.list_snapshots(project_id, branch_id=branch_id)
        ]

    # ------------------------------------------------------------------
    # Confidence tools
    # ------------------------------------------------------------------

    @server.tool()
    def record_confidence(
        memory_id: str, sequence: int, score: float, reason: str | None = None
    ) -> dict:
        """Record a confidence score for a specific memory version.

        Scores must be between 0.0 and 1.0 inclusive.

        Args:
            memory_id: The memory ID.
            sequence: The version sequence number.
            score: Confidence score (0.0 to 1.0).
            reason: Optional reason for the score.
        """
        return _confidence(
            engine.record_confidence(
                memory_id=memory_id, sequence=sequence, score=score, reason=reason
            )
        )

    @server.tool()
    def get_confidence(memory_id: str, sequence: int) -> dict:
        """Get the current confidence score for a memory version.

        Returns an empty object if no confidence has been recorded.

        Args:
            memory_id: The memory ID.
            sequence: The version sequence number.
        """
        score = engine.get_confidence(memory_id=memory_id, sequence=sequence)
        if score is None:
            return {}
        return ConfidenceRead.model_validate(score).model_dump(mode="json")

    @server.tool()
    def get_confidence_history(memory_id: str, sequence: int) -> list:
        """Get the full confidence history for a memory version.

        Args:
            memory_id: The memory ID.
            sequence: The version sequence number.
        """
        return [
            ConfidenceRead.model_validate(s).model_dump(mode="json")
            for s in engine.get_confidence_history(memory_id=memory_id, sequence=sequence)
        ]

    # ------------------------------------------------------------------
    # Verification tools
    # ------------------------------------------------------------------

    @server.tool()
    def verify_project(project_id: str) -> dict:
        """Verify all knowledge in a project.

        Checks version integrity, traceability, and relationship consistency.

        Args:
            project_id: The project ID.
        """
        report = engine.verify_project(project_id=project_id)
        return VerificationReportRead(
            scope=report.scope,
            scope_id=report.scope_id,
            results=[
                VerificationResultRead(check=r.check, outcome=r.outcome, message=r.message)
                for r in report.results
            ],
            passed=report.passed,
            has_failures=report.has_failures,
        ).model_dump(mode="json")

    @server.tool()
    def verify_memory(memory_id: str) -> dict:
        """Verify a single memory and its relationships.

        Args:
            memory_id: The memory ID.
        """
        report = engine.verify_memory(memory_id=memory_id)
        return VerificationReportRead(
            scope=report.scope,
            scope_id=report.scope_id,
            results=[
                VerificationResultRead(check=r.check, outcome=r.outcome, message=r.message)
                for r in report.results
            ],
            passed=report.passed,
            has_failures=report.has_failures,
        ).model_dump(mode="json")

    @server.tool()
    def verify_version(memory_id: str, sequence: int) -> dict:
        """Verify a single memory version against its available evidence.

        Args:
            memory_id: The memory ID.
            sequence: The version sequence number.
        """
        report = engine.verify_version(memory_id=memory_id, sequence=sequence)
        return VerificationReportRead(
            scope=report.scope,
            scope_id=report.scope_id,
            results=[
                VerificationResultRead(check=r.check, outcome=r.outcome, message=r.message)
                for r in report.results
            ],
            passed=report.passed,
            has_failures=report.has_failures,
        ).model_dump(mode="json")

    @server.tool()
    def verify_snapshot(snapshot_id: str) -> dict:
        """Verify a snapshot's captured state against current knowledge.

        Args:
            snapshot_id: The snapshot ID.
        """
        report = engine.verify_snapshot(snapshot_id=snapshot_id)
        return VerificationReportRead(
            scope=report.scope,
            scope_id=report.scope_id,
            results=[
                VerificationResultRead(check=r.check, outcome=r.outcome, message=r.message)
                for r in report.results
            ],
            passed=report.passed,
            has_failures=report.has_failures,
        ).model_dump(mode="json")

    # ------------------------------------------------------------------
    # Drift detection tools
    # ------------------------------------------------------------------

    @server.tool()
    def detect_drift(project_id: str, repo_path: str | None = None) -> dict:
        """Detect whether a project's knowledge may have drifted.

        Compares the current Git state against the evidence recorded for the
        project's knowledge. Read-only; never modifies knowledge.

        Args:
            project_id: The project ID.
            repo_path: Optional path to the Git repository to check.
        """
        report = engine.detect_drift(project_id=project_id, repo_path=repo_path)
        return DriftReportRead(
            project_id=report.project_id,
            state=report.state,
            changed_artifacts=report.changed_artifacts,
            affected_knowledge=[
                DriftAffectedKnowledgeRead(
                    memory_id=k.memory_id,
                    sequence=k.sequence,
                    content=k.content,
                    reason=k.reason,
                )
                for k in report.affected_knowledge
            ],
            reasons=report.reasons,
        ).model_dump(mode="json")

    # ------------------------------------------------------------------
    # Memory decay tools
    # ------------------------------------------------------------------

    @server.tool()
    def assess_decay(project_id: str) -> dict:
        """Assess the freshness (decay) of a project's knowledge.

        Scores each memory's current version by how long ago it was updated.
        A version is "fresh", "aging", or "stale". Read-only; never modifies
        knowledge, confidence, or verification state.

        Args:
            project_id: The project ID.
        """
        report = engine.assess_decay(project_id=project_id)
        return DecayReportRead(
            project_id=report.project_id,
            assessments=[
                DecayAssessmentRead(
                    memory_id=assessment.memory_id,
                    sequence=assessment.sequence,
                    content=assessment.content,
                    state=assessment.state,
                    freshness=assessment.freshness,
                    age_days=assessment.age_days,
                    created_at=assessment.created_at,
                )
                for assessment in report.assessments
            ],
            generated_at=report.generated_at,
            fresh_days=report.fresh_days,
            stale_days=report.stale_days,
            stale_count=report.stale_count,
        ).model_dump(mode="json")

    return server


mcp = create_mcp_server()


def main() -> None:
    """Run the Chronicle MCP server over stdio."""
    mcp.run()

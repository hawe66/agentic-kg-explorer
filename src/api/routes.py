"""FastAPI route handlers."""

from fastapi import APIRouter, HTTPException

from config.settings import get_settings, reset_settings
from src.agents import run_agent
from src.graph.client import Neo4jClient
from src.retrieval.vector_store import get_vector_store

from .schemas import (
    HealthResponse,
    PrincipleItem,
    PrinciplesResponse,
    QueryRequest,
    QueryResponse,
    SourceItem,
    StatsResponse,
    VectorResultItem,
    WebResultItem,
    KgResultItem,
    ProposeNodeRequest,
    ProposedNodeResponse,
    ApproveNodeRequest,
    ApproveNodeResponse,
    # Optimizer schemas
    AnalyzeRequest,
    ApproveHypothesesRequest,
    TestVariantsRequest,
    ActivateVersionRequest,
    RollbackRequest,
    FailurePatternItem,
    FailurePatternsResponse,
    PromptVariantItem,
    GenerateVariantsResponse,
    TestResultItem,
    TestResultsResponse,
    PromptVersionItem,
    VersionHistoryResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_neo4j_client() -> Neo4jClient:
    settings = get_settings()
    client = Neo4jClient(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )
    client.connect()
    return client


# ---------------------------------------------------------------------------
# POST /query
# ---------------------------------------------------------------------------

@router.post("/query", response_model=QueryResponse)
def query_agent(request: QueryRequest):
    """Run the agent pipeline on a user query."""

    # Apply provider/model overrides if given
    overridden = False
    settings = get_settings()
    original_provider = settings.llm_provider
    original_model = settings.llm_model

    if request.llm_provider and request.llm_provider != "string":
        settings.llm_provider = request.llm_provider
        overridden = True
    if request.llm_model and request.llm_model != "string":
        settings.llm_model = request.llm_model
        overridden = True

    try:
        result = run_agent(request.query)
    finally:
        # Restore original settings
        if overridden:
            settings.llm_provider = original_provider
            settings.llm_model = original_model

    return QueryResponse(
        answer=result.get("answer"),
        intent=result.get("intent"),
        entities=result.get("entities") or [],
        confidence=result.get("confidence"),
        sources=[
            SourceItem(**s) for s in (result.get("sources") or [])
        ],
        vector_results=[
            VectorResultItem(**v) for v in (result.get("vector_results") or [])
        ],
        web_results=[
            WebResultItem(**w) for w in (result.get("web_results") or [])
        ],
        web_query=result.get("web_query"),
        cypher_executed=result.get("cypher_executed") or [],
        kg_results=[
            KgResultItem(**k) for k in (result.get("kg_results") or [])
        ],
        error=result.get("error"),
    )


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
def health_check():
    """Check service health: Neo4j connectivity and ChromaDB status."""
    neo4j_ok = False
    try:
        client = _get_neo4j_client()
        client.close()
        neo4j_ok = True
    except Exception:
        pass

    chroma_count = 0
    try:
        store = get_vector_store()
        chroma_count = store.count
    except Exception:
        pass

    return HealthResponse(
        status="ok" if neo4j_ok else "degraded",
        neo4j=neo4j_ok,
        chromadb_entries=chroma_count,
    )


# ---------------------------------------------------------------------------
# GET /stats
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=StatsResponse)
def get_stats():
    """Get Neo4j database statistics."""
    try:
        client = _get_neo4j_client()
        stats = client.get_stats()
        client.close()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Neo4j unavailable: {e}")

    return StatsResponse(
        total_nodes=stats.total_nodes,
        total_relationships=stats.total_relationships,
        nodes_by_label=stats.nodes_by_label,
        relationships_by_type=stats.relationships_by_type,
    )


# ---------------------------------------------------------------------------
# GET /graph/principles
# ---------------------------------------------------------------------------

@router.get("/graph/principles", response_model=PrinciplesResponse)
def get_principles():
    """List all 11 principles with method and implementation counts."""
    try:
        client = _get_neo4j_client()
        # Custom query that returns id, name, description, counts
        rows = client.run_cypher("""
            MATCH (p:Principle)
            OPTIONAL MATCH (p)<-[:ADDRESSES]-(m:Method)
            OPTIONAL MATCH (m)<-[:IMPLEMENTS]-(i:Implementation)
            RETURN p.id AS id, p.name AS name, p.description AS description,
                   count(DISTINCT m) AS method_count,
                   count(DISTINCT i) AS impl_count
            ORDER BY p.name
        """)
        client.close()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Neo4j unavailable: {e}")

    principles = [
        PrincipleItem(
            id=row["id"],
            name=row["name"],
            description=row.get("description") or "",
            method_count=row["method_count"],
            impl_count=row["impl_count"],
        )
        for row in rows
    ]

    return PrinciplesResponse(principles=principles)


# ---------------------------------------------------------------------------
# POST /graph/nodes/propose
# ---------------------------------------------------------------------------

@router.post("/graph/nodes/propose", response_model=ProposedNodeResponse)
def propose_node(request: ProposeNodeRequest):
    """Use LLM to extract a KG node proposal from web content.

    This is step 1 of adding web content to the KG.
    The response can be reviewed and modified before approval.
    """
    from .kg_writer import propose_node as _propose_node, WebResult

    web_result = WebResult(
        title=request.title,
        url=request.url,
        content=request.content,
    )

    proposed = _propose_node(web_result)

    if proposed is None:
        raise HTTPException(
            status_code=422,
            detail="Could not extract entity from web content",
        )

    return ProposedNodeResponse(
        node_type=proposed.node_type,
        node_id=proposed.node_id,
        name=proposed.name,
        description=proposed.description,
        method_family=proposed.method_family,
        method_type=proposed.method_type,
        granularity=proposed.granularity,
        addresses=proposed.addresses,
        impl_type=proposed.impl_type,
        maintainer=proposed.maintainer,
        source_repo=proposed.source_repo,
        implements=proposed.implements,
        doc_type=proposed.doc_type,
        authors=proposed.authors,
        year=proposed.year,
        venue=proposed.venue,
        proposes=proposed.proposes,
        source_url=proposed.source_url,
        confidence=proposed.confidence,
    )


# ---------------------------------------------------------------------------
# POST /graph/nodes/approve
# ---------------------------------------------------------------------------

@router.post("/graph/nodes/approve", response_model=ApproveNodeResponse)
def approve_node(request: ApproveNodeRequest):
    """Approve and create a proposed node in Neo4j and VDB.

    This is step 2 of adding web content to the KG.
    The request should contain the (possibly modified) proposal from step 1.
    """
    from .kg_writer import approve_node as _approve_node, ProposedNode

    proposed = ProposedNode(
        node_type=request.node_type,
        node_id=request.node_id,
        name=request.name,
        description=request.description,
        method_family=request.method_family,
        method_type=request.method_type,
        granularity=request.granularity,
        addresses=request.addresses,
        impl_type=request.impl_type,
        maintainer=request.maintainer,
        source_repo=request.source_repo,
        implements=request.implements,
        doc_type=request.doc_type,
        authors=request.authors,
        year=request.year,
        venue=request.venue,
        proposes=request.proposes,
        source_url=request.source_url,
    )

    result = _approve_node(proposed)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)

    return ApproveNodeResponse(
        success=result.success,
        node_id=result.node_id,
        message=result.message,
    )


# ---------------------------------------------------------------------------
# GET /evaluations
# ---------------------------------------------------------------------------

@router.get("/evaluations")
def get_evaluations(
    agent: str | None = None,
    limit: int = 20,
    min_score: float | None = None,
):
    """Get recent evaluations from Neo4j.

    Args:
        agent: Filter by agent name (e.g., 'synthesizer').
        limit: Maximum number of evaluations to return (default 20).
        min_score: Filter to evaluations with composite_score >= this value.

    Returns:
        List of evaluation records.
    """
    try:
        client = _get_neo4j_client()

        # Build query with optional filters
        where_clauses = []
        params = {"limit": limit}

        if agent:
            where_clauses.append("e.agent_name = $agent")
            params["agent"] = agent

        if min_score is not None:
            where_clauses.append("e.composite_score >= $min_score")
            params["min_score"] = min_score

        where_str = ""
        if where_clauses:
            where_str = "WHERE " + " AND ".join(where_clauses)

        query = f"""
            MATCH (e:Evaluation)
            {where_str}
            RETURN e.id AS id,
                   e.agent_name AS agent_name,
                   e.query AS query,
                   e.composite_score AS composite_score,
                   e.feedback AS feedback,
                   e.created_at AS created_at
            ORDER BY e.created_at DESC
            LIMIT $limit
        """

        rows = client.run_cypher(query, params)
        client.close()

        return {
            "evaluations": [
                {
                    "id": row["id"],
                    "agent_name": row["agent_name"],
                    "query": row["query"],
                    "composite_score": row["composite_score"],
                    "feedback": row["feedback"],
                    "created_at": str(row["created_at"]) if row["created_at"] else None,
                }
                for row in rows
            ],
            "count": len(rows),
        }

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Neo4j unavailable: {e}")


# ---------------------------------------------------------------------------
# GET /evaluation-criteria
# ---------------------------------------------------------------------------

@router.get("/evaluation-criteria")
def get_evaluation_criteria(agent: str | None = None):
    """Get all evaluation criteria, optionally filtered by agent.

    Args:
        agent: Filter by agent_target (e.g., 'synthesizer').

    Returns:
        List of evaluation criteria.
    """
    try:
        client = _get_neo4j_client()

        if agent:
            query = """
                MATCH (ec:EvaluationCriteria {agent_target: $agent})-[:DERIVED_FROM]->(p:Principle)
                WHERE ec.is_active = true
                RETURN ec.id AS id, ec.name AS name, ec.description AS description,
                       ec.weight AS weight, p.name AS principle_name
                ORDER BY ec.weight DESC
            """
            rows = client.run_cypher(query, {"agent": agent})
        else:
            query = """
                MATCH (ec:EvaluationCriteria)-[:DERIVED_FROM]->(p:Principle)
                WHERE ec.is_active = true
                RETURN ec.id AS id, ec.name AS name, ec.description AS description,
                       ec.agent_target AS agent_target, ec.weight AS weight, p.name AS principle_name
                ORDER BY ec.agent_target, ec.weight DESC
            """
            rows = client.run_cypher(query)

        client.close()

        return {
            "criteria": [dict(row) for row in rows],
            "count": len(rows),
        }

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Neo4j unavailable: {e}")


# ---------------------------------------------------------------------------
# Optimizer Endpoints
# ---------------------------------------------------------------------------

@router.get("/optimizer/patterns", response_model=FailurePatternsResponse)
def get_failure_patterns(
    agent: str | None = None,
    status: str | None = None,
    limit: int = 20,
):
    """Get detected failure patterns.

    Args:
        agent: Filter by agent name.
        status: Filter by status (detected, reviewing, addressing, resolved).
        limit: Maximum patterns to return.
    """
    from src.optimizer import get_analyzer

    try:
        analyzer = get_analyzer()
        patterns = analyzer.get_patterns(status=status, agent_name=agent)
        patterns = patterns[:limit]

        return FailurePatternsResponse(
            patterns=[
                FailurePatternItem(
                    id=p.id,
                    agent_name=p.agent_name,
                    criterion_id=p.criterion_id,
                    pattern_type=p.pattern_type,
                    description=p.description,
                    frequency=p.frequency,
                    avg_score=p.avg_score,
                    sample_queries=p.sample_queries[:5],
                    root_cause_hypotheses=p.root_cause_hypotheses,
                    status=p.status,
                )
                for p in patterns
            ],
            count=len(patterns),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get patterns: {e}")


@router.post("/optimizer/analyze", response_model=FailurePatternsResponse)
def analyze_failures(request: AnalyzeRequest):
    """Trigger failure pattern detection.

    Args:
        agent: Filter by agent name.
        threshold: Score threshold for failures (default 0.6).
    """
    from src.optimizer import FailureAnalyzer

    try:
        analyzer = FailureAnalyzer(threshold=request.threshold)
        patterns = analyzer.analyze(agent_name=request.agent)

        return FailurePatternsResponse(
            patterns=[
                FailurePatternItem(
                    id=p.id,
                    agent_name=p.agent_name,
                    criterion_id=p.criterion_id,
                    pattern_type=p.pattern_type,
                    description=p.description,
                    frequency=p.frequency,
                    avg_score=p.avg_score,
                    sample_queries=p.sample_queries[:5],
                    root_cause_hypotheses=p.root_cause_hypotheses,
                    status=p.status,
                )
                for p in patterns
            ],
            count=len(patterns),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@router.post("/optimizer/patterns/{pattern_id}/approve", response_model=GenerateVariantsResponse)
def approve_hypotheses(pattern_id: str, request: ApproveHypothesesRequest):
    """Approve hypotheses and generate prompt variants (Gate 1 -> Testing).

    Args:
        pattern_id: The failure pattern ID.
        hypotheses: List of approved/edited hypotheses.
    """
    from src.optimizer import get_analyzer, VariantGenerator

    try:
        analyzer = get_analyzer()
        patterns = analyzer.get_patterns()
        pattern = next((p for p in patterns if p.id == pattern_id), None)

        if not pattern:
            raise HTTPException(status_code=404, detail=f"Pattern not found: {pattern_id}")

        # Update pattern with edited hypotheses
        pattern.root_cause_hypotheses = request.hypotheses
        analyzer.update_pattern_status(pattern_id, "reviewing")

        # Generate variants
        generator = VariantGenerator()
        variants = generator.generate_variants(pattern, num_variants=3)

        return GenerateVariantsResponse(
            variants=[
                PromptVariantItem(
                    id=v.id,
                    agent_name=v.agent_name,
                    prompt_content=v.prompt_content,
                    rationale=v.rationale,
                    addresses_hypotheses=v.addresses_hypotheses,
                    failure_pattern_id=v.failure_pattern_id,
                )
                for v in variants
            ],
            pattern_id=pattern_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Variant generation failed: {e}")


@router.post("/optimizer/test", response_model=TestResultsResponse)
def test_variants(request: TestVariantsRequest):
    """Run tests on prompt variants.

    Args:
        agent_name: Agent being tested.
        pattern_id: The failure pattern ID.
        variant_ids: List of variant IDs to test.
    """
    from src.optimizer import TestRunner, get_analyzer, VariantGenerator

    try:
        # Get the pattern and variants
        analyzer = get_analyzer()
        patterns = analyzer.get_patterns()
        pattern = next((p for p in patterns if p.id == request.pattern_id), None)

        if not pattern:
            raise HTTPException(status_code=404, detail=f"Pattern not found: {request.pattern_id}")

        # Regenerate variants for testing (or use cached)
        generator = VariantGenerator()
        variants = generator.generate_variants(pattern, num_variants=3)

        # Run tests
        runner = TestRunner()
        results = runner.run_tests(request.agent_name, variants)

        # Update pattern status
        analyzer.update_pattern_status(request.pattern_id, "addressing")

        return TestResultsResponse(
            results=[
                TestResultItem(
                    variant_id=r.variant.id,
                    scores=r.scores,
                    baseline_scores=r.baseline_scores,
                    performance_delta=r.performance_delta,
                    pass_rate=r.pass_rate,
                    passed_count=r.passed_count,
                    failed_count=r.failed_count,
                )
                for r in results
            ],
            best_variant_id=results[0].variant.id if results else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Testing failed: {e}")


@router.post("/optimizer/versions/{version_id}/activate")
def activate_version(version_id: str, request: ActivateVersionRequest):
    """Activate a prompt version (Gate 2 approval).

    Args:
        version_id: The version ID to activate.
        approved_by: User who approved.
    """
    from src.optimizer import get_registry

    try:
        registry = get_registry()
        success = registry.activate_version(version_id, approved_by=request.approved_by)

        if not success:
            raise HTTPException(status_code=400, detail=f"Failed to activate version: {version_id}")

        return {
            "success": True,
            "version_id": version_id,
            "message": f"Version {version_id} activated",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Activation failed: {e}")


@router.post("/optimizer/rollback")
def rollback_version(request: RollbackRequest):
    """Rollback to a previous prompt version.

    Args:
        agent_name: Agent to rollback.
        to_version: Specific version ID or None for previous.
    """
    from src.optimizer import get_registry

    try:
        registry = get_registry()
        success = registry.rollback(request.agent_name, to_version=request.to_version)

        if not success:
            raise HTTPException(status_code=400, detail="Rollback failed")

        current = registry.get_current_version(request.agent_name)
        return {
            "success": True,
            "current_version": current.id if current else None,
            "message": f"Rolled back to {current.version if current else 'initial'}",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rollback failed: {e}")


@router.get("/optimizer/versions", response_model=VersionHistoryResponse)
def get_versions(agent: str, limit: int = 10):
    """Get version history for an agent.

    Args:
        agent: Agent name.
        limit: Maximum versions to return.
    """
    from src.optimizer import get_registry

    try:
        registry = get_registry()
        versions = registry.get_version_history(agent, limit=limit)
        current = registry.get_current_version(agent)

        return VersionHistoryResponse(
            versions=[
                PromptVersionItem(
                    id=v.id,
                    agent_name=v.agent_name,
                    version=v.version,
                    is_active=v.is_active,
                    user_approved=v.user_approved,
                    performance_delta=v.performance_delta,
                    rationale=v.rationale,
                    parent_version=v.parent_version,
                    approved_by=v.approved_by,
                    approved_at=v.approved_at.isoformat() if v.approved_at else None,
                    created_at=v.created_at.isoformat() if v.created_at else "",
                )
                for v in versions
            ],
            current_version=current.id if current else None,
            count=len(versions),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get versions: {e}")

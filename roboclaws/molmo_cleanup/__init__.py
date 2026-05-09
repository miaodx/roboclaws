"""MolmoSpaces-shaped cleanup contracts for provenance-labeled demos."""

from roboclaws.molmo_cleanup.advisory_scoring import build_advisory_evaluation
from roboclaws.molmo_cleanup.planner_primitive_executor import (
    CleanupPrimitiveRequest,
    CleanupPrimitiveResult,
    PlannerBackedCleanupContractAdapter,
)
from roboclaws.molmo_cleanup.realworld_contract import (
    REALWORLD_CONTRACT,
    RealWorldCleanupContract,
)
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario
from roboclaws.molmo_cleanup.scoring import score_cleanup
from roboclaws.molmo_cleanup.semantic_acceptability import (
    annotate_score_with_semantic_acceptability,
)

__all__ = [
    "REALWORLD_CONTRACT",
    "CleanupPrimitiveRequest",
    "CleanupPrimitiveResult",
    "PlannerBackedCleanupContractAdapter",
    "RealWorldCleanupContract",
    "annotate_score_with_semantic_acceptability",
    "build_advisory_evaluation",
    "build_cleanup_scenario",
    "score_cleanup",
]

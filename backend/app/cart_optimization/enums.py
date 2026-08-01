from enum import StrEnum


class CoverageState(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNKNOWN = "unknown"
    INVALID = "invalid"


class PlanFeasibility(StrEnum):
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    UNRESOLVED = "unresolved"
    INVALID = "invalid"


class OptimizationOutcome(StrEnum):
    SELECTED = "selected"
    INFEASIBLE = "infeasible"
    UNRESOLVED = "unresolved"


class ConstraintHardness(StrEnum):
    HARD = "hard"
    SOFT = "soft"


class PlanRejectionCode(StrEnum):
    HARD_CONSTRAINT_VIOLATION = "hard_constraint_violation"
    MISSING_REQUIRED_ALLOCATION = "missing_required_allocation"
    INVALID_ALLOCATION = "invalid_allocation"
    UNSUPPORTED_PLAN = "unsupported_plan"

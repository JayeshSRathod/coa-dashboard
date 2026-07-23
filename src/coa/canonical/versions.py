"""The immutable rule registry for canonical COA v1."""
from .models import RuleVersion
CANONICAL_COA_VERSION = "1.0.0"
RULE_REGISTRY = (
    RuleVersion("COA-STRUCTURE-001", "1.0", "Frozen COA v1 support, resistance, vector and scenario evaluation."),
    RuleVersion("COA-TACTICAL-001", "1.0", "Frozen COA v2 OI state classification and tactical scenario evaluation."),
    RuleVersion("COA-COMPATIBILITY-001", "1.0", "Structural and tactical decision compatibility matrix."),
    RuleVersion("COA-RISK-001", "1.0", "Deterministic EOS/EOR-derived research risk coordinates."),
)

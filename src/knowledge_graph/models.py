"""Immutable knowledge-graph and governance models for CQRP.

The graph links research artifacts from evidence through qualified shadow rules.
Governance decisions remain append-only and cannot authorize live trading unless
a later, separate control plane explicitly changes execution policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_ALLOWED_NODE_TYPES = {
    "TRADE_PLAN", "VALIDATION", "PAPER_TRADE", "EVIDENCE", "STATISTICS",
    "EXPERIMENT", "PATTERN", "PATTERN_VALIDATION", "QUALIFIED_RULE",
    "GOVERNANCE_DECISION",
}
_ALLOWED_EDGE_TYPES = {
    "GENERATED", "VALIDATED_BY", "EXECUTED_AS", "PRODUCED_EVIDENCE",
    "AGGREGATED_IN", "USED_BY", "DISCOVERED", "VALIDATED_PATTERN",
    "QUALIFIED_AS", "GOVERNED_BY", "SUPERSEDES", "DEPENDS_ON",
}
_ALLOWED_DECISIONS = {
    "APPROVE_SHADOW", "APPROVE_CONDITIONAL", "REJECT", "SUSPEND", "RETIRE",
}


@dataclass(frozen=True)
class KnowledgeNode:
    node_id: str
    node_type: str
    artifact_id: str
    label: str
    status: str | None
    attributes: Mapping[str, Any]
    lineage: Mapping[str, Any]
    created_at: str

    @classmethod
    def new(cls, **values: Any) -> "KnowledgeNode":
        values.setdefault("node_id", str(uuid4()))
        values.setdefault("status", None)
        values.setdefault("attributes", {})
        values.setdefault("lineage", {})
        values.setdefault("created_at", _now())
        values["node_type"] = str(values["node_type"]).upper()
        values["attributes"] = MappingProxyType(dict(values["attributes"]))
        values["lineage"] = MappingProxyType(dict(values["lineage"]))
        if values["node_type"] not in _ALLOWED_NODE_TYPES:
            raise ValueError("unsupported knowledge node type")
        if not str(values.get("artifact_id") or "").strip():
            raise ValueError("artifact_id is required")
        if not str(values.get("label") or "").strip():
            raise ValueError("label is required")
        return cls(**values)

    def as_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "artifact_id": self.artifact_id,
            "label": self.label,
            "status": self.status,
            "attributes": dict(self.attributes),
            "lineage": dict(self.lineage),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class KnowledgeEdge:
    edge_id: str
    source_node_id: str
    target_node_id: str
    edge_type: str
    attributes: Mapping[str, Any]
    created_at: str

    @classmethod
    def new(cls, **values: Any) -> "KnowledgeEdge":
        values.setdefault("edge_id", str(uuid4()))
        values.setdefault("attributes", {})
        values.setdefault("created_at", _now())
        values["edge_type"] = str(values["edge_type"]).upper()
        values["attributes"] = MappingProxyType(dict(values["attributes"]))
        if values["edge_type"] not in _ALLOWED_EDGE_TYPES:
            raise ValueError("unsupported knowledge edge type")
        if values["source_node_id"] == values["target_node_id"]:
            raise ValueError("self-referencing edges are not allowed")
        return cls(**values)

    def as_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "edge_type": self.edge_type,
            "attributes": dict(self.attributes),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class GovernanceDecision:
    decision_id: str
    artifact_type: str
    artifact_id: str
    decision: str
    authority: str
    rationale: tuple[str, ...]
    conditions: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    previous_decision_id: str | None
    effective_mode: str
    created_at: str
    created_by: str = "CQRP_GOVERNANCE"

    @classmethod
    def new(cls, **values: Any) -> "GovernanceDecision":
        values.setdefault("decision_id", str(uuid4()))
        values.setdefault("rationale", ())
        values.setdefault("conditions", ())
        values.setdefault("evidence_refs", ())
        values.setdefault("previous_decision_id", None)
        values.setdefault("effective_mode", "SHADOW_ONLY")
        values.setdefault("created_at", _now())
        values.setdefault("created_by", "CQRP_GOVERNANCE")
        values["decision"] = str(values["decision"]).upper()
        values["effective_mode"] = str(values["effective_mode"]).upper()
        values["rationale"] = tuple(str(item) for item in values["rationale"])
        values["conditions"] = tuple(str(item) for item in values["conditions"])
        values["evidence_refs"] = tuple(str(item) for item in values["evidence_refs"])
        if values["decision"] not in _ALLOWED_DECISIONS:
            raise ValueError("unsupported governance decision")
        if values["effective_mode"] != "SHADOW_ONLY":
            raise ValueError("Sprint-212 governance must remain SHADOW_ONLY")
        if not str(values.get("authority") or "").strip():
            raise ValueError("governance authority is required")
        return cls(**values)

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "artifact_type": self.artifact_type,
            "artifact_id": self.artifact_id,
            "decision": self.decision,
            "authority": self.authority,
            "rationale": list(self.rationale),
            "conditions": list(self.conditions),
            "evidence_refs": list(self.evidence_refs),
            "previous_decision_id": self.previous_decision_id,
            "effective_mode": self.effective_mode,
            "created_at": self.created_at,
            "created_by": self.created_by,
        }

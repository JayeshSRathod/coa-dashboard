"""Knowledge graph builder and governed shadow-rule decision engine."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from .models import GovernanceDecision, KnowledgeEdge, KnowledgeNode


class KnowledgeGraphEngine:
    version = "knowledge-graph-v1"

    _TYPE_MAP = {
        "trade_plan_id": "TRADE_PLAN",
        "validation_id": "VALIDATION",
        "trade_id": "PAPER_TRADE",
        "evidence_id": "EVIDENCE",
        "snapshot_id": "STATISTICS",
        "experiment_id": "EXPERIMENT",
        "pattern_id": "PATTERN",
        "qualification_id": "QUALIFIED_RULE",
    }

    def build_nodes(self, artifacts: Iterable[Mapping[str, Any]]) -> tuple[KnowledgeNode, ...]:
        nodes: list[KnowledgeNode] = []
        seen: set[tuple[str, str]] = set()
        for artifact in artifacts:
            record = dict(artifact)
            for id_field, node_type in self._TYPE_MAP.items():
                artifact_id = record.get(id_field)
                if not artifact_id:
                    continue
                key = (node_type, str(artifact_id))
                if key in seen:
                    continue
                seen.add(key)
                nodes.append(
                    KnowledgeNode.new(
                        node_type=node_type,
                        artifact_id=str(artifact_id),
                        label=str(record.get("title") or record.get("instrument") or f"{node_type}:{artifact_id}"),
                        status=record.get("status") or record.get("outcome"),
                        attributes={
                            "instrument": record.get("instrument"),
                            "planning_horizon": record.get("planning_horizon"),
                            "score": record.get("qualification_score") or record.get("validation_score") or record.get("confidence_score"),
                            "mode": record.get("mode"),
                        },
                        lineage={"source_fields": sorted(record.keys()), "engine_version": self.version},
                    )
                )
        return tuple(nodes)

    def build_edges(
        self,
        nodes: Iterable[KnowledgeNode],
        artifacts: Iterable[Mapping[str, Any]],
    ) -> tuple[KnowledgeEdge, ...]:
        index = {(node.node_type, node.artifact_id): node.node_id for node in nodes}
        edges: list[KnowledgeEdge] = []
        seen: set[tuple[str, str, str]] = set()

        relations = (
            ("TRADE_PLAN", "trade_plan_id", "VALIDATION", "validation_id", "VALIDATED_BY"),
            ("TRADE_PLAN", "trade_plan_id", "PAPER_TRADE", "trade_id", "EXECUTED_AS"),
            ("PAPER_TRADE", "trade_id", "EVIDENCE", "evidence_id", "PRODUCED_EVIDENCE"),
            ("EVIDENCE", "evidence_id", "EXPERIMENT", "experiment_id", "USED_BY"),
            ("EXPERIMENT", "experiment_id", "PATTERN", "pattern_id", "DISCOVERED"),
            ("PATTERN", "pattern_id", "VALIDATION", "validation_id", "VALIDATED_PATTERN"),
            ("PATTERN", "pattern_id", "QUALIFIED_RULE", "qualification_id", "QUALIFIED_AS"),
        )
        for artifact in artifacts:
            record = dict(artifact)
            for source_type, source_field, target_type, target_field, edge_type in relations:
                source_id = record.get(source_field)
                target_id = record.get(target_field)
                if not source_id or not target_id:
                    continue
                source_node = index.get((source_type, str(source_id)))
                target_node = index.get((target_type, str(target_id)))
                if not source_node or not target_node:
                    continue
                key = (source_node, target_node, edge_type)
                if key in seen:
                    continue
                seen.add(key)
                edges.append(
                    KnowledgeEdge.new(
                        source_node_id=source_node,
                        target_node_id=target_node,
                        edge_type=edge_type,
                        attributes={"engine_version": self.version},
                    )
                )
        return tuple(edges)


class GovernanceEngine:
    version = "governance-v1"

    def decide_shadow_rule(
        self,
        qualification: Mapping[str, Any],
        *,
        authority: str,
        previous_decision_id: str | None = None,
    ) -> GovernanceDecision:
        record = dict(qualification)
        status = str(record.get("status") or "").upper()
        recommendation = str(record.get("recommendation") or "").upper()
        score = float(record.get("qualification_score") or 0.0)
        failed = tuple(str(item) for item in record.get("failed_gates") or ())

        if status == "QUALIFIED" and recommendation == "PROMOTE_TO_SHADOW_RULE" and score >= 75.0 and not failed:
            decision = "APPROVE_SHADOW"
            rationale = ("Rule qualification passed all configured gates.",)
            conditions = tuple(record.get("required_conditions") or ())
        elif status == "CONDITIONAL":
            decision = "APPROVE_CONDITIONAL"
            rationale = ("Rule remains conditional and requires further evidence or controls.",)
            conditions = tuple(record.get("required_conditions") or ()) + tuple(failed)
        else:
            decision = "REJECT"
            rationale = ("Rule qualification did not satisfy governance promotion gates.",)
            conditions = tuple(failed)

        return GovernanceDecision.new(
            artifact_type="QUALIFIED_RULE",
            artifact_id=str(record.get("rule_id") or record.get("qualification_id")),
            decision=decision,
            authority=authority,
            rationale=rationale,
            conditions=conditions,
            evidence_refs=tuple(
                str(item)
                for item in (record.get("pattern_id"), record.get("validation_id"), record.get("qualification_id"))
                if item
            ),
            previous_decision_id=previous_decision_id,
            effective_mode="SHADOW_ONLY",
            created_by="GovernanceEngine",
        )

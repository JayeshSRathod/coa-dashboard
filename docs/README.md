# CQRP Documentation

This directory is CQRP's version-controlled documentation source of truth. Markdown documents are maintained with code and reviewed in pull requests. The foundation `.docx` documents remain reference material; they are not the authoritative engineering record.

## Start here

1. [Product overview](product/cqrp-overview.md)
2. [System architecture](architecture/system-overview.md)
3. [COA strategy governance](strategy/coa-governance.md)
4. [Research governance](research/research-governance.md)
5. [Operations runbook](operations/runbook.md)
6. [Getting started](user-guides/getting-started.md)

## Reference map

- `adr/` — durable architecture decisions.
- `api/` — application and transport contracts.
- `architecture/` — system boundaries, data flow, and module maps.
- `database/` — schema, migration, retention, and audit guidance.
- `development/` — contributor standards.
- `operations/` — deployment, monitoring, recovery, and incident response.
- `product/` — vision, scope, requirements, and roadmap.
- `research/` — experimentation, replay, and promotion controls.
- `sprints/` — delivered sprint scope and acceptance notes.
- `strategy/` — frozen COA rules and strategy version governance.
- `user-guides/` — safe local use of CQRP.
- `releases/` — release and compatibility notes.

Every implementation PR must update the relevant reference document, sprint record, and ADR when a durable architectural decision changes.

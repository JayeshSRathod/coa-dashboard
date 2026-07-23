# CQRP Application and API Contracts

Presentation components consume application services and serializable API facades. These are transport-neutral Python contracts today; a web framework may adapt them later without exposing domain internals.

| Area | Boundary |
| --- | --- |
| Decisions | `src.application.services.DecisionService`, `src.api.rest.CQRPApiV1` |
| Offline Copilot | `src.application.ai_service.CopilotApplicationService`, `src.api.copilot.CopilotApiV1` |
| Dashboard | Dashboard application services and view models |

API responses must be serializable, read/advisory-only unless an explicitly approved application service owns the command, and must never include raw secrets.

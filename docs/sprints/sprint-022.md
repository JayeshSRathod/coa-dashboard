# Sprint-022 — Application API & Event Bus

CQRP exposes application services through DTOs, a versioned `/api/v1`-style facade, and an internal event bus. Presentation clients must use this boundary; they must not import decision or COA domain models directly.

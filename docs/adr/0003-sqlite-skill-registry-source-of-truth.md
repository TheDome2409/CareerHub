# ADR 0003: Registry-First Skill Knowledge With YAML Seeds And Fallbacks

Status: **Accepted; implementation clarified for v0.1.0 on 2026-10-12**

## Context

The Unknown Skill workflow originally produced review candidates, but accepted
skills needed a durable runtime home. YAML seed files are useful for examples
and bootstrapping, but they are not ideal as mutable runtime storage.

## Decision

Use SQLite as the durable home of human-reviewed skills and aliases, with
registry-first lookup. This is not an exclusive SQLite runtime architecture.

`taxonomy_loader.py` runs idempotent YAML seed migration when loading taxonomy,
adds configured YAML keywords and falls back to YAML if registry loading fails.
`skill_alias_service.py` prefers registry aliases but retains a YAML-backed alias
map. YAML therefore remains a runtime configuration and fallback input as well
as a seed/import source. Broad exception fallbacks currently do not expose a
degraded-registry warning.

Seed refreshes may add aliases, but preserve human/runtime provenance, status,
display name and description. Seed-owned entries may still receive seed updates.

## Consequences

- Approved skills survive restarts.
- Matching can immediately use newly accepted registry entries.
- Alias merge and type-conflict handling can be transactional.
- Migration from seed YAML must be idempotent.
- Registry management UI remains future work.
- A SQLite-only runtime would require separate migration/bootstrap and explicit
  degraded-mode handling. It is future work, not the current implementation.

## Alternatives Considered

- Continue with YAML only: simple, but weak for runtime mutation and conflict
  handling.
- JSON file registry: easier than SQLite, but weaker transactions and querying.
- Full database layer from the start: more scalable, too heavy for v0.1.0.

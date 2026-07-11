# ADR 0003: SQLite Skill Registry As Source Of Truth

Status: **Accepted**

## Context

The Unknown Skill workflow originally produced review candidates, but accepted
skills needed a durable runtime home. YAML seed files are useful for examples
and bootstrapping, but they are not ideal as mutable runtime storage.

## Decision

Use a SQLite-backed Skill Registry as the runtime source of truth for approved
skills and aliases. Keep YAML as seed, import/export and configuration material.

## Consequences

- Approved skills survive restarts.
- Matching can immediately use newly accepted registry entries.
- Alias merge and type-conflict handling can be transactional.
- Migration from seed YAML must be idempotent.
- Registry management UI remains future work.

## Alternatives Considered

- Continue with YAML only: simple, but weak for runtime mutation and conflict
  handling.
- JSON file registry: easier than SQLite, but weaker transactions and querying.
- Full database layer from the start: more scalable, too heavy for v0.1.0.

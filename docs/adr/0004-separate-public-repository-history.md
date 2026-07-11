# ADR 0004: Separate Public Repository History

Status: **Accepted**

## Context

The private development repository contained local runtime artifacts, private
context and iterative work that should not be published. A public portfolio
release needs clean source, documentation and synthetic examples without
private history.

## Decision

Create the public candidate from an approved private source commit and initialize
a new public Git history. Do not publish the private Git history.

## Consequences

- Public history is easier to audit.
- Private artifacts and intermediate commits are not exposed.
- Traceability to the private source commit is documented, but not published as
  history.
- Future public development starts from a clean baseline.

## Alternatives Considered

- Publish the private repository after cleanup: higher risk of historical data
  exposure.
- Rewrite private history: possible, but still more complex and higher risk.
- Publish only an archive without Git history: less useful for open-source
  collaboration.

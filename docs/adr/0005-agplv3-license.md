# ADR 0005: AGPLv3 License

Status: **Accepted**

## Context

CareerHub is an open-source portfolio project that handles explainable matching,
document generation and local AI workflows. If modified versions are exposed
over a network, users should still be able to inspect the corresponding source.

## Decision

License CareerHub under the GNU Affero General Public License v3.0.

## Consequences

- The full AGPLv3 text is included as `LICENSE`.
- Modified network-deployed versions have source-availability obligations under
  the license.
- Some commercial users may need legal review before adoption.
- Third-party dependencies and local model files keep their own licenses.

## Alternatives Considered

- MIT or Apache-2.0: simpler adoption, weaker network transparency obligation.
- GPLv3: strong copyleft, but no AGPL network-use clause.
- Dual licensing: possible later, unnecessary for v0.1.0.

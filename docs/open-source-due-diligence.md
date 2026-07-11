# Open-Source Due Diligence

Status: **Ready with documented limitations**

CareerHub is prepared as a public portfolio release from a private development
repository. This document records due-diligence status and remaining limitations.
It is not legal advice and does not claim legal certainty.

## Project Origin

CareerHub was developed as an AI-assisted local prototype for career matching,
company analysis foundations, document processing and application package
generation.

The public candidate was exported from approved private source commit
`6b48856c68dd58f627d5c8bca70d7a814443fb9a` and initialized with a new public
single-commit Git history. The private Git history was not carried into the
public repository.

## AI-Assisted Development

Parts of the code and documentation were created with AI assistance and reviewed
through local tests, documentation audits, privacy scans and manual inspection.
AI assistance is documented as part of the project process; it does not remove
the need for human review.

## Code Provenance

No intentional copy of a complete third-party codebase is included. The project
uses ordinary Python dependencies through `requirements.txt`; those packages
remain third-party software under their own licenses.

## Dependency License Review

Status: **Partially complete / requires review**

Completed:

- direct dependencies reviewed from installed package metadata
- optional system tools listed separately
- optional local LLM model licensing called out explicitly
- no confirmed incompatible direct Python dependency found

Remaining:

- automate dependency inventory regeneration
- review transitive dependencies in more detail before commercial redistribution
- review optional DuckDB/WeasyPrint stacks if they become required
- verify external binaries and local model licenses in each user environment

See:

- [Dependency License Inventory](dependency-license-inventory.md)
- [Third-Party Notices](../THIRD_PARTY_NOTICES.md)

## Related Work

Status: **Completed for v0.1.0 public launch preparation**

A first related-work review is documented in [Related Work](related-work.md).
It covers resume builders, resume/job matching, ESCO-style taxonomies, local LLM
tools, company intelligence concepts and benchmark frameworks.

This is a best-effort project-context review, not a formal patent or prior-art
opinion.

## Name and Trademark Review

Status: **Requires review**

The project name CareerHub is used as a descriptive portfolio project name. A
formal trademark clearance has not been performed.

## Assets and Data

Status: **Checked for public candidate**

The public candidate should contain only source code, configuration examples,
synthetic examples and tests. Runtime databases, benchmark outputs, uploads,
exports, real resumes, applications, certificates and private company documents
are ignored and were removed from the public candidate.

Synthetic examples are included and labelled as synthetic.

## Privacy Scan

Status: **Completed for public candidate**

The final public candidate was scanned for:

- private names and employer references
- local absolute paths
- common e-mail domains in private examples
- runtime databases and generated artifacts
- visible mojibake/encoding regressions in docs and source

No confirmed blocking privacy issue was found in the public candidate before the
initial public commit.

## Secret Scan

Status: **Completed for public candidate**

The public candidate was scanned for common secret patterns such as private keys,
API keys, bearer tokens, passwords, connection strings and local paths.

Only harmless placeholders, environment-variable names and code variable names
were observed. No confirmed secret value was found.

## Runtime Data Separation

Status: **Implemented**

`.gitignore` excludes runtime and private artifacts such as:

- `.env`
- `.venv*`
- logs
- runtime databases
- review queues
- recommendation/outcome files
- uploaded/generated application packages
- benchmark outputs and reports
- non-public company profile files

## License

Status: **Implemented**

CareerHub is licensed under AGPLv3. The full text is included as `LICENSE`.

## Remaining Due-Diligence Items

- Formal trademark/name clearance.
- Deeper transitive dependency license review before commercial reuse.
- Optional native tool and model-license review for each installation.
- Broader patent/prior-art review if needed.
- Public issue triage after repository creation.

No statement in this repository should be read as a guarantee that publication,
deployment or commercial reuse is legally safe.

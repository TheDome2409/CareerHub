# Product Backlog

Status: **Prepared backlog**

This backlog captures product direction without inventing delivery dates, story
points or business results.

## Now

### Name / Trademark Review

- Problem: The project name is descriptive, but formal clearance has not been
  performed.
- Intended outcome: reduce naming risk before broader publication.
- Acceptance signal: documented decision to keep or rename the repository.
- Status: **Planned**
- Priority: High

### Synthetic Screenshots

- Problem: README has no visual walkthrough yet.
- Intended outcome: public screenshots using only synthetic data.
- Acceptance signal: screenshots pass the checklist in `docs/screenshots/`.
- Status: **Planned**
- Priority: High

### GitHub Repository Publication

- Problem: the public candidate exists locally but is not yet published.
- Intended outcome: public repository with clean history, AGPLv3, CI and docs.
- Acceptance signal: repository is created, remote is set, first push succeeds.
- Status: **Planned**
- Priority: High

### v0.1.0 Release

- Problem: release notes exist locally but no GitHub release has been created.
- Intended outcome: initial public portfolio release is tagged and documented.
- Acceptance signal: `v0.1.0` release notes are published.
- Status: **Planned**
- Priority: High

### Installation Validation

- Problem: setup should be validated outside the development machine.
- Intended outcome: fresh setup path is confirmed and documented.
- Acceptance signal: documented Windows setup result and known optional-tool
  gaps.
- Status: **Planned**
- Priority: High

## Next

### Skill Registry Management UI

- Problem: persistence exists, but registry inspection and management can be
  improved.
- Intended outcome: users can inspect canonical skills, aliases and conflicts
  more comfortably.
- Acceptance signal: tested UI path for viewing and managing registry entries.
- Status: **Planned**
- Priority: Medium

### End-to-End Synthetic Demo

- Problem: synthetic data exists, but the complete demo flow needs one curated
  walkthrough.
- Intended outcome: repeatable demo from profile import to package export.
- Acceptance signal: documented flow runs without private data.
- Status: **Planned**
- Priority: High

### Linux Compatibility

- Problem: current public checks were performed in a Windows environment.
- Intended outcome: Linux setup and test behavior are documented.
- Acceptance signal: test and startup results recorded for Linux.
- Status: **Planned**
- Priority: Medium

### CompanyHub Source Configurability

- Problem: CompanyHub source workflows are functional but still foundation-level.
- Intended outcome: easier public-safe configuration of tracked company sources.
- Acceptance signal: source add/list/disable behavior remains tested and easier
  to configure.
- Status: **Planned**
- Priority: Medium

### Dependency License Automation

- Problem: dependency inventory is currently manual.
- Intended outcome: repeatable generation of direct/transitive dependency
  license inventory.
- Acceptance signal: command or script generates a reviewable report without
  claiming legal certainty.
- Status: **Planned**
- Priority: Medium

## Later

### Agent-Based Workflows

- Problem: more complex research workflows need orchestration and controls.
- Intended outcome: agents can assist while preserving human review and
  evidence traceability.
- Acceptance signal: scoped design with safety, privacy and review gates.
- Status: **Concept**
- Priority: Low

### Scheduled Job Crawling

- Problem: job data refresh is manual/workflow-triggered.
- Intended outcome: scheduled refresh with deduplication and source governance.
- Acceptance signal: scheduler design and tests avoid uncontrolled crawling.
- Status: **Planned**
- Priority: Low

### Deeper Company Intelligence

- Problem: CompanyHub stores evidence and drafts but lacks richer source
  coverage and approval workflows.
- Intended outcome: more reliable company knowledge with source traceability.
- Acceptance signal: knowledge approval flow and stronger evidence extraction.
- Status: **Planned**
- Priority: Medium

### Richer Lifestyle / Resonance Matching

- Problem: role fit alone does not capture all practical career-fit factors.
- Intended outcome: more nuanced preferences for work rhythm, product
  identification, travel and work-life constraints.
- Acceptance signal: explicit model fields, configuration and explainability.
- Status: **Concept**
- Priority: Low

### Multi-User Architecture

- Problem: current design is local-first and single-user oriented.
- Intended outcome: a separate design for authentication, authorization,
  deployment and data isolation.
- Acceptance signal: architecture proposal before any implementation.
- Status: **Concept**
- Priority: Low

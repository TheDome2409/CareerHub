# Initial GitHub Issues

Status: **Prepared suggestions - no GitHub issues created**

Suggested milestone:

`v0.2.0 - Public Usability`

## 1. Complete screenshot-based synthetic demo

- Priority: High
- Labels: `documentation`, `demo`, `good first issue`
- Milestone: `v0.2.0 - Public Usability`
- Description: Capture a privacy-reviewed screenshot walkthrough using only
  synthetic profile, job and company data.
- Acceptance criteria:
  - screenshots follow `docs/screenshots/README.md`
  - no private data or local paths are visible
  - README references only existing screenshot files

## 2. Validate setup on a fresh Windows machine

- Priority: High
- Labels: `setup`, `windows`, `testing`
- Milestone: `v0.2.0 - Public Usability`
- Description: Re-run installation and smoke tests on a fresh Windows
  environment.
- Acceptance criteria:
  - `python -m pip install -r requirements.txt` succeeds
  - Streamlit starts through documented commands
  - optional renderer/OCR gaps are documented clearly

## 3. Check Linux compatibility

- Priority: Medium
- Labels: `setup`, `linux`, `portability`
- Milestone: `v0.2.0 - Public Usability`
- Description: Validate import paths, tests and optional tool documentation on
  Linux.
- Acceptance criteria:
  - test suite outcome is documented
  - path assumptions are identified
  - setup notes are added where needed

## 4. Expand Skill Registry management UI

- Priority: Medium
- Labels: `skill-registry`, `ux`, `enhancement`
- Milestone: `v0.2.0 - Public Usability`
- Description: Improve inspection and management of persistent skills and
  aliases from the UI.
- Acceptance criteria:
  - active skills can be inspected by canonical name, type and aliases
  - conflicts are visible
  - no direct SQL is exposed in the UI

## 5. Make CompanyHub sources easier to configure

- Priority: Medium
- Labels: `companyhub`, `configuration`, `enhancement`
- Milestone: `v0.2.0 - Public Usability`
- Description: Improve public-safe editing/import of company sources without
  changing the evidence pipeline.
- Acceptance criteria:
  - source examples are documented
  - duplicate source handling remains stable
  - tests cover source add/list/disable workflow

## 6. Automate dependency license inventory

- Priority: Medium
- Labels: `licensing`, `automation`, `documentation`
- Milestone: `v0.2.0 - Public Usability`
- Description: Add a repeatable command or script to regenerate dependency
  license inventory from an installed environment.
- Acceptance criteria:
  - direct and transitive dependencies are exported
  - missing/ambiguous metadata is flagged
  - output does not claim legal certainty

## 7. Document DuckDB benchmark extra

- Priority: Low
- Labels: `benchmarking`, `documentation`, `openllmbench`
- Milestone: `v0.2.0 - Public Usability`
- Description: Clarify how to install and use DuckDB for optional benchmark
  archiving.
- Acceptance criteria:
  - skipped tests explain optional DuckDB status
  - docs separate CareerHub runtime from benchmark archive experiments

## 8. Run end-to-end synthetic demo smoke

- Priority: High
- Labels: `demo`, `testing`, `privacy`
- Milestone: `v0.2.0 - Public Usability`
- Description: Execute the complete synthetic flow from profile import through
  job matching, CompanyHub context and application package generation.
- Acceptance criteria:
  - no private data is required
  - generated runtime files remain ignored
  - any local LLM dependency is optional and documented

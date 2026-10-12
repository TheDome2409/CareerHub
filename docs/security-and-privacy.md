# Security And Privacy

## Status

Privacy posture: **Partially implemented**

CareerHub is designed for local processing. Runtime paths exist in code, but
runtime databases, private documents and generated outputs are excluded from
the public source snapshot. Local use can create sensitive files again.

## Local-First Design

CareerHub runs locally through Streamlit. LLM integration is designed around local Ollama. This reduces the need to send CVs, application documents or company research to external cloud APIs.

Local-first does not automatically mean safe. Runtime data, logs and generated outputs can still contain sensitive information.

## Data That Must Not Be Published

Do not commit:

- real CVs
- certificates or employment references
- application letters
- generated application packages
- personal contact details
- private company notes
- local review queue content
- recommendation snapshots or outcomes from real usage
- benchmark outputs containing private prompts or model responses
- API keys, passwords or tokens

## Current Repository Risks

Runtime risks (not a claim that these files are currently tracked):

- `data/companyhub.db` is a runtime SQLite database.
- `data/review_queue.json`, `data/recommendation_snapshots.json`, `data/recommendation_outcomes.json` and `data/global_skill_candidates.json` are runtime data.
- `benchmarks/outputs/` stores full benchmark responses when a benchmark runs.
- `logs/` may contain LLM prompt or export debug details.
- OCR configuration now uses `TESSERACT_CMD` and `POPPLER_PATH` instead of checked-in local paths. Keep real machine paths in local environment variables only.
- Live source credentials or client identifiers should be configured through environment variables such as `BUNDESAGENTUR_API_KEY`, not committed as concrete values.
- Public tests/examples use synthetic application material; future fixtures must maintain that boundary.

The `.gitignore` has been expanded to reduce accidental commits of runtime data.

## LLM Safety

LLM output is used for:

- unknown skill candidate evaluation
- cover-letter drafts
- context resume drafts
- company initiative letters
- optional company knowledge draft review

Controls in code include:

- JSON-only prompts for structured candidate and company review paths.
- Canonicalization and deduplication after LLM candidate evaluation.
- Review queue instead of automatic taxonomy modification.
- Strict prompts for initiative letters that prohibit invented skills, roles, certificates, projects and company claims.

Limitations:

- Prompts reduce but do not eliminate hallucinations.
- Human review remains necessary.
- Logs may capture metadata about LLM calls.

## Public Demo Guidance

Use only:

- synthetic profiles
- synthetic or public-safe job descriptions
- fake names
- demo companies or public company facts that are not private
- generated sample attachments with no personal data

Before publishing screenshots, check all visible names, paths, dates, salaries, emails, application text and review queue entries.

## Recommended Local Hygiene

- Keep personal profiles outside Git.
- Keep runtime `data/` files private.
- Clear `logs/` before sharing.
- Do not publish `benchmarks/outputs/`.
- Prefer `config/profile.example.yaml` for public examples.
- Move public demo fixtures to an explicit `examples/` folder if they are intended for publication.
- Prefer the synthetic examples under `examples/` for demos.

See [Publication Readiness Audit](publication-readiness-audit.md) for the
historical private-repository cleanup. It is not the current public release gate.

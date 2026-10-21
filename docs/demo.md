# Demo

This demo flow is intended for recruiters, technical interviewers or portfolio reviewers. Use only synthetic or public-safe data.

Setup: [Windows Quick Start](windows-quick-start.md). A minimal demo can use
the synthetic skill CSV and manual company profile without a local LLM.
OCR, drafting and full PDF export require their respective optional tools.
Job-source examples enable network sources; there is no automatic offline job
fixture loader. See the [dependency matrix](windows-setup.md).

## Demo 1: Profile And Skill Review

Status: **Implemented**

1. Start the Streamlit app.
2. Load or upload a synthetic profile document.
3. Show detected skill candidates and active profile skills.
4. Run unknown skill evaluation if local Ollama is available.
5. Show the review queue and status handling.

Message to communicate: CareerHub separates extraction, LLM suggestion and human approval.

## Demo 2: Job Matching

Status: **Implemented**

1. Load jobs from configured sources.
2. Show active profile-aware search queries.
3. Open a job result.
4. Explain total score and components such as skill score, competency match, qualification warnings and role mismatch penalty.
5. Show how hard exclusions affect results.

Message to communicate: Matching is not only keyword search; it combines profile, preferences, skills and explainability.

## Demo 3: Application Package

Status: **Partially implemented**

1. Select a job result.
2. Generate a cover-letter draft with local Ollama.
3. Generate a context resume draft if needed.
4. Add safe demo attachments.
5. Export HTML or ZIP.
6. Export final PDF only if WeasyPrint or wkhtmltopdf/pdfkit is available.

Message to communicate: CareerHub can produce a structured application package, but final review is human responsibility.

## Demo 4: CompanyHub

Status: **Experimental / Implemented foundation**

1. Open CompanyHub.
2. Show recommended companies.
3. Track a company.
4. Add or inspect sources.
5. Manually fetch sources.
6. Generate evidence and build a knowledge draft.
7. Show the pipeline inspector.
8. Optionally run Ollama draft review if a local model is available.

Message to communicate: CompanyHub is a transparent evidence pipeline, not a black-box company crawler.

## Demo 5: Company Match Initiative Application

Status: **Partially implemented**

1. Use a company match result or manual demo company profile.
2. Generate a Company Match report.
3. Mark the company as initiative target.
4. Open the application tab.
5. Generate an initiative letter using only available profile and company context.
6. Export an application package.

Message to communicate: The initiative flow is context-aware but still prototype-level and needs human review.

## Screenshot Rules

Before publishing screenshots:

- remove personal names and contact details
- remove local paths
- remove real company notes unless public-safe
- remove generated letters based on real application material
- inspect review queue entries

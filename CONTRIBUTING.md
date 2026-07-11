# Contributing

CareerHub is currently a private local prototype. Contributions, experiments and bug reports should keep the project safe to publish later.

## Principles

- Use synthetic or anonymized data in tests, examples and screenshots.
- Do not commit real CVs, application letters, contact data, exported application packages or private company notes.
- Keep UI, services, repositories and models separated.
- Prefer configuration over hardcoded behavior when the value is user- or domain-specific.
- Add focused tests for new business logic.
- Do not bypass human review for uncertain skill, company or LLM-derived knowledge.
- Treat LLM output as suggestion or draft, not as ground truth.
- Keep changes small and auditable.

## Status Labels

Use these labels in documentation and issue descriptions:

- **Implemented**
- **Partially implemented**
- **Experimental**
- **Planned**
- **Concept**

Do not describe a feature as implemented unless code, configuration and at least basic validation exist.

## Privacy Rules

Never add:

- real CVs or certificates
- real application letters
- private contact details
- API keys or credentials
- local absolute user paths
- generated benchmark outputs that contain private prompts or responses
- runtime review queue or recommendation data
- exported PDF/HTML/ZIP application packages

## Testing

Run the smallest relevant test set for the change. Examples:

```powershell
python -m pytest test_skill_profile_io.py
python -m pytest test_company_profile_match_service.py
python -m pytest test_application_pdf_service.py
```

Use broader test runs before larger documentation or architecture changes.

## Documentation

Documentation must match the code. If a feature is only a foundation, mark it as **Experimental** or **Concept**. If a feature depends on local tools such as Ollama, Tesseract, Poppler, wkhtmltopdf or WeasyPrint, state that dependency explicitly.

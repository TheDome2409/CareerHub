# Security Policy

## Supported Versions

CareerHub is a portfolio prototype. Security fixes are considered for the current
`main` branch only.

## Reporting a Vulnerability

Please do not disclose sensitive security issues publicly before maintainers have
had a reasonable chance to review them. For a future hosted repository, use
GitHub Security Advisories where available. If no private advisory channel is
available, open a minimal public issue that avoids exploit details and sensitive
data.

Do not include real resumes, application documents, API keys, database files,
model outputs containing personal data or local filesystem paths in reports.

## Local Data and Models

CareerHub is designed for local experimentation. Users are responsible for their
own local documents, generated application packages, SQLite databases, Ollama
models and environment variables. Do not commit `.env` files, runtime databases,
exports, uploads, logs or benchmark outputs.

## Scope

This project does not provide a hosted production service, managed security
operations or guaranteed response times.

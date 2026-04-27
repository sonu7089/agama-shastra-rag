# Security Policy

## Supported Scope

This repository is an experimental application and research workflow. Security fixes are handled on a best-effort basis.

## Reporting a Vulnerability

Please do not open a public issue for suspected vulnerabilities.

Instead, report:

- the affected file or component
- the impact
- reproduction steps
- any proof-of-concept details needed to verify the issue

Send the report privately to the repository maintainer through the contact channel listed on the repository profile.

## Sensitive Areas

Please be especially careful around:

- `.env` secrets
- Gemini and Hugging Face tokens
- checked-in corpus data and derived artifacts
- any future API endpoints that expose retrieval or chat functionality

## Disclosure

Please allow reasonable time for investigation and remediation before public disclosure.

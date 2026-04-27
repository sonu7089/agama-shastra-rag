# Contributing

## Scope

This repository contains an experimental RAG pipeline for Agama-related source material. Contributions should improve correctness, maintainability, or reproducibility without overstating the project's maturity.

## Ground Rules

- Keep changes focused and reviewable.
- Do not add undocumented features or unsupported claims to the README.
- Preserve existing data unless the change explicitly updates corpus artifacts.
- Prefer small, testable modules over large prompt-only changes.

## Development Setup

1. Create a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env`.
4. Add `GEMINI_API_KEY` and `HF_TOKEN`.

## Recommended Workflow

1. Create a branch from `main`.
2. Make the smallest change that solves the problem.
3. Run relevant verification locally.
4. Update documentation if behavior, setup, or outputs changed.
5. Open a pull request with a clear summary, rationale, and test notes.

## Verification

Before submitting, run what is relevant:

```bash
python -m compileall src tests
pytest
```

If a change affects retrieval or enrichment behavior, include a short note describing:

- what you changed
- how you verified it
- any known limitations or follow-up work

## Pull Request Guidelines

- Use a precise title.
- Describe user-visible impact first.
- Mention configuration or data migration requirements.
- Include logs or terminal output only when it helps reviewers validate behavior.

## Documentation Expectations

- Keep README claims aligned with the actual repository state.
- Mark assumptions explicitly when corpus provenance or behavior is unclear.
- Do not describe the static frontend as production-ready unless the backend exists and is documented.

## What and why

<!-- What does this change, and which problem does it solve? Link issues with "Fixes #123". -->

## Checklist

- [ ] No real DSKs, PINs or SmartStart strings anywhere (synthetic DSKs start with `12345`)
- [ ] Tests added or updated; `pytest`, `ruff check .`, `ruff format --check .` and `mypy` pass
- [ ] The core (`core.py`) still uses only the standard library
- [ ] CLI output unchanged, or the change is intended and `tests/test_regression.py` is updated
- [ ] Entry added to `CHANGELOG.md` under `[Unreleased]`

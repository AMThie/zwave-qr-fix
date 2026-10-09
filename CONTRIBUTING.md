# Contributing

Thanks for helping! Bug reports, newly affected devices, and code are all welcome.

## Golden rule: never share a real DSK

The DSK (and its first block, the PIN) is part of a device's S2 security.
**Do not put real DSKs, PINs or complete SmartStart strings** into issues,
pull requests, tests, examples or commit messages.

- Mask them in reports: `90012345...` → `9001xxxxx…`, `12345-23456-…` → `xxxxx-xxxxx-…`.
- Test data must be synthetic. By convention, **every synthetic DSK starts
  with the block `12345`**. A pre-commit hook and CI reject anything else that
  looks like a DSK.

## Reporting an affected device

Open an issue using the **Affected device** template. The manufacturer,
model, article number/EAN, the error message, and the *shape* of the
defect (e.g. "ends in `.9999999999999`") are enough. See [DEVICES.md](DEVICES.md).

## Development setup

You need Python 3.9 or newer and pip 25.1 or newer (for `--group`).

```bash
git clone https://github.com/AMThie/zwave-qr-fix.git
cd zwave-qr-fix
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[all]" --group dev
pre-commit install
```

## Checks

These are the same checks CI runs:

```bash
pytest --cov          # tests and coverage
ruff check .          # lint
ruff format .         # format
mypy                  # strict type check (targets Python 3.9)
pre-commit run --all-files
```

### Cross-check against Z-Wave JS

CI also validates our output with the reference parser from
[`@zwave-js/core`](https://www.npmjs.com/package/@zwave-js/core). Run it
locally with Node.js 20+:

```bash
python crosscheck/generate_vectors.py > crosscheck/vectors.json
cd crosscheck && npm ci && npm run crosscheck
```

## Ground rules for changes

- **The core stays dependency-free.** `src/zwave_qr_fix/core.py` may only use
  the standard library. Optional features go into extras (`[image]`, `[png]`).
- **CLI output is a contract.** People paste it into forums and scripts may
  parse it. `tests/test_regression.py` pins the exact output for the Heatit
  defect. If a change alters it on purpose, update the test and mention it
  in the changelog.
- **Python 3.9 compatibility.** ruff and mypy check against 3.9.
- Add or update tests for every behaviour change.
- Add a line under `## [Unreleased]` in [CHANGELOG.md](CHANGELOG.md).

## Commit messages

We use [Conventional Commits](https://www.conventionalcommits.org/):
`fix: …`, `feat: …`, `docs: …`, `test: …`, `ci: …`, `build: …`, `chore: …`,
`refactor: …`, `style: …`. Keep commits small and focused on one topic.

# Contributing

Thanks for helping improve `ofmx2pgsql`. This repository is maintained by SkyAlgorithm and aims to stay small, auditable, and reliable.

## Quick Start
- Install locally: `pip install -e .`
- Fetch sample data: `scripts/fetch_ofmx.sh`
- Run tests: `python -m unittest discover -s tests`
- Run a dry import: `python -m ofmx2pgsql import --config config/ofmx2pgsql.example.ini --dry-run --verbose`

## Code Style
- Use 4-space indentation and keep line lengths reasonable.
- Prefer explicit names and small functions over compact logic.
- Keep type hints where they improve clarity.
- Avoid adding large data files to the repo (use `scripts/fetch_ofmx.sh`).

## Pull Requests
Please include:
- A short summary of what changed and why.
- Any new commands or flags (with examples).
- Tests or validation steps run locally.

## Scope
Focus changes on OFMX parsing, schema evolution, and import reliability. If you are proposing major new features, open an issue first.

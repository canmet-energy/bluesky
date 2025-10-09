# Bluesky AI Agent Instructions

Concise, project-specific guidance for AI coding agents working in this repo.

## 1. Project Purpose & Architecture
- Python package `bluesky` (CLI-centric) offering a styled greeting plus future extensibility.
- Layers:
  - `bluesky.cli.main`: User-facing CLI via Click + Rich + PyFiglet.
  - `bluesky.utils.dependencies`: External dependency bootstrap (notably OpenStudio) reading config from `[tool.bluesky.dependencies]` in `pyproject.toml`.
  - `bluesky.core`: Reserved for domain/business logic (currently empty scaffold).
  - Dev environment infra under `.devcontainer/` (tool installers + robust certificate management script `certctl-safe.sh`).
- Certificate management is a first-class concern so that development works inside corporate proxy / MITM environments; environment variables (e.g. `CURL_FLAGS`, `CERT_STATUS`) drive downstream install scripts.

## 2. Key Workflows
- Install (editable): `pip install -e .` or `pip install -e ".[dev]"` (Python >=3.12 enforced in `pyproject.toml`).
- Run CLI: `bluesky --help`, examples in README.
- Dependency manager: `bluesky-deps --check-only` or `--auto-install` to fetch external (OpenStudio) pieces.
- Tests: `pytest` (config in `[tool.pytest.ini_options]`; markers: `unit`, `integration`, `slow`). Keep new tests in `tests/unit/` unless exercising cross-component flows.
- Lint / Format: `ruff check src/ --fix`, `black src/`, `mypy src/` (mypy mostly permissive; `ignore_missing_imports = true`).
- DevContainer build: relies on scripts in `.devcontainer/scripts/` which respect `CURL_FLAGS` and certificate state.

## 3. Certificate & Networking Model
- User adds corporate certs into `.devcontainer/certs/*.crt|*.pem` before container build.
- Build path: copy certs -> `certctl-safe.sh certs-refresh` -> populate `/usr/local/share/ca-certificates/custom` -> `update-ca-certificates`.
- Runtime probe (strict): all predefined HTTPS targets must succeed or environment flips to INSECURE (adds `-k` via `CURL_FLAGS`, sets `NODE_TLS_REJECT_UNAUTHORIZED=0`, etc.).
- Custom cert detection sets status `SECURE_CUSTOM`. Unknown -> conservative secure defaults.
- When modifying install scripts, always source `certctl-safe.sh` or run `eval "$(certctl env)"` early so subsequent downloads reuse correct TLS flags.

## 4. Project Conventions
- CLI options use explicit `show_default=True` and narrow `Choice` enumerations for colors.
- Rich output preferred for user-facing text; plain `print` avoided. Follow existing style (Panels, Text color tokens like `[bold cyan]`).
- Central config: version pins & dependency metadata live in `pyproject.toml`; duplicate version strings in code (e.g. `click.version_option`) should be kept in sync manually (no dynamic version import yet).
- Dependency discovery: `_load_dependency_config()` searches multiple fallbacks; extend by appending new search paths instead of altering existing order.
- Avoid adding heavy logic to `cli.main`; move expansion logic into `core/` modules to preserve a thin CLI layer.

## 5. Adding Features
- New CLI command: create a new module under `bluesky/cli/`, register via a group command (might need to refactor current single-command structure into a Click group first). Provide tests in `tests/unit/` verifying option parsing and output text (use `capsys` or Click's CliRunner).
- New dependency management step: add helper method to `DependencyManager`; expose flag in `dependencies.py`; reflect configurable values in `[tool.bluesky.dependencies]`.
- External downloads: always honor `CURL_FLAGS` (exported by certctl) or use `requests` which respects `REQUESTS_CA_BUNDLE`.

## 6. Testing Patterns
- Use small, direct tests for CLI (invoke main via Click testing utilities; avoid spawning subprocess unless necessary).
- Mark longer or network dependent tests with `@pytest.mark.slow` or `@pytest.mark.integration` to keep default test runs fast.
- When touching cert logic, prefer adding shell-level smoke test scripts outside Python scope only if essential; otherwise limit to Python unit tests mocking environment variables.

## 7. Tooling & Linting Nuances
- Ruff & Black: Black line-length 100; Ruff ignores E501 so rely on Black for wrapping.
- Mypy: permissive (many `disallow_*` flags off); introducing stricter typing should be incremental—avoid flipping global switches; add targeted `# type: ignore` sparingly.
- Per-file Ruff ignores allow unused imports in `__init__.py` and tests; keep new wildcard or convenience imports confined to those contexts.

## 8. External Integrations
- OpenStudio dependency is installed via platform-specific download (Debian `.deb` preferred). Avoid embedding platform logic elsewhere; extend inside `DependencyManager`.
- Rich / PyFiglet user experience is part of the brand; maintain colorful, readable defaults when expanding output.

## 9. Common Pitfalls & Gotchas
- Forgetting to rebuild DevContainer after adding certs -> custom certs not trusted (check with `certctl certs-status`).
- Adding CLI code that imports heavy libs at module import time slows command startup—delay heavy imports inside function bodies if they become sizable.
- Version mismatch: update both `pyproject.toml` and `click.version_option` simultaneously.
- Network issues: inspect `/var/log/certctl.log` (added logging) for probe & installation traces.

## 10. Quick Reference Paths
- CLI entry: `src/bluesky/cli/main.py`
- Dependency manager: `src/bluesky/utils/dependencies.py`
- Cert manager script: `.devcontainer/scripts/certctl-safe.sh`
- Cert drop-in dir: `.devcontainer/certs/`
- Tests: `tests/unit/` & `tests/integration/`

---
Feedback welcome: indicate unclear sections or missing patterns so this guide can iterate.

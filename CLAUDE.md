# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bluesky is a Python CLI application (Python >=3.12, <3.14) with a focus on corporate development environments. The project includes comprehensive certificate management for MITM proxy environments and external dependency bootstrapping (notably OpenStudio).

**Core Architecture:**
- `bluesky.cli.main`: User-facing CLI built with Click, Rich, and PyFiglet for styled terminal output
- `bluesky.utils.dependencies`: External dependency manager (OpenStudio installation with platform detection)
- `bluesky.core`: Reserved for domain logic (currently empty scaffold ready for expansion)
- `.devcontainer/`: DevContainer infrastructure with robust certificate management via `certctl-safe.sh`

**MCP Integration:**
The project includes MCP (Model Context Protocol) server configuration in `.mcp.json`:
- `aws-api-mcp-server`: AWS CLI command execution via uv tool
- `aws-knowledge-mcp-server`: AWS documentation and knowledge access
- Default region: `ca-central-1`

**DevContainer Features:**
- Python 3.12 with UV package manager (configurable via `DEVCONTAINER_UV_VERSION`, `DEVCONTAINER_PYTHON_VERSION`)
- Node.js 22.11.0 (configurable via `DEVCONTAINER_NODE_VERSION`)
- Optional GPU/AI stack (controlled by `ENABLE_GPU_AI` environment variable)
- WSLg support for GUI applications with X11 and Wayland
- Docker-in-Docker support
- Pre-configured VS Code extensions: Python, Black, MyPy, Jupyter, Claude Code, GitHub Copilot
- Automatic virtual environment activation via `/etc/profile.d/dev-env-init.sh`

## Build and Test Commands

### Installation
```bash
# Editable install
pip install -e .

# With dev dependencies
pip install -e ".[dev]"
```

### Running the Application
```bash
# Main CLI
bluesky --help
bluesky --name "Developer" --fancy --color cyan

# Verify energy simulation dependencies
python -c "import openstudio; import h2k_hpxml; print('✓ Energy simulation tools ready')"
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=bluesky

# Run specific test markers
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m "not slow"    # Skip slow tests

# Run single test file
pytest tests/unit/test_main.py

# Parallel execution (faster)
pytest -n auto
```

### Code Quality
```bash
# Format code
black src/

# Lint and auto-fix
ruff check src/ --fix

# Type checking
mypy src/

# Run all pre-commit hooks
pre-commit run --all-files

# Install pre-commit hooks
pre-commit install
```

## Key Architecture Patterns

### Certificate Management System

The project has a sophisticated certificate management system for corporate proxy environments:

**Flow:**
1. User places corporate certificates in `.devcontainer/certs/*.{crt,pem}` before container build
2. During build: `certctl-safe.sh certs-refresh` copies certs → validates → updates system store
3. At runtime: `certctl-safe.sh` probes HTTPS endpoints and sets environment mode:
   - `SECURE`: All probes pass, use strict TLS validation
   - `SECURE_CUSTOM`: Custom certs detected and all probes pass
   - `INSECURE`: Some probes fail, disable TLS verification (sets `-k`, `NODE_TLS_REJECT_UNAUTHORIZED=0`, etc.)
   - `UNKNOWN`: Probe timed out, use conservative secure defaults

**Critical exports managed by certctl:**
- Certificate paths: `SSL_CERT_FILE`, `CURL_CA_BUNDLE`, `REQUESTS_CA_BUNDLE`, `AWS_CA_BUNDLE`, `NODE_EXTRA_CA_CERTS`, `PIP_CERT`
- Security flags: `CURL_FLAGS`, `UV_NATIVE_TLS`, `UV_INSECURE_HOST`, `GIT_SSL_NO_VERIFY`, `NPM_CONFIG_STRICT_SSL`
- Status variables: `CERT_STATUS`, `CERT_SUCCESS_COUNT`, `CERT_FAIL_COUNT`

**When modifying install scripts:**
- Always source `certctl-safe.sh` early: `eval "$(certctl env)"` or `source /usr/local/bin/certctl && certctl_load`
- Use `$CURL_FLAGS` for all curl operations
- Check `/var/log/certctl.log` for certificate probe/install traces

### Dependency Configuration

Energy simulation dependencies (OpenStudio, EnergyPlus, OS-HPXML) are managed through the `h2k-hpxml` package:
```toml
dependencies = [
    "h2k-hpxml @ git+https://github.com/canmet-energy/h2k-hpxml.git@refactor",
    "openstudio==3.9.0",  # Installed via h2k-hpxml
    ...
]
```

The `h2k-hpxml` library handles platform-specific installation automatically, eliminating the need for manual dependency management.

### CLI Design

Current CLI is a single command. To add commands, refactor to Click command groups:
```python
@click.group()
def cli():
    pass

@cli.command()
def greet(...):
    # Current main() logic
    pass

@cli.command()
def new_feature(...):
    # New command logic
    pass
```

Keep CLI modules thin—move business logic to `bluesky.core/`.

## Development Conventions

### CLI Options
- Always use `show_default=True`
- Use `click.Choice()` for constrained values (see color options: cyan/green/yellow/red/magenta)
- Prefer Rich output (Panels, Text with style tags like `[bold cyan]`) over plain print

### Dependencies
- Energy simulation dependencies (OpenStudio, EnergyPlus) are managed via `h2k-hpxml` package
- Version pins in pyproject.toml must be manually synced with `click.version_option()` in CLI (no dynamic version import yet)
- All dependencies specified in `pyproject.toml` are installed automatically via pip/uv

### Testing
- Unit tests in `tests/unit/`, integration tests in `tests/integration/`
- Use Click's `CliRunner` for CLI testing (avoid subprocess spawning)
- Mark slow/network tests with `@pytest.mark.slow` or `@pytest.mark.integration`
- Use `capsys` fixture for output capture

### Code Style
- Black line-length: 100
- Ruff ignores E501 (line length handled by Black)
- MyPy is permissive (`ignore_missing_imports = true`, most `disallow_*` flags off)
  - Introduce stricter typing incrementally, avoid global mypy config changes
- Unused imports allowed in `__init__.py` and `tests/**` (per-file ignores in ruff config)

### External Downloads
- Always honor `CURL_FLAGS` exported by certctl
- For Python code using `requests`, it automatically respects `REQUESTS_CA_BUNDLE`
- UV/pip operations automatically configured via environment variables

## Common Workflows

### Adding a New CLI Command
1. Create new module under `bluesky/cli/` (may need to refactor `main.py` to command group first)
2. Implement command logic (keep thin, delegate to `bluesky.core/`)
3. Add tests in `tests/unit/` using `CliRunner`
4. Update `pyproject.toml` `[project.scripts]` if adding new entry point

### Adding Python Package Dependencies
1. Add dependencies to `dependencies` list in `pyproject.toml`
2. For complex external tools, prefer existing pip-installable wrappers (like `h2k-hpxml` for OpenStudio)
3. Use version constraints appropriately (`==` for exact, `>=` for minimum with security fixes)
4. Document any special installation requirements in README.md

### Troubleshooting Certificate Issues
1. Check cert status: `certctl certs-status`
2. Review probe log: `tail -f /var/log/certctl.log`
3. Test probe manually: `certctl probe` or `CERTCTL_DEBUG=1 certctl probe`
4. Verify certs placed in `.devcontainer/certs/` before rebuild
5. Rebuild container after adding certs

### Configuring DevContainer Environment
Key environment variables in `.devcontainer/devcontainer.json`:
- `DEVCONTAINER_PYTHON_VERSION`: Python version for venv (default: "3.12")
- `DEVCONTAINER_UV_VERSION`: UV package manager version (default: "0.8.15")
- `DEVCONTAINER_NODE_VERSION`: Node.js version (default: "22.11.0")
- `ENABLE_GPU_AI`: Enable GPU AI stack installation ("0" to disable, "1" to enable)
- `UV_PROJECT_ENVIRONMENT`: Path to project venv (default: `${containerWorkspaceFolder}/.venv`)

### Working with AWS MCP Servers
The project includes two AWS MCP servers configured in `.mcp.json`:
1. **aws-api-mcp-server**: Execute AWS CLI commands programmatically
   - Run via: `uv tool run awslabs.aws-api-mcp-server@latest`
   - Default region: `ca-central-1`
2. **aws-knowledge-mcp-server**: Access AWS documentation
   - Run via: `uv tool run fastmcp run https://knowledge-mcp.global.api.aws`

AWS credentials and SSO configuration handled by `.devcontainer/scripts/install-user-aws.sh`

## Important Files

- `src/bluesky/cli/main.py` - CLI entry point (currently single-command, ready for group refactor)
- `.devcontainer/scripts/certctl-safe.sh` - Certificate management script (sourced by install scripts)
- `.devcontainer/scripts/dev-env-init.sh` - Unified shell initialization script for venv activation and prompt
- `.devcontainer/scripts/post-create.sh` - DevContainer lifecycle hook
- `.devcontainer/scripts/install-user-aws.sh` - AWS CLI and SSO configuration installer
- `.devcontainer/scripts/install-user-uv.sh` - UV package manager installer
- `.devcontainer/scripts/install-user-nodejs.sh` - Node.js installer
- `.devcontainer/devcontainer.json` - DevContainer configuration with environment variables
- `.mcp.json` - MCP server configuration for AWS tools
- `pyproject.toml` - All configuration: dependencies, tool settings, version pins
- `tests/unit/test_main.py` - CLI test examples

## Version Management

**Critical:** Version is defined in two places and must be kept in sync:
1. `pyproject.toml`: `version = "0.1.0"`
2. `src/bluesky/cli/main.py`: `@click.version_option(version="0.1.0", ...)`

Update both simultaneously when bumping versions.

## Package Dependencies

Notable dependencies with specific roles:
- `h2k-hpxml` - NRCan's H2K to HPXML library (includes OpenStudio and EnergyPlus installation)
- `openstudio==3.9.0` - Energy modeling library (installed via h2k-hpxml)
- `click` - CLI framework
- `rich` - Terminal formatting and output
- `pyfiglet` - ASCII art generation
- `pandas`, `numpy` - Data processing
- `requests>=2.32.4` - HTTP client (respects `REQUESTS_CA_BUNDLE`, CVE-2024-47081 fixed)

## Pre-commit Hooks

Configured hooks (`.pre-commit-config.yaml`):
- trailing-whitespace, end-of-file-fixer
- YAML/JSON/TOML validation
- Black formatting (Python 3.11 target)
- Ruff linting with auto-fix

Run `pre-commit install` to enable automatic checks on commit.

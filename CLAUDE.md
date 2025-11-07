# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bluesky is a comprehensive template for building energy simulation application development, supporting **Python**, **Ruby**, and **Hot2000** with full language interoperability. The project serves as a starting point for simulation research and development, with over 30 working examples demonstrating complete workflows.

**Core Architecture:**
- `bluesky.cli.main`: User-facing CLI built with Click, Rich, and PyFiglet for styled terminal output
- `bluesky.core.interop`: Python↔Ruby interoperability utilities for mixed-language workflows
- `examples/`: Comprehensive collection of 30+ working examples
  - `examples/python/`: Python OpenStudio and Hot2000 workflows (11 examples)
  - `examples/ruby/`: Ruby OpenStudio and openstudio-standards workflows (10 examples)
  - `examples/interop/`: Python-Ruby interop workflows (4+ complete workflows)
  - `examples/data/`: Shared test models and reference data
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

**Ruby Environment:**
- Ruby 3.2.2 via rbenv (configurable via `DEVCONTAINER_RUBY_VERSION`)
- Bundler for gem management
- openstudio gem (OpenStudio Ruby SDK)
- openstudio-standards gem v0.8.4 (NECB, ASHRAE 90.1, DOE prototypes)

**Hot2000 Integration:**
- Hot2000 CLI wrapper at `/home/vscode/.local/bin/hot2000`
- Runs via Wine with headless-first optimization
- h2k-hpxml Python library for H2K → HPXML → EnergyPlus workflows

## Examples and Workflows

The repository includes **3 proof-of-concept examples** demonstrating key capabilities enabled by the Python-Ruby-Hot2000 environment.

**Example Structure:**
```
examples/
├── README.md                           # Complete guide and decision matrix
├── 01_python_hot2000_workflow/
│   ├── README.md                       # Detailed documentation
│   └── h2k_to_energyplus.py           # H2K → HPXML → EnergyPlus
├── 02_ruby_necb_compliance/
│   ├── README.md                       # NECB guide
│   └── create_necb_model.rb           # NECB-compliant model generation
├── 03_python_ruby_interop/
│   ├── README.md                       # Interop patterns
│   ├── create_model.rb                # Ruby: NECB model
│   └── runner.py                       # Python: orchestrator + analysis
└── data/                               # Test models and reference data
    ├── models/
    └── reference/
```

**The Three Examples:**

1. **Python Hot2000 Workflow** (`01_python_hot2000_workflow/`)
   - Demonstrates H2K → HPXML → EnergyPlus translation
   - Uses h2k-hpxml library (Python-exclusive)
   - Canadian residential building simulation

2. **Ruby NECB Compliance** (`02_ruby_necb_compliance/`)
   - Creates National Energy Code of Canada compliant models
   - Uses openstudio-standards gem (Ruby-exclusive)
   - Canadian commercial building code compliance

3. **Python-Ruby Interop** (`03_python_ruby_interop/`)
   - Ruby creates standards-based model, Python analyzes
   - Demonstrates subprocess communication via JSON
   - Uses `bluesky.core.interop` utilities

**When to Use Each Language:**
- **Python:** Hot2000 workflows (h2k-hpxml), data analysis (pandas/numpy), parametric orchestration
- **Ruby:** NECB/ASHRAE compliance (openstudio-standards - no Python equivalent), native OpenStudio SDK
- **Interop:** Leverage both - Ruby for standards, Python for analysis

See `examples/README.md` for detailed documentation, decision guide, and extension ideas.

## Python-Ruby Interoperability

**Interop Utilities:**
- `src/bluesky/core/interop.py` - Python → Ruby helpers
- `src/bluesky/core/interop.rb` - Ruby → Python helpers

**Key Functions:**

Python calling Ruby:
```python
from bluesky.core.interop import run_ruby_script

result = run_ruby_script(
    'create_necb_model.rb',
    input_data={'climate_zone': '6', 'building_type': 'Office'}
)
model_path = result['model_path']
```

Ruby calling Python:
```ruby
require_relative 'bluesky/core/interop'

result = Bluesky::Interop.run_python_script(
  'analyze.py',
  input_data: { model_path: 'model.osm' }
)
```

**Data Exchange:**
- Primary: JSON via stdin/stdout
- Alternative: JSON files for complex data structures
- Use `exchange_via_file()` and `read_exchange_file()` helpers

**Common Interop Patterns:**
1. **Ruby model creation + Python analysis** - Leverage openstudio-standards then analyze with pandas
2. **H2K translation + Ruby enhancement** - Translate with Python h2k-hpxml, enhance with Ruby standards
3. **Parametric orchestration** - Python orchestrates, Ruby generates standards-based variants
4. **Engine comparison** - Python runs Hot2000, Ruby runs OpenStudio, Python compares

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

## Error Debugging Protocol

This repository includes comprehensive error documentation to assist with debugging building energy simulation workflows. When users encounter errors, follow this debugging protocol:

### Error Documentation Structure

```
docs/
├── error-solutions/
│   ├── energyplus-errors.md          # Top 30 EnergyPlus errors with solutions
│   ├── openstudio-errors.md          # Top 20 OpenStudio SDK errors (Python & Ruby)
│   └── hot2000-errors.md              # Hot2000 CLI and h2k-hpxml library errors
└── idf-format/
    └── debugging-guide.md             # IDF file structure and debugging
```

### When to Use Each Guide

**User reports simulation failure:**
1. **Identify error source** - Where did the error occur?
   - During model creation (Python/Ruby code) → `openstudio-errors.md`
   - During forward translation (OSM → IDF) → `openstudio-errors.md`
   - During EnergyPlus simulation → `energyplus-errors.md`
   - During Hot2000 workflow → `hot2000-errors.md`

2. **Search the appropriate guide** for the specific error message

3. **Check IDF debugging guide** if error involves geometry, HVAC nodes, or IDF objects

**Example workflow for "Surface has no construction" error:**
```python
# User gets error: "Surface 'Wall 1' has no construction assigned"

# Step 1: Search openstudio-errors.md for "construction"
# Find: Error #17 - Missing Default Construction Set

# Step 2: Apply solution from guide (both Python and Ruby examples provided)
# Step 3: Re-run simulation
```

### Error Debugging Quick Reference

| Error Pattern | Check This Guide | Common Causes |
|--------------|------------------|---------------|
| "Zone not found", "Surface not assigned" | openstudio-errors.md | Object relationship issues |
| "Severe **", "Fatal **" in eplusout.err | energyplus-errors.md | EnergyPlus simulation errors |
| "Node connection error", "HVAC" | energyplus-errors.md + idf-format/debugging-guide.md | HVAC topology issues |
| "H2KParsingError", "Wine error" | hot2000-errors.md | Hot2000 workflow issues |
| "Forward translation failed" | openstudio-errors.md | Model validation failures |
| Geometry errors, vertex issues | openstudio-errors.md + idf-format/debugging-guide.md | Surface definition problems |

### Reading Error Files

**Python/Ruby exceptions:**
- File and line number show where error occurred in user code
- Error type (RuntimeError, ValueError, etc.) indicates category
- Message explains what went wrong

**EnergyPlus errors (eplusout.err):**
- `** Warning **` - Review but may be acceptable
- `** Severe  **` - Must fix, results invalid
- `**  Fatal  **` - Simulation stops
- `**   ~~~   **` - Additional context for error above

**Forward Translator warnings:**
- `<1>` Info/Warning
- `<2>` Warning (should review)
- `<3>` Error (will cause problems)

### Common Error Patterns

**Pattern 1: "Object Not Assigned"**
```python
# Symptom: Spaces not assigned to zones, surfaces not assigned to spaces
# Solution: Always establish parent-child relationships
space.setThermalZone(zone)      # Space → Zone
surface.setSpace(space)          # Surface → Space
```

**Pattern 2: "Optional Not Initialized"**
```python
# Symptom: NoneType errors (Python), NoMethodError (Ruby)
# Solution: Always check optional return values
model_optional = openstudio.model.Model.load(path)
if model_optional.is_initialized():
    model = model_optional.get()
else:
    raise RuntimeError("Failed to load model")
```

**Pattern 3: "Translation Failed"**
```python
# Symptom: Empty workspace, missing IDF objects
# Solution: Check forward translator errors
translator = openstudio.energyplus.ForwardTranslator()
workspace = translator.translateModel(model)
if translator.errors():
    for error in translator.errors():
        print(f"Error: {error.logMessage()}")
```

### Emergency Debugging Checklist

When simulation completely fails:

**Environment Check:**
- [ ] Dependencies installed (run `validate_dependencies()` for Hot2000)
- [ ] OpenStudio found: `which openstudio`
- [ ] Wine installed (if using Hot2000 CLI): `which wine`

**Model Validation:**
- [ ] All surfaces assigned to spaces
- [ ] All spaces assigned to thermal zones
- [ ] All zones have thermostats (if conditioned)
- [ ] Constructions have material layers
- [ ] HVAC components connected to loops (if HVAC present)

**File Check:**
- [ ] Input files exist and are readable
- [ ] Output directory writable
- [ ] Check eplusout.err for EnergyPlus errors
- [ ] Check run/run.log for OpenStudio-HPXML errors (Hot2000 workflows)

**Common Quick Fixes:**
```python
# Fix 1: Validate dependencies (Hot2000)
from h2k_hpxml.api import validate_dependencies
status = validate_dependencies()
if not status['valid']:
    print("Missing:", status['missing'])

# Fix 2: Check translation errors
translator = openstudio.energyplus.ForwardTranslator()
workspace = translator.translateModel(model)
for error in translator.errors():
    print(error.logMessage())

# Fix 3: Validate H2K file encoding
# Try UTF-8, then ISO-8859-1 if UnicodeDecodeError
```

### Using Error Guides

**When user provides error message:**
1. Identify which component failed (OpenStudio, EnergyPlus, Hot2000)
2. Open appropriate error guide from `docs/error-solutions/`
3. Search for error message or similar pattern
4. Provide solution in user's language (Python or Ruby)
5. Reference line numbers from error guide if helpful

**When user shows code with issues:**
1. Identify the object types being used (Surface, Zone, HVAC, etc.)
2. Check openstudio-errors.md for common patterns with those objects
3. Verify required relationships are established
4. Check for optional return value handling

**When user needs IDF debugging:**
1. Direct them to `docs/idf-format/debugging-guide.md`
2. Show how to read eplusout.err (severity levels, context lines)
3. Explain IDF object relationships relevant to their error
4. Provide grep/search commands to find objects in IDF

### Resources for Different Error Types

**Python OpenStudio errors:**
- `docs/error-solutions/openstudio-errors.md` - Errors #1-20 with Python examples
- All examples show proper error handling with try/except

**Ruby OpenStudio errors:**
- `docs/error-solutions/openstudio-errors.md` - Same errors with Ruby examples
- Includes openstudio-standards specific errors (Error #11)

**EnergyPlus simulation errors:**
- `docs/error-solutions/energyplus-errors.md` - Top 30 errors with code fixes
- Solutions provided in both Python and Ruby

**Hot2000 workflow errors:**
- `docs/error-solutions/hot2000-errors.md` - Wine, h2k-hpxml, workflow errors
- Covers encoding issues, CLI problems, translation failures

**IDF understanding:**
- `docs/idf-format/debugging-guide.md` - Complete IDF tutorial
- Includes syntax, object relationships, debugging scenarios

### Error Guide Format

Each error guide follows this structure:
- **Error message** - Exact text user will see
- **Cause** - Why this error occurs
- **Solution** - Working code to fix it
- **Code examples** - In both Python and Ruby (where applicable)
- **Prevention** - How to avoid this error

This consistent format allows quick lookup and copy-paste solutions.

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

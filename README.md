# Bluesky

**A quick-start template for building energy simulation research and development.**

This repository provides researchers with a ready-to-use development environment for building energy simulation work. It's designed for researchers who need to focus on their R&D rather than configuration management. Use this as a starting point for your bluesky ideas. Future work will include access to MCP servers to support weather, simulation workflow, and building model development with Python and Ruby.  

## What's Included

### Pre-installed Core Tools
- **Python** (3.12+) - Modern Python environment with UV package manager
- **OpenStudio** (3.9.0) - Energy modeling and simulation platform
- **EnergyPlus** - Building energy simulation engine (included with OpenStudio)

### DevContainer Environment
- Full VS Code DevContainer support with reproducible builds
- Certificate management for corporate network environments (Place your corporate cert file in .devcontainer/certs)
- Pre-configured development tools (Black, Ruff, MyPy, Pytest)
- WSLg support for GUI applications
- Docker-in-Docker for containerized workflows (optional)

### Optional Installations
Additional tools available via optional install scripts:
- AWS CLI and MCP servers for cloud integration
- Node.js development stack
- GPU/AI development tools
- Custom development frameworks

## Getting Started

### Important: Project Workflow

**The `main` branch is always kept as a clean template with only the essential tools and dependencies for building energy simulation research.**

To start your research project:

1. **Fork or branch** from `main` to create your project workspace
2. **Develop your project** in your branch/fork
3. **Use your branch** to incubate and develop your project ideas
4. **Never commit project-specific code to `main`** - it remains the clean template

### Step 1: Fork or Branch This Repository

```bash
# Option A: Fork on GitHub (recommended for independent projects)
# Click "Fork" button on GitHub, then clone your fork

# Option B: Create a branch (for collaborative projects)
git clone https://github.com/yourusername/bluesky.git
cd bluesky
git checkout -b my-research-project
```

### Step 2: Open in DevContainer (Recommended)

**Prerequisites:**
- Docker Desktop installed and running
- VS Code with Remote-Containers extension

**Steps:**
1. Open the project folder in VS Code
2. When prompted, click "Reopen in Container"
3. Or use Command Palette: `Remote-Containers: Reopen in Container`

**What happens automatically:**
- Python 3.12 environment is configured with UV package manager
- OpenStudio and EnergyPlus are installed via the `h2k-hpxml` library
- All typical research Python dependencies from `pyproject.toml` are installed
- Certificate management is configured for NRCan network
- Development tools are ready (black, ruff, mypy, pytest)
- Optional: GPU AI stack (PyTorch with CUDA) if `ENABLE_GPU_AI=1` in devcontainer.json

### Step 3: Verify Installation

```bash
# Check that core tools are available
python -c "import openstudio; import h2k_hpxml; print('✓ Energy simulation tools ready')"

# Start developing your research project!
```

### Step 4: Optional Installations

The template includes optional install scripts in `.devcontainer/scripts/`. Run these as needed:

```bash
# AWS CLI and SSO configuration for cloud integration
bash .devcontainer/scripts/install-user-aws.sh

# Node.js (required for Claude CLI and GitHub Copilot CLI)
bash .devcontainer/scripts/install-user-nodejs.sh

# Claude CLI (requires Node.js)
bash .devcontainer/scripts/install-user-claude-cli.sh

# GitHub Copilot CLI (requires Node.js)
bash .devcontainer/scripts/install-user-github-copilot-cli.sh
```


### Alternative: Local Installation (Without DevContainer)

If you prefer not to use DevContainer:

```bash
# After cloning/forking
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install -e ".[dev]"

# Verify installation
python -c "import openstudio; import h2k_hpxml; print('✓ Energy simulation tools ready')"
```

**Note:** Local installation may require manual certificate configuration for NRCan network environments. OpenStudio and EnergyPlus are automatically installed as dependencies of the `h2k-hpxml` package.

### Example CLI (Template Placeholder)

The template includes a sample CLI application as a starting point:

```bash
# Sample greeting command
bluesky --help
bluesky --name "Researcher" --fancy --color cyan
```

**Replace this with your research application logic** as you develop your project.

## Development

### Running Tests
```bash
pytest
# Or with coverage:
pytest --cov=bluesky
```

### Code Formatting
```bash
black src/
ruff check src/ --fix
```

### Type Checking
```bash
mypy src/
```

### Pre-commit Hooks
```bash
pre-commit install
pre-commit run --all-files
```

## Project Structure

```
bluesky/
├── src/
│   └── bluesky/
│       ├── __init__.py
│       ├── cli/
│       │   ├── __init__.py
│       │   └── main.py          # Main CLI entry point
│       ├── core/                # Core business logic
│       └── utils/               # Utility modules
├── tests/
│   ├── unit/                    # Unit tests
│   └── integration/             # Integration tests
├── config/
│   └── defaults/                # Default configuration templates
├── .devcontainer/               # DevContainer configuration
│   ├── Dockerfile
│   ├── devcontainer.json
│   ├── certs/                   # Place your corporate certificate .crt file here and rebuild your container if required.
│   └── scripts/                 # Setup and utility scripts
├── pyproject.toml               # Project configuration
├── README.md                    # This file
└── .gitignore
```

## Configuration

Configuration templates are provided in `config/defaults/`. Copy and customize as needed:

```bash
cp config/defaults/config.template.ini config/config.ini
```

## NRCan Network Certificate Management

For researchers working on NRCan's corporate network with MITM proxy certificates:

### Automatic Certificate Handling

The DevContainer includes sophisticated certificate management via the `certctl` utility:

1. **Before building the container:** Place your corporate certificates (`.crt` or `.pem` files) in `.devcontainer/certs/`
2. **During container build:** Certificates are automatically validated and installed
3. **At runtime:** Network environment is detected and appropriate security settings are applied

### Certificate Status

```bash
# Check certificate configuration status
certctl certs-status

# View certificate probe logs
tail -f /var/log/certctl.log

# Test network connectivity
certctl probe
```

### Environment Modes

The system automatically configures itself based on network detection:
- **SECURE**: Standard TLS validation (external networks)
- **SECURE_CUSTOM**: Custom certificates with full validation (NRCan network)
- **INSECURE**: Validation disabled for troubleshooting (requires cert fix)

All Python, Node.js, UV, and system tools are automatically configured to work with the detected certificate environment.

## Key Dependencies

### Building Energy Simulation
- **h2k-hpxml** - NRCan's H2K to HPXML conversion library (includes OpenStudio and EnergyPlus)
- **OpenStudio** (3.9.0) - Energy modeling platform (via h2k-hpxml)
- **EnergyPlus** - Whole building energy simulation (bundled with OpenStudio)

### Python Development
- **Click**: CLI framework for building command-line tools
- **Rich**: Terminal formatting for beautiful output
- **Pandas & NumPy**: Data analysis and processing
- **Requests**: HTTP client (certificate-aware)
- **PyYAML**: Configuration file processing

### Development Tools
- **Black**: Code formatting
- **Ruff**: Fast Python linter
- **MyPy**: Static type checking
- **Pytest**: Testing framework
- **Pre-commit**: Git hook automation

See `pyproject.toml` for the complete dependency list and version pins.

## Contributing to the Template

If you've developed improvements to the **base template** (not project-specific code):

1. Create a feature branch from `main`
2. Make improvements to the template infrastructure
3. Ensure changes benefit all researchers (not project-specific)
4. Run tests and linting
5. Submit a pull request to `main`

**Examples of template contributions:**
- Improvements to certificate management
- New optional install scripts
- Enhanced dependency detection
- DevContainer configuration improvements
- Documentation updates

**Project-specific code should remain in your fork/branch**, not submitted to `main`.

## Support

For template issues and questions, please use the GitHub issue tracker.

For project-specific research questions, consult with your research team or supervisor.

## License

GPLv3 - See LICENSE file for details.

---

**Remember:** Fork or branch from `main` to start your research project. Keep `main` as the clean template for future projects.
# Bluesky

A Python application with comprehensive development environment setup, including certificate management and DevContainer support.

## Features

- 🚀 Modern Python application structure
- 🐳 Full DevContainer support with VS Code integration
- 🔒 Built-in certificate management for corporate environments
- 📦 Comprehensive dependency management
- 🎨 Rich CLI with colorful output and ASCII art
- 🛠️ Pre-configured development tools (Black, Ruff, MyPy, Pytest)

## Quick Start

### Option 1: Local Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/bluesky.git
cd bluesky
```

2. **Create a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install the package:**
```bash
pip install -e .
# Or with development dependencies:
pip install -e ".[dev]"
```

4. **Run the application:**
```bash
bluesky --help
bluesky --fancy --color cyan
bluesky --name "Your Name" --fancy
```

### Option 2: Using DevContainer (Recommended)

1. **Prerequisites:**
   - Docker Desktop installed and running
   - VS Code with Remote-Containers extension

2. **Open in DevContainer:**
   - Open the project folder in VS Code
   - When prompted, click "Reopen in Container"
   - Or use Command Palette: `Remote-Containers: Reopen in Container`

3. **The DevContainer provides:**
   - Python 3.12 environment
   - All dependencies pre-installed
   - Certificate management tools
   - Development tools (uv, black, ruff, etc.)
   - GitHub CLI and Claude CLI

## CLI Usage

### Basic Hello World
```bash
bluesky
# Output: Hello, World!
```

### Personalized Greeting
```bash
bluesky --name Alice
# Output: Hello, Alice!
```

### Fancy Mode with ASCII Art
```bash
bluesky --fancy
# Shows ASCII art banner and styled greeting
```

### Custom Colors
```bash
bluesky --fancy --color green --name "Developer"
# Shows green-colored fancy greeting
```

## Dependency Management

The project includes a dependency management tool:

```bash
# Check dependencies
bluesky-deps --check-only

# Auto-install missing dependencies
bluesky-deps --auto-install

# Interactive setup
bluesky-deps --setup
```

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
│       └── utils/
│           ├── __init__.py
│           └── dependencies.py   # Dependency management
├── tests/
│   ├── unit/                    # Unit tests
│   └── integration/             # Integration tests
├── config/
│   └── defaults/                # Default configuration templates
├── .devcontainer/               # DevContainer configuration
│   ├── Dockerfile
│   ├── devcontainer.json
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

## Certificate Management

For corporate environments with custom certificates, the DevContainer includes automatic certificate management through the `certctl` utility.

## Dependencies

The project includes the following major dependencies:
- **Click**: CLI framework
- **Rich**: Beautiful terminal formatting
- **Pyfiglet**: ASCII art generation
- **Pandas & NumPy**: Data processing capabilities
- **Requests**: HTTP client
- **PyYAML**: YAML processing
- And more...

See `pyproject.toml` for the complete list.

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## Support

For issues and questions, please use the GitHub issue tracker.
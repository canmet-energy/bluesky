# DevContainer Installation Scripts

This directory contains modular installation scripts for the Bluesky development container. These scripts make the Dockerfile cleaner, more maintainable, and allow for easier testing and reuse.

## Script Overview

### `certctl-safe.sh`
Unified certificate utility (strict-only) replaces all former certificate scripts. Handles certificate installation, probing, environment emission, and a user banner (MOTD snapshot functionality removed for simplicity).

Commands:
```
certctl install        # Install custom certs (idempotent)
certctl probe|status   # Live strict probe (all targets) --json/--quiet
certctl env            # Emit CERT_STATUS/CURL_FLAGS lines (use with eval)
certctl refresh        # Probe + update user banner
certctl banner         # Probe + update user banner, then print it
```

Strict only: any failure => INSECURE. Targets:
```
https://pypi.org/
https://registry.npmjs.org/
https://github.com/
https://cli.github.com/
https://download.docker.com/
https://nodejs.org/
https://awscli.amazonaws.com/
https://s3.amazonaws.com/
```

Exit codes:
```
0  SECURE / SECURE_CUSTOM
10 INSECURE
20 UNKNOWN
30 install error (certificate store)
```

### Core Scripts

#### `post-create.sh`
DevContainer lifecycle hook that runs after container creation:
- Sets up Python virtual environment with configurable version
- Installs project dependencies (including h2k-hpxml, OpenStudio, EnergyPlus)
- Optional: Installs GPU AI stack (PyTorch with CUDA) if `ENABLE_GPU_AI=1`
- Configures shell environment for automatic venv activation
- Configures Docker socket permissions
- Updates certificate status banner

#### `dev-env-init.sh`
Shell initialization script for venv activation and prompt customization:
- Automatically activated via `/etc/profile.d/dev-env-init.sh`
- Handles virtual environment activation
- Provides custom shell prompt

### User-Level Installation Scripts (No sudo required)

#### `install-user-uv.sh`
Installs UV Python package manager user-locally:
- Downloads from GitHub releases
- Installs to `~/.local/bin/uv`
- Configurable version via `DEVCONTAINER_UV_VERSION` environment variable
- Certificate-aware downloads using `CURL_FLAGS`

#### `install-user-nodejs.sh`
Installs Node.js user-locally for development tooling:
- Downloads Node.js binary distribution
- Installs to `~/.local/`
- Configurable version via `DEVCONTAINER_NODE_VERSION` environment variable
- Configures npm for certificate environments
- Certificate-aware downloads using `CURL_FLAGS`

#### `install-user-aws.sh`
Comprehensive AWS CLI setup with SSO and MCP integration:
- Installs AWS CLI v2 user-locally via AWS's official installer
- Supports x86_64 and aarch64 architectures automatically
- Installs AWS Session Manager plugin for EC2 access
- Configures AWS SSO for NRCan (ca-central-1 region, PowerUser role)
- Creates `aws-sync-sso` helper script to sync AWS Toolkit VSCode tokens with CLI
- Installs AWS Toolkit VSCode extension automatically
- Configures AWS MCP servers in `.mcp.json`:
  - `aws-api-mcp-server`: Natural language AWS API access
  - `aws-knowledge-mcp-server`: AWS documentation access
- Command-line options: `--help`, `--force`, `--quiet`
- Certificate-aware downloads using `CURL_FLAGS`

#### `install-user-claude-cli.sh`
Installs Claude CLI (Anthropic's command-line interface):
- Requires Node.js and npm (installed via `install-user-nodejs.sh`)
- Installs globally via npm: `@anthropic-ai/claude-cli`
- Provides comprehensive error handling and diagnostics
- Tests npm registry connectivity if installation fails
- Includes usage instructions and documentation links

#### `install-user-github-copilot-cli.sh`
Installs GitHub Copilot CLI:
- Requires Node.js and npm (installed via `install-user-nodejs.sh`)
- Installs globally via npm: `@githubnext/github-copilot-cli`
- Provides command-line AI assistance
- Certificate-aware installation

### System-Level Installation Scripts (Require sudo)

#### `install-system-csharp.sh`
Installs .NET SDK and C# development tools:
- Installs via apt from Microsoft's official repository
- Provides C# development capabilities
- Certificate-aware downloads using `CURL_FLAGS`

#### `install-system-docker-cli.sh`
Installs Docker CLI and Compose plugin:
- Adds Docker apt repository
- Installs docker-ce-cli and docker-compose-plugin
- Sets up docker group for vscode user
- Certificate-aware repository key download using `CURL_FLAGS`

#### `install-system-github-cli.sh`
Installs GitHub CLI (`gh` command):
- Adds GitHub CLI apt repository
- Installs via apt package manager
- Provides `gh` command for GitHub operations
- Certificate-aware repository key download using `CURL_FLAGS`

## Benefits of Modular Approach

1. **Maintainability**: Each tool installation is isolated and easier to update
2. **Testing**: Individual scripts can be tested separately
3. **Reusability**: Scripts can be used outside of Docker context
4. **Debugging**: Easier to identify issues with specific installations
5. **Clean Dockerfile**: Main Dockerfile remains focused on structure, not implementation details
6. **Version Management**: Tool versions are centralized in individual scripts

## Usage

### In DevContainer

The scripts are designed to be used within the Bluesky DevContainer environment. The `post-create.sh` script automatically runs after container creation and handles core setup.

**Optional installations** can be run manually inside the container:

```bash
# Install AWS CLI with SSO and MCP integration
bash .devcontainer/scripts/install-user-aws.sh

# Install Node.js
bash .devcontainer/scripts/install-user-nodejs.sh

# Install Claude CLI (requires Node.js first)
bash .devcontainer/scripts/install-user-nodejs.sh
bash .devcontainer/scripts/install-user-claude-cli.sh

# Install GitHub Copilot CLI (requires Node.js first)
bash .devcontainer/scripts/install-user-github-copilot-cli.sh
```

### Environment Configuration

The DevContainer supports environment variables for version control in `.devcontainer/devcontainer.json`:

```json
{
  "containerEnv": {
    "DEVCONTAINER_PYTHON_VERSION": "3.12",
    "DEVCONTAINER_NODE_VERSION": "22.11.0",
    "DEVCONTAINER_UV_VERSION": "0.8.15",
    "ENABLE_GPU_AI": "0"
  }
}
```

## Corporate Network Support

Place `.crt` or `.pem` files in `.devcontainer/certs/` before build/rebuild. Installed via `certctl install` into system trust store.

Runtime behavior:
- `certctl probe` tests live connectivity (strict only)
- Shell startup uses a per-user banner only (no /etc/motd.d writes)
- `certctl banner` prints latest live banner
- `certctl env` supplies `CERT_STATUS` and `CURL_FLAGS`

Statuses returned by probe:
- `SECURE` – All targets succeeded with base store.
- `SECURE_CUSTOM` – All targets succeeded and custom cert(s) detected.
- `INSECURE` – One or more targets failed under current condition.

JSON output (`certctl probe --json`) example (no legacy snapshot/divergence fields):
```json
{
  "status": "INSECURE",
  "curl_flags": "-fsSLk",
  "custom_certs": false,
  "timestamp": 1700000000,
  "success": 6,
  "fail": 2,
  "total": 8
}
```

Lenient mode removed: strict-only (all targets must succeed).

## Standalone Usage

Individual scripts can be run independently:

```bash
# Set certificate flags if needed
export CURL_FLAGS="-fsSL"  # or "-fsSLk" for insecure environments

# Install AWS CLI
.devcontainer/scripts/install-user-aws.sh

# Install Node.js and Claude CLI
.devcontainer/scripts/install-user-nodejs.sh
.devcontainer/scripts/install-user-claude-cli.sh
```

**Prerequisites:**
- Scripts assume a Debian/Ubuntu-based Linux environment
- User-level scripts don't require sudo
- System-level scripts require sudo access
- Some scripts have dependencies (e.g., Claude CLI requires Node.js)

## Installation Examples

### AWS CLI Installation
```bash
# Install with default settings
bash .devcontainer/scripts/install-user-aws.sh

# Force reinstall
bash .devcontainer/scripts/install-user-aws.sh --force

# Quiet mode
bash .devcontainer/scripts/install-user-aws.sh --quiet

# Show help
bash .devcontainer/scripts/install-user-aws.sh --help
```

### Node.js Installation
```bash
# Install with version from environment variable
DEVCONTAINER_NODE_VERSION=20.10.0 bash .devcontainer/scripts/install-user-nodejs.sh

# Or use default version (22.11.0)
bash .devcontainer/scripts/install-user-nodejs.sh
```

### Claude/Copilot CLI Installation
```bash
# Requires Node.js to be installed first
bash .devcontainer/scripts/install-user-nodejs.sh
bash .devcontainer/scripts/install-user-claude-cli.sh
bash .devcontainer/scripts/install-user-github-copilot-cli.sh
```

## Security Scanning

### `security-scan.sh`
Comprehensive security scanning script that checks for vulnerabilities across multiple dimensions:
- **Python Dependencies**: Scans for known CVEs using pip-audit and Safety
- **Python Code**: Static analysis with Bandit to detect security issues
- **Node.js Dependencies**: npm audit on global packages (if installed)
- **Installed Tool Inventory**: Version tracking for Python, Node.js, AWS CLI, GitHub CLI, Docker
- **Container Configuration**: Scans DevContainer configs with Trivy
- **System Packages**: Checks for available security updates (apt)
- **Shell Scripts**: Pattern analysis for dangerous shell constructs

**Features:**
- Auto-installs required security tools (pip-audit, bandit, safety, trivy)
- Automatically detects and scans optional tools installed via install-*.sh scripts
- Generates JSON reports and consolidated Markdown summary
- Provides actionable remediation recommendations
- Supports quick scans and custom output directories
- Gracefully skips unavailable tools with informative warnings

**Usage:**
```bash
# Full security scan (recommended weekly)
.devcontainer/scripts/security-scan.sh

# Quick scan (skips slower container scans)
.devcontainer/scripts/security-scan.sh --quick

# Custom output directory
.devcontainer/scripts/security-scan.sh --output-dir /workspace/security-reports

# Skip tool installation (if already installed)
.devcontainer/scripts/security-scan.sh --skip-install

# Show help
.devcontainer/scripts/security-scan.sh --help
```

**Output:**
Reports are saved to timestamped directories:
- `/tmp/security-reports/YYYYMMDD_HHMMSS/security-report.md` - Main consolidated report
- `/tmp/security-reports/YYYYMMDD_HHMMSS/pip-audit.json` - Python dependency vulnerabilities
- `/tmp/security-reports/YYYYMMDD_HHMMSS/bandit.json` - Python code security issues
- `/tmp/security-reports/YYYYMMDD_HHMMSS/npm-audit.json` - Node.js dependency vulnerabilities (if installed)
- `/tmp/security-reports/YYYYMMDD_HHMMSS/npm-global-packages.json` - Installed npm packages
- `/tmp/security-reports/YYYYMMDD_HHMMSS/installed-versions.txt` - Tool version inventory
- `/tmp/security-reports/YYYYMMDD_HHMMSS/trivy-*.json` - Container/config scans
- `/tmp/security-reports/YYYYMMDD_HHMMSS/dpkg-packages.txt` - System packages
- `/tmp/security-reports/YYYYMMDD_HHMMSS/security-updates.txt` - Available security updates
- `/tmp/security-reports/YYYYMMDD_HHMMSS/safety.json` - Alternative Python dependency check

**Exit Codes:**
- `0` - Scan completed successfully, no critical issues
- `1` - Scan failed or critical vulnerabilities found
- `2` - Invalid arguments

**Recommended Schedule:**
- **Weekly**: Full scan during development
- **Pre-commit**: Quick scan before major commits
- **CI/CD**: Automated scanning in pipeline
- **After dependency updates**: Full scan to verify no new vulnerabilities

## Updating Tool Versions

To update tool versions, modify environment variables or script defaults:
- **UV**: Set `DEVCONTAINER_UV_VERSION` environment variable
- **Node.js**: Set `DEVCONTAINER_NODE_VERSION` environment variable
- **Python**: Set `DEVCONTAINER_PYTHON_VERSION` environment variable
- **AWS CLI**: Always installs latest v2 from AWS
- **Claude CLI**: Always installs latest from npm registry
- **GitHub Copilot CLI**: Always installs latest from npm registry
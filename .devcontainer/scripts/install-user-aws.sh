#!/bin/bash
set -euo pipefail

echo "â˜ï¸ Installing AWS CLI (user-local)..."

# Certificate environment now handled by certctl if present
CURL_FLAGS="${CURL_FLAGS:--fsSL}"

HELP=false
FORCE=false
QUIET=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            HELP=true; shift ;;
        -f|--force)
            FORCE=true; shift ;;
        -q|--quiet)
            QUIET=true; shift ;;
        *)
            echo "âŒ Unknown option: $1" >&2
            echo "Use --help for usage information" >&2
            exit 2 ;;
    esac
done

if [ "$HELP" = true ]; then
    cat <<'EOF'
Usage: install-system-aws-cli.sh [OPTIONS]

User-local installation of AWS CLI v2 (no sudo required).

Options:
  -h, --help      Show this help text and exit
  -f, --force     Reinstall even if an existing installation is detected
  -q, --quiet     Reduce non-error output

Behavior:
  * Installs under:   ~/.local/aws-cli
  * Symlinks/bin under ~/.local/bin (added to PATH if missing)
  * Idempotent: skips install when aws binary already present unless --force
  * Installs Session Manager plugin into ~/.local/bin (best-effort)
  * Respects CURL_FLAGS for corporate TLS / proxy environment

Examples:
  ./install-system-aws-cli.sh          # Install if not already installed
  ./install-system-aws-cli.sh --force  # Reinstall

Note: Original system-wide variant replaced because container has single user.
EOF
    exit 0
fi

log() {
    if [ "$QUIET" = false ]; then
        echo -e "$1"
    fi
}

AWS_LOCAL_DIR="$HOME/.local/aws-cli"
USER_BIN_DIR="$HOME/.local/bin"
AWS_BIN_LINK="$USER_BIN_DIR/aws"

mkdir -p "$USER_BIN_DIR"

# Ensure PATH contains user bin for subsequent shells (idempotent)
ensure_path_export() {
    local export_line="export PATH=\"$USER_BIN_DIR:\$PATH\""
    for rc in "$HOME/.bashrc" "$HOME/.profile"; do
        if [ -f "$rc" ]; then
            if ! grep -F "$USER_BIN_DIR" "$rc" >/dev/null 2>&1; then
                echo "$export_line" >> "$rc"
            fi
        else
            echo "$export_line" >> "$rc"
        fi
    done
}
ensure_path_export
export PATH="$USER_BIN_DIR:$PATH"

AWS_CLI_SKIP_INSTALL=false
if command -v aws >/dev/null 2>&1 && [ "$FORCE" = false ]; then
    CURRENT_PATH="$(command -v aws)"
    if [[ "$CURRENT_PATH" == "$AWS_BIN_LINK" || "$CURRENT_PATH" == $AWS_LOCAL_DIR/* ]]; then
        log "âœ… AWS CLI already installed at $CURRENT_PATH (use --force to reinstall)"
        AWS_CLI_SKIP_INSTALL=true
    else
        log "â„¹ï¸  An AWS CLI already exists at $CURRENT_PATH (outside user-local target). Use --force to override with user-local install."
        AWS_CLI_SKIP_INSTALL=true
    fi
fi


# Function to install AWS CLI v2 via official installer
install_aws_cli_user() {
    log "ðŸ“¦ Installing AWS CLI v2 (user-local)..."

    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64)    AWS_INSTALLER_URL="https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" ;;
        aarch64|arm64) AWS_INSTALLER_URL="https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" ;;
        *) echo "âŒ Unsupported architecture: $ARCH" >&2; exit 1 ;;
    esac

    TMP_DIR="$(mktemp -d)"
    trap 'rm -rf "$TMP_DIR"' EXIT

    log "ðŸ—ï¸  Architecture: $ARCH"
    log "ðŸ“¥ Downloading AWS CLI v2 installer..."
    curl ${CURL_FLAGS} -o "$TMP_DIR/awscliv2.zip" "$AWS_INSTALLER_URL"
    if [ ! -s "$TMP_DIR/awscliv2.zip" ]; then
        echo "âŒ Download failed (empty file)" >&2; exit 1
    fi
    log "ðŸ“‚ Extracting..."
    unzip -q "$TMP_DIR/awscliv2.zip" -d "$TMP_DIR"

    log "âš™ï¸  Running installer to $AWS_LOCAL_DIR ..."
    rm -rf "$AWS_LOCAL_DIR"
    mkdir -p "$AWS_LOCAL_DIR"
    "$TMP_DIR/aws/install" --install-dir "$AWS_LOCAL_DIR" --bin-dir "$USER_BIN_DIR"

    # Ensure symlink exists (installer normally handles this)
    if [ ! -f "$AWS_BIN_LINK" ]; then
        ln -sf "$AWS_LOCAL_DIR/v2/current/bin/aws" "$AWS_BIN_LINK"
    fi
}





if [ "$AWS_CLI_SKIP_INSTALL" = false ]; then
    install_aws_cli_user
fi

# Verify installation (only if we just installed)
if [ "$AWS_CLI_SKIP_INSTALL" = false ]; then
    echo "ðŸ” Verifying AWS CLI installation..."
    if ! command -v aws >/dev/null 2>&1; then
        echo "âŒ aws not found in PATH after install" >&2; exit 1
    fi
    INSTALLED_VERSION=$(aws --version 2>&1 || true)
    echo "âœ… AWS CLI installed"
    echo "   Version: $INSTALLED_VERSION"
    echo "   Binary: $(command -v aws)"
    echo "   Root Dir: $AWS_LOCAL_DIR"
    echo "   User Bin: $USER_BIN_DIR"

    echo "ðŸ§ª Testing basic command..."
    if aws help >/dev/null 2>&1; then
        echo "âœ… Help command OK"
    else
        echo "âš ï¸  Help command returned non-zero (continuing)"
    fi
fi

echo "ï¿½ Attempting user-local Session Manager plugin install..."
SM_TMP="$(mktemp -d)"; trap 'rm -rf "$SM_TMP"' RETURN
if curl ${CURL_FLAGS} "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin.deb" -o "$SM_TMP/session-manager-plugin.deb" 2>/dev/null; then
    if command -v dpkg-deb >/dev/null 2>&1 && dpkg-deb -x "$SM_TMP/session-manager-plugin.deb" "$SM_TMP/extracted" 2>/dev/null; then
        BIN_CANDIDATE="$SM_TMP/extracted/usr/local/sessionmanagerplugin/bin/session-manager-plugin"
        if [ -f "$BIN_CANDIDATE" ]; then
            cp "$BIN_CANDIDATE" "$USER_BIN_DIR/session-manager-plugin" || true
            chmod +x "$USER_BIN_DIR/session-manager-plugin" || true
            if command -v session-manager-plugin >/dev/null 2>&1; then
                echo "âœ… Session Manager plugin installed user-locally"
            else
                echo "âš ï¸  Session Manager plugin copy finished but not on PATH"
            fi
        else
            echo "â„¹ï¸  Session Manager plugin binary layout unexpected; skipping"
        fi
    else
        echo "â„¹ï¸  Could not extract session manager plugin; dpkg-deb missing or extraction failed"
    fi
else
    echo "â„¹ï¸  Session Manager plugin download skipped/failed (non-fatal)"
fi

if [ "$AWS_CLI_SKIP_INSTALL" = false ]; then
    echo "ðŸŽ‰ AWS CLI user-local installation complete!"
fi

# Configure AWS CLI with SSO settings for NRCan
echo "âš™ï¸  Configuring AWS CLI with default SSO profile..."
mkdir -p ~/.aws

# Only create config if it doesn't already exist
if [ ! -f ~/.aws/config ]; then
    cat > ~/.aws/config << 'EOF'
[default]
sso_start_url = https://nrcan-rncan.awsapps.com/start
sso_region = ca-central-1
sso_account_id = 834599497928
sso_role_name = PowerUser
region = ca-central-1
output = json
EOF
    echo "âœ… AWS CLI SSO config created at ~/.aws/config"
else
    echo "â„¹ï¸  AWS config already exists at ~/.aws/config (skipping)"
fi

# Create helper script to sync AWS Toolkit SSO tokens with AWS CLI
cat > "$USER_BIN_DIR/aws-sync-sso" << 'SYNCEOF'
#!/bin/bash
# Sync AWS Toolkit VSCode SSO tokens with AWS CLI
# This allows you to login once via AWS Toolkit and use the same session in CLI

SSO_CACHE_DIR="$HOME/.aws/sso/cache"
SSO_START_URL="https://nrcan-rncan.awsapps.com/start"

# Calculate the expected filename for AWS CLI
EXPECTED_HASH=$(echo -n "$SSO_START_URL" | sha1sum | awk '{print $1}')
EXPECTED_FILE="$SSO_CACHE_DIR/$EXPECTED_HASH.json"

# Find the AWS Toolkit token file (contains accessToken)
TOOLKIT_TOKEN=$(find "$SSO_CACHE_DIR" -name "*.json" -type f -exec grep -l "accessToken" {} \; 2>/dev/null | head -n 1)

if [ -z "$TOOLKIT_TOKEN" ]; then
    echo "âš ï¸  No AWS Toolkit SSO token found. Please login via AWS Toolkit in VSCode first."
    exit 1
fi

# Create or update symlink
if [ -L "$EXPECTED_FILE" ] || [ -f "$EXPECTED_FILE" ]; then
    rm -f "$EXPECTED_FILE"
fi

ln -sf "$TOOLKIT_TOKEN" "$EXPECTED_FILE"
echo "âœ… SSO token synced: AWS CLI can now use AWS Toolkit session"
echo "   Token: $(basename "$TOOLKIT_TOKEN")"
echo "   Linked to: $EXPECTED_HASH.json"
SYNCEOF

chmod +x "$USER_BIN_DIR/aws-sync-sso"
echo "âœ… Created helper script: aws-sync-sso"

# Sync tokens if AWS Toolkit has already created a token
if [ -d ~/.aws/sso/cache ]; then
    echo "ðŸ”„ Syncing existing AWS Toolkit SSO tokens..."
    "$USER_BIN_DIR/aws-sync-sso" 2>/dev/null || true
fi

# Install AWS Toolkit VS Code extension if not present
echo "ðŸ”Œ Checking for AWS Toolkit VS Code extension..."
if command -v code >/dev/null 2>&1; then
    EXTENSION_ID="amazonwebservices.aws-toolkit-vscode"
    if code --list-extensions 2>/dev/null | grep -q "^$EXTENSION_ID$"; then
        echo "âœ… AWS Toolkit extension already installed"
    else
        echo "ðŸ“¦ Installing AWS Toolkit VS Code extension..."
        if code --install-extension "$EXTENSION_ID" >/dev/null 2>&1; then
            echo "âœ… AWS Toolkit extension installed successfully"
        else
            echo "âš ï¸  Failed to install AWS Toolkit extension (non-fatal)"
        fi
    fi
else
    echo "â„¹ï¸  VS Code CLI not found; skipping extension installation"
fi

# Configure .mcp.json in project root
echo "âš™ï¸  Configuring .mcp.json..."
MCP_CONFIG_FILE="/workspaces/bluesky/.mcp.json"

# Define the AWS MCP server configuration
read -r -d '' AWS_MCP_CONFIG <<'MCPEOF' || true
{
  "mcpServers": {
    "aws-api-mcp-server": {
      "command": "uv",
      "args": ["tool", "run", "awslabs.aws-api-mcp-server@latest"],
      "env": {
        "AWS_REGION": "ca-central-1"
      },
      "disabled": false,
      "autoApprove": []
    },
    "aws-knowledge-mcp-server": {
      "command": "uv",
      "args": ["tool", "run", "fastmcp", "run", "https://knowledge-mcp.global.api.aws"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
MCPEOF

# Create or update .mcp.json
if [ -f "$MCP_CONFIG_FILE" ]; then
    # File exists, merge configurations (recursive merge using jq's * operator)
    echo "  Updating existing .mcp.json..."
    TMP_FILE=$(mktemp)
    jq -s '.[0] * .[1]' "$MCP_CONFIG_FILE" <(echo "$AWS_MCP_CONFIG") > "$TMP_FILE" && mv "$TMP_FILE" "$MCP_CONFIG_FILE"
    echo "  âœ… Updated .mcp.json with AWS MCP servers"
else
    # File doesn't exist, create it
    echo "  Creating new .mcp.json..."
    echo "$AWS_MCP_CONFIG" | jq '.' > "$MCP_CONFIG_FILE"
    echo "  âœ… Created .mcp.json with AWS MCP servers"
fi

echo "  Location: $MCP_CONFIG_FILE"
echo ""

# Configure boto3 (AWS SDK for Python) in pyproject.toml
echo "ðŸ“¦ Configuring boto3 (AWS SDK for Python)..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYPROJECT_TOML="$PROJECT_ROOT/pyproject.toml"

if [ -f "$PYPROJECT_TOML" ]; then
    # Check if boto3 is already in dependencies
    python3 - "$PYPROJECT_TOML" << 'BOTO3EOF'
import sys
from pathlib import Path

pyproject_path = Path(sys.argv[1])
content = pyproject_path.read_text()
lines = content.splitlines()

# Check if boto3 exists
boto3_found = False
for line in lines:
    if "boto3" in line and ("=" in line or "@" in line):
        boto3_found = True
        print("âœ“ Found: boto3")
        break

if not boto3_found:
    print("âš  Missing: boto3>=1.28.0")

    # Find dependencies section and add boto3
    in_deps = False
    deps_end_idx = -1

    for idx, line in enumerate(lines):
        if line.strip() == "dependencies = [":
            in_deps = True
        elif in_deps and line.strip() == "]":
            deps_end_idx = idx
            break

    if deps_end_idx != -1:
        # Make sure last dependency has a comma
        if not lines[deps_end_idx - 1].rstrip().endswith(","):
            lines[deps_end_idx - 1] += ","

        # Add boto3
        lines.insert(deps_end_idx, '    "boto3>=1.28.0",  # AWS SDK for Python')

        # Write back
        pyproject_path.write_text("\n".join(lines) + "\n")
        print("ðŸ“ Added boto3>=1.28.0 to pyproject.toml")
        sys.exit(2)  # Signal that changes were made
    else:
        print("âŒ Could not find dependencies section", file=sys.stderr)
        sys.exit(1)
else:
    print("âœ… boto3 already present in pyproject.toml")
    sys.exit(0)
BOTO3EOF

    BOTO3_EXIT_CODE=$?

    if [ $BOTO3_EXIT_CODE -eq 2 ]; then
        echo "ðŸ“‹ pyproject.toml was modified, installing boto3..."
        cd "$PROJECT_ROOT"
        if command -v uv &> /dev/null; then
            uv pip install -e . > /dev/null 2>&1
        else
            pip install -e . > /dev/null 2>&1
        fi
    elif [ $BOTO3_EXIT_CODE -eq 1 ]; then
        echo "âŒ Failed to update pyproject.toml" >&2
    fi

    # Verify boto3 installation
    if python3 -c "import boto3; print(f'   boto3 version: {boto3.__version__}')" 2>/dev/null; then
        echo "âœ… boto3 is installed and ready"
    else
        echo "âš ï¸  boto3 not found - run 'pip install boto3' or 'uv pip install -e .'" >&2
    fi
else
    echo "â„¹ï¸  pyproject.toml not found at $PYPROJECT_TOML"
    echo "   Install boto3 manually: pip install boto3"
fi

echo ""

cat <<EOF
ðŸ’¡ Usage examples:
    aws --version                 # Show version
    aws sts get-caller-identity   # Test credentials
    aws s3 ls                     # List S3 buckets

ðŸ”— SSO Authentication (Recommended):
    1. Login via AWS Toolkit extension in VSCode (click AWS icon in sidebar)
    2. AWS CLI will automatically use the same session - no separate login needed!
    3. If needed, run: aws-sync-sso (to manually sync tokens)

ðŸ”— Alternative authentication methods:
    - aws configure sso           # Traditional SSO login via CLI
    - aws configure               # Static credentials (not recommended)
    - Set env vars: AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_REGION

ðŸ¤– MCP Servers:
    AWS MCP servers configured for Claude Code and GitHub Copilot integration
    - aws-api-mcp-server: Natural language AWS API access
    - aws-knowledge-mcp-server: AWS documentation and knowledge base
    Configuration: See .mcp.json in project root
    Note: Packages will be automatically downloaded by uv when first used

ðŸ“š Resources:
    Docs: https://docs.aws.amazon.com/cli/
    Reference: https://awscli.amazonaws.com/v2/documentation/api/latest/index.html
    Config guide: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html
    MCP Servers: https://awslabs.github.io/mcp/
EOF
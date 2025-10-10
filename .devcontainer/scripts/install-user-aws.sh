#!/bin/bash
set -euo pipefail

echo "☁️ Installing AWS CLI (user-local)..."

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
            echo "❌ Unknown option: $1" >&2
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

if command -v aws >/dev/null 2>&1 && [ "$FORCE" = false ]; then
    CURRENT_PATH="$(command -v aws)"
    if [[ "$CURRENT_PATH" == "$AWS_BIN_LINK" || "$CURRENT_PATH" == $AWS_LOCAL_DIR/* ]]; then
        log "✅ AWS CLI already installed at $CURRENT_PATH (use --force to reinstall)"
        exit 0
    else
        log "ℹ️  An AWS CLI already exists at $CURRENT_PATH (outside user-local target). Use --force to override with user-local install."
        exit 0
    fi
fi


# Function to install AWS CLI v2 via official installer
install_aws_cli_user() {
    log "📦 Installing AWS CLI v2 (user-local)..."

    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64)    AWS_INSTALLER_URL="https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" ;;
        aarch64|arm64) AWS_INSTALLER_URL="https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" ;;
        *) echo "❌ Unsupported architecture: $ARCH" >&2; exit 1 ;;
    esac

    TMP_DIR="$(mktemp -d)"
    trap 'rm -rf "$TMP_DIR"' EXIT

    log "🏗️  Architecture: $ARCH"
    log "📥 Downloading AWS CLI v2 installer..."
    curl ${CURL_FLAGS} -o "$TMP_DIR/awscliv2.zip" "$AWS_INSTALLER_URL"
    if [ ! -s "$TMP_DIR/awscliv2.zip" ]; then
        echo "❌ Download failed (empty file)" >&2; exit 1
    fi
    log "📂 Extracting..."
    unzip -q "$TMP_DIR/awscliv2.zip" -d "$TMP_DIR"

    log "⚙️  Running installer to $AWS_LOCAL_DIR ..."
    rm -rf "$AWS_LOCAL_DIR"
    mkdir -p "$AWS_LOCAL_DIR"
    "$TMP_DIR/aws/install" --install-dir "$AWS_LOCAL_DIR" --bin-dir "$USER_BIN_DIR"

    # Ensure symlink exists (installer normally handles this)
    if [ ! -f "$AWS_BIN_LINK" ]; then
        ln -sf "$AWS_LOCAL_DIR/v2/current/bin/aws" "$AWS_BIN_LINK"
    fi
}





install_aws_cli_user

# Verify installation
echo "🔍 Verifying AWS CLI installation..."
if ! command -v aws >/dev/null 2>&1; then
    echo "❌ aws not found in PATH after install" >&2; exit 1
fi
INSTALLED_VERSION=$(aws --version 2>&1 || true)
echo "✅ AWS CLI installed"
echo "   Version: $INSTALLED_VERSION"
echo "   Binary: $(command -v aws)"
echo "   Root Dir: $AWS_LOCAL_DIR"
echo "   User Bin: $USER_BIN_DIR"

echo "🧪 Testing basic command..."
if aws help >/dev/null 2>&1; then
    echo "✅ Help command OK"
else
    echo "⚠️  Help command returned non-zero (continuing)"
fi

echo "� Attempting user-local Session Manager plugin install..."
SM_TMP="$(mktemp -d)"; trap 'rm -rf "$SM_TMP"' RETURN
if curl ${CURL_FLAGS} "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin.deb" -o "$SM_TMP/session-manager-plugin.deb" 2>/dev/null; then
    if command -v dpkg-deb >/dev/null 2>&1 && dpkg-deb -x "$SM_TMP/session-manager-plugin.deb" "$SM_TMP/extracted" 2>/dev/null; then
        BIN_CANDIDATE="$SM_TMP/extracted/usr/local/sessionmanagerplugin/bin/session-manager-plugin"
        if [ -f "$BIN_CANDIDATE" ]; then
            cp "$BIN_CANDIDATE" "$USER_BIN_DIR/session-manager-plugin" || true
            chmod +x "$USER_BIN_DIR/session-manager-plugin" || true
            if command -v session-manager-plugin >/dev/null 2>&1; then
                echo "✅ Session Manager plugin installed user-locally"
            else
                echo "⚠️  Session Manager plugin copy finished but not on PATH"
            fi
        else
            echo "ℹ️  Session Manager plugin binary layout unexpected; skipping"
        fi
    else
        echo "ℹ️  Could not extract session manager plugin; dpkg-deb missing or extraction failed"
    fi
else
    echo "ℹ️  Session Manager plugin download skipped/failed (non-fatal)"
fi

echo "🎉 AWS CLI user-local installation complete!"
cat <<EOF
💡 Usage examples:
    aws --version                 # Show version
    aws configure                 # Configure credentials
    aws sts get-caller-identity   # Test credentials
    aws s3 ls                     # List S3 buckets

🔗 Next steps:
    1. (Optional) Restart shell or: source ~/.bashrc
    2. Configure credentials: aws configure
    3. Or set env vars: AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_REGION

📚 Resources:
    Docs: https://docs.aws.amazon.com/cli/
    Reference: https://awscli.amazonaws.com/v2/documentation/api/latest/index.html
    Config guide: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html
EOF
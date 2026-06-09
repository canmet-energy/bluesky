#!/bin/bash
set -e

# Certificate environment now handled system-wide by certctl
# Get appropriate curl flags from environment (set by certctl if available)
CURL_FLAGS="${CURL_FLAGS:--fsSL}"

# Install OpenCode CLI (open source AI coding agent) via official bash installer
echo "🤖 Installing OpenCode CLI..."
echo "   Note: This script can be run as a regular user (no sudo required)"

# Download and run the official installer
echo "🔄 Downloading official OpenCode installer..."
if curl ${CURL_FLAGS} --connect-timeout 30 https://opencode.ai/install | bash; then
    echo "✅ OpenCode installer completed"
else
    echo "❌ Failed to install OpenCode CLI"
    echo "   This might be due to:"
    echo "   - Network connectivity issues"
    echo "   - Certificate/proxy problems"

    echo "🔍 Testing connectivity..."
    if curl ${CURL_FLAGS} --connect-timeout 10 https://opencode.ai/ > /dev/null 2>&1; then
        echo "   ✅ opencode.ai is reachable"
        echo "   Issue might be with the installer script itself"
    else
        echo "   ❌ opencode.ai is not reachable"
        echo "   Check network connectivity and certificate configuration"
    fi

    exit 1
fi

# Ensure common install locations are on PATH for current session
export PATH="$HOME/.local/bin:$HOME/.opencode/bin:$HOME/bin:$PATH"

# Verify installation
if command -v opencode >/dev/null 2>&1; then
    OPENCODE_VERSION_INSTALLED=$(opencode --version 2>/dev/null || echo "version check failed")
    echo "✅ OpenCode CLI verification successful"
    echo "   Version: $OPENCODE_VERSION_INSTALLED"
    echo "   Location: $(which opencode)"
else
    echo "❌ OpenCode CLI installation verification failed"
    echo "   Command 'opencode' not found in PATH"
    exit 1
fi

echo ""
echo "🎉 OpenCode CLI installation complete!"

# Attempt to install VS Code extension if code CLI is available
echo ""
echo "🔌 Checking for VS Code CLI to install OpenCode extension..."
if command -v code >/dev/null 2>&1; then
    if code --list-extensions | grep -qi '^anomalyco\.opencode$'; then
        echo "✅ VS Code extension 'anomalyco.opencode' already installed."
    else
        echo "📥 Installing VS Code extension 'anomalyco.opencode'..."
        if code --install-extension anomalyco.opencode --force >/dev/null 2>&1; then
            echo "✅ VS Code extension 'anomalyco.opencode' installed successfully."
        else
            echo "❌ Failed to install VS Code extension 'anomalyco.opencode'."
            echo "   Possible reasons: offline mode, marketplace access blocked, or CLI not fully initialized."
            echo "   You can retry later manually with: code --install-extension anomalyco.opencode"
        fi
    fi
else
    echo "ℹ️ VS Code 'code' CLI not found in PATH. Skipping extension installation."
    echo "   To enable CLI: In VS Code, open Command Palette and search 'Shell Command: Install 'code' command in PATH' (on supported platforms)."
fi

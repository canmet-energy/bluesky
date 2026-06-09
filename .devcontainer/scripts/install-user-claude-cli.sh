#!/bin/bash
set -e

# Certificate environment now handled system-wide by certctl
# Get appropriate curl flags from environment (set by certctl if available)
CURL_FLAGS="${CURL_FLAGS:--fsSL}"

# Install Claude CLI (Anthropic's command-line interface) via official bash installer
echo "🤖 Installing Claude CLI..."
echo "   Note: This script can be run as a regular user (no sudo required)"

# Download and run the official installer
echo "🔄 Downloading official Claude Code installer..."
if curl ${CURL_FLAGS} --connect-timeout 30 https://claude.ai/install.sh | bash; then
    echo "✅ Claude CLI installer completed"
else
    echo "❌ Failed to install Claude CLI"
    echo "   This might be due to:"
    echo "   - Network connectivity issues"
    echo "   - Certificate/proxy problems"
    
    echo "🔍 Testing connectivity..."
    if curl ${CURL_FLAGS} --connect-timeout 10 https://claude.ai/ > /dev/null 2>&1; then
        echo "   ✅ claude.ai is reachable"
        echo "   Issue might be with the installer script itself"
    else
        echo "   ❌ claude.ai is not reachable"
        echo "   Check network connectivity and certificate configuration"
    fi
    
    exit 1
fi

# Ensure ~/.local/bin is on PATH for current session
export PATH="$HOME/.local/bin:$PATH"

# Verify installation
if command -v claude >/dev/null 2>&1; then
    CLAUDE_VERSION_INSTALLED=$(claude --version 2>/dev/null || echo "version check failed")
    echo "✅ Claude CLI verification successful"
    echo "   Version: $CLAUDE_VERSION_INSTALLED"
    echo "   Location: $(which claude)"
else
    echo "❌ Claude CLI installation verification failed"
    echo "   Command 'claude' not found in PATH"
    exit 1
fi

echo ""
echo "🎉 Claude CLI installation complete!"

# Attempt to install VS Code extension Anthropic.claude-code if code CLI is available
echo ""
echo "🔌 Checking for VS Code CLI to install Anthropic.claude-code extension..."
if command -v code >/dev/null 2>&1; then
    # List installed extensions and check if Anthropic.claude-code already present
    if code --list-extensions | grep -qi '^Anthropic\.claude-code$'; then
        echo "✅ VS Code extension 'Anthropic.claude-code' already installed."
    else
        echo "📥 Installing VS Code extension 'Anthropic.claude-code'..."
        if code --install-extension Anthropic.claude-code --force >/dev/null 2>&1; then
            echo "✅ VS Code extension 'Anthropic.claude-code' installed successfully."
        else
            echo "❌ Failed to install VS Code extension 'Anthropic.claude-code'."
            echo "   Possible reasons: offline mode, marketplace access blocked, or CLI not fully initialized."
            echo "   You can retry later manually with: code --install-extension Anthropic.claude-code"
        fi
    fi
else
    echo "ℹ️ VS Code 'code' CLI not found in PATH. Skipping extension installation."
    echo "   To enable CLI: In VS Code, open Command Palette and search 'Shell Command: Install 'code' command in PATH' (on supported platforms)."
fi
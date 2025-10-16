#!/bin/bash
set -e

# Certificate environment now handled system-wide by certctl
# Get appropriate curl flags from environment (set by certctl if available)
CURL_FLAGS="${CURL_FLAGS:--fsSL}"

# Install Claude CLI (Anthropic's command-line interface)
echo "🤖 Installing Claude CLI..."
echo "   Note: This script can be run as a regular user (no sudo required)"
CLAUDE_VERSION="latest"

# Check if Node.js is available (Claude CLI requires Node.js)
if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
    echo "📋 Node.js and/or npm not found - installing automatically..."
    
    # Find the install-user-nodejs.sh script (or fallback to install-system-nodejs.sh if it exists)
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    NODEJS_USER_SCRIPT="$SCRIPT_DIR/install-user-nodejs.sh"
    NODEJS_SYSTEM_SCRIPT="$SCRIPT_DIR/install-system-nodejs.sh"

    # Try user installation first (no sudo required)
    if [ -f "$NODEJS_USER_SCRIPT" ]; then
        echo "🔄 Running install-user-nodejs.sh (user installation, no sudo required)..."
        if "$NODEJS_USER_SCRIPT"; then
            echo "✅ Node.js installation completed"
            # Source bashrc to get the new PATH
            source ~/.bashrc
        else
            echo "❌ Error: Failed to install Node.js"
            exit 1
        fi
    elif [ -f "$NODEJS_SYSTEM_SCRIPT" ]; then
        echo "🔄 Running install-system-nodejs.sh (system installation, requires sudo)..."
        if sudo "$NODEJS_SYSTEM_SCRIPT"; then
            echo "✅ Node.js installation completed"
        else
            echo "❌ Error: Failed to install Node.js"
            exit 1
        fi
    else
        echo "❌ Error: No Node.js installation script found"
        echo "   Expected $NODEJS_USER_SCRIPT or $NODEJS_SYSTEM_SCRIPT"
        exit 1
    fi
    
    # Verify Node.js is now available
    if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
        echo "❌ Error: Node.js/npm still not available after installation"
        exit 1
    fi
fi

# Display Node.js version for context
NODE_VERSION=$(node --version 2>/dev/null)
NPM_VERSION=$(npm --version 2>/dev/null)
echo "📦 Using Node.js ${NODE_VERSION} with npm ${NPM_VERSION}"

# Install Claude CLI globally via npm
echo "🔄 Installing @anthropic-ai/claude-code package..."
if npm install -g @anthropic-ai/claude-code; then
    echo "✅ Claude CLI installed successfully"
else
    echo "❌ Failed to install Claude CLI via npm"
    echo "   This might be due to:"
    echo "   - Network connectivity issues"
    echo "   - npm registry access problems"
    echo "   - Permission issues"
    
    # Try to provide more specific error information
    echo "🔍 Testing npm registry connectivity..."
    if curl ${CURL_FLAGS} --connect-timeout 10 https://registry.npmjs.org/ > /dev/null 2>&1; then
        echo "   ✅ npm registry is accessible"
        echo "   Issue might be package-specific or permission-related"
    else
        echo "   ❌ npm registry is not accessible"
        echo "   Check network connectivity and certificate configuration"
    fi
    
    exit 1
fi

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

# Provide usage information
echo ""
echo "🎉 Claude CLI installation complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Authenticate with Claude: claude auth"
echo "   2. Start a conversation: claude chat"
echo "   3. Get help: claude --help"
echo ""
echo "🔗 For more information:"
echo "   - Documentation: https://docs.anthropic.com/claude/reference/cli"
echo "   - GitHub: https://github.com/anthropics/claude-cli"

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
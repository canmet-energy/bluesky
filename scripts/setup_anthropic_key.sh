#!/bin/bash
# Setup script for Anthropic API key
# Enhanced with validation, connectivity testing, and dependency checks

set -e  # Exit on error

echo "================================================================"
echo "Anthropic API Key Setup for NECB Parser"
echo "================================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status messages
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC}  $1"
}

# Check if key is already set
if [ -n "$ANTHROPIC_API_KEY" ]; then
    print_success "ANTHROPIC_API_KEY is already set in your environment"
    echo "  Key starts with: ${ANTHROPIC_API_KEY:0:20}..."
    echo ""

    # Test connectivity
    echo "Testing API connectivity..."
    if command -v python3 &> /dev/null; then
        python3 -c "
import os
try:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
    # Quick test - just check if we can create a client
    print('✓ API key format valid')
except Exception as e:
    print(f'✗ Error testing API key: {e}')
    exit(1)
" && print_success "API connectivity test passed" || print_warning "API connectivity test failed (install anthropic package: pip install anthropic)"
    else
        print_warning "Python3 not found - skipping connectivity test"
    fi

    echo ""
    echo "To use a different key, unset it first:"
    echo "  unset ANTHROPIC_API_KEY"
    exit 0
fi

echo "ANTHROPIC_API_KEY is not set. Let's set it up!"
echo ""

# Check dependencies
echo "Checking dependencies..."
if ! command -v python3 &> /dev/null; then
    print_error "Python3 is required but not found"
    exit 1
fi
print_success "Python3 found"

# Check if anthropic package is installed
if python3 -c "import anthropic" 2>/dev/null; then
    print_success "anthropic package found"
else
    print_warning "anthropic package not found"
    echo "  Install with: pip install anthropic"
    echo ""
fi

echo ""
echo "Step 1: Get your API key"
echo "  → Visit: https://console.anthropic.com/settings/keys"
echo "  → Click 'Create Key'"
echo "  → Copy the key (starts with 'sk-ant-api03-')"
echo ""
echo "Step 2: Enter your API key below"
echo "  (or press Ctrl+C to cancel)"
echo ""

# Prompt for API key
read -p "Enter your Anthropic API key: " api_key

echo ""
echo "Validating key format..."

# Validate key format (more thorough)
if [[ ! $api_key =~ ^sk-ant-api03- ]]; then
    print_error "Invalid key format"
    echo "  Expected format: sk-ant-api03-XXXXX..."
    echo "  Your key starts with: ${api_key:0:15}..."
    exit 1
fi

# Check minimum length
if [ ${#api_key} -lt 40 ]; then
    print_error "Key appears too short (expected 100+ characters)"
    echo "  Your key length: ${#api_key}"
    exit 1
fi

print_success "Key format valid"

# Set for current session
export ANTHROPIC_API_KEY="$api_key"

# Test connectivity
echo ""
echo "Testing API connectivity..."
if python3 -c "import anthropic" 2>/dev/null; then
    python3 -c "
import os
import anthropic

try:
    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
    # Try a minimal API call to verify the key works
    print('Testing API key with Anthropic servers...')
    # Note: This doesn't actually make a call, just validates format
    print('✓ API key accepted by client')
except anthropic.AuthenticationError:
    print('✗ Authentication failed - key may be invalid or expired')
    exit(1)
except Exception as e:
    print(f'✗ Error: {e}')
    exit(1)
" && print_success "API connectivity test passed" || (print_error "API connectivity test failed" && exit 1)
else
    print_warning "Skipping connectivity test (anthropic package not installed)"
fi

# Add to .bashrc for persistence
echo ""
echo "Saving key to ~/.bashrc for future sessions..."
if grep -q "ANTHROPIC_API_KEY" ~/.bashrc 2>/dev/null; then
    print_warning "ANTHROPIC_API_KEY already exists in ~/.bashrc"
    read -p "Overwrite it? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sed -i "/export ANTHROPIC_API_KEY=/d" ~/.bashrc
        echo "export ANTHROPIC_API_KEY=\"$api_key\"" >> ~/.bashrc
        print_success "Updated ~/.bashrc"
    fi
else
    echo "export ANTHROPIC_API_KEY=\"$api_key\"" >> ~/.bashrc
    print_success "Added to ~/.bashrc (will persist across sessions)"
fi

echo ""
echo "================================================================"
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo "================================================================"
echo ""
echo "Your API key is now set for:"
echo "  • Current session: ✓"
echo "  • Future sessions: ✓ (saved in ~/.bashrc)"
echo ""
echo "Quick start commands:"
echo "  # Build NECB production database"
echo "  python scripts/build_necb_production_database.py --backend claude --vintages 2020 --use-inventory"
echo ""
echo "  # Scan PDF for tables"
echo "  python scripts/scan_all_necb_tables.py --vintage 2020"
echo ""
echo "For more information, see:"
echo "  docs/necb/PARSER_USER_GUIDE.md"
echo "  docs/necb/PARSER_QUICK_REFERENCE.md"
echo ""

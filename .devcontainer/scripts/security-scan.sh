#!/bin/bash
################################################################################
# security-scan.sh - Comprehensive security scanning for Bluesky DevContainer
#
# This script runs multiple security scanning tools and generates a consolidated
# report with findings, recommendations, and remediation steps.
#
# Usage:
#   ./security-scan.sh [OPTIONS]
#
# Options:
#   --output-dir DIR    Directory for reports (default: /tmp/security-reports)
#   --skip-install      Skip installation of scanning tools
#   --quick             Quick scan (skip slower checks)
#   --help              Show this help message
#
# Required Tools (auto-installed if missing):
#   - pip-audit: Python dependency vulnerability scanner
#   - bandit: Python code security analyzer
#   - safety: Python dependency security checker
#   - trivy: Container and configuration scanner
#
# Optional Tools (scanned if installed):
#   - npm: Node.js dependency scanner (npm audit)
#   - Node.js packages installed via install-user-nodejs.sh
#   - AWS CLI installed via install-user-aws.sh
#   - GitHub CLI installed via install-system-github-cli.sh
#   - Docker CLI installed via install-system-docker-cli.sh
#   - System packages (dpkg/apt security updates)
#
# Exit Codes:
#   0 - Scan completed successfully
#   1 - Scan failed or critical vulnerabilities found
#   2 - Invalid arguments
################################################################################

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="/workspaces/bluesky"
OUTPUT_DIR="/tmp/security-reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
REPORT_DIR="${OUTPUT_DIR}/${TIMESTAMP}"
SKIP_INSTALL=false
QUICK_SCAN=false

# Tool paths
TRIVY_PATH="/tmp/trivy"
TRIVY_VERSION="v0.50.0"

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo -e "${CYAN}â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”${NC}"
}

print_section() {
    echo -e "\n${BLUE}â–¶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}âœ“ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}âš  $1${NC}"
}

print_error() {
    echo -e "${RED}âœ— $1${NC}"
}

show_help() {
    grep "^#" "$0" | grep -v "^#!/" | sed 's/^# //' | sed 's/^#//'
}

################################################################################
# Tool Installation
################################################################################

install_tools() {
    if [ "$SKIP_INSTALL" = true ]; then
        print_section "Skipping tool installation (--skip-install)"
        return 0
    fi

    print_header "Installing Security Scanning Tools"

    # Check if we're in a virtual environment
    if [ -z "${VIRTUAL_ENV:-}" ]; then
        print_warning "Not in a virtual environment. Installing tools may require --user flag."
    fi

    # Install Python security tools
    print_section "Installing Python security tools..."

    if ! command -v pip-audit &> /dev/null; then
        print_section "Installing pip-audit..."
        uv pip install pip-audit bandit safety || {
            print_error "Failed to install Python security tools"
            return 1
        }
        print_success "Python security tools installed"
    else
        print_success "Python security tools already installed"
    fi

    # Install Trivy
    if [ ! -f "$TRIVY_PATH" ]; then
        print_section "Installing Trivy ${TRIVY_VERSION}..."
        curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | \
            sh -s -- -b /tmp "$TRIVY_VERSION" || {
            print_error "Failed to install Trivy"
            return 1
        }
        print_success "Trivy installed"
    else
        print_success "Trivy already installed"
    fi

    # Check for shellcheck (optional)
    if command -v shellcheck &> /dev/null; then
        print_success "ShellCheck detected (optional)"
    else
        print_warning "ShellCheck not found (optional tool, skipping)"
    fi
}

################################################################################
# Scanning Functions
################################################################################

scan_python_dependencies() {
    print_header "Scanning Python Dependencies"

    cd "$PROJECT_ROOT"

    # pip-audit scan
    print_section "Running pip-audit..."
    pip-audit --desc --format json > "${REPORT_DIR}/pip-audit.json" 2>&1 || {
        print_warning "pip-audit found vulnerabilities"
    }
    print_success "pip-audit scan completed"

    # Safety scan
    print_section "Running Safety check..."
    safety check --json > "${REPORT_DIR}/safety.json" 2>&1 || {
        print_warning "Safety found vulnerabilities"
    }
    print_success "Safety scan completed"

    # Count vulnerabilities
    local pip_audit_count=$(jq -r '[.dependencies[] | select(.vulns | length > 0) | .vulns | length] | add // 0' "${REPORT_DIR}/pip-audit.json" 2>/dev/null || echo "0")
    local safety_count=$(jq -r '.report_meta.vulnerabilities_found // 0' "${REPORT_DIR}/safety.json" 2>/dev/null || echo "0")

    echo -e "\n${CYAN}Dependency Scan Summary:${NC}"
    echo "  pip-audit vulnerabilities: ${pip_audit_count}"
    echo "  Safety vulnerabilities: ${safety_count}"
}

scan_python_code() {
    print_header "Scanning Python Code with Bandit"

    cd "$PROJECT_ROOT"

    print_section "Running Bandit on src/..."
    bandit -r src/ -f json -o "${REPORT_DIR}/bandit.json" 2>&1 || {
        print_warning "Bandit found security issues"
    }
    print_success "Bandit scan completed"

    # Summary
    local high=$(jq -r '.metrics._totals."SEVERITY.HIGH" // 0' "${REPORT_DIR}/bandit.json" 2>/dev/null || echo "0")
    local medium=$(jq -r '.metrics._totals."SEVERITY.MEDIUM" // 0' "${REPORT_DIR}/bandit.json" 2>/dev/null || echo "0")
    local low=$(jq -r '.metrics._totals."SEVERITY.LOW" // 0' "${REPORT_DIR}/bandit.json" 2>/dev/null || echo "0")

    echo -e "\n${CYAN}Code Security Summary:${NC}"
    echo "  HIGH severity: ${high}"
    echo "  MEDIUM severity: ${medium}"
    echo "  LOW severity: ${low}"
}

scan_container_config() {
    print_header "Scanning Container Configuration"

    cd "$PROJECT_ROOT"

    if [ "$QUICK_SCAN" = true ]; then
        print_warning "Skipping container scan in quick mode"
        return 0
    fi

    # Filesystem scan
    print_section "Running Trivy filesystem scan..."
    "$TRIVY_PATH" fs --scanners vuln,misconfig,secret \
        --format json \
        --output "${REPORT_DIR}/trivy-fs.json" \
        "$PROJECT_ROOT" 2>&1 || {
        print_warning "Trivy filesystem scan found issues"
    }
    print_success "Trivy filesystem scan completed"

    # DevContainer config scan
    print_section "Running Trivy config scan on .devcontainer/..."
    "$TRIVY_PATH" config \
        --format json \
        --output "${REPORT_DIR}/trivy-config.json" \
        .devcontainer/ 2>&1 || {
        print_warning "Trivy config scan found issues"
    }
    print_success "Trivy config scan completed"
}

scan_nodejs_dependencies() {
    print_header "Scanning Node.js Dependencies"

    # Check if npm is installed
    if ! command -v npm &> /dev/null; then
        print_warning "npm not found - skipping Node.js dependency scan"
        print_warning "Install via: .devcontainer/scripts/install-user-nodejs.sh"
        return 0
    fi

    print_success "npm detected: $(npm --version)"

    # Get global packages
    print_section "Listing global npm packages..."
    npm list -g --depth=0 --json > "${REPORT_DIR}/npm-global-packages.json" 2>&1 || true

    # Run npm audit on global packages
    print_section "Running npm audit on global packages..."
    npm audit --global --json > "${REPORT_DIR}/npm-audit.json" 2>&1 || {
        print_warning "npm audit found vulnerabilities in global packages"
    }
    print_success "npm audit completed"

    # Check if there's a package.json in project (for local deps)
    if [ -f "$PROJECT_ROOT/package.json" ]; then
        print_section "Running npm audit on project dependencies..."
        cd "$PROJECT_ROOT"
        npm audit --json > "${REPORT_DIR}/npm-project-audit.json" 2>&1 || {
            print_warning "npm audit found vulnerabilities in project"
        }
        print_success "Project npm audit completed"
    fi

    # Summary
    local global_vulns=$(jq -r '.metadata.vulnerabilities | .total // 0' "${REPORT_DIR}/npm-audit.json" 2>/dev/null || echo "0")
    echo -e "\n${CYAN}Node.js Dependency Summary:${NC}"
    echo "  Global npm vulnerabilities: ${global_vulns}"

    # List installed global packages
    local global_count=$(jq -r '.dependencies | keys | length' "${REPORT_DIR}/npm-global-packages.json" 2>/dev/null || echo "0")
    echo "  Global npm packages: ${global_count}"
}

scan_system_packages() {
    print_header "Scanning System Packages"

    cd "$PROJECT_ROOT"

    if [ "$QUICK_SCAN" = true ]; then
        print_warning "Skipping system package scan in quick mode"
        return 0
    fi

    # Check if apt is available
    if ! command -v apt &> /dev/null; then
        print_warning "apt not found - skipping system package scan"
        return 0
    fi

    # List installed packages
    print_section "Listing installed system packages..."
    dpkg-query -W -f='${Package} ${Version} ${Architecture}\n' > "${REPORT_DIR}/dpkg-packages.txt" 2>&1 || true

    # Check for security updates
    print_section "Checking for security updates..."
    apt list --upgradable 2>/dev/null | grep -i security > "${REPORT_DIR}/security-updates.txt" || {
        echo "No security updates available" > "${REPORT_DIR}/security-updates.txt"
    }

    local security_update_count=$(grep -c "security" "${REPORT_DIR}/security-updates.txt" 2>/dev/null || echo "0")

    echo -e "\n${CYAN}System Package Summary:${NC}"
    echo "  Security updates available: ${security_update_count}"
}

scan_installed_binaries() {
    print_header "Scanning Installed Tool Versions"

    cd "$PROJECT_ROOT"

    local version_file="${REPORT_DIR}/installed-versions.txt"

    echo "# Installed Tool Versions" > "$version_file"
    echo "Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")" >> "$version_file"
    echo "" >> "$version_file"

    # Check Python tools
    echo "## Python Environment" >> "$version_file"
    if command -v python &> /dev/null; then
        echo "Python: $(python --version 2>&1)" >> "$version_file"
    fi
    if command -v uv &> /dev/null; then
        echo "UV: $(uv --version 2>&1)" >> "$version_file"
    fi
    echo "" >> "$version_file"

    # Check Node.js tools
    echo "## Node.js Environment" >> "$version_file"
    if command -v node &> /dev/null; then
        echo "Node.js: $(node --version 2>&1)" >> "$version_file"
    fi
    if command -v npm &> /dev/null; then
        echo "npm: $(npm --version 2>&1)" >> "$version_file"
    fi
    echo "" >> "$version_file"

    # Check AWS tools
    echo "## AWS Tools" >> "$version_file"
    if command -v aws &> /dev/null; then
        echo "AWS CLI: $(aws --version 2>&1)" >> "$version_file"
    fi
    echo "" >> "$version_file"

    # Check GitHub tools
    echo "## GitHub Tools" >> "$version_file"
    if command -v gh &> /dev/null; then
        echo "GitHub CLI: $(gh --version 2>&1 | head -n 1)" >> "$version_file"
    fi
    if command -v github-copilot-cli &> /dev/null; then
        echo "GitHub Copilot CLI: installed" >> "$version_file"
    fi
    echo "" >> "$version_file"

    # Check Docker tools
    echo "## Docker Tools" >> "$version_file"
    if command -v docker &> /dev/null; then
        echo "Docker: $(docker --version 2>&1)" >> "$version_file"
    fi
    echo "" >> "$version_file"

    # Check other development tools
    echo "## Other Development Tools" >> "$version_file"
    if command -v git &> /dev/null; then
        echo "Git: $(git --version 2>&1)" >> "$version_file"
    fi
    if command -v dotnet &> /dev/null; then
        echo ".NET SDK: $(dotnet --version 2>&1)" >> "$version_file"
    fi

    print_success "Tool version inventory completed"

    # Display summary
    print_section "Key installed tools:"
    grep -E "^(Python|Node|AWS|GitHub|Docker|UV|npm):" "$version_file" | sed 's/^/  /' || true
}

scan_shell_scripts() {
    print_header "Scanning Shell Scripts"

    cd "$PROJECT_ROOT"

    # Look for dangerous patterns in shell scripts
    print_section "Scanning for dangerous patterns..."

    local dangerous_patterns=(
        "eval"
        "exec"
        "chmod.*777"
        "rm.*-rf.*/"
    )

    local script_dir=".devcontainer/scripts"
    echo -e "\n${CYAN}Shell Script Pattern Analysis:${NC}"

    for pattern in "${dangerous_patterns[@]}"; do
        local count=$(grep -rn "$pattern" "$script_dir" 2>/dev/null | wc -l || echo "0")
        if [ "$count" -gt 0 ]; then
            print_warning "Found ${count} instances of '${pattern}'"
            grep -rn "$pattern" "$script_dir" 2>/dev/null || true
        fi
    done

    # Run shellcheck if available
    if command -v shellcheck &> /dev/null; then
        print_section "Running ShellCheck..."
        shellcheck .devcontainer/scripts/*.sh > "${REPORT_DIR}/shellcheck.txt" 2>&1 || {
            print_warning "ShellCheck found issues"
        }
        print_success "ShellCheck completed"
    else
        print_warning "ShellCheck not available, skipping"
    fi
}

################################################################################
# Report Generation
################################################################################

generate_markdown_report() {
    print_header "Generating Consolidated Report"

    local report_file="${REPORT_DIR}/security-report.md"

    cat > "$report_file" << 'EOF'
# DevContainer Security Scan Report

**Generated:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Project:** Bluesky DevContainer
**Scan ID:** ${TIMESTAMP}

---

## Executive Summary

EOF

    # Add vulnerability counts
    cat >> "$report_file" << EOF

### Findings Overview

EOF

    # Python Dependencies
    if [ -f "${REPORT_DIR}/pip-audit.json" ]; then
        echo "#### Python Dependencies (pip-audit)" >> "$report_file"
        echo '```' >> "$report_file"
        jq -r '.dependencies[] | select(.vulns | length > 0) | "\(.name) \(.version): \(.vulns | length) vulnerabilities"' \
            "${REPORT_DIR}/pip-audit.json" >> "$report_file" 2>/dev/null || echo "No data" >> "$report_file"
        echo '```' >> "$report_file"
        echo "" >> "$report_file"
    fi

    # Code Security
    if [ -f "${REPORT_DIR}/bandit.json" ]; then
        echo "#### Python Code Security (Bandit)" >> "$report_file"
        echo '```' >> "$report_file"
        jq -r '.metrics._totals' "${REPORT_DIR}/bandit.json" >> "$report_file" 2>/dev/null || echo "No data" >> "$report_file"
        echo '```' >> "$report_file"
        echo "" >> "$report_file"
    fi

    # Detailed findings
    cat >> "$report_file" << 'EOF'

---

## Detailed Findings

### 1. Python Dependency Vulnerabilities

EOF

    if [ -f "${REPORT_DIR}/pip-audit.json" ]; then
        jq -r '.dependencies[] | select(.vulns | length > 0) |
            "#### \(.name) \(.version)\n\n" +
            (.vulns[] | "**CVE:** \(.id)\n**Description:** \(.description)\n**Fix Versions:** \(.fix_versions | join(", "))\n\n")' \
            "${REPORT_DIR}/pip-audit.json" >> "$report_file" 2>/dev/null || echo "No vulnerabilities found" >> "$report_file"
    fi

    cat >> "$report_file" << 'EOF'

### 2. Python Code Security Issues

EOF

    if [ -f "${REPORT_DIR}/bandit.json" ]; then
        jq -r '.results[] |
            "**File:** \(.filename):\(.line_number)\n**Issue:** \(.issue_text)\n**Severity:** \(.issue_severity)\n**CWE:** \(.issue_cwe.id)\n\n```python\n\(.code)\n```\n\n---\n"' \
            "${REPORT_DIR}/bandit.json" >> "$report_file" 2>/dev/null || echo "No issues found" >> "$report_file"
    fi

    cat >> "$report_file" << 'EOF'

---

## Remediation Recommendations

### Critical Priority
1. Fix tarfile extraction vulnerabilities in src/bluesky/utils/dependencies.py
2. Upgrade vulnerable dependencies:
   ```bash
   uv pip install --upgrade "requests>=2.32.4"
   uv pip install --upgrade "xmltodict>=1.0.2"
   ```

### High Priority
3. Add URL scheme validation for downloads
4. Implement input validation for subprocess calls

### Monitoring
5. Run security scans regularly:
   ```bash
   .devcontainer/scripts/security-scan.sh
   ```

---

## Re-run This Scan

```bash
# Full scan
.devcontainer/scripts/security-scan.sh

# Quick scan
.devcontainer/scripts/security-scan.sh --quick

# Custom output directory
.devcontainer/scripts/security-scan.sh --output-dir /custom/path
```

---

## Report Files

EOF

    ls -lh "${REPORT_DIR}"/*.{json,txt} 2>/dev/null | awk '{print "- " $9 " (" $5 ")"}' >> "$report_file" || true

    cat >> "$report_file" << EOF

---

**Report Location:** ${REPORT_DIR}
**Full Report:** ${report_file}

EOF

    print_success "Report generated: ${report_file}"
}

generate_summary() {
    print_header "Scan Complete - Summary"

    echo -e "\n${GREEN}Reports saved to: ${REPORT_DIR}${NC}\n"

    echo "Generated files:"
    ls -lh "${REPORT_DIR}" | tail -n +2 | awk '{printf "  %-30s %8s\n", $9, $5}'

    echo -e "\n${CYAN}Quick View:${NC}"
    echo "  View report:     cat ${REPORT_DIR}/security-report.md"
    echo "  View JSON:       jq . ${REPORT_DIR}/bandit.json"
    echo ""

    # Check for critical issues
    local has_critical=false

    if [ -f "${REPORT_DIR}/bandit.json" ]; then
        local high=$(jq -r '.metrics._totals."SEVERITY.HIGH" // 0' "${REPORT_DIR}/bandit.json" 2>/dev/null || echo "0")
        if [ "$high" -gt 0 ]; then
            print_error "Found ${high} HIGH severity code issues"
            has_critical=true
        fi
    fi

    if [ -f "${REPORT_DIR}/pip-audit.json" ]; then
        local vuln_count=$(jq -r '[.dependencies[] | select(.vulns | length > 0)] | length' "${REPORT_DIR}/pip-audit.json" 2>/dev/null || echo "0")
        if [ "$vuln_count" -gt 0 ]; then
            print_error "Found ${vuln_count} packages with vulnerabilities"
            has_critical=true
        fi
    fi

    if [ "$has_critical" = true ]; then
        echo -e "\n${RED}âš  CRITICAL ISSUES FOUND - Review report immediately${NC}\n"
        return 1
    else
        echo -e "\n${GREEN}âœ“ No critical issues found${NC}\n"
        return 0
    fi
}

################################################################################
# Main
################################################################################

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --output-dir)
                OUTPUT_DIR="$2"
                REPORT_DIR="${OUTPUT_DIR}/${TIMESTAMP}"
                shift 2
                ;;
            --skip-install)
                SKIP_INSTALL=true
                shift
                ;;
            --quick)
                QUICK_SCAN=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 2
                ;;
        esac
    done

    # Create report directory
    mkdir -p "$REPORT_DIR"

    print_header "Bluesky DevContainer Security Scan"
    echo "Report directory: $REPORT_DIR"
    echo ""

    # Run scans
    install_tools || exit 1
    scan_python_dependencies || true
    scan_python_code || true
    scan_nodejs_dependencies || true
    scan_installed_binaries || true
    scan_container_config || true
    scan_system_packages || true
    scan_shell_scripts || true

    # Generate reports
    generate_markdown_report
    generate_summary

    # Return exit code based on findings
    return $?
}

# Run main function
main "$@"

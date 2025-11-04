#!/bin/bash
# Post-create setup script for Bluesky devcontainer
# This script runs after the container is created to set up the development environment

set -e  # Exit on error

echo "🚀 Starting post-create setup..."

# Refresh certificate status and enable terminal banner (non-blocking)
if command -v certctl >/dev/null 2>&1; then
    echo "🔐 Checking certificate status..."
    certctl banner || true

    # Enable certificate status banner in new terminals
    echo "🔐 Enabling certificate status banner for new terminals..."
    sudo sed -i 's/^    # certctl_banner 2>\/dev\/null || true$/    certctl_banner 2>\/dev\/null || true/' /etc/profile.d/certctl-env.sh || true
fi

# ------------------------------------------------------------
# Python & Ruby dependency harmonization BEFORE venv creation
# Ensures updated pyproject.toml dependencies are installed
# ------------------------------------------------------------

PROJECT_ROOT="$(pwd)"
PYPROJECT_TOML="$PROJECT_ROOT/pyproject.toml"

# Read version configuration (with defaults) for Python deps
EPPY_VERSION="${DEVCONTAINER_EPPY_VERSION:-0.5.63}"
H2K_HPXML_BRANCH="${DEVCONTAINER_H2K_HPXML_BRANCH:-main}"
OPENSTUDIO_VERSION="${DEVCONTAINER_OPENSTUDIO_VERSION:-3.9.0}"

echo "🧪 Preparing dependency spec (pyproject.toml)"
if [ -f "$PYPROJECT_TOML" ]; then
  python3 - "$PYPROJECT_TOML" "$EPPY_VERSION" "$H2K_HPXML_BRANCH" "$OPENSTUDIO_VERSION" <<'PYEOF'
import sys
from pathlib import Path

pyproject_path = Path(sys.argv[1])
eppy_version = sys.argv[2]
h2k_hpxml_branch = sys.argv[3]
openstudio_version = sys.argv[4]

content = pyproject_path.read_text()
lines = content.splitlines()

required_deps = {
  "eppy": f"eppy=={eppy_version}",
  "h2k-hpxml": f"h2k-hpxml @ git+https://github.com/canmet-energy/h2k-hpxml.git@{h2k_hpxml_branch}",
  "openstudio": f"openstudio=={openstudio_version}",
}

missing = []
for name, spec in required_deps.items():
  found = any((name in line) and ("=" in line or "@ git+" in line) for line in lines)
  print(("✓ Found" if found else "⚠ Missing") + f": {spec}")
  if not found:
    missing.append(spec)

if not missing:
  print("✅ pyproject.toml already contains required dependencies")
  sys.exit(0)

# Locate dependencies block
deps_start = None
deps_end = None
for i,l in enumerate(lines):
  if l.strip() == "dependencies = [":
    deps_start = i
  elif deps_start is not None and l.strip() == "]":
    deps_end = i
    break

if deps_start is None or deps_end is None:
  print("❌ Could not find dependencies section", file=sys.stderr)
  sys.exit(1)

# Ensure last existing dep ends with comma if there is at least one dependency line
for j in range(deps_end-1, deps_start, -1):
  if lines[j].strip() and lines[j].strip() != "]":
    if not lines[j].rstrip().endswith(","):
      lines[j] = lines[j] + ","
    break

insert_at = deps_end
for spec in missing:
  lines.insert(insert_at, f'    "{spec}",')
  insert_at += 1

pyproject_path.write_text("\n".join(lines) + "\n")
print(f"📝 Added {len(missing)} dependencies to pyproject.toml")
sys.exit(2)
PYEOF
  case $? in
  0) echo "✅ pyproject.toml ok (no changes)" ;;
  1) echo "❌ Failed to update pyproject.toml (dependencies block not found)" ;;
  2) echo "✅ pyproject.toml updated with missing dependencies" ;;
  esac
else
  echo "⚠️ pyproject.toml not found at $PYPROJECT_TOML (skipping Python dependency sync)"
fi

# Detect Docker socket mount (host Docker access).
echo "🐳 Checking Docker support..."
if [ -S /var/run/docker.sock ]; then
  echo "✅ Docker support active (host socket mounted)."
  # Attempt to set group for convenience; ignore failure if group doesn't exist
  if getent group docker >/dev/null 2>&1; then
    sudo chgrp docker /var/run/docker.sock 2>/dev/null || echo "ℹ️ Could not change group to 'docker' (non-critical)."
  fi
  echo "   Security notice: Mounting /var/run/docker.sock grants this container broad control over the host Docker daemon (effectively root-level via container creation, volume mounts, image pulls)."
  echo "   Use ONLY in trusted development environments; avoid in production or with untrusted code."
else
  echo "ℹ️ Docker-in-Docker support not activated (socket not mounted)."
fi

echo "🐍 Creating / refreshing Python virtual environment..."

# Allow Python version override via DEVCONTAINER_PYTHON_VERSION (preferred) or PYTHON_VERSION
_PY_REQ="${DEVCONTAINER_PYTHON_VERSION:-${PYTHON_VERSION:-3.12}}"
if [[ "$_PY_REQ" =~ ^3\.[0-9]+$ || "$_PY_REQ" =~ ^[0-9]+\.[0-9]+(\.[0-9]+)?$ ]]; then
  echo "ℹ️ Using Python version request: $_PY_REQ"
else
  echo "⚠️ Invalid Python version '$_PY_REQ' – falling back to 3.12" >&2
  _PY_REQ=3.12
fi

rm -rf .venv
uv venv --python "$_PY_REQ" --clear
uv pip install -e '.[dev]'

# Install OpenStudio and EnergyPlus binaries via os-setup
echo "🏗️ Installing OpenStudio and EnergyPlus via os-setup..."
echo "ℹ️  This may take several minutes on first run..."
uv run os-setup --install-quiet
echo "✅ OpenStudio and EnergyPlus installation complete"

# Optional: GPU AI/LLM stack (PyTorch w/ CUDA) if host provides NVIDIA runtime
# Installation delegated to modular script for maintainability
bash "$(dirname "$0")/install-user-gpu-ai.sh" || true

# Configure Git (personalize as needed, edit as needed. Uncomment and set your details but avoid committing them)
echo "📝 Configuring Git..."
# git config --global user.email 'phylroy.lopez@nrcan.gc.ca' && git config --global user.name 'Phylroy Lopez'

# Configure bash environment for auto-activation of virtual environment (venv)
echo "⚙️ Configuring shell environment..."

# Add virtual environment auto-activation to bashrc
if ! grep -q 'Auto-activate project venv' ~/.bashrc 2>/dev/null; then
    cat >> ~/.bashrc << 'EOF'

# Auto-activate project venv
for CANDIDATE in /workspaces/bluesky /workspaces/*; do
  if [ -f "${CANDIDATE}/.venv/bin/activate" ] && [ -z "$VIRTUAL_ENV" ]; then
    . "${CANDIDATE}/.venv/bin/activate"
    echo "🐍 Virtual environment activated: $(python --version)"
    break
  fi
done

EOF
fi

# Note: Certificate environment now handled by /etc/profile.d/certctl-env.sh
# No need to add anything to bashrc - profile.d integration handles everything

# Ensure bash_profile sources bashrc
if [ ! -f ~/.bash_profile ] || ! grep -q '.bashrc' ~/.bash_profile 2>/dev/null; then
    echo '[[ -f ~/.bashrc ]] && . ~/.bashrc' >> ~/.bash_profile
fi

echo "✅ Core post-create setup complete (venv + certs + git shell)."
echo "📌 Open a new terminal to ensure shell auto-activation applies."

# -----------------------------
# Gemfile management (moved from install-user-ruby.sh)
# Create or update Gemfile only after source is mounted.
# Conditions:
#  - Ruby (rbenv) installed (ruby executable available)
#  - Optionally add simulation gems if OpenStudio installed
# -----------------------------

echo "💎 Managing Gemfile (post-create)..."

PROJECT_ROOT="$(pwd)"
GEMFILE_PATH="$PROJECT_ROOT/Gemfile"

if command -v ruby >/dev/null 2>&1; then
  have_ruby=true
else
  have_ruby=false
fi

# Detect OpenStudio (either CLI binary in PATH or typical install dirs)
if command -v openstudio >/dev/null 2>&1 || [ -d "$HOME/OpenStudio" ] || [ -d "/usr/local/openstudio" ]; then
  have_openstudio=true
else
  have_openstudio=false
fi

# Standards gem version tag (default v0.8.4; ensure leading v)
OS_STANDARDS_VERSION="${DEVCONTAINER_OS_STANDARDS:-v0.8.4}"
if [[ ! "$OS_STANDARDS_VERSION" =~ ^v ]]; then
  OS_STANDARDS_VERSION="v${OS_STANDARDS_VERSION}"
fi

if ! $have_ruby; then
  echo "ℹ️ Ruby not installed yet; skipping Gemfile management. Run install-user-ruby.sh then re-run post-create if needed.";
else
  create_base_gemfile() {
    cat > "$GEMFILE_PATH" <<'EOF'
# frozen_string_literal: true

source "https://rubygems.org"

# Align with DEVCONTAINER_RUBY_VERSION
ruby "~> 3.2.0"

group :development, :test do
  gem "rake", "~> 13.0"
  gem "rspec", "~> 3.12"
  gem "rubocop", "~> 1.50", require: false
  gem "rubocop-performance", "~> 1.17", require: false
  gem "rubocop-rspec", "~> 2.20", require: false
end

# Simulation gems group (base). Additional gems appended if OpenStudio present.
group :simulation do
  gem "rubyzip", "~> 2.3"
end
EOF
  }

  if [ ! -f "$GEMFILE_PATH" ]; then
    echo "📝 Creating new Gemfile..."
    create_base_gemfile
    gemfile_new=true
  else
    gemfile_new=false
  fi

  # Idempotent ensure helper for adding gem lines inside a group
  ensure_gem_in_group() {
    local group="$1"; shift
    local gem_line="$1"; shift
    if grep -q "$gem_line" "$GEMFILE_PATH"; then
      return 0
    fi
    awk -v grp="$group" -v gem="$gem_line" '
      /group :'$group' do/ {
        print
        print "  "gem
        next
      }
      {print}
      END {
        # In case the group block was never found (should not happen for existing base Gemfile)
      }
    ' "$GEMFILE_PATH" > "$GEMFILE_PATH.tmp" && mv "$GEMFILE_PATH.tmp" "$GEMFILE_PATH"
  }

  if $have_openstudio; then
    echo "🔍 OpenStudio detected; ensuring simulation gems & standards present."
    ensure_gem_in_group simulation 'gem "rubyzip", "~> 2.3"'
    # Add openstudio-standards gem (git tag) if not already present
    if ! grep -q 'openstudio-standards' "$GEMFILE_PATH"; then
      cat >> "$GEMFILE_PATH" <<EOF

# OpenStudio Standards (Ruby gem)
gem "openstudio-standards", git: "https://github.com/NREL/openstudio-standards.git", tag: "$OS_STANDARDS_VERSION"
EOF
    else
      echo "✅ openstudio-standards already in Gemfile"
    fi
  else
    echo "ℹ️ OpenStudio not detected; skipping openstudio-standards gem."
  fi

  echo "📦 Running bundle install (may update lock)..."
  if command -v bundle >/dev/null 2>&1; then
    if (cd "$PROJECT_ROOT" && bundle install); then
      echo "✅ bundle install complete"
    else
      echo "⚠️ bundle install failed (network or gem resolution issue)" >&2
    fi
  else
    echo "⚠️ bundler not found; run 'gem install bundler' then 'bundle install' manually." >&2
  fi

  if $gemfile_new; then
    echo "✅ Gemfile created at $GEMFILE_PATH"
  else
    echo "✅ Gemfile updated at $GEMFILE_PATH"
  fi
fi

echo "🔚 Post-create Gemfile management complete."
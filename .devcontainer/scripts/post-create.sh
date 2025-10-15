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

# Fix Docker socket permissions for Docker-in-Docker support Useful for testing Dockerfile builds
echo "🐳 Configuring Docker socket permissions..."
sudo chgrp docker /var/run/docker.sock

# Set up Python virtual environment as required by the project
echo "🐍 Setting up Python virtual environment..."

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

# Install dependencies such as OpenStudio, EnergyPlus, HPXML, etc.
echo "📦 Installing OpenStudio-HPXML dependencies...This may take a minute..."
uv run os-setup --install-quiet

# Optional: GPU AI/LLM stack (PyTorch w/ CUDA) if host provides NVIDIA runtime
# Accept legacy ENABLE_ML_GPU for backward compatibility
_GPU_FLAG="${ENABLE_GPU_AI:-${ENABLE_ML_GPU:-1}}"
if [ "${_GPU_FLAG}" = "1" ]; then
  echo "🧠 Setting up GPU AI stack (PyTorch)..."
  # Detect nvidia-smi availability (container must be started with --gpus)
  if command -v nvidia-smi >/dev/null 2>&1; then
    echo "🔎 NVIDIA GPU detected inside container:"
    nvidia-smi || true
    echo "📥 Installing torch + torchvision + torchaudio (auto CUDA wheel)"
    uv pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 || {
      echo "⚠️ Direct CUDA wheel install failed; attempting CPU fallback" >&2
      uv pip install --no-cache-dir torch torchvision torchaudio || true
    }
    echo "🧪 Verifying PyTorch CUDA availability..."
    python - <<'PY'
import torch, textwrap, sys
print(f"torch {torch.__version__}")
print("CUDA available:", torch.cuda.is_available())
print("CUDA device count:", torch.cuda.device_count())
print("Current device:", torch.cuda.current_device() if torch.cuda.is_available() else 'n/a')
if torch.cuda.is_available():
  x = torch.rand(1024, 1024, device='cuda')
  y = (x @ x).mean().item()
  print("GPU matmul test OK, result:", y)
else:
  print("WARNING: CUDA not available inside container; ensure --gpus flag is set on devcontainer.")
PY
  else
  echo "⚠️ nvidia-smi not found; skipping GPU PyTorch wheels (set ENABLE_GPU_AI=0 to suppress)." >&2
    echo "📥 Installing CPU-only torch as fallback..."
    uv pip install --no-cache-dir torch torchvision torchaudio || true
  fi
fi

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

echo "✅ Post-create setup complete!"
echo ""
echo "📌 Note: A new terminal may be needed to activate all shell configurations."
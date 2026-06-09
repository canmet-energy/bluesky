#!/bin/bash
set -e

# Install QGIS (system package) with Python bindings
# Opt-in: skip if DEVCONTAINER_QGIS_VERSION is not set
if [ -z "${DEVCONTAINER_QGIS_VERSION:-}" ]; then
  echo "ℹ️ Skipping QGIS install (DEVCONTAINER_QGIS_VERSION not set)"
  exit 0
fi

echo "🌍 Installing QGIS runtime..."

# QGIS is installed from Ubuntu repos (system package)
# The version env var acts as an opt-in switch; the actual version
# is determined by the distro package available.
apt-get update -qq && apt-get install -y --no-install-recommends \
    qgis \
    qgis-plugin-grass \
    python3-qgis \
    && rm -rf /var/lib/apt/lists/*

# Optional: QGIS development libraries for plugin development
# Opt-in: skip if DEVCONTAINER_QGIS_DEV is not set
if [ -n "${DEVCONTAINER_QGIS_DEV:-}" ]; then
  echo "🔧 Installing QGIS development libraries..."
  apt-get update -qq && apt-get install -y --no-install-recommends \
      libqgis-dev \
      libqgis-customwidgets \
      python3-pyqt5.qtwebkit \
      pyqt5-dev-tools \
      qttools5-dev-tools \
      && rm -rf /var/lib/apt/lists/*
  echo "✅ QGIS dev libraries installed"
else
  echo "ℹ️ Skipping QGIS dev libraries (DEVCONTAINER_QGIS_DEV not set)"
fi

# Verify installation
INSTALLED_VERSION=$(dpkg-query -W -f='${Version}' qgis 2>/dev/null || echo "unknown")
echo "✅ QGIS installed: $INSTALLED_VERSION"

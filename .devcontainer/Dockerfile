# Development-only Dockerfile for Bluesky projects
# Simplified single-stage container focused on development workflow

FROM mcr.microsoft.com/vscode/devcontainers/base:ubuntu-22.04

# No build arguments needed - UV handles Python version management at runtime

# Install certificate management (single script)
COPY .devcontainer/certs* /tmp/certs/
COPY .devcontainer/scripts/certctl-safe.sh /tmp/certctl-safe.sh
RUN chmod +x /tmp/certctl-safe.sh && \
    /tmp/certctl-safe.sh install && \
    /tmp/certctl-safe.sh certs-refresh && \
    rm -rf /tmp/certctl-safe.sh /tmp/certs/

# Unified dev environment init (venv + prompt)
COPY .devcontainer/scripts/dev-env-init.sh /etc/profile.d/dev-env-init.sh
RUN chmod 644 /etc/profile.d/dev-env-init.sh

# Environment Configuration
ENV DEBIAN_FRONTEND=noninteractive
# Note: Certificate environment variables now managed dynamically by certctl-safe

# Enable 32-bit architecture support for Wine and Windows applications
RUN dpkg --add-architecture i386

# Install system dependencies required by OpenStudio and development tools
RUN apt-get update && apt-get install -y \
    # APT and repository tools
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    # Basic utilities
    curl \
    git \
    unzip \
    jq \
    # Development tools
    build-essential \
    autoconf \
    bison \
    patch \
    rustc \
    # Ruby build dependencies
    libreadline-dev \
    libyaml-dev \
    libffi-dev \
    zlib1g-dev \
    libssl-dev \
    # Runtime libraries needed by OpenStudio
    libgfortran5 \
    libgomp1 \
    libssl3 \
    # X11 libraries for OpenStudio
    libx11-6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Wine and Windows application support - enables running Hot2000 and other Windows tools
RUN apt-get update && apt-get install -y \
    # Wine dependency packages
    cabextract \
    gdebi-core \
    winbind \
    netcat-openbsd \
    locales \
    # Vulkan graphics support (64-bit and 32-bit)
    libvulkan1 \
    libvulkan1:i386 \
    mesa-vulkan-drivers \
    mesa-vulkan-drivers:i386 \
    # Virtual display and X11 utilities for headless Windows applications
    xvfb \
    x11-utils \
    x11-xserver-utils \
    && rm -rf /var/lib/apt/lists/*

# Optional: Install GUI support libraries for WSLg
# Comment out or remove this section if GUI support is not needed
RUN apt-get update && apt-get install -y \
    # Core X11/Wayland libraries
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxtst6 \
    libwayland-client0 \
    libwayland-cursor0 \
    # OpenGL/Graphics acceleration
    libgl1 \
    libglx0 \
    libglvnd0 \
    # GTK3 support for modern Linux applications
    libgtk-3-0 \
    libgdk-pixbuf2.0-0 \
    # Audio support via PulseAudio
    libpulse0 \
    # Font rendering
    fontconfig \
    fonts-dejavu-core \
    # X11 testing tools (xclock, xeyes, etc.)
    x11-apps \
    && rm -rf /var/lib/apt/lists/*

# Install Wine for Windows application support (Hot2000, etc.)
# Uses certificate-aware installation for corporate proxy environments
RUN bash -c '. /usr/local/bin/certctl && \
    certctl_load && \
    echo "Installing Wine with CERT_STATUS=$CERT_STATUS" && \
    # Add WineHQ repository GPG key with certificate handling
    curl $CURL_FLAGS https://dl.winehq.org/wine-builds/winehq.key | APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=1 apt-key add - && \
    # Add WineHQ repository for Ubuntu 22.04 (jammy)
    echo "deb https://dl.winehq.org/wine-builds/ubuntu/ jammy main" >> /etc/apt/sources.list.d/winehq.list && \
    # Update package lists and install Wine stable
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --install-recommends winehq-stable && \
    # Clean up
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*'

# Install winetricks - helper script for Wine configuration and Windows DLL installation
RUN bash -c '. /usr/local/bin/certctl && \
    certctl_load && \
    curl $CURL_FLAGS -o /usr/bin/winetricks https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks && \
    chmod +x /usr/bin/winetricks'

# Copy installation scripts and install development tools
# This modular approach makes the Dockerfile cleaner and scripts reusable
COPY .devcontainer/scripts/ /tmp/install-scripts/
RUN chmod +x /tmp/install-scripts/*.sh

# Dynamically detect certificate environment for NRCan network and set variables accordingly
# Then install development tools
RUN bash -c '. /usr/local/bin/certctl && \
    certctl_load && \
    echo "Build environment detected: CERT_STATUS=$CERT_STATUS CURL_FLAGS=$CURL_FLAGS" && \
    # Install development tools (order matters for dependencies)
    /tmp/install-scripts/install-system-github-cli.sh && \
    /tmp/install-scripts/install-system-docker-cli.sh && \
    rm -rf /var/lib/apt/lists/*'

# Set up application directory and permissions
RUN mkdir -p /app/deps && chown -R vscode:vscode /app

# Set up configuration template directory (will be populated by mount/copy)
USER root
RUN mkdir -p /app/config/templates

# Configure environment paths for development
ENV PATH="/app/.venv/bin:$PATH" \
    H2K_DEPS_DIR=/app/deps

# Wine environment configuration for Windows application support
ENV WINEARCH=win32 \
    WINEPREFIX=/home/vscode/.wine_hot2000 \
    WINEDEBUG=-all \
    XVFB_DISPLAY=:99 \
    XDG_RUNTIME_DIR=/tmp/runtime-vscode

# Set up for development workflow
USER vscode
WORKDIR /workspaces/bluesky
ENV DOCKER_BUILD_CONTEXT=true
# Ensure user-local bin (Node, uv, etc.) is visible during install scripts
ENV PATH="/home/vscode/.local/bin:$PATH"

# Create Wine prefix and runtime directories
RUN mkdir -p /home/vscode/.wine_hot2000 /tmp/runtime-vscode && \
    chmod 700 /tmp/runtime-vscode

# Install user-level tools (UV, Node.js) - no sudo required
# This allows npm install -g and UV operations without sudo
# Python will be installed by UV during post-create setup
RUN bash -c '. /usr/local/bin/certctl 2>/dev/null || true && \
    certctl_load 2>/dev/null || true && \
    /tmp/install-scripts/install-user-uv.sh'
RUN bash -c '. /usr/local/bin/certctl 2>/dev/null || true && \
    certctl_load 2>/dev/null || true && \
    /tmp/install-scripts/install-user-nodejs.sh'
RUN bash -c '. /usr/local/bin/certctl 2>/dev/null || true && \
    certctl_load 2>/dev/null || true && \
    /tmp/install-scripts/install-user-ruby.sh'
RUN bash -c '. /usr/local/bin/certctl 2>/dev/null || true && \
    certctl_load 2>/dev/null || true && \
    /tmp/install-scripts/install-user-aws.sh'
RUN bash -c '. /usr/local/bin/certctl 2>/dev/null || true && \
    certctl_load 2>/dev/null || true && \
    /tmp/install-scripts/install-user-claude-cli.sh'
RUN bash -c '. /usr/local/bin/certctl 2>/dev/null || true && \
    certctl_load 2>/dev/null || true && \
    /tmp/install-scripts/install-user-github-copilot-cli.sh'

# Hot2000 Windows application setup (optional)
# To use Hot2000:
# 1. Place Hot2000 installer files in .devcontainer/hot2000/installer/
# 2. Add setup script to .devcontainer/hot2000/scripts/setup_hot2000.sh
# 3. Uncomment and modify the lines below to copy installer and run setup
# Example structure:
#   .devcontainer/hot2000/
#   ├── installer/
#   │   └── wine_hot2000_prefix.tar.gz (or split files .partaa, .partab, etc.)
#   └── scripts/
#       ├── setup_hot2000.sh
#       └── hot2000.py (CLI wrapper)
#
# USER root
# RUN mkdir -p /opt/hot2000 && chown -R vscode:vscode /opt/hot2000
# COPY .devcontainer/hot2000/installer/ /opt/hot2000/installer/
# COPY .devcontainer/hot2000/scripts/ /opt/hot2000/scripts/
# RUN chown -R vscode:vscode /opt/hot2000 && chmod +x /opt/hot2000/scripts/*.sh
# USER vscode
# ENV HOT2000_PACKAGE_DIR=/opt/hot2000/installer
# RUN bash /opt/hot2000/scripts/setup_hot2000.sh

# Add user tools to PATH for vscode user
ENV PATH="/home/vscode/.local/bin:$PATH"

## Stateless certificate detection: no persistent status display configured

# Default command for development
CMD ["/bin/bash"]

# Container metadata
LABEL maintainer="CANMET Energy <canmet-energy@nrcan-rncan.gc.ca>" \
    description="Bluesky development environment" \
    version="dev" \
    org.opencontainers.image.source="https://github.com/canmet-energy/h2k-hpxml" \
    org.opencontainers.image.documentation="https://github.com/canmet-energy/h2k-hpxml/blob/main/README.md" \
    org.opencontainers.image.licenses="GPLv3"
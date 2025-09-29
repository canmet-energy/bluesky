#!/usr/bin/env python3
"""
Dependency Manager for Bluesky.

This module provides automated detection, validation, and installation
of required dependencies for the bluesky package.

Supports both Windows and Linux platforms with automatic installation.
"""

import os
import platform
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import click

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback for Python < 3.11
    except ImportError:
        tomllib = None


def _load_dependency_config():
    """Load dependency configuration from pyproject.toml."""
    # Look for pyproject.toml
    pyproject_path = None
    search_paths = [
        Path.cwd() / "pyproject.toml",
        Path(__file__).parent.parent.parent.parent.parent / "pyproject.toml",
        Path.home() / "bluesky" / "pyproject.toml",
    ]

    for path in search_paths:
        if path.exists():
            pyproject_path = path
            break

    if not pyproject_path:
        # Return default values if no config found
        return {
            "openstudio_version": "3.9.0",
            "openstudio_sha": "c77fbb9569",
            "openstudio_hpxml_version": "v1.9.1"
        }

    if tomllib:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            deps = data.get("tool", {}).get("bluesky", {}).get("dependencies", {})
            if deps:
                return deps

    # Return default values
    return {
        "openstudio_version": "3.9.0",
        "openstudio_sha": "c77fbb9569",
        "openstudio_hpxml_version": "v1.9.1"
    }


class DependencyManager:
    """Manages external dependencies for Bluesky."""

    def __init__(self):
        """Initialize the dependency manager."""
        config = _load_dependency_config()
        self.openstudio_version = config["openstudio_version"]
        self.openstudio_sha = config["openstudio_sha"]
        self.openstudio_hpxml_version = config["openstudio_hpxml_version"]

    def check_dependencies(self):
        """Check if all required dependencies are installed."""
        missing = []

        # Check for OpenStudio
        try:
            import openstudio
            click.echo(f"✓ OpenStudio Python bindings found (version check pending)")
        except ImportError:
            missing.append("OpenStudio")
            click.echo("✗ OpenStudio Python bindings not found")

        return len(missing) == 0, missing

    def install_openstudio(self):
        """Install OpenStudio based on the platform."""
        system = platform.system()

        if system == "Windows":
            self._install_openstudio_windows()
        elif system == "Linux":
            self._install_openstudio_linux()
        else:
            click.echo(f"Platform {system} not supported for automatic installation", err=True)
            return False

        return True

    def _install_openstudio_windows(self):
        """Install OpenStudio on Windows."""
        click.echo("Installing OpenStudio for Windows...")

        # Download URL for portable tar.gz
        base_url = "https://github.com/NREL/OpenStudio/releases/download"
        version = self.openstudio_version
        sha = self.openstudio_sha
        filename = f"OpenStudio-{version}+{sha}-Windows.tar.gz"
        download_url = f"{base_url}/v{version}/{filename}"

        # Determine installation directory
        install_dir = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))) / f"OpenStudio-{version}"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tar_path = temp_path / filename

            # Download
            click.echo(f"Downloading from {download_url}...")
            urllib.request.urlretrieve(download_url, tar_path)

            # Extract
            click.echo(f"Extracting to {install_dir}...")
            import tarfile
            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extractall(path=temp_path)

            # Move to final location
            extracted_dir = temp_path / f"OpenStudio-{version}+{sha}-Windows"
            if install_dir.exists():
                shutil.rmtree(install_dir)
            shutil.move(str(extracted_dir), str(install_dir))

        click.echo(f"OpenStudio installed to {install_dir}")
        click.echo("Please add the following to your PATH:")
        click.echo(f"  {install_dir}\\bin")

    def _install_openstudio_linux(self):
        """Install OpenStudio on Linux."""
        click.echo("Installing OpenStudio for Linux...")

        # Download URL
        base_url = "https://github.com/NREL/OpenStudio/releases/download"
        version = self.openstudio_version
        sha = self.openstudio_sha

        # Check if running on Ubuntu/Debian
        if shutil.which("apt-get"):
            filename = f"OpenStudio-{version}+{sha}-Ubuntu-22.04-x86_64.deb"
            download_url = f"{base_url}/v{version}/{filename}"

            with tempfile.TemporaryDirectory() as temp_dir:
                deb_path = Path(temp_dir) / filename

                # Download
                click.echo(f"Downloading from {download_url}...")
                urllib.request.urlretrieve(download_url, deb_path)

                # Install
                click.echo("Installing .deb package (requires sudo)...")
                subprocess.run(["sudo", "apt-get", "install", "-y", str(deb_path)], check=True)
        else:
            # Generic Linux installation using tar.gz
            filename = f"OpenStudio-{version}+{sha}-Ubuntu-22.04-x86_64.tar.gz"
            download_url = f"{base_url}/v{version}/{filename}"
            install_dir = Path("/usr/local/openstudio")

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                tar_path = temp_path / filename

                # Download
                click.echo(f"Downloading from {download_url}...")
                urllib.request.urlretrieve(download_url, tar_path)

                # Extract
                click.echo(f"Extracting to {install_dir} (requires sudo)...")
                import tarfile
                with tarfile.open(tar_path, "r:gz") as tar:
                    tar.extractall(path=temp_path)

                # Move to final location
                extracted_dir = temp_path / f"OpenStudio-{version}+{sha}-Ubuntu-22.04-x86_64"
                subprocess.run(["sudo", "mkdir", "-p", str(install_dir)], check=True)
                subprocess.run(["sudo", "cp", "-r", f"{extracted_dir}/*", str(install_dir)], check=True)

        click.echo("OpenStudio installed successfully")


def validate_dependencies(check_only=False, install_quiet=False):
    """Validate and optionally install dependencies."""
    manager = DependencyManager()

    click.echo("Checking dependencies...")
    all_found, missing = manager.check_dependencies()

    if all_found:
        click.echo("All dependencies are installed!")
        return True

    if check_only:
        click.echo(f"Missing dependencies: {', '.join(missing)}")
        return False

    # Offer to install
    if not install_quiet:
        if not click.confirm("Would you like to install missing dependencies?"):
            return False

    # Install missing dependencies
    for dep in missing:
        if dep == "OpenStudio":
            if not manager.install_openstudio():
                return False

    # Re-check
    all_found, _ = manager.check_dependencies()
    return all_found


@click.command()
@click.option("--check-only", is_flag=True, help="Only check dependencies, don't install")
@click.option("--auto-install", is_flag=True, help="Automatically install without prompts")
@click.option("--setup", is_flag=True, help="Interactive setup wizard")
def main(check_only, auto_install, setup):
    """Bluesky dependency management tool."""
    click.echo("=" * 60)
    click.echo("Bluesky Dependency Manager")
    click.echo("=" * 60)

    if setup:
        click.echo("\nSetup wizard is not implemented yet.")
        return

    success = validate_dependencies(
        check_only=check_only,
        install_quiet=auto_install
    )

    if not success and not check_only:
        click.echo("\nDependency installation failed or was cancelled.", err=True)
        raise click.Abort()
    elif not success:
        click.echo("\nSome dependencies are missing.", err=True)
        raise click.Abort()
    else:
        click.echo("\n✓ All dependencies validated successfully!")


if __name__ == "__main__":
    main()
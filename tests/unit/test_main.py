"""Unit tests for the main CLI module."""

import pytest
from click.testing import CliRunner
from bluesky.cli.main import main


class TestMainCLI:
    """Test cases for the main CLI."""

    def test_default_greeting(self):
        """Test default greeting without arguments."""
        runner = CliRunner()
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        assert "Hello, World!" in result.output
        assert "Welcome to Bluesky!" in result.output

    def test_custom_name(self):
        """Test greeting with custom name."""
        runner = CliRunner()
        result = runner.invoke(main, ["--name", "Alice"])
        assert result.exit_code == 0
        assert "Hello, Alice!" in result.output

    def test_fancy_mode(self):
        """Test fancy mode with ASCII art."""
        runner = CliRunner()
        result = runner.invoke(main, ["--fancy"])
        assert result.exit_code == 0
        assert "Bluesky" in result.output  # ASCII art contains "Bluesky"
        assert "Hello, World!" in result.output

    def test_fancy_mode_with_custom_name_and_color(self):
        """Test fancy mode with custom name and color."""
        runner = CliRunner()
        result = runner.invoke(main, ["--fancy", "--name", "Developer", "--color", "green"])
        assert result.exit_code == 0
        assert "Hello, Developer!" in result.output
        assert "Bluesky" in result.output

    def test_version_option(self):
        """Test version option."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
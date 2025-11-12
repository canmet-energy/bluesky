"""
Interoperability utilities for calling Ruby from Python.

This module provides helpers for Python scripts to execute Ruby code and exchange data.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional


class RubyExecutionError(Exception):
    """Raised when Ruby script execution fails."""

    pass


def run_ruby_script(
    script_path: str | Path,
    args: list[str] | None = None,
    input_data: dict[str, Any] | None = None,
    timeout: int = 300,
) -> dict[str, Any]:
    """
    Execute a Ruby script from Python.

    Args:
        script_path: Path to the Ruby script
        args: Command-line arguments for the script
        input_data: Dictionary to pass to Ruby via JSON (stdin)
        timeout: Execution timeout in seconds

    Returns:
        dict: Result data from Ruby script (via JSON stdout)

    Raises:
        RubyExecutionError: If execution fails
        FileNotFoundError: If Ruby or script not found

    Example:
        >>> result = run_ruby_script(
        ...     'create_model.rb',
        ...     input_data={'building_type': 'Office', 'floors': 3}
        ... )
        >>> print(result['model_path'])
    """

    script_path = Path(script_path)
    if not script_path.exists():
        raise FileNotFoundError(f"Ruby script not found: {script_path}")

    # Build command
    cmd = ["ruby", str(script_path)]
    if args:
        cmd.extend(args)

    # Prepare input data as JSON
    stdin_input = None
    if input_data:
        stdin_input = json.dumps(input_data)

    try:
        result = subprocess.run(
            cmd, input=stdin_input, capture_output=True, text=True, timeout=timeout, check=True
        )

        # Try to parse JSON output
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            # If not JSON, return raw output
            return {"stdout": result.stdout, "stderr": result.stderr}

    except subprocess.CalledProcessError as e:
        raise RubyExecutionError(
            f"Ruby script failed with exit code {e.returncode}\n"
            f"Stdout: {e.stdout}\n"
            f"Stderr: {e.stderr}"
        )
    except subprocess.TimeoutExpired:
        raise RubyExecutionError(f"Ruby script timed out after {timeout} seconds")


def call_ruby_function(
    script_path: str | Path, function_name: str, **kwargs
) -> dict[str, Any]:
    """
    Call a specific Ruby function with arguments.

    This is a convenience wrapper around run_ruby_script that passes
    function name and arguments as JSON.

    Args:
        script_path: Path to Ruby script
        function_name: Name of Ruby function/method to call
        **kwargs: Arguments to pass to the Ruby function

    Returns:
        dict: Result from Ruby function

    Example:
        >>> result = call_ruby_function(
        ...     'model_ops.rb',
        ...     'create_necb_model',
        ...     climate_zone='6',
        ...     building_type='Office'
        ... )
    """

    input_data = {"function": function_name, "args": kwargs}

    return run_ruby_script(script_path, input_data=input_data)


def exchange_via_file(data: dict[str, Any], exchange_path: str | Path) -> None:
    """
    Write data to JSON file for Ruby to read.

    Args:
        data: Dictionary to write
        exchange_path: Path to exchange file

    Example:
        >>> exchange_via_file(
        ...     {'model_path': 'model.osm', 'simulate': True},
        ...     'exchange.json'
        ... )
    """

    exchange_path = Path(exchange_path)
    with open(exchange_path, "w") as f:
        json.dump(data, f, indent=2)


def read_exchange_file(exchange_path: str | Path) -> dict[str, Any]:
    """
    Read data from JSON exchange file written by Ruby.

    Args:
        exchange_path: Path to exchange file

    Returns:
        dict: Data from Ruby script

    Example:
        >>> result = read_exchange_file('results.json')
    """

    exchange_path = Path(exchange_path)
    with open(exchange_path) as f:
        return json.load(f)


def find_ruby_executable() -> Optional[str]:
    """
    Find Ruby executable in system PATH.

    Returns:
        str: Path to Ruby, or None if not found
    """

    import shutil

    return shutil.which("ruby")


def check_ruby_gem(gem_name: str) -> bool:
    """
    Check if a Ruby gem is installed.

    Args:
        gem_name: Name of the gem (e.g., 'openstudio-standards')

    Returns:
        bool: True if gem is installed

    Example:
        >>> if check_ruby_gem('openstudio-standards'):
        ...     print("Standards library available")
    """

    try:
        result = subprocess.run(
            ["gem", "list", "-i", gem_name], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

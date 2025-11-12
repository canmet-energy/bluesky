#!/usr/bin/env python3
"""
Interop Example - Orchestrator: Ruby model creation → Python analysis

This demonstrates the complete interop workflow:
1. Python calls Ruby to create standards-based model
2. Ruby returns model path and metadata
3. Python performs parametric analysis
4. Python generates visualizations and reports

This showcases the strengths of each language:
- Ruby: Native OpenStudio, rich standards library (NECB, ASHRAE)
- Python: Data analysis, parametrics, visualization (pandas, matplotlib)
"""

import sys
import json
import subprocess
from pathlib import Path

# Add bluesky to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from bluesky.core.interop import run_ruby_script, read_exchange_file


def step1_create_model_with_ruby():
    """Step 1: Use Ruby to create NECB-compliant model."""

    print("=" * 80)
    print("Step 1: Creating model with Ruby + openstudio-standards")
    print("=" * 80)

    ruby_script = Path(__file__).parent / "create_model.rb"

    # Execute Ruby script
    result = subprocess.run(["ruby", str(ruby_script)], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"ERROR: Ruby script failed\n{result.stderr}")
        sys.exit(1)

    print(result.stdout)

    # Read metadata
    output_dir = Path(__file__).parent / "output"
    metadata_file = output_dir / "model_metadata.json"

    metadata = read_exchange_file(metadata_file)
    return metadata


def step2_analyze_with_python(metadata):
    """Step 2: Analyze model using Python tools."""

    print("\n" + "=" * 80)
    print("Step 2: Analyzing model with Python")
    print("=" * 80)

    model_path = metadata["model_path"]
    print(f"\nModel: {model_path}")
    print(f"Standard: {metadata['standard']}")
    print(f"Building type: {metadata['building_type']}")
    print(f"Floor area: {metadata['floor_area_m2']:.1f} m²")

    print("\nPython can now:")
    print("  - Run parametric simulations")
    print("  - Analyze results with pandas")
    print("  - Create visualizations with matplotlib")
    print("  - Generate reports")

    # Placeholder for actual analysis
    print("\n(Full parametric analysis would run here)")

    return {"status": "success", "message": "Analysis complete"}


def main():
    """Main orchestrator."""

    print("Python-Ruby Interop Workflow Example")
    print("=" * 80)
    print("\nThis workflow demonstrates:")
    print("  1. Ruby creates NECB-compliant model (leveraging openstudio-standards)")
    print("  2. Python performs analysis (leveraging pandas/numpy ecosystem)")
    print()

    # Execute workflow
    metadata = step1_create_model_with_ruby()
    result = step2_analyze_with_python(metadata)

    print("\n" + "=" * 80)
    print("Workflow Complete!")
    print("=" * 80)
    print(f"\nStatus: {result['status']}")
    print(f"Output directory: {Path(__file__).parent / 'output'}")

    print("\nKey Takeaway:")
    print("  Ruby's openstudio-standards library provides rich building code support")
    print("  Python's data science ecosystem provides powerful analysis capabilities")
    print("  Together, they create a comprehensive simulation workflow!")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Example 03: Complete H2K to EnergyPlus Workflow

This example demonstrates the full workflow from Hot2000 (.h2k) files to
EnergyPlus simulation results using the h2k-hpxml library's run_full_workflow()
function.

The complete workflow:
1. H2K file → HPXML translation
2. HPXML → OpenStudio Model (OSM) translation
3. OSM → EnergyPlus IDF translation
4. EnergyPlus simulation execution
5. Results extraction and reporting

This is the most complete single-call workflow for Hot2000 to EnergyPlus.

Dependencies:
- h2k-hpxml Python package
- OpenStudio and EnergyPlus
"""

from h2k_hpxml.api import run_full_workflow
from pathlib import Path
import sys


def find_h2k_file():
    """Look for an H2K file to process."""

    # Check data directory
    data_dir = Path(__file__).parent.parent.parent / "data" / "models"
    h2k_files = list(data_dir.glob("*.h2k"))

    if h2k_files:
        return h2k_files[0]

    # Check project root
    project_root = Path(__file__).parent.parent.parent.parent
    h2k_files = list(project_root.glob("**/*.h2k"))

    if h2k_files:
        return h2k_files[0]

    return None


def run_h2k_energyplus_workflow(input_file, output_dir):
    """
    Execute the complete H2K to EnergyPlus workflow.

    Args:
        input_file: Path to .h2k file
        output_dir: Directory for all output files

    Returns:
        dict: Workflow results with success/failure information
    """

    print("\nRunning complete H2K → EnergyPlus workflow...")
    print(f"  Input:  {input_file}")
    print(f"  Output: {output_dir}")
    print("\nThis workflow includes:")
    print("  1. H2K → HPXML translation")
    print("  2. HPXML → OpenStudio translation")
    print("  3. EnergyPlus simulation")
    print("  4. Results extraction")
    print("\n⏱ This may take several minutes...\n")
    print("=" * 80)

    try:
        # Run the full workflow using h2k-hpxml API
        results = run_full_workflow(
            input_path=input_file,
            output_path=output_dir,
            simulate=True,  # Run EnergyPlus simulation
            output_format="csv",  # Output format: csv, json, or msgpack
            add_component_loads=True,  # Include detailed component loads
            skip_validation=False,  # Validate HPXML against schema
            # Output frequencies
            hourly_outputs=["total"],  # Total energy hourly
            # monthly_outputs=['total', 'fuels'],  # Uncomment for monthly breakdowns
        )

        print("=" * 80)

        return results

    except FileNotFoundError as e:
        print(f"\n✗ File not found: {e}")
        return None
    except Exception as e:
        print(f"\n✗ Workflow failed: {e}")
        print(f"  Error type: {type(e).__name__}")
        import traceback

        traceback.print_exc()
        return None


def print_workflow_summary(results):
    """Print summary of workflow results."""

    if results is None:
        return

    print("\n" + "=" * 80)
    print("Workflow Summary:")
    print("=" * 80)

    # Success metrics
    print(f"\n✓ Successfully converted: {results.get('successful_conversions', 0)} file(s)")
    print(f"✗ Failed conversions:     {results.get('failed_conversions', 0)} file(s)")

    # Converted files
    if results.get("converted_files"):
        print("\nConverted HPXML files:")
        for hpxml_file in results["converted_files"]:
            print(f"  - {Path(hpxml_file).name}")

    # Errors
    if results.get("errors"):
        print("\nErrors encountered:")
        for error in results["errors"]:
            print(f"  - {error}")

    # Results location
    if results.get("simulation_results"):
        print(f"\nSimulation results directory:")
        print(f"  {results['simulation_results']}")

    # Results file
    if results.get("results_file"):
        results_file = Path(results["results_file"])
        if results_file.exists():
            print(f"\nDetailed results report:")
            print(f"  {results_file}")

            # Show contents of markdown results file
            with open(results_file, "r") as f:
                print("\n" + "-" * 80)
                print(f.read())
                print("-" * 80)


def find_energyplus_outputs(output_dir):
    """Locate and summarize EnergyPlus output files."""

    print("\nLocating EnergyPlus outputs...")

    # Look for common output files
    output_patterns = {
        "results.csv": "Annual/monthly results summary",
        "results_annual.csv": "Annual totals",
        "results_timeseries.csv": "Hourly timeseries data",
        "run.log": "Simulation log file",
        "*.xml": "HPXML input file(s)",
    }

    found_files = []

    for pattern, description in output_patterns.items():
        matches = list(output_dir.rglob(pattern))
        if matches:
            for match in matches:
                rel_path = match.relative_to(output_dir)
                size_kb = match.stat().st_size / 1024
                print(f"  ✓ {rel_path} ({size_kb:.1f} KB) - {description}")
                found_files.append(match)

    if not found_files:
        print("  ⚠ No output files found")
        print("  Check the results directory for simulation outputs")

    return found_files


def quick_results_preview(output_dir):
    """Show a quick preview of simulation results."""

    print("\nQuick Results Preview:")

    # Look for results.csv (annual summary)
    results_csv = list(output_dir.rglob("results.csv"))
    if not results_csv:
        results_csv = list(output_dir.rglob("results_annual.csv"))

    if results_csv:
        import pandas as pd

        try:
            df = pd.read_csv(results_csv[0])
            print(f"\nFound results file: {results_csv[0].name}")
            print("\nColumn names:")
            for col in df.columns:
                print(f"  - {col}")

            if len(df) > 0:
                print(f"\nShowing first row of results:")
                print(df.head(1).to_string())

        except Exception as e:
            print(f"  Could not read results: {e}")
    else:
        print("  No results CSV found")
        print("  Check simulation_results directory for outputs")


def main():
    """Main execution function."""

    print("Complete H2K to EnergyPlus Workflow Example")
    print("=" * 80)

    # Find H2K file
    h2k_file = find_h2k_file()

    if h2k_file is None:
        print("\nNo .h2k file found!")
        print("\nTo run this example:")
        print("  1. Place a .h2k file in examples/data/models/")
        print("  2. Create one using the Hot2000 GUI application")
        print("  3. Download sample files from NRCan resources")
        sys.exit(1)

    print(f"\nUsing file: {h2k_file.name}")

    # Setup output directory
    output_dir = Path(__file__).parent.parent.parent / "runs" / "h2k_full_workflow"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run the complete workflow
    results = run_h2k_energyplus_workflow(h2k_file, output_dir)

    if results and results.get("successful_conversions", 0) > 0:
        # Print summary
        print_workflow_summary(results)

        # Find output files
        output_files = find_energyplus_outputs(output_dir)

        # Preview results
        if output_files:
            quick_results_preview(output_dir)

        print("\n" + "=" * 80)
        print("Workflow complete!")
        print(f"\nAll outputs saved to: {output_dir}")
        print("\nNext steps:")
        print("  1. Review the results CSV files for detailed energy data")
        print("  2. Open results_timeseries.csv for hourly profiles")
        print("  3. Run example 05 to compare with native Hot2000 results")
        print("  4. Use example 04 for batch processing multiple files")
    else:
        print("\n" + "=" * 80)
        print("Workflow failed!")
        print("\nTroubleshooting:")
        print("  1. Verify the .h2k file is valid")
        print("  2. Check that OpenStudio and EnergyPlus are installed")
        print("  3. Review error messages above")
        print(f"  4. Check log files in: {output_dir}")
        sys.exit(1)


if __name__ == "__main__":
    main()

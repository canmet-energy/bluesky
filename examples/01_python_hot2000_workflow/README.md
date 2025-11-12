# Example 01: Python Hot2000 Workflow

## What This Example Demonstrates

This example shows the complete workflow for translating Canadian residential Hot2000 (.h2k) building models to EnergyPlus format and running detailed hourly simulations.

**Key Capabilities:**
- Hot2000 file format (H2K) → HPXML translation
- HPXML → OpenStudio → EnergyPlus workflow
- Residential building energy simulation
- Canadian building code compliance workflows
- Automated simulation execution and results extraction

**Why This Matters:**
Hot2000 is the primary simulation tool for Canadian residential building code compliance. This workflow enables:
- Detailed hourly simulation of Hot2000 models in EnergyPlus
- Comparison between Hot2000 and EnergyPlus results
- Integration with parametric analysis tools
- Modern simulation workflows for Canadian residential buildings

## Prerequisites

**Software:**
- Python 3.12+
- h2k-hpxml library (installed)
- OpenStudio and EnergyPlus (installed via h2k-hpxml)

**Input Files:**
- One or more Hot2000 .h2k files
- Place in `examples/data/models/` directory

**Check Installation:**
```bash
python -c "import h2k_hpxml; print('✓ h2k-hpxml ready')"
python -c "import openstudio; print('✓ OpenStudio ready')"
```

## How to Run

```bash
# From repository root
python examples/01_python_hot2000_workflow/h2k_to_energyplus.py
```

**What Happens:**
1. Script searches for .h2k files in `examples/data/models/`
2. Translates H2K → HPXML format
3. Translates HPXML → OpenStudio Model (OSM)
4. Forwards translates OSM → EnergyPlus IDF
5. Runs EnergyPlus simulation
6. Extracts results to CSV files

## Expected Output

```
runs/h2k_full_workflow/
├── <building_name>/
│   ├── <building_name>.xml      # HPXML file
│   ├── run/
│   │   ├── run.log              # Simulation log
│   │   ├── results_annual.csv   # Annual results
│   │   └── results_*.csv        # Other result files
│   └── error.txt                # If simulation fails
└── processing_results.md        # Summary report
```

## Key Concepts

### Hot2000 (H2K) Format
- Canadian residential building simulation format
- Used for building code compliance (NBC 9.36)
- Monthly quasi-steady-state calculation method
- XML-based file format

### HPXML Format
- Home Performance XML - standardized residential building format
- Developed by US Department of Energy
- Enables interoperability between simulation tools
- More detailed than Hot2000 format

### h2k-hpxml Library
- Python library for H2K ↔ HPXML translation
- Includes OpenStudio-HPXML workflow for EnergyPlus simulation
- Automatically handles climate data, schedules, and system mapping
- Provides `run_full_workflow()` API for complete automation

### Translation Considerations
- Hot2000 uses simplified algorithms; EnergyPlus uses heat balance
- Climate data formats differ (CWEC vs EPW)
- Some Hot2000-specific features may not have direct HPXML equivalents
- Results will differ due to calculation methodology

## What You'll Learn

1. **Hot2000 Integration:** How to work with Canadian residential building models
2. **Format Translation:** Converting between simulation tool formats
3. **Workflow Automation:** Using `run_full_workflow()` for complete pipelines
4. **Results Handling:** Extracting and interpreting simulation outputs
5. **h2k-hpxml API:** Key functions and parameters

## Customization Options

Edit the script to modify:

```python
results = run_full_workflow(
    input_path=h2k_file,
    output_path=output_dir,
    simulate=True,                      # Set False for translation only
    output_format="csv",                # Options: csv, json, msgpack
    add_component_loads=True,           # Include detailed load breakdowns
    hourly_outputs=["total"],           # Request hourly timeseries
    monthly_outputs=["total", "fuels"], # Request monthly breakdowns
)
```

## Troubleshooting

**No .h2k file found:**
- Place a .h2k file in `examples/data/models/`
- Or modify script to point to your file location

**Translation fails:**
- Check .h2k file is valid (open in Hot2000 GUI)
- Review error messages for specific issues
- Some complex Hot2000 features may not translate

**Simulation fails:**
- Check `run.log` for EnergyPlus errors
- Ensure climate data is available
- Try with simpler model first

## Next Steps

- **Run native Hot2000:** See how to run .h2k files directly via Wine
- **Batch processing:** Process multiple files (see h2k-hpxml docs)
- **Compare engines:** Run same model in Hot2000 and EnergyPlus
- **Parametric studies:** Vary parameters and analyze impacts

## Related Resources

- h2k-hpxml documentation: https://github.com/canmet-energy/h2k-hpxml
- HPXML schema: https://hpxml.nrel.gov/
- OpenStudio-HPXML: https://github.com/NREL/OpenStudio-HPXML
- Hot2000 (NRCan): Natural Resources Canada building simulation tool

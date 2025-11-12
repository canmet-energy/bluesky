# Building Simulation Examples

This directory contains **proof-of-concept examples** demonstrating the unique capabilities enabled by this development environment: Python, Ruby, Hot2000, and full interoperability between languages.

## The Three Examples

Each example showcases a distinct capability and workflow:

### 01: Python Hot2000 Workflow
**Path:** `01_python_hot2000_workflow/`
**What:** Translate Canadian residential Hot2000 models to EnergyPlus
**Why:** Hot2000 → HPXML → EnergyPlus enables detailed hourly simulation of Canadian residential buildings
**Language:** Python
**Key Library:** h2k-hpxml

[📖 Read detailed README](01_python_hot2000_workflow/README.md) | [▶️ Run Script](01_python_hot2000_workflow/h2k_to_energyplus.py)

---

### 02: Ruby NECB Compliance
**Path:** `02_ruby_necb_compliance/`
**What:** Create National Energy Code of Canada (NECB) compliant building models
**Why:** openstudio-standards gem provides complete Canadian code requirements (Ruby-exclusive!)
**Language:** Ruby
**Key Library:** openstudio-standards (v0.8.4)

[📖 Read detailed README](02_ruby_necb_compliance/README.md) | [▶️ Run Script](02_ruby_necb_compliance/create_necb_model.rb)

---

### 03: Python-Ruby Interoperability
**Path:** `03_python_ruby_interop/`
**What:** Combine Ruby's standards library with Python's analysis ecosystem
**Why:** Leverage unique strengths - Ruby for code-compliant models, Python for data analysis
**Languages:** Python + Ruby
**Key Capability:** Cross-language workflow orchestration

[📖 Read detailed README](03_python_ruby_interop/README.md) | [▶️ Run Script](03_python_ruby_interop/runner.py)

---

## Quick Start Decision Guide

**Choose your starting point:**

| Your Need | Start With | Why |
|-----------|------------|-----|
| I have Hot2000 (.h2k) files | Example 01 | Translate to detailed EnergyPlus simulation |
| I need NECB-compliant models | Example 02 | Use Ruby's standards library for Canadian code |
| I want to use both ecosystems | Example 03 | Learn interop patterns for mixed workflows |
| I'm new to building simulation | Example 02 | Creates complete, ready-to-simulate model |

## What Each Example Teaches

### Example 01 (Python Hot2000)
✅ Hot2000 file format and workflows
✅ H2K → HPXML → EnergyPlus translation pipeline
✅ h2k-hpxml library API
✅ Canadian residential building simulation
✅ Workflow automation with `run_full_workflow()`

### Example 02 (Ruby NECB)
✅ National Energy Code of Canada for Buildings (NECB)
✅ openstudio-standards gem usage
✅ Climate-zone-specific requirements
✅ Automated code-compliant model generation
✅ Ruby OpenStudio SDK

### Example 03 (Interop)
✅ Python ↔ Ruby communication via JSON
✅ Subprocess management across languages
✅ Leveraging language-specific libraries
✅ Workflow orchestration patterns
✅ Using interop utilities (`bluesky.core.interop`)

## Common Workflows

### Workflow A: Canadian Residential Analysis
```bash
# 1. Translate Hot2000 model
python 01_python_hot2000_workflow/h2k_to_energyplus.py

# 2. Analyze results with Python tools (pandas, matplotlib)
# ... your analysis code ...
```

### Workflow B: Canadian Commercial Baseline
```bash
# Create NECB baseline
ruby 02_ruby_necb_compliance/create_necb_model.rb

# Open in OpenStudio Application or simulate via CLI
# openstudio run -w weather.epw model.osm
```

### Workflow C: Standards-Based Parametric Study
```bash
# Use interop to combine Ruby baselines with Python analysis
python 03_python_ruby_interop/runner.py

# Extend runner.py to:
# - Create multiple variants (Ruby)
# - Run simulations in parallel (Python)
# - Analyze with pandas (Python)
```

## Language Ecosystem Comparison

| Capability | Python | Ruby | Notes |
|------------|--------|------|-------|
| **OpenStudio SDK** | ✅ Good | ✅ Native | Ruby is OpenStudio's native language |
| **NECB Standards** | ❌ None | ✅ openstudio-standards | **Ruby-exclusive library** |
| **ASHRAE 90.1** | ❌ None | ✅ openstudio-standards | DOE prototypes, multiple vintages |
| **Hot2000 Workflows** | ✅ h2k-hpxml | ❌ None | Python-exclusive |
| **Data Analysis** | ✅ pandas, numpy | ⚠️ Limited | Python ecosystem is vastly richer |
| **Visualization** | ✅ matplotlib, seaborn | ⚠️ Basic | Python has comprehensive tools |
| **Machine Learning** | ✅ scikit-learn, PyTorch | ❌ Limited | Python dominates ML |
| **Parametric Studies** | ✅ Excellent | ⚠️ OK | Python better for orchestration |

**Key Takeaway:** Use **Ruby** for standards-based models, **Python** for analysis. Use **interop** to get both!

## Repository Structure

```
examples/
├── README.md (this file)
│
├── 01_python_hot2000_workflow/
│   ├── README.md
│   └── h2k_to_energyplus.py
│
├── 02_ruby_necb_compliance/
│   ├── README.md
│   └── create_necb_model.rb
│
├── 03_python_ruby_interop/
│   ├── README.md
│   ├── create_model.rb
│   └── runner.py
│
└── data/
    ├── models/          # Place your test .h2k and .osm files here
    └── reference/       # Reference results for validation
```

## Prerequisites

**All Examples Require:**
- DevContainer environment (or manual setup)
- Python 3.12+ with openstudio and h2k-hpxml
- Ruby 3.2.2+ with openstudio and openstudio-standards gems

**Verify Installation:**
```bash
# Check Python
python -c "import openstudio; import h2k_hpxml; print('✓ Python ready')"

# Check Ruby
ruby -e "require 'openstudio'; require 'openstudio-standards'; puts '✓ Ruby ready'"

# Check Hot2000 CLI (for Example 01)
hot2000 --help | head -n 1
```

## Test Data

**For Example 01 (Hot2000):**
- Requires .h2k files
- Place in `data/models/` directory
- Or obtain from:
  - Hot2000 GUI (create test building)
  - NRCan sample files
  - Existing project files

**For Example 02 & 03:**
- Creates models programmatically
- No input files needed
- Outputs to `data/models/`

## Getting Help

**Documentation:**
- Each example has detailed README.md
- See root README.md for environment setup
- See CLAUDE.md for development guidance

**Resources:**
- OpenStudio SDK: https://openstudio-sdk-documentation.s3.amazonaws.com/
- openstudio-standards: https://github.com/NREL/openstudio-standards
- h2k-hpxml: https://github.com/canmet-energy/h2k-hpxml
- NECB information: Canadian Codes Centre, NRC

**Common Issues:**
- **Script not found:** Run from repository root
- **Import/require errors:** Check prerequisites above
- **Ruby gem errors:** Run `bundle install`
- **.h2k file not found:** Place file in `data/models/`

## Extending the Examples

These examples are **starting points**. Extend them for your needs:

**Example 01 Extensions:**
- Batch process multiple .h2k files
- Compare Hot2000 vs EnergyPlus results
- Extract specific metrics for analysis
- Integrate with parametric tools

**Example 02 Extensions:**
- Try different NECB versions (2011, 2015, 2017, 2020)
- Explore different building types (retail, school, hospital)
- Vary climate zones across Canada
- Add energy conservation measures (ECMs)

**Example 03 Extensions:**
- Add real pandas analysis
- Create matplotlib visualizations
- Build parametric runner with multiple variants
- Implement machine learning predictions

## Why These Three Examples?

1. **Example 01:** Unique to this environment - Hot2000 integration with EnergyPlus
2. **Example 02:** Showcases Ruby-exclusive capability (NECB via openstudio-standards)
3. **Example 03:** Demonstrates the power of combining both ecosystems

Together, they prove that this environment enables workflows **impossible with either language alone**.

## Next Steps

1. **Read** the README for the example that matches your needs
2. **Run** the example to see it in action
3. **Modify** the code for your specific use case
4. **Build** your own simulation application using these as templates

Happy simulating! 🏢⚡

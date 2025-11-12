# Bluesky Documentation

LLM-optimized documentation for building energy simulation using OpenStudio, NECB, Hot2000, and related tools.

---

## Purpose

This documentation is optimized for **LLM consumption** to help generate, debug, and optimize building energy models. All content is designed for:
- **Searchability** - Clear headers, consistent structure
- **Code completeness** - Copy-paste ready examples
- **Minimal explanation** - Focus on what/how, not why

---

## Quick Start by Task

### I need to...

**Fix a simulation error:**
→ [error-solutions/](error-solutions/)

**Create a new building model:**
→ [necb/necb-guide.md](necb/necb-guide.md) (NECB with geometry)
→ [ruby-gems/model-articulation-catalog.md](ruby-gems/model-articulation-catalog.md) (Prototypes)

**Write OpenStudio code (Python/Ruby):**
→ [quick-reference/python-cheatsheet.md](quick-reference/python-cheatsheet.md)
→ [quick-reference/ruby-cheatsheet.md](quick-reference/ruby-cheatsheet.md)

**Add HVAC systems:**
→ [openstudio-sdk/hvac-patterns.md](openstudio-sdk/hvac-patterns.md)

**Calibrate model to utility data:**
→ [ruby-gems/calibration-catalog.md](ruby-gems/calibration-catalog.md)

**Model energy efficiency retrofits:**
→ [ruby-gems/ee-measures-catalog.md](ruby-gems/ee-measures-catalog.md)

**Use OpenStudio measures:**
→ [ruby-gems/](ruby-gems/)

**Work with BuildingSync XML:**
→ [ruby-gems/buildingsync-guide.md](ruby-gems/buildingsync-guide.md)

**Debug IDF files:**
→ [idf-format/debugging-guide.md](idf-format/debugging-guide.md)

---

## Documentation Structure

```
docs/
├── README.md                          # This file - navigation hub
│
├── error-solutions/                   # ERROR DEBUGGING
│   ├── energyplus-errors.md          # Top 10 EnergyPlus errors
│   ├── openstudio-errors.md          # Top 20 OpenStudio errors (Python & Ruby)
│   ├── hot2000-errors.md             # Hot2000 CLI and h2k-hpxml errors
│   └── ...
│
├── idf-format/                        # IDF DEBUGGING
│   └── debugging-guide.md            # Complete IDF tutorial and error reading
│
├── quick-reference/                   # SDK QUICK REFERENCE
│   ├── python-cheatsheet.md          # Top 20 Python operations
│   └── ruby-cheatsheet.md            # Top 20 Ruby operations
│
├── openstudio-sdk/                    # SDK PATTERNS
│   ├── geometry-patterns.md          # 5 complete geometry patterns (Python)
│   └── hvac-patterns.md              # 6 complete HVAC patterns (Python)
│
├── necb/                              # NECB (CANADIAN CODE)
│   └── necb-guide.md                 # Geometry creation + NECB space types + compliance
│
└── ruby-gems/                         # OPENSTUDIO MEASURES
    ├── README.md                      # Measures navigation + decision flowchart
    ├── buildingsync-guide.md          # BuildingSync XML translator
    ├── common-measures-catalog.md     # 79 utility measures
    ├── model-articulation-catalog.md  # 45 prototype/geometry measures
    ├── calibration-catalog.md         # 35 calibration measures
    ├── ee-measures-catalog.md         # 25 energy efficiency measures
    └── load-flexibility-catalog.md    # 5 load shifting measures
```

---

## By Use Case

### 1. Debugging Simulation Errors

**Scenario:** Simulation failed, need to fix errors

**Files:**
- [error-solutions/energyplus-errors.md](error-solutions/energyplus-errors.md) - EnergyPlus `eplusout.err` errors
- [error-solutions/openstudio-errors.md](error-solutions/openstudio-errors.md) - OpenStudio SDK errors
- [error-solutions/hot2000-errors.md](error-solutions/hot2000-errors.md) - Hot2000 workflow errors
- [idf-format/debugging-guide.md](idf-format/debugging-guide.md) - How to read IDF files

**Example errors handled:**
- "Zone not found"
- "Missing thermostat"
- "Severe ** Surface vertices not convex"
- "Objects from different models"
- Hot2000 Wine execution failures

---

### 2. Creating Building Models

#### Option A: NECB (Canadian Code)

**File:** [necb/necb-guide.md](necb/necb-guide.md)

**Capabilities:**
- Create geometry using `create_shape_rectangle`, `create_shape_l`, `create_shape_courtyard`, etc.
- Assign NECB space types (NECB2011, NECB2015, NECB2017, NECB2020)
- Apply NECB constructions (by climate zone)
- Add NECB-compliant HVAC
- Complete NECB workflows (office, retail, school examples)

**When to use:** Canadian projects, NECB compliance

---

#### Option B: DOE Prototypes

**File:** [ruby-gems/model-articulation-catalog.md](ruby-gems/model-articulation-catalog.md)

**Capabilities:**
- Create DOE commercial reference buildings (ASHRAE 90.1-2004 through 90.1-2019)
- 16 building types: SmallOffice, MediumOffice, LargeOffice, Retail, Schools, Hotels, etc.
- Simple bar/box geometry creation
- Space type assignment

**When to use:** US projects, ASHRAE 90.1 baselines, quick prototypes

---

#### Option C: Custom Geometry from Scratch

**Files:**
- [openstudio-sdk/geometry-patterns.md](openstudio-sdk/geometry-patterns.md) - Python patterns
- [quick-reference/python-cheatsheet.md](quick-reference/python-cheatsheet.md) - Python SDK operations
- [quick-reference/ruby-cheatsheet.md](quick-reference/ruby-cheatsheet.md) - Ruby SDK operations

**Capabilities:**
- Create custom geometry vertex-by-vertex
- Simple box buildings
- Multi-zone buildings
- L-shaped buildings
- Parametric building functions

**When to use:** Custom geometry, specific building shapes

---

### 3. Adding Building Systems

#### HVAC Systems

**File:** [openstudio-sdk/hvac-patterns.md](openstudio-sdk/hvac-patterns.md)

**Systems included:**
- Ideal Air Loads (testing)
- PSZ-AC (packaged single zone)
- VAV with Reheat (large commercial)
- PTAC (hotels/apartments)
- Baseboard Heating (residential)
- Plant Loop (boiler + hot water)

**Includes:** Complete Python code, system comparison table

---

#### NECB-Compliant HVAC

**File:** [necb/necb-guide.md](necb/necb-guide.md) → Section 5

**Capabilities:**
- Auto-select HVAC system based on NECB rules
- NECB efficiency requirements
- Primary fuel selection (NaturalGas, Electricity, FuelOil, etc.)

---

### 4. Model Calibration

**File:** [ruby-gems/calibration-catalog.md](ruby-gems/calibration-catalog.md)

**Workflow:**
1. Import utility data (monthly bills or 15-min interval data)
2. Run baseline simulation
3. Generate calibration report (CVRMSE, NMBE)
4. Tune parameters (infiltration, loads, HVAC efficiency, etc.)
5. Iterate until CVRMSE < 15%, NMBE < ±5% (ASHRAE Guideline 14)

**Measures available:** 35 measures for data import, reporting, and parameter tuning

---

### 5. Energy Efficiency Analysis

**File:** [ruby-gems/ee-measures-catalog.md](ruby-gems/ee-measures-catalog.md)

**Categories:**
- **Envelope:** Insulation, windows, air sealing, cool roofs
- **HVAC:** High-efficiency equipment, VFDs, economizers, DCV, ERV
- **Lighting:** LED retrofits, occupancy sensors, daylighting
- **Controls:** BAS upgrades, setpoint optimization, plug load controls

**Includes:** Typical savings percentages, simple payback estimates, retrofit package examples

---

### 6. Load Flexibility / Demand Response

**File:** [ruby-gems/load-flexibility-catalog.md](ruby-gems/load-flexibility-catalog.md)

**Strategies:**
- Ice/chilled water thermal storage
- Heat pump water heater load shifting
- Precooling/preheating using building thermal mass
- Schedule shifting
- Demand limiting

**Includes:** TOU rate analysis, economic evaluation, sizing guides

---

### 7. Working with BuildingSync XML

**File:** [ruby-gems/buildingsync-guide.md](ruby-gems/buildingsync-guide.md)

**Capabilities:**
- Import BuildingSync XML → OpenStudio model
- Export OpenStudio model → BuildingSync XML
- Scenario modeling (baseline vs retrofit packages)
- Results population into XML
- ASHRAE Standard 211 workflows

---

### 8. Using OpenStudio Measures

**File:** [ruby-gems/README.md](ruby-gems/README.md)

**Overview:** Navigation guide for 189 measures across 6 gems

**Key catalogs:**
- [common-measures-catalog.md](ruby-gems/common-measures-catalog.md) - 79 utility measures (costing, reporting, manipulation)
- [model-articulation-catalog.md](ruby-gems/model-articulation-catalog.md) - 45 prototype/geometry measures
- [calibration-catalog.md](ruby-gems/calibration-catalog.md) - 35 calibration measures
- [ee-measures-catalog.md](ruby-gems/ee-measures-catalog.md) - 25 energy efficiency measures
- [load-flexibility-catalog.md](ruby-gems/load-flexibility-catalog.md) - 5 load shifting measures

**Includes:** Decision flowchart, workflow examples, measure compatibility matrix

---

## By Programming Language

### Python

**Quick reference:**
- [quick-reference/python-cheatsheet.md](quick-reference/python-cheatsheet.md) - Top 20 operations

**Patterns:**
- [openstudio-sdk/geometry-patterns.md](openstudio-sdk/geometry-patterns.md) - 5 geometry patterns
- [openstudio-sdk/hvac-patterns.md](openstudio-sdk/hvac-patterns.md) - 6 HVAC systems

**Error solutions:**
- [error-solutions/openstudio-errors.md](error-solutions/openstudio-errors.md) - Python + Ruby errors
- [error-solutions/hot2000-errors.md](error-solutions/hot2000-errors.md) - Python h2k-hpxml errors

---

### Ruby

**Quick reference:**
- [quick-reference/ruby-cheatsheet.md](quick-reference/ruby-cheatsheet.md) - Top 20 operations

**NECB workflows:**
- [necb/necb-guide.md](necb/necb-guide.md) - Complete NECB examples in Ruby

**Measures:**
- [ruby-gems/](ruby-gems/) - 189 OpenStudio measures (all Ruby-based)

**Error solutions:**
- [error-solutions/openstudio-errors.md](error-solutions/openstudio-errors.md) - Python + Ruby errors

---

## By Tool/Technology

### OpenStudio SDK

**Python:**
- [quick-reference/python-cheatsheet.md](quick-reference/python-cheatsheet.md)
- [openstudio-sdk/geometry-patterns.md](openstudio-sdk/geometry-patterns.md)
- [openstudio-sdk/hvac-patterns.md](openstudio-sdk/hvac-patterns.md)

**Ruby:**
- [quick-reference/ruby-cheatsheet.md](quick-reference/ruby-cheatsheet.md)
- [necb/necb-guide.md](necb/necb-guide.md)

**Errors:**
- [error-solutions/openstudio-errors.md](error-solutions/openstudio-errors.md)

---

### OpenStudio Measures

**Overview:**
- [ruby-gems/README.md](ruby-gems/README.md)

**All catalogs:**
- [ruby-gems/common-measures-catalog.md](ruby-gems/common-measures-catalog.md)
- [ruby-gems/model-articulation-catalog.md](ruby-gems/model-articulation-catalog.md)
- [ruby-gems/calibration-catalog.md](ruby-gems/calibration-catalog.md)
- [ruby-gems/ee-measures-catalog.md](ruby-gems/ee-measures-catalog.md)
- [ruby-gems/load-flexibility-catalog.md](ruby-gems/load-flexibility-catalog.md)
- [ruby-gems/buildingsync-guide.md](ruby-gems/buildingsync-guide.md)

---

### EnergyPlus

**IDF debugging:**
- [idf-format/debugging-guide.md](idf-format/debugging-guide.md)

**Error solutions:**
- [error-solutions/energyplus-errors.md](error-solutions/energyplus-errors.md)

---

### Hot2000

**Error solutions:**
- [error-solutions/hot2000-errors.md](error-solutions/hot2000-errors.md)

**Includes:** Wine execution errors, H2K→HPXML→EnergyPlus pipeline, encoding issues

---

### NECB (Canadian Code)

**Complete guide:**
- [necb/necb-guide.md](necb/necb-guide.md)

**Includes:**
- Geometry creation methods
- NECB space types and load densities
- NECB construction requirements by climate zone
- NECB HVAC system selection rules
- Complete workflow examples
- Compliance checks

---

### BuildingSync

**Complete guide:**
- [ruby-gems/buildingsync-guide.md](ruby-gems/buildingsync-guide.md)

**Includes:**
- XML structure overview
- Translator workflows (XML ↔ OpenStudio)
- Scenario modeling
- Results population

---

## Complete File Index

### Error Solutions (3 files)

| File | Lines | Content |
|------|-------|---------|
| [energyplus-errors.md](error-solutions/energyplus-errors.md) | 471 | Top 10 EnergyPlus errors |
| [openstudio-errors.md](error-solutions/openstudio-errors.md) | 1,456 | Top 20 OpenStudio errors (Python & Ruby) |
| [hot2000-errors.md](error-solutions/hot2000-errors.md) | 1,078 | Hot2000 workflow errors |

### IDF Format (1 file)

| File | Lines | Content |
|------|-------|---------|
| [debugging-guide.md](idf-format/debugging-guide.md) | 481 | IDF structure and error reading tutorial |

### Quick Reference (2 files)

| File | Lines | Content |
|------|-------|---------|
| [python-cheatsheet.md](quick-reference/python-cheatsheet.md) | 703 | Top 20 Python operations |
| [ruby-cheatsheet.md](quick-reference/ruby-cheatsheet.md) | 737 | Top 20 Ruby operations |

### OpenStudio SDK Patterns (2 files)

| File | Lines | Content |
|------|-------|---------|
| [geometry-patterns.md](openstudio-sdk/geometry-patterns.md) | 788 | 5 complete geometry patterns (Python) |
| [hvac-patterns.md](openstudio-sdk/hvac-patterns.md) | 627 | 6 complete HVAC systems (Python) |

### NECB (1 file)

| File | Lines | Content |
|------|-------|---------|
| [necb-guide.md](necb/necb-guide.md) | ~800 | Geometry creation + NECB space types + compliance |

### Ruby Gems / Measures (7 files)

| File | Lines | Content |
|------|-------|---------|
| [README.md](ruby-gems/README.md) | ~300 | Measures navigation + decision flowchart |
| [buildingsync-guide.md](ruby-gems/buildingsync-guide.md) | ~500 | BuildingSync XML translator |
| [common-measures-catalog.md](ruby-gems/common-measures-catalog.md) | ~800 | 79 utility measures |
| [model-articulation-catalog.md](ruby-gems/model-articulation-catalog.md) | ~500 | 45 prototype/geometry measures |
| [calibration-catalog.md](ruby-gems/calibration-catalog.md) | ~400 | 35 calibration measures |
| [ee-measures-catalog.md](ruby-gems/ee-measures-catalog.md) | ~300 | 25 energy efficiency measures |
| [load-flexibility-catalog.md](ruby-gems/load-flexibility-catalog.md) | ~200 | 5 load shifting measures |

**Total:** 17 documentation files, ~9,000 lines of LLM-optimized content

---

## Search Guide

### Search by Keyword

**Need to find:**
- **"Zone not found"** → error-solutions/openstudio-errors.md → Error #1
- **"Severe **"** → error-solutions/energyplus-errors.md or idf-format/debugging-guide.md
- **"create geometry"** → necb/necb-guide.md or openstudio-sdk/geometry-patterns.md
- **"NECB"** → necb/necb-guide.md
- **"calibration"** → ruby-gems/calibration-catalog.md
- **"CVRMSE"** → ruby-gems/calibration-catalog.md
- **"LED"** → ruby-gems/ee-measures-catalog.md
- **"ice storage"** → ruby-gems/load-flexibility-catalog.md
- **"BuildingSync"** → ruby-gems/buildingsync-guide.md
- **"create_shape"** → necb/necb-guide.md → Section 1
- **"space type"** → necb/necb-guide.md → Section 2
- **"Hot2000"** → error-solutions/hot2000-errors.md
- **"IDF"** → idf-format/debugging-guide.md
- **"Python"** → quick-reference/python-cheatsheet.md or openstudio-sdk/
- **"Ruby"** → quick-reference/ruby-cheatsheet.md or necb/necb-guide.md or ruby-gems/
- **"HVAC"** → openstudio-sdk/hvac-patterns.md or necb/necb-guide.md → Section 5
- **"window"** → necb/necb-guide.md or ruby-gems/common-measures-catalog.md
- **"measure"** → ruby-gems/

---

## LLM Usage Tips

### For Code Generation

1. **Start with cheatsheets** for basic operations:
   - Python: quick-reference/python-cheatsheet.md
   - Ruby: quick-reference/ruby-cheatsheet.md

2. **Use patterns** for complete examples:
   - Geometry: openstudio-sdk/geometry-patterns.md
   - HVAC: openstudio-sdk/hvac-patterns.md
   - NECB: necb/necb-guide.md

3. **Check measures** for pre-built functionality:
   - ruby-gems/README.md (decision flowchart)
   - Specific catalogs for detailed arguments

### For Debugging

1. **Identify error source:**
   - EnergyPlus simulation → error-solutions/energyplus-errors.md
   - OpenStudio SDK → error-solutions/openstudio-errors.md
   - Hot2000 workflow → error-solutions/hot2000-errors.md
   - IDF structure → idf-format/debugging-guide.md

2. **Search error message** in appropriate file

3. **Apply solution** (code examples included)

### For Workflows

1. **Check ruby-gems/README.md** decision flowchart for measure workflows

2. **Check necb/necb-guide.md** for complete NECB workflows

3. **Combine multiple files** for complex tasks:
   - Example: Calibration workflow = model-articulation-catalog.md (baseline) + calibration-catalog.md (tuning) + common-measures-catalog.md (reporting)

---

## Contributing

When adding new documentation:
1. Optimize for LLM searchability (clear headers, consistent structure)
2. Include complete, copy-paste ready code examples
3. Minimize explanatory text (focus on what/how)
4. Update this README.md with links to new files
5. Add to appropriate section in decision flowchart

---

## Related Resources

**Project root:**
- `CLAUDE.md` - Project-level instructions for LLMs
- `.devcontainer/` - DevContainer setup with certificate management
- `pyproject.toml` - Python dependencies including h2k-hpxml, openstudio

**External links:**
- OpenStudio SDK: https://openstudio-sdk-documentation.s3.amazonaws.com/index.html
- NREL BCL: https://bcl.nrel.gov
- CanmetENERGY measures: https://github.com/canmet-energy
- NECB: https://www.nrc-cnrc.gc.ca/eng/solutions/advisory/codes_centre/necb.html

# Ruby Gems Reference

Navigation guide for CanmetENERGY OpenStudio extension gems. These gems provide measures and utilities for building energy modeling workflows.

---

## Available Documentation

### 1. BuildingSync Guide
**File:** [buildingsync-guide.md](buildingsync-guide.md)
**Purpose:** BuildingSync XML translator and scenario modeling
**Use when:**
- Importing building data from BuildingSync XML
- Exporting OpenStudio models to BuildingSync format
- Modeling baseline vs retrofit scenarios
- ASHRAE Standard 211 workflows

**Key capabilities:**
- XML ↔ OpenStudio model translation
- Scenario management (baseline, packages of measures)
- Energy results population
- BuildingSync API methods

---

### 2. Common Measures Catalog
**File:** [common-measures-catalog.md](common-measures-catalog.md)
**Purpose:** 79+ utility measures for costing, reporting, and model manipulation
**Use when:**
- Adding cost analysis to workflows
- Generating reports (OpenStudioResults, StandardReports)
- Modifying existing models (WWR, schedules, loads)
- Adding output variables/meters
- Running SQL queries on results

**Key categories:**
- **Costing:** Life cycle cost, utility tariffs
- **Outputs & Reporting:** Custom reports, CSV exports, calibration metrics
- **Model Manipulation:** Geometry changes, construction swaps, load adjustments
- **Advanced Features:** Radiance, EMS, IDF injection, PV systems

**Most used measures:**
- `OpenStudioResults` - HTML report generation
- `AddOutputVariable` / `AddMeter` - Add EnergyPlus outputs
- `TimeseriesObjectiveFunction` - Calibration metrics
- `AddRemoveOrReplaceWindows` - Modify WWR
- `SetLifecycleCostParameters` - Configure economic analysis

---

### 3. Model Articulation Catalog
**File:** [model-articulation-catalog.md](model-articulation-catalog.md)
**Purpose:** 45+ measures for creating prototype buildings and geometry
**Use when:**
- Generating buildings from scratch
- Creating DOE/NECB prototype buildings
- Parametric geometry studies
- Assigning space types and templates

**Key categories:**
- **Bar Buildings:** Simple parametric box geometry
- **Prototype Buildings:** DOE commercial reference buildings, NECB archetypes
- **Space Type Assignment:** Apply templates to models
- **Geometry Manipulation:** WWR by facade, overhangs, surface matching

**Most used measures:**
- `CreateBarBuilding` - Fast parametric geometry
- `CreateDOEPrototypeBuilding` - ASHRAE 90.1 prototypes
- `CreateNECBPrototypeBuilding` - NECB archetypes
- `SetWindowToWallRatioByFacade` - Facade-specific WWR
- `AddDaylightingControls` - Daylighting sensors

**Building types available:**
- SmallOffice, MediumOffice, LargeOffice
- RetailStandalone, RetailStripmall
- PrimarySchool, SecondarySchool
- SmallHotel, LargeHotel
- Hospital, Outpatient
- Warehouse, Restaurants, Apartments

---

### 4. Calibration Catalog
**File:** [calibration-catalog.md](calibration-catalog.md)
**Purpose:** 35+ measures for model calibration to utility data
**Use when:**
- Calibrating models to utility bills or interval data
- Calculating CVRMSE, NMBE (ASHRAE Guideline 14)
- Tuning uncertain parameters
- Generating calibration reports

**Key categories:**
- **Utility Data Import:** Monthly bills, 15-min/hourly interval data
- **Calibration Reporting:** CVRMSE/NMBE calculation, comparison charts
- **HVAC Tuning:** Adjust boiler/chiller efficiency, fan/pump performance
- **Envelope Tuning:** Adjust R-values, infiltration, window properties
- **General Tuning:** Schedules, loads, occupancy density

**Calibration workflow:**
1. Import utility data → `AddMonthlyUtilityData`, `AddIntervalUtilityData`
2. Run baseline simulation
3. Generate report → `CalibrationReportsEnhanced20`
4. Tune parameters → Adjustment measures
5. Iterate until CVRMSE < 15%, NMBE < ±5%

**Most impactful tuning parameters:**
- Infiltration, thermostat setpoints, lighting/plug loads
- Chiller COP, boiler efficiency
- Occupancy schedules

---

### 5. Energy Efficiency Measures Catalog
**File:** [ee-measures-catalog.md](ee-measures-catalog.md)
**Purpose:** 25+ energy efficiency retrofit measures
**Use when:**
- Modeling energy efficiency retrofits
- Evaluating savings potential
- Creating retrofit packages
- Estimating costs and paybacks

**Key categories:**
- **Envelope:** Insulation, high-performance windows, air sealing, cool roofs
- **HVAC:** High-efficiency equipment, VFDs, economizers, DCV, ERV
- **Lighting:** LED retrofits, occupancy sensors, daylighting controls
- **Controls:** BAS upgrades, setpoint optimization, plug load controls

**Typical savings by measure:**
- LED lighting: 40-60% lighting energy (2-5 year payback)
- VFDs: 20-40% fan/pump energy (3-8 year payback)
- High-efficiency chiller: 20-35% cooling energy (5-12 year payback)
- Economizer: 10-25% cooling energy (2-6 year payback)

**Example retrofit packages:**
- Small office: LED + occupancy sensors + air sealing + roof insulation
- Medium office: High-eff chiller + VFDs + economizer + DCV
- Deep retrofit: Envelope + HVAC + lighting + controls (50-60% savings)

---

### 6. Load Flexibility Catalog
**File:** [load-flexibility-catalog.md](load-flexibility-catalog.md)
**Purpose:** 5 measures for load shifting and thermal energy storage
**Use when:**
- Modeling demand response strategies
- Evaluating time-of-use rate savings
- Shifting loads to off-peak periods
- Integrating thermal storage

**Key strategies:**
- **Ice/Chilled Water Storage:** Shift cooling to nighttime
- **HPWH Controls:** Shift DHW loads (preheat + lockout)
- **Precooling/Preheating:** Use building thermal mass
- **Schedule Shifting:** Move equipment operation to off-peak
- **Demand Limiting:** Cap peak demand

**Best candidates:**
- Buildings with TOU rates + demand charges
- High cooling loads (> 100 tons)
- Significant thermal mass
- Flexible occupancy schedules

**Typical savings:**
- Ice storage: 30-50% cooling cost (5-10 year payback)
- HPWH controls: 20-40% DHW cost (1-3 year payback)
- Precooling: 15-30% cooling cost (2-5 year payback)

---

## Decision Flowchart

```
START: What do you need to do?

├─ Create new building model
│  ├─ From scratch (parametric)
│  │  └─ Use: model-articulation-catalog.md → CreateBarBuilding
│  ├─ DOE/NECB prototype
│  │  └─ Use: model-articulation-catalog.md → CreateDOEPrototypeBuilding / CreateNECBPrototypeBuilding
│  └─ From BuildingSync XML
│     └─ Use: buildingsync-guide.md → Translator workflow
│
├─ Modify existing model
│  ├─ Change geometry (WWR, overhangs, etc.)
│  │  └─ Use: common-measures-catalog.md (Model Manipulation) or model-articulation-catalog.md (Geometry)
│  ├─ Change loads/schedules
│  │  └─ Use: common-measures-catalog.md (Model Manipulation)
│  └─ Apply standards/templates
│     └─ Use: model-articulation-catalog.md (Space Type Assignment)
│
├─ Calibrate model to measured data
│  ├─ Import utility data
│  │  └─ Use: calibration-catalog.md → AddMonthlyUtilityData / AddIntervalUtilityData
│  ├─ Calculate calibration metrics
│  │  └─ Use: calibration-catalog.md → CalibrationReportsEnhanced20
│  └─ Tune parameters
│     └─ Use: calibration-catalog.md (HVAC/Envelope/General Tuning)
│
├─ Model energy efficiency retrofits
│  ├─ Envelope improvements
│  │  └─ Use: ee-measures-catalog.md (Envelope Improvements)
│  ├─ HVAC upgrades
│  │  └─ Use: ee-measures-catalog.md (HVAC Improvements)
│  ├─ Lighting upgrades
│  │  └─ Use: ee-measures-catalog.md (Lighting Improvements)
│  └─ Controls/automation
│     └─ Use: ee-measures-catalog.md (Controls & Automation)
│
├─ Model load flexibility / demand response
│  ├─ Thermal energy storage
│  │  └─ Use: load-flexibility-catalog.md → AddIceThermalStorage / AddChilledWaterThermalStorage
│  ├─ DHW load shifting
│  │  └─ Use: load-flexibility-catalog.md → AddHPWHLoadShifting
│  └─ Building thermal mass / schedules
│     └─ Use: load-flexibility-catalog.md → AddPrecoolingPreconditioningControl / ShiftScheduleForDemandResponse
│
├─ Generate reports / add outputs
│  ├─ Standard HTML reports
│  │  └─ Use: common-measures-catalog.md → OpenStudioResults / StandardReports
│  ├─ Add output variables/meters
│  │  └─ Use: common-measures-catalog.md → AddOutputVariable / AddMeter
│  ├─ Export to CSV
│  │  └─ Use: common-measures-catalog.md → ExportVariabletoCSV / ExportMetertoCSV
│  └─ Calibration reports
│     └─ Use: calibration-catalog.md → CalibrationReportsEnhanced20
│
└─ Economic analysis
   ├─ Add costs to measures
   │  └─ Use: common-measures-catalog.md (Costing measures)
   ├─ Configure life cycle analysis
   │  └─ Use: common-measures-catalog.md → SetLifecycleCostParameters
   └─ Apply utility tariffs
      └─ Use: common-measures-catalog.md → TariffSelectionFlatRate / TariffSelectionTimeAndDateDependant
```

---

## Common Workflows

### Workflow 1: Create Baseline Model from Prototype

```ruby
# Step 1: Create prototype building
CreateDOEPrototypeBuilding
  - template: '90.1-2019'
  - building_type: 'MediumOffice'
  - climate_zone: 'ASHRAE 169-2013-6A'

# Step 2: Customize WWR
SetWindowToWallRatioByFacade
  - wwr_north: 0.30
  - wwr_south: 0.40

# Step 3: Add reporting
OpenStudioResults
```

### Workflow 2: Calibration Workflow

```ruby
# Step 1: Import utility bills
AddMonthlyUtilityData
  - electric_json: '{...}'
  - gas_json: '{...}'

# Step 2: Run simulation (baseline)

# Step 3: Generate calibration report
CalibrationReportsEnhanced20
  - fuel_type: 'All'
  - report_frequency: 'Monthly'

# Step 4: Review CVRMSE/NMBE, tune parameters
AdjustLightingLoadByPercentage
  - lighting_adjustment_percent: -15.0

AdjustInfiltrationByPercentage
  - infiltration_adjustment_percent: 20.0

# Step 5: Re-run until calibrated (CVRMSE < 15%, NMBE < ±5%)
```

### Workflow 3: Energy Efficiency Retrofit Analysis

```ruby
# Step 1: Create baseline (calibrated model or prototype)

# Step 2: Apply retrofit measures
ReplaceLightingWithLED
  - lighting_power_reduction_percent: 50.0
  - led_cost_per_watt_saved: 1.20

AddVariableFrequencyDrivesToFans
  - fan_power_reduction_percent: 30.0
  - vfd_cost_per_hp: 120.0

AddOrImproveEconomizer
  - economizer_control_type: 'DifferentialDryBulb'

# Step 3: Configure economic analysis
SetLifecycleCostParameters
  - study_period: 25
  - real_discount_rate: 0.03

TariffSelectionFlatRate
  - elec_rate: 0.12

# Step 4: Generate reports
StandardReports
OpenStudioResults
```

### Workflow 4: Load Flexibility Analysis

```ruby
# Step 1: Create baseline model

# Step 2: Apply load flexibility measures
AddIceThermalStorage
  - storage_capacity_ton_hrs: 1200.0
  - charge_schedule_name: 'Ice Charge (10 PM - 6 AM)'

AddPrecoolingPreconditioningControl
  - precool_start_hour: 5
  - precool_setpoint_adjustment_f: -3.0

# Step 3: Apply time-of-use tariff
TariffSelectionTimeAndDateDependant
  - elec_rate_json: '{...}'  # TOU rates

# Step 4: Generate reports and compare costs
```

---

## Measure Compatibility Matrix

| Workflow Type | Compatible Catalogs | Notes |
|--------------|-------------------|-------|
| **New model creation** | Model Articulation → Common (reporting) | Start with prototypes or bar buildings |
| **Calibration** | Model Articulation (baseline) → Calibration → Common (reporting) | Create baseline first, then calibrate |
| **Retrofit analysis** | Model Articulation (baseline) → EE Measures → Common (costing/reporting) | Baseline + retrofit package comparison |
| **Load flexibility** | Model Articulation → Load Flexibility → Common (TOU tariffs) | Requires TOU rates for cost benefits |
| **BuildingSync workflow** | BuildingSync → Common (reporting) | Import XML, run scenarios |
| **Parametric study** | Model Articulation (bar studies) → Common (reporting) | Automated multi-model generation |

---

## Measure Type Reference

### OpenStudio Measure Types

1. **ModelMeasure** - Modifies OpenStudio model before translation
   - Examples: CreateBarBuilding, ReplaceLightingWithLED, AddIceThermalStorage
   - Runs: Before IDF translation
   - Use for: Geometry, loads, HVAC, constructions

2. **EnergyPlusMeasure** - Modifies EnergyPlus IDF before simulation
   - Examples: AddOutputVariable, AddMeter, InjectIDFObjects
   - Runs: After IDF translation, before simulation
   - Use for: Output variables, IDF object injection

3. **ReportingMeasure** - Processes simulation results
   - Examples: OpenStudioResults, CalibrationReportsEnhanced20, StandardReports
   - Runs: After simulation completes
   - Use for: Reports, data extraction, calibration metrics

### Workflow Placement

```
┌─────────────────────────────────────────────────────────┐
│ OpenStudio Workflow (OSW) Execution Order              │
├─────────────────────────────────────────────────────────┤
│ 1. ModelMeasures (Ruby)                                │
│    ├─ Create/modify geometry                           │
│    ├─ Apply templates/standards                        │
│    ├─ Add HVAC systems                                 │
│    ├─ Add loads/schedules                              │
│    └─ Add costs                                         │
├─────────────────────────────────────────────────────────┤
│ 2. Forward Translation (OSM → IDF)                     │
├─────────────────────────────────────────────────────────┤
│ 3. EnergyPlusMeasures (Ruby)                           │
│    ├─ Add output variables/meters                      │
│    └─ Inject IDF objects                               │
├─────────────────────────────────────────────────────────┤
│ 4. EnergyPlus Simulation                               │
├─────────────────────────────────────────────────────────┤
│ 5. ReportingMeasures (Ruby)                            │
│    ├─ Generate HTML reports                            │
│    ├─ Calculate metrics                                │
│    └─ Export data                                       │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Search

**Need to...**
- **Create a simple building?** → model-articulation-catalog.md → `CreateBarBuilding`
- **Create DOE prototype?** → model-articulation-catalog.md → `CreateDOEPrototypeBuilding`
- **Import BuildingSync XML?** → buildingsync-guide.md → Translator workflow
- **Generate HTML report?** → common-measures-catalog.md → `OpenStudioResults`
- **Add output variables?** → common-measures-catalog.md → `AddOutputVariable`
- **Change WWR?** → common-measures-catalog.md → `AddRemoveOrReplaceWindows`
- **Calibrate to utility bills?** → calibration-catalog.md → `AddMonthlyUtilityData` + `CalibrationReportsEnhanced20`
- **LED retrofit?** → ee-measures-catalog.md → `ReplaceLightingWithLED`
- **Add VFDs?** → ee-measures-catalog.md → `AddVariableFrequencyDrivesToFans`
- **Ice storage?** → load-flexibility-catalog.md → `AddIceThermalStorage`
- **Precooling?** → load-flexibility-catalog.md → `AddPrecoolingPreconditioningControl`
- **Life cycle cost analysis?** → common-measures-catalog.md → `SetLifecycleCostParameters`
- **Time-of-use rates?** → common-measures-catalog.md → `TariffSelectionTimeAndDateDependant`

---

## Additional Resources

**Related Documentation:**
- `/docs/openstudio-sdk/` - OpenStudio SDK patterns (Python/Ruby)
- `/docs/quick-reference/` - Language-specific cheatsheets
- `/docs/error-solutions/` - Debugging guides

**External Resources:**
- OpenStudio SDK Documentation: https://openstudio-sdk-documentation.s3.amazonaws.com/index.html
- Building Component Library (BCL): https://bcl.nrel.gov
- OpenStudio GitHub: https://github.com/NREL/OpenStudio
- CanmetENERGY Measures: https://github.com/canmet-energy

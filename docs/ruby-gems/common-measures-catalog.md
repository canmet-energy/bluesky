# OpenStudio Common Measures Catalog

**Purpose:** Collection of 79+ utility measures for costing, outputs, model manipulation, and advanced OpenStudio features.

**Repository:** https://github.com/canmet-energy/openstudio-common-measures-gem.git (branch: develop)

**When to use:** Add supporting functionality to OpenStudio workflows (cost calculations, custom reports, model transformations, QA/QC checks).

---

## Categories

1. **Costing** - Life cycle cost analysis, utility tariffs, cost estimation
2. **Outputs & Reporting** - Custom reports, data extraction, visualization
3. **Model Manipulation** - Bulk edits, object cloning, search/replace
4. **Advanced Features** - Radiance integration, SQL queries, external tools

---

## 1. Costing Measures

### AddCostPerFloorAreaToBuilding
**Purpose:** Add cost to entire building based on floor area
**Arguments:**
- `remove_costs` (bool) - Remove existing costs before adding
- `material_cost_per_area` (double) - $/m² material cost
- `demolition_cost_per_area` (double) - $/m² demolition cost
- `years_until_costs_start` (int) - Delay before costs apply
- `demo_cost_initial_const` (bool) - Include demolition in initial cost
- `expected_life` (int) - Years until replacement
- `om_cost_per_area` (double) - $/m²/year O&M cost

**Example:**
```ruby
# Add $100/m² construction cost with 20-year life
measure.setArgument('material_cost_per_area', 100.0)
measure.setArgument('expected_life', 20)
measure.setArgument('om_cost_per_area', 2.0)
```

### AddCostToBuilding
**Purpose:** Add fixed cost to building (not area-based)
**Arguments:**
- `remove_costs` (bool)
- `material_cost` (double) - $ total material cost
- `demolition_cost` (double) - $ total demolition cost
- `years_until_costs_start` (int)
- `demo_cost_initial_const` (bool)
- `expected_life` (int)
- `om_cost` (double) - $/year O&M

**Example:**
```ruby
# Add $50,000 one-time cost
measure.setArgument('material_cost', 50000.0)
measure.setArgument('years_until_costs_start', 0)
```

### AddMonthlyJSONUtilityData
**Purpose:** Import utility bill data from JSON for calibration
**Arguments:**
- `json` (string) - JSON string with monthly utility data
- `variable_name` (string) - Output variable name for reporting
- `fuel_type` (choice) - Electricity, Gas, Water, etc.
- `consumption_unit` (choice) - kWh, therms, ccf, etc.

**Example:**
```ruby
json_data = '{
  "2023-01": {"consumption": 15000, "demand": 100, "cost": 1800},
  "2023-02": {"consumption": 14000, "demand": 95, "cost": 1680}
}'
measure.setArgument('json', json_data)
measure.setArgument('fuel_type', 'Electricity')
measure.setArgument('consumption_unit', 'kWh')
```

### TariffSelectionFlatRate
**Purpose:** Apply simple flat-rate utility tariff
**Arguments:**
- `elec_rate` (double) - $/kWh electricity rate
- `gas_rate` (double) - $/therm natural gas rate
- `water_rate` (double) - $/gal water rate

**Example:**
```ruby
measure.setArgument('elec_rate', 0.12)
measure.setArgument('gas_rate', 1.05)
```

### TariffSelectionTimeAndDateDependant
**Purpose:** Apply time-of-use (TOU) utility tariff
**Arguments:**
- `demand_window_length` (choice) - QuarterHour, HalfHour, FullHour
- `elec_rate_json` (string) - JSON with TOU rates by hour/month
- `gas_rate` (double) - $/therm flat gas rate

**Example:**
```ruby
tou_rates = '{
  "summer_peak": 0.25,
  "summer_offpeak": 0.10,
  "winter_peak": 0.18,
  "winter_offpeak": 0.08
}'
measure.setArgument('elec_rate_json', tou_rates)
measure.setArgument('demand_window_length', 'QuarterHour')
```

---

## 2. Outputs & Reporting Measures

### AddOutputVariable
**Purpose:** Add EnergyPlus output variable to SQL results
**Arguments:**
- `variable_name` (string) - EnergyPlus variable name
- `reporting_frequency` (choice) - Timestep, Hourly, Daily, Monthly, RunPeriod
- `key_value` (string) - Object key (e.g., zone name) or "*" for all

**Example:**
```ruby
# Add hourly zone temperature output
measure.setArgument('variable_name', 'Zone Mean Air Temperature')
measure.setArgument('reporting_frequency', 'Hourly')
measure.setArgument('key_value', '*')
```

### AddMeter
**Purpose:** Add EnergyPlus meter to SQL results
**Arguments:**
- `meter_name` (string) - Meter name (e.g., "Electricity:Facility")
- `reporting_frequency` (choice) - Timestep, Hourly, Daily, Monthly, RunPeriod

**Example:**
```ruby
measure.setArgument('meter_name', 'Electricity:Facility')
measure.setArgument('reporting_frequency', 'Hourly')
```

### ExportVariabletoCSV
**Purpose:** Export specific output variable to CSV file
**Arguments:**
- `variable_name` (string) - Variable to export
- `reporting_frequency` (choice) - Frequency to export
- `key_value` (string) - Object key

**Example:**
```ruby
measure.setArgument('variable_name', 'Zone Mean Air Temperature')
measure.setArgument('reporting_frequency', 'Hourly')
```

### ExportMetertoCSV
**Purpose:** Export meter data to CSV file
**Arguments:**
- `meter_name` (string) - Meter to export
- `reporting_frequency` (choice)

**Example:**
```ruby
measure.setArgument('meter_name', 'Electricity:Facility')
measure.setArgument('reporting_frequency', 'Monthly')
```

### OpenStudioResults
**Purpose:** Generate comprehensive HTML report with charts
**Arguments:** (none - automatically generates report)

**Example:**
```ruby
# No arguments needed - place at end of workflow
# Generates report.html in reports/ directory
```

### TimeseriesObjectiveFunction
**Purpose:** Calculate objective function for calibration/optimization
**Arguments:**
- `csv_name` (string) - Path to measured data CSV
- `csv_time_header` (string) - Time column header
- `csv_var_header` (string) - Variable column header
- `csv_var_dn` (string) - Display name for variable
- `variable_name` (string) - Simulated variable name
- `reporting_frequency` (choice)
- `key_value` (string)
- `objective_function` (choice) - CVRMSE, NMBE, R2

**Example:**
```ruby
measure.setArgument('csv_name', 'measured_electricity.csv')
measure.setArgument('csv_time_header', 'Date/Time')
measure.setArgument('csv_var_header', 'kWh')
measure.setArgument('variable_name', 'Electricity:Facility')
measure.setArgument('objective_function', 'CVRMSE')
```

### StandardReports
**Purpose:** Generate ASHRAE 90.1 Appendix G compliance report
**Arguments:**
- `building_summary_section` (bool) - Include building summary
- `annual_overview_section` (bool) - Include annual overview
- `monthly_overview_section` (bool) - Include monthly breakdown
- `utility_bills_rates_section` (bool) - Include utility costs
- `envelope_section_section` (bool) - Include envelope details
- `space_type_breakdown_section` (bool) - Include space types
- `hvac_load_profile` (bool) - Include load profiles
- `zone_condition_section` (bool) - Include zone conditions
- `zone_summary_section` (bool) - Include zone summary

**Example:**
```ruby
# Enable all sections for comprehensive report
measure.setArgument('building_summary_section', true)
measure.setArgument('annual_overview_section', true)
measure.setArgument('monthly_overview_section', true)
```

### EnvelopeAndLoadsSummary
**Purpose:** Detailed report on envelope performance and loads
**Arguments:** (none - auto-generates from model)

**Example:**
```ruby
# Generates envelope_report.html with:
# - Construction details
# - Window-to-wall ratios
# - Thermal performance metrics
# - Peak heating/cooling loads
```

### OccupantImpactReport
**Purpose:** Report on occupant comfort and indoor conditions
**Arguments:**
- `zone_condition_section` (bool) - Include zone conditions
- `airloop_detail_section` (bool) - Include HVAC details

**Example:**
```ruby
measure.setArgument('zone_condition_section', true)
measure.setArgument('airloop_detail_section', true)
```

---

## 3. Model Manipulation Measures

### AddRemoveOrReplaceWindows
**Purpose:** Modify window-to-wall ratio (WWR) by adding/removing windows
**Arguments:**
- `wwr` (double) - Target window-to-wall ratio (0.0 to 0.95)
- `facade` (choice) - North, South, East, West, or All
- `construction` (string) - Construction name for new windows

**Example:**
```ruby
# Set south facade to 40% WWR
measure.setArgument('wwr', 0.40)
measure.setArgument('facade', 'South')
measure.setArgument('construction', 'U 0.45 SHGC 0.25 Dbl Ref-D Clr 6mm/6mm Air')
```

### AssignSpaceTypeBySpaceName
**Purpose:** Auto-assign space types based on space name patterns
**Arguments:**
- `standards_building_type` (choice) - Building type (Office, Retail, etc.)
- `standards_space_type` (choice) - Space type category

**Example:**
```ruby
# Assign office space types based on name matching
measure.setArgument('standards_building_type', 'Office')
```

### ChangeBuildingLocation
**Purpose:** Update building location and climate
**Arguments:**
- `weather_file_name` (choice) - EPW file from library
- `climate_zone` (choice) - ASHRAE climate zone

**Example:**
```ruby
measure.setArgument('weather_file_name', 'CAN_ON_Toronto.716240_CWEC2016.epw')
measure.setArgument('climate_zone', 'ASHRAE 169-2013-6A')
```

### CopySpaceTypeLoadsAndSchedules
**Purpose:** Clone loads and schedules from one space type to another
**Arguments:**
- `source_space_type_name` (string) - Source space type
- `target_space_type_name` (string) - Target space type

**Example:**
```ruby
measure.setArgument('source_space_type_name', 'Office - OpenOffice')
measure.setArgument('target_space_type_name', 'Office - ClosedOffice')
```

### SetInteriorWallsAndCeilingsToAdiabatic
**Purpose:** Make interior surfaces adiabatic (no heat transfer)
**Arguments:** (none)

**Example:**
```ruby
# Useful for single-zone models to ignore interior surfaces
```

### SetSpaceTypeLoadValues
**Purpose:** Bulk edit load densities for space type
**Arguments:**
- `space_type` (choice) - Space type to modify
- `lighting_per_area` (double) - W/m² lighting
- `electric_equipment_per_area` (double) - W/m² plug loads
- `gas_equipment_per_area` (double) - W/m² gas equipment
- `people_per_area` (double) - people/m²
- `infiltration_per_exterior_area` (double) - m³/s/m² infiltration

**Example:**
```ruby
measure.setArgument('space_type', 'Office - OpenOffice')
measure.setArgument('lighting_per_area', 10.5)
measure.setArgument('electric_equipment_per_area', 8.0)
measure.setArgument('people_per_area', 0.05)
```

### ReplaceExteriorWindowConstruction
**Purpose:** Replace all window constructions with new construction
**Arguments:**
- `construction` (choice) - New construction name from model

**Example:**
```ruby
measure.setArgument('construction', 'U 0.35 SHGC 0.30 Dbl Ref-A Clr 3mm/13mm Arg')
```

### ReplaceExteriorWallConstruction
**Purpose:** Replace all exterior wall constructions
**Arguments:**
- `construction` (choice) - New construction name

**Example:**
```ruby
measure.setArgument('construction', 'Metal Framing Wall R-15.87')
```

### ReplaceRoofConstruction
**Purpose:** Replace all roof constructions
**Arguments:**
- `construction` (choice) - New construction name

**Example:**
```ruby
measure.setArgument('construction', 'IEAD Roof R-30.08')
```

### RotateBuilding
**Purpose:** Rotate building geometry around origin
**Arguments:**
- `relative_building_rotation` (double) - Degrees to rotate (positive = clockwise)

**Example:**
```ruby
# Rotate building 90 degrees clockwise
measure.setArgument('relative_building_rotation', 90.0)
```

### ScaleGeometry
**Purpose:** Scale entire building geometry
**Arguments:**
- `x_scale` (double) - X-axis scale factor
- `y_scale` (double) - Y-axis scale factor
- `z_scale` (double) - Z-axis scale factor

**Example:**
```ruby
# Make building 20% taller
measure.setArgument('x_scale', 1.0)
measure.setArgument('y_scale', 1.0)
measure.setArgument('z_scale', 1.2)
```

### ShiftScheduleByType
**Purpose:** Time-shift schedules (useful for load flexibility)
**Arguments:**
- `schedule_type` (choice) - Lights, Equipment, Occupancy, etc.
- `shift_value` (double) - Hours to shift (positive = later)

**Example:**
```ruby
# Shift lighting schedules 2 hours later
measure.setArgument('schedule_type', 'Lights')
measure.setArgument('shift_value', 2.0)
```

### SetLifecycleCostParameters
**Purpose:** Configure economic analysis parameters
**Arguments:**
- `study_period` (int) - Analysis period (years)
- `base_year` (int) - Base year for costs
- `inflation_rate` (double) - Annual inflation rate
- `real_discount_rate` (double) - Real discount rate
- `elec_inflation_rate` (double) - Electricity inflation rate
- `gas_inflation_rate` (double) - Gas inflation rate

**Example:**
```ruby
measure.setArgument('study_period', 25)
measure.setArgument('inflation_rate', 0.02)
measure.setArgument('real_discount_rate', 0.03)
```

### AddElectricMeanRadiantFloor
**Purpose:** Add electric radiant floor heating to zones
**Arguments:**
- `zones` (choice) - Zones to add radiant heating (or "*" for all)

**Example:**
```ruby
measure.setArgument('zones', '*')
```

### AddHydronic MeanRadiantFloor
**Purpose:** Add hydronic radiant floor heating to zones
**Arguments:**
- `zones` (choice) - Zones to add radiant heating

**Example:**
```ruby
measure.setArgument('zones', '*')
```

### AssignConstructionSetToBuilding
**Purpose:** Apply construction set to entire building
**Arguments:**
- `construction_set` (choice) - Construction set name

**Example:**
```ruby
measure.setArgument('construction_set', 'ASHRAE 189.1-2009 ExtWall Mass ClimateZone 6')
```

### ChangeBuildingName
**Purpose:** Rename building object
**Arguments:**
- `building_name` (string) - New building name

**Example:**
```ruby
measure.setArgument('building_name', 'Office Building - Toronto')
```

---

## 4. Advanced Features Measures

### RunSQLiteScript
**Purpose:** Execute custom SQL query on EnergyPlus results database
**Arguments:**
- `script` (string) - SQL query to execute
- `output_name` (string) - Output variable name for results

**Example:**
```ruby
sql_query = "SELECT AVG(VariableValue) FROM ReportVariableData WHERE Name='Zone Mean Air Temperature'"
measure.setArgument('script', sql_query)
measure.setArgument('output_name', 'avg_zone_temp')
```

### GLHEProSetGFunction
**Purpose:** Configure ground heat exchanger g-function
**Arguments:**
- `borehole_depth` (double) - Depth of boreholes (m)
- `borehole_spacing` (double) - Spacing between boreholes (m)
- `ghe_configuration` (choice) - Rectangle, L-shape, U-shape, etc.

**Example:**
```ruby
measure.setArgument('borehole_depth', 100.0)
measure.setArgument('borehole_spacing', 6.0)
measure.setArgument('ghe_configuration', 'Rectangle')
```

### RadianceMeasure
**Purpose:** Enable Radiance daylighting simulation
**Arguments:**
- `include_sqlite_output` (bool) - Include SQL output
- `include_html_output` (bool) - Include HTML report

**Example:**
```ruby
measure.setArgument('include_sqlite_output', true)
measure.setArgument('include_html_output', true)
```

### AddDesignDayFromDDY
**Purpose:** Import design days from DDY file
**Arguments:**
- `ddy_file` (string) - Path to DDY file
- `summer_design_day_name` (string) - Summer design day name
- `winter_design_day_name` (string) - Winter design day name

**Example:**
```ruby
measure.setArgument('ddy_file', 'CAN_ON_Toronto.716240_CWEC2016.ddy')
measure.setArgument('summer_design_day_name', '.4% Cooling Design Day')
measure.setArgument('winter_design_day_name', '99.6% Heating Design Day')
```

### AddEMSToCallEMiniProgram
**Purpose:** Add EnergyManagementSystem (EMS) program to model
**Arguments:**
- `ems_program_text` (string) - EMS program code
- `ems_program_name` (string) - Program name

**Example:**
```ruby
ems_code = "SET MyVariable = 0.5"
measure.setArgument('ems_program_text', ems_code)
measure.setArgument('ems_program_name', 'CustomControl')
```

### InjectIDFObjects
**Purpose:** Inject raw IDF objects into model
**Arguments:**
- `idf_objects_text` (string) - IDF object text

**Example:**
```ruby
idf_text = "
Output:Variable,
  *,                           ! Key Value
  Zone Mean Air Temperature,   ! Variable Name
  Hourly;                      ! Reporting Frequency
"
measure.setArgument('idf_objects_text', idf_text)
```

### AddSimplePVtoShadingSurfacesByType
**Purpose:** Add photovoltaic panels to shading surfaces
**Arguments:**
- `fraction_surface_with_pv` (double) - Coverage fraction (0.0 to 1.0)
- `cell_efficiency` (double) - PV cell efficiency
- `inverter_efficiency` (double) - Inverter efficiency

**Example:**
```ruby
measure.setArgument('fraction_surface_with_pv', 0.85)
measure.setArgument('cell_efficiency', 0.19)
measure.setArgument('inverter_efficiency', 0.96)
```

### EnableDemandControlledVentilation
**Purpose:** Enable DCV (CO2-based ventilation control) for air loops
**Arguments:**
- `air_loop_name` (choice) - Air loop to modify (or "*" for all)

**Example:**
```ruby
measure.setArgument('air_loop_name', '*')
```

### EnableEconomizerControl
**Purpose:** Enable or modify economizer control on air loops
**Arguments:**
- `air_loop_name` (choice) - Air loop to modify
- `economizer_control_type` (choice) - DifferentialDryBulb, FixedDryBulb, etc.
- `economizer_maximum_limit_dry_bulb_temperature` (double) - High limit (°C)

**Example:**
```ruby
measure.setArgument('air_loop_name', 'Main VAV System')
measure.setArgument('economizer_control_type', 'DifferentialDryBulb')
measure.setArgument('economizer_maximum_limit_dry_bulb_temperature', 28.0)
```

### ImproveMotorEfficiency
**Purpose:** Replace motors with high-efficiency versions
**Arguments:**
- `motor_eff` (double) - New motor efficiency (0.0 to 1.0)
- `remove_costs` (bool) - Remove existing costs
- `material_cost` (double) - Cost per motor
- `expected_life` (int) - Years

**Example:**
```ruby
measure.setArgument('motor_eff', 0.95)
measure.setArgument('material_cost', 2500.0)
measure.setArgument('expected_life', 15)
```

### ReduceElectricEquipmentLoadsByPercentage
**Purpose:** Reduce plug load densities by percentage
**Arguments:**
- `elec_equip_power_reduction_percent` (double) - Reduction % (0 to 100)
- `material_and_installation_cost` (double) - Cost
- `om_cost` (double) - Annual O&M cost

**Example:**
```ruby
# Reduce plug loads by 20%
measure.setArgument('elec_equip_power_reduction_percent', 20.0)
```

### ReduceLightingLoadsByPercentage
**Purpose:** Reduce lighting power density by percentage
**Arguments:**
- `lighting_power_reduction_percent` (double) - Reduction % (0 to 100)
- `material_and_installation_cost` (double) - Cost

**Example:**
```ruby
# Reduce lighting by 30%
measure.setArgument('lighting_power_reduction_percent', 30.0)
measure.setArgument('material_and_installation_cost', 50000.0)
```

### ReduceVentilationByPercentage
**Purpose:** Reduce outdoor air ventilation rates
**Arguments:**
- `design_spec_outdoor_air_reduction_percent` (double) - Reduction % (0 to 100)

**Example:**
```ruby
# Reduce ventilation by 10%
measure.setArgument('design_spec_outdoor_air_reduction_percent', 10.0)
```

### SetBoilerEfficiency
**Purpose:** Set efficiency for all boilers
**Arguments:**
- `boiler_thermal_efficiency` (double) - Thermal efficiency (0.0 to 1.0)

**Example:**
```ruby
measure.setArgument('boiler_thermal_efficiency', 0.92)
```

### SetChillerCOP
**Purpose:** Set COP for all chillers
**Arguments:**
- `chiller_cop` (double) - Coefficient of performance

**Example:**
```ruby
measure.setArgument('chiller_cop', 5.5)
```

### SetGasEquipmentEfficiency
**Purpose:** Set efficiency for gas equipment
**Arguments:**
- `gas_equipment_efficiency` (double) - Efficiency (0.0 to 1.0)

**Example:**
```ruby
measure.setArgument('gas_equipment_efficiency', 0.85)
```

---

## Quick Reference

### Most Used Measures

| Measure | Purpose | Common Use Case |
|---------|---------|-----------------|
| `OpenStudioResults` | HTML report generation | Every workflow (reporting step) |
| `AddOutputVariable` | Add EnergyPlus output | Detailed analysis, calibration |
| `StandardReports` | ASHRAE compliance report | Code compliance workflows |
| `TimeseriesObjectiveFunction` | Calibration metric | Model calibration |
| `AddRemoveOrReplaceWindows` | Modify WWR | Parametric studies |
| `ReduceLightingLoadsByPercentage` | Lighting retrofits | Energy efficiency measures |
| `ReduceElectricEquipmentLoadsByPercentage` | Plug load retrofits | Energy efficiency measures |
| `EnableEconomizerControl` | Add economizer | HVAC retrofits |
| `TariffSelectionFlatRate` | Add utility costs | Economic analysis |
| `SetLifecycleCostParameters` | Configure LCC | Economic analysis |

### Workflow Placement

| Measure Type | Workflow Position | Reason |
|--------------|-------------------|--------|
| Costing | Beginning (ModelMeasure) | Apply costs to objects as created |
| Manipulation | Beginning (ModelMeasure) | Modify geometry/loads before simulation |
| Output variables | Middle (EnergyPlusMeasure) | Add outputs before simulation |
| Reporting | End (ReportingMeasure) | Process results after simulation |

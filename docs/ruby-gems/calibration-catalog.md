# OpenStudio Calibration Measures Catalog

**Purpose:** Collection of 35+ measures for model calibration, utility data import, reporting calibration metrics, and tuning HVAC/envelope parameters.

**Repository:** https://github.com/canmet-energy/openstudio-calibration-gem.git (tag: develop)

**When to use:** Calibrate energy models to match utility bills or measured data, tune uncertain parameters, calculate calibration statistics (CVRMSE, NMBE).

---

## Categories

1. **Utility Data Import** - Import utility bills, interval data
2. **Calibration Reporting** - Calculate CVRMSE, NMBE, visualize comparisons
3. **HVAC Tuning** - Adjust HVAC parameters for better match
4. **Envelope Tuning** - Adjust envelope parameters for better match
5. **General Tuning** - Schedules, infiltration, loads

---

## 1. Utility Data Import

### AddMonthlyUtilityData
**Purpose:** Import monthly utility bills for calibration
**Arguments:**
- `electric_json` (string) - JSON with monthly electricity data
- `gas_json` (string) - JSON with monthly gas data
- `water_json` (string) - JSON with monthly water data

**Example:**
```ruby
elec_data = '{
  "2023-01": {"consumption": 45000, "demand": 120, "cost": 5400},
  "2023-02": {"consumption": 42000, "demand": 115, "cost": 5040},
  "2023-03": {"consumption": 38000, "demand": 105, "cost": 4560}
}'
measure.setArgument('electric_json', elec_data)
```

### AddIntervalUtilityData
**Purpose:** Import 15-min/hourly interval meter data
**Arguments:**
- `csv_path` (string) - Path to CSV with interval data
- `fuel_type` (choice) - Electricity, Gas, Water
- `timestamp_column` (string) - Column name for timestamps
- `value_column` (string) - Column name for values
- `unit` (choice) - kWh, kW, therms, CCF, gallons

**Example:**
```ruby
measure.setArgument('csv_path', 'electric_interval.csv')
measure.setArgument('fuel_type', 'Electricity')
measure.setArgument('timestamp_column', 'Date/Time')
measure.setArgument('value_column', 'kW')
measure.setArgument('unit', 'kW')
```

### AddDesignDayUtilityData
**Purpose:** Import peak demand data for design days
**Arguments:**
- `summer_peak_kw` (double) - Summer peak demand (kW)
- `winter_peak_kw` (double) - Winter peak demand (kW)

**Example:**
```ruby
measure.setArgument('summer_peak_kw', 350.0)
measure.setArgument('winter_peak_kw', 280.0)
```

---

## 2. Calibration Reporting

### CalibrationReportsEnhanced
**Purpose:** Comprehensive calibration report with CVRMSE, NMBE, charts
**Arguments:**
- `fuel_type` (choice) - Electricity, Gas, or All
- `report_frequency` (choice) - Monthly, Daily, Hourly

**Example:**
```ruby
measure.setArgument('fuel_type', 'All')
measure.setArgument('report_frequency', 'Monthly')
# Generates calibration_report.html with:
# - CVRMSE and NMBE statistics
# - Measured vs simulated charts
# - Monthly/daily breakdown tables
```

### CalibrationReportsEnhanced20
**Purpose:** Enhanced version with ASHRAE Guideline 14 compliance checks
**Arguments:**
- `fuel_type` (choice) - Electricity, Gas, All
- `report_frequency` (choice) - Monthly, Daily, Hourly
- `display_standards_calibration_threshold` (bool) - Show ASHRAE G14 thresholds

**Example:**
```ruby
measure.setArgument('fuel_type', 'Electricity')
measure.setArgument('report_frequency', 'Monthly')
measure.setArgument('display_standards_calibration_threshold', true)
# Shows ASHRAE Guideline 14 thresholds:
# Monthly: CVRMSE < 15%, NMBE < ±5%
# Hourly: CVRMSE < 30%, NMBE < ±10%
```

### TimeseriesCalibrationMetrics
**Purpose:** Calculate calibration metrics for timeseries data
**Arguments:**
- `measured_data_csv` (string) - Path to measured data CSV
- `timestamp_column` (string) - Timestamp column name
- `value_column` (string) - Value column name
- `variable_name` (string) - EnergyPlus variable to compare
- `reporting_frequency` (choice) - Hourly, Daily, Monthly

**Example:**
```ruby
measure.setArgument('measured_data_csv', 'measured_electricity.csv')
measure.setArgument('timestamp_column', 'Date/Time')
measure.setArgument('value_column', 'kWh')
measure.setArgument('variable_name', 'Electricity:Facility')
measure.setArgument('reporting_frequency', 'Hourly')
# Outputs: CVRMSE, NMBE, R², MBE, RMSE
```

### ViewMonthlyUtilityData
**Purpose:** Visualize imported utility data before calibration
**Arguments:** (none - auto-generates from imported data)

**Example:**
```ruby
# Generates chart comparing imported utility bills across months
```

### ExportCalibrationData
**Purpose:** Export calibration results to CSV for external analysis
**Arguments:**
- `output_path` (string) - Path for output CSV

**Example:**
```ruby
measure.setArgument('output_path', 'calibration_results.csv')
# CSV columns: Month, Measured, Simulated, Error%, CVRMSE, NMBE
```

---

## 3. HVAC Tuning Measures

### AdjustThermostatSetpointsByDegrees
**Purpose:** Shift heating/cooling setpoints for calibration
**Arguments:**
- `heating_adjustment` (double) - °C to add to heating setpoint
- `cooling_adjustment` (double) - °C to add to cooling setpoint

**Example:**
```ruby
# Lower heating setpoint by 1°C, raise cooling by 1°C
measure.setArgument('heating_adjustment', -1.0)
measure.setArgument('cooling_adjustment', 1.0)
```

### AdjustBoilerEfficiency
**Purpose:** Tune boiler efficiency to match gas consumption
**Arguments:**
- `boiler_thermal_efficiency` (double) - Thermal efficiency (0.0 to 1.0)
- `apply_to_all_boilers` (bool) - Apply to all or selected boilers

**Example:**
```ruby
measure.setArgument('boiler_thermal_efficiency', 0.82)
measure.setArgument('apply_to_all_boilers', true)
```

### AdjustChillerCOP
**Purpose:** Tune chiller COP to match electric consumption
**Arguments:**
- `chiller_cop` (double) - Coefficient of performance
- `apply_to_all_chillers` (bool)

**Example:**
```ruby
measure.setArgument('chiller_cop', 4.8)
measure.setArgument('apply_to_all_chillers', true)
```

### AdjustFanPressureDrop
**Purpose:** Tune fan pressure to match electric consumption
**Arguments:**
- `pressure_adjustment_factor` (double) - Multiplier (e.g., 1.2 = +20%)
- `apply_to_all_fans` (bool)

**Example:**
```ruby
# Increase fan pressure by 15%
measure.setArgument('pressure_adjustment_factor', 1.15)
measure.setArgument('apply_to_all_fans', true)
```

### AdjustFanEfficiency
**Purpose:** Tune fan efficiency
**Arguments:**
- `fan_total_efficiency` (double) - Total efficiency (0.0 to 1.0)
- `apply_to_all_fans` (bool)

**Example:**
```ruby
measure.setArgument('fan_total_efficiency', 0.55)
measure.setArgument('apply_to_all_fans', true)
```

### AdjustPumpEfficiency
**Purpose:** Tune pump efficiency
**Arguments:**
- `pump_motor_efficiency` (double) - Motor efficiency (0.0 to 1.0)
- `apply_to_all_pumps` (bool)

**Example:**
```ruby
measure.setArgument('pump_motor_efficiency', 0.88)
measure.setArgument('apply_to_all_pumps', true)
```

### AdjustCoolingTowerEffectiveness
**Purpose:** Tune cooling tower performance
**Arguments:**
- `effectiveness_adjustment_factor` (double) - Multiplier

**Example:**
```ruby
measure.setArgument('effectiveness_adjustment_factor', 0.95)
```

### AdjustDHWSetpoint
**Purpose:** Adjust domestic hot water setpoint temperature
**Arguments:**
- `dhw_setpoint_c` (double) - Setpoint temperature (°C)

**Example:**
```ruby
measure.setArgument('dhw_setpoint_c', 55.0)
```

### AdjustDHWLoadByPercentage
**Purpose:** Scale hot water consumption
**Arguments:**
- `dhw_load_adjustment_percent` (double) - Percentage change (-100 to +100)

**Example:**
```ruby
# Reduce DHW load by 20%
measure.setArgument('dhw_load_adjustment_percent', -20.0)
```

### EnableHeatRecovery
**Purpose:** Add/enable heat recovery to air systems
**Arguments:**
- `heat_recovery_effectiveness` (double) - Sensible effectiveness (0.0 to 1.0)
- `apply_to_all_air_loops` (bool)

**Example:**
```ruby
measure.setArgument('heat_recovery_effectiveness', 0.70)
measure.setArgument('apply_to_all_air_loops', true)
```

---

## 4. Envelope Tuning Measures

### AdjustInfiltrationByPercentage
**Purpose:** Scale infiltration rates to match heating/cooling loads
**Arguments:**
- `infiltration_adjustment_percent` (double) - Percentage change

**Example:**
```ruby
# Increase infiltration by 25%
measure.setArgument('infiltration_adjustment_percent', 25.0)
```

### AdjustRValueOfExteriorWalls
**Purpose:** Tune wall insulation R-value
**Arguments:**
- `r_value_mult` (double) - R-value multiplier

**Example:**
```ruby
# Reduce wall R-value by 20% (higher heat loss)
measure.setArgument('r_value_mult', 0.80)
```

### AdjustRValueOfRoof
**Purpose:** Tune roof insulation R-value
**Arguments:**
- `r_value_mult` (double) - R-value multiplier

**Example:**
```ruby
measure.setArgument('r_value_mult', 1.10)
```

### AdjustWindowUValueAndSHGC
**Purpose:** Tune window thermal performance
**Arguments:**
- `u_value_mult` (double) - U-value multiplier
- `shgc_mult` (double) - SHGC multiplier

**Example:**
```ruby
# Increase U-value by 15%, decrease SHGC by 10%
measure.setArgument('u_value_mult', 1.15)
measure.setArgument('shgc_mult', 0.90)
```

### AdjustGroundTemperature
**Purpose:** Tune ground temperature for ground heat transfer
**Arguments:**
- `ground_temp_adjustment_c` (double) - Temperature adjustment (°C)

**Example:**
```ruby
# Increase ground temperature by 2°C
measure.setArgument('ground_temp_adjustment_c', 2.0)
```

### AdjustSolarAbsorptance
**Purpose:** Tune exterior surface solar absorptance
**Arguments:**
- `wall_absorptance` (double) - Wall solar absorptance (0.0 to 1.0)
- `roof_absorptance` (double) - Roof solar absorptance

**Example:**
```ruby
measure.setArgument('wall_absorptance', 0.65)
measure.setArgument('roof_absorptance', 0.85)
```

---

## 5. General Tuning Measures

### AdjustLightingLoadByPercentage
**Purpose:** Scale lighting power density
**Arguments:**
- `lighting_adjustment_percent` (double) - Percentage change

**Example:**
```ruby
# Reduce lighting by 15%
measure.setArgument('lighting_adjustment_percent', -15.0)
```

### AdjustElectricEquipmentLoadByPercentage
**Purpose:** Scale plug load density
**Arguments:**
- `electric_equipment_adjustment_percent` (double) - Percentage change

**Example:**
```ruby
# Increase plug loads by 10%
measure.setArgument('electric_equipment_adjustment_percent', 10.0)
```

### AdjustOccupancyDensityByPercentage
**Purpose:** Scale occupant density
**Arguments:**
- `occupancy_adjustment_percent` (double) - Percentage change

**Example:**
```ruby
# Reduce occupancy by 20%
measure.setArgument('occupancy_adjustment_percent', -20.0)
```

### AdjustScheduleByMultiplier
**Purpose:** Scale schedule values by multiplier
**Arguments:**
- `schedule_name` (choice) - Schedule to adjust
- `multiplier` (double) - Multiplier

**Example:**
```ruby
measure.setArgument('schedule_name', 'Office Lighting Schedule')
measure.setArgument('multiplier', 0.85)
```

### ShiftScheduleByHours
**Purpose:** Time-shift schedule for occupancy pattern calibration
**Arguments:**
- `schedule_name` (choice) - Schedule to shift
- `shift_hours` (double) - Hours to shift (positive = later)

**Example:**
```ruby
# Shift occupancy 1 hour earlier
measure.setArgument('schedule_name', 'Office Occupancy')
measure.setArgument('shift_hours', -1.0)
```

### AdjustVentilationRateByPercentage
**Purpose:** Scale outdoor air ventilation rates
**Arguments:**
- `ventilation_adjustment_percent` (double) - Percentage change

**Example:**
```ruby
# Reduce ventilation by 15%
measure.setArgument('ventilation_adjustment_percent', -15.0)
```

### AddUnmetLoadOutputs
**Purpose:** Add output variables for unmet hours debugging
**Arguments:** (none - auto-adds outputs)

**Example:**
```ruby
# Adds outputs for:
# - Zone Heating Unmet Hours
# - Zone Cooling Unmet Hours
# - Zone Heating Unmet Time
# - Zone Cooling Unmet Time
```

---

## 6. Calibration Workflow Examples

### Example 1: Monthly Utility Bill Calibration

```ruby
# Step 1: Import utility bills
add_utility = AddMonthlyUtilityData.new
add_utility.setArgument('electric_json', '{
  "2023-01": {"consumption": 45000},
  "2023-02": {"consumption": 42000},
  "2023-03": {"consumption": 38000}
}')

# Step 2: Run initial simulation
# (run OpenStudio workflow)

# Step 3: Generate calibration report
cal_report = CalibrationReportsEnhanced20.new
cal_report.setArgument('fuel_type', 'Electricity')
cal_report.setArgument('report_frequency', 'Monthly')
# Review report: CVRMSE = 22%, NMBE = -12%

# Step 4: Tune parameters
# Hypothesis: Overestimating lighting loads
reduce_lighting = AdjustLightingLoadByPercentage.new
reduce_lighting.setArgument('lighting_adjustment_percent', -15.0)

# Hypothesis: Underestimating plug loads
increase_plugs = AdjustElectricEquipmentLoadByPercentage.new
increase_plugs.setArgument('electric_equipment_adjustment_percent', 10.0)

# Step 5: Re-run simulation and check new CVRMSE/NMBE
# Goal: CVRMSE < 15%, NMBE < ±5% (ASHRAE G14 monthly)
```

### Example 2: Interval Data Calibration

```ruby
# Step 1: Import 15-minute interval data
add_interval = AddIntervalUtilityData.new
add_interval.setArgument('csv_path', 'electric_15min.csv')
add_interval.setArgument('fuel_type', 'Electricity')
add_interval.setArgument('timestamp_column', 'Timestamp')
add_interval.setArgument('value_column', 'kW')
add_interval.setArgument('unit', 'kW')

# Step 2: Calculate timeseries metrics
timeseries_cal = TimeseriesCalibrationMetrics.new
timeseries_cal.setArgument('measured_data_csv', 'electric_15min.csv')
timeseries_cal.setArgument('variable_name', 'Electricity:Facility')
timeseries_cal.setArgument('reporting_frequency', 'Timestep')

# Step 3: Review metrics and tune
# If peak demand is too high: reduce fan pressure
adjust_fans = AdjustFanPressureDrop.new
adjust_fans.setArgument('pressure_adjustment_factor', 0.90)

# If nighttime baseload is too low: increase plug loads
adjust_plugs = AdjustElectricEquipmentLoadByPercentage.new
adjust_plugs.setArgument('electric_equipment_adjustment_percent', 15.0)
```

### Example 3: Heating Fuel Calibration

```ruby
# Step 1: Import gas bills
add_gas = AddMonthlyUtilityData.new
add_gas.setArgument('gas_json', '{
  "2023-01": {"consumption": 8500},
  "2023-02": {"consumption": 7200},
  "2023-03": {"consumption": 5800}
}')

# Step 2: Generate calibration report
cal_report = CalibrationReportsEnhanced.new
cal_report.setArgument('fuel_type', 'Gas')
cal_report.setArgument('report_frequency', 'Monthly')
# Review: Model underestimates gas by 18%

# Step 3: Tune heating parameters
# Option A: Reduce boiler efficiency
adjust_boiler = AdjustBoilerEfficiency.new
adjust_boiler.setArgument('boiler_thermal_efficiency', 0.78)  # Down from 0.85

# Option B: Increase infiltration
adjust_infil = AdjustInfiltrationByPercentage.new
adjust_infil.setArgument('infiltration_adjustment_percent', 20.0)

# Option C: Increase DHW load
adjust_dhw = AdjustDHWLoadByPercentage.new
adjust_dhw.setArgument('dhw_load_adjustment_percent', 15.0)

# Step 4: Re-run and iterate until CVRMSE < 15%
```

### Example 4: Multi-Parameter Optimization

```ruby
# Define parameter ranges for optimization
parameters = [
  { measure: 'AdjustInfiltrationByPercentage',
    arg: 'infiltration_adjustment_percent',
    range: [-20, 0, 20, 40] },

  { measure: 'AdjustLightingLoadByPercentage',
    arg: 'lighting_adjustment_percent',
    range: [-20, -10, 0, 10] },

  { measure: 'AdjustChillerCOP',
    arg: 'chiller_cop',
    range: [4.0, 4.5, 5.0, 5.5] },

  { measure: 'AdjustThermostatSetpointsByDegrees',
    arg: 'cooling_adjustment',
    range: [-1.0, 0.0, 1.0] }
]

# Use parametric analysis tool or optimization algorithm
# to find best combination minimizing CVRMSE
# This would typically be done via:
# - OpenStudio Parametric Analysis Tool (PAT)
# - Custom optimization script (e.g., genetic algorithm)
# - Manual iteration with most sensitive parameters first
```

---

## Quick Reference

### Calibration Metrics

| Metric | Definition | ASHRAE G14 Threshold (Monthly) |
|--------|------------|-------------------------------|
| **CVRMSE** | Coefficient of variation of RMSE | < 15% |
| **NMBE** | Normalized mean bias error | ±5% |
| **R²** | Coefficient of determination | > 0.75 (not in G14) |
| **MBE** | Mean bias error | N/A |
| **RMSE** | Root mean square error | N/A |

### Most Impactful Tuning Parameters

| Parameter | Measure | Impact On |
|-----------|---------|-----------|
| Infiltration | `AdjustInfiltrationByPercentage` | Heating/cooling loads |
| Thermostat setpoints | `AdjustThermostatSetpointsByDegrees` | Heating/cooling energy |
| Lighting loads | `AdjustLightingLoadByPercentage` | Electricity, cooling loads |
| Plug loads | `AdjustElectricEquipmentLoadByPercentage` | Electricity, cooling loads |
| Chiller COP | `AdjustChillerCOP` | Cooling electricity |
| Boiler efficiency | `AdjustBoilerEfficiency` | Heating gas/fuel |
| Occupancy schedules | `ShiftScheduleByHours` | Load profiles, peak demand |

### Calibration Workflow

1. **Import Data** → `AddMonthlyUtilityData` or `AddIntervalUtilityData`
2. **Run Baseline** → Simulate with initial parameters
3. **Generate Report** → `CalibrationReportsEnhanced20`
4. **Analyze Gaps** → Review CVRMSE, NMBE, monthly patterns
5. **Tune Parameters** → Apply adjustment measures
6. **Iterate** → Repeat until CVRMSE < 15%, NMBE < ±5%
7. **Export Results** → `ExportCalibrationData`

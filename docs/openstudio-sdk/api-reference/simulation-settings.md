# Simulation Settings API Reference

Complete reference for simulation control, run period, timestep, sizing, and output settings in OpenStudio SDK (Python & Ruby).

---

## 1. Run Period

### Set Annual Simulation

**Python:**
```python
import openstudio

model = openstudio.model.Model()

# Get run period (auto-created)
run_period = model.getRunPeriod()

# Set to full year (Jan 1 - Dec 31)
run_period.setBeginMonth(1)
run_period.setBeginDayOfMonth(1)
run_period.setEndMonth(12)
run_period.setEndDayOfMonth(31)

# Use weather file run period (typical year)
run_period.setUseWeatherFileHolidays(True)
run_period.setUseWeatherFileDaylightSavings(True)
run_period.setUseWeatherFileRainInd(True)
run_period.setUseWeatherFileSnowInd(True)
```

**Ruby:**
```ruby
require 'openstudio'

model = OpenStudio::Model::Model.new

run_period = model.getRunPeriod

run_period.setBeginMonth(1)
run_period.setBeginDayOfMonth(1)
run_period.setEndMonth(12)
run_period.setEndDayOfMonth(31)

run_period.setUseWeatherFileHolidays(true)
run_period.setUseWeatherFileDaylightSavings(true)
run_period.setUseWeatherFileRainInd(true)
run_period.setUseWeatherFileSnowInd(true)
```

---

### Set Partial Year (Summer Only)

**Python:**
```python
# Simulate June 1 - August 31
run_period.setBeginMonth(6)
run_period.setBeginDayOfMonth(1)
run_period.setEndMonth(8)
run_period.setEndDayOfMonth(31)
```

**Ruby:**
```ruby
run_period.setBeginMonth(6)
run_period.setBeginDayOfMonth(1)
run_period.setEndMonth(8)
run_period.setEndDayOfMonth(31)
```

---

## 2. Timestep

### Set Simulation Timestep

**Python:**
```python
# Get timestep object (auto-created)
timestep = model.getTimestep()

# Set timesteps per hour
# Options: 1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60
timestep.setNumberOfTimestepsPerHour(4)  # 15-minute timestep

# Higher timestep = more accurate but slower
# Recommended: 4-6 for most models
```

**Ruby:**
```ruby
timestep = model.getTimestep
timestep.setNumberOfTimestepsPerHour(4)
```

**Timestep Recommendations:**

| Timestep/Hour | Minutes | Use Case |
|--------------|---------|----------|
| 1 | 60 min | Quick rough analysis |
| 4 | 15 min | Standard (recommended) |
| 6 | 10 min | Detailed analysis, controls |
| 12 | 5 min | Very detailed, fast controls |
| 60 | 1 min | Sub-minute controls (rarely needed) |

---

## 3. Simulation Control

### Configure Simulation Settings

**Python:**
```python
# Get simulation control (auto-created)
sim_control = model.getSimulationControl()

# Run design days
sim_control.setRunSimulationforSizingPeriods(True)   # Run sizing

# Run weather file periods
sim_control.setRunSimulationforWeatherFileRunPeriods(True)  # Run annual

# Solar distribution
sim_control.setSolarDistribution("FullExteriorWithReflections")
# Options: MinimalShadowing, FullExterior, FullInteriorAndExterior,
#          FullExteriorWithReflections, FullInteriorAndExteriorWithReflections

# Maximum warmup days
sim_control.setMaximumNumberofWarmupDays(25)

# Minimum warmup days
sim_control.setMinimumNumberofWarmupDays(6)
```

**Ruby:**
```ruby
sim_control = model.getSimulationControl

sim_control.setRunSimulationforSizingPeriods(true)
sim_control.setRunSimulationforWeatherFileRunPeriods(true)

sim_control.setSolarDistribution("FullExteriorWithReflections")
sim_control.setMaximumNumberofWarmupDays(25)
sim_control.setMinimumNumberofWarmupDays(6)
```

**Solar Distribution Options:**

| Option | Speed | Accuracy | Use Case |
|--------|-------|----------|----------|
| `MinimalShadowing` | Fastest | Lowest | Initial testing |
| `FullExterior` | Fast | Good | Standard models |
| `FullExteriorWithReflections` | Medium | Better | Models with reflective surfaces |
| `FullInteriorAndExterior` | Slow | High | Detailed daylighting |
| `FullInteriorAndExteriorWithReflections` | Slowest | Highest | Detailed daylighting with reflections |

---

## 4. Shadow Calculation

### Configure Shadow Calculation

**Python:**
```python
# Get shadow calculation (auto-created)
shadow_calc = model.getShadowCalculation()

# Calculation method
shadow_calc.setCalculationMethod("AverageOverDaysInFrequency")
# Options: AverageOverDaysInFrequency, TimestepFrequency

# Calculation frequency (days)
shadow_calc.setCalculationFrequency(20)  # Recalculate every 20 days

# Maximum figures in shadow overlap calculations
shadow_calc.setMaximumFiguresInShadowOverlapCalculations(15000)
```

**Ruby:**
```ruby
shadow_calc = model.getShadowCalculation

shadow_calc.setCalculationMethod("AverageOverDaysInFrequency")
shadow_calc.setCalculationFrequency(20)
shadow_calc.setMaximumFiguresInShadowOverlapCalculations(15000)
```

**Recommendations:**
- **Standard:** AverageOverDaysInFrequency, every 20-30 days
- **Detailed:** TimestepFrequency (slower)
- **Simple models:** AverageOverDaysInFrequency, every 30 days

---

## 5. Sizing Parameters

### Building-Level Sizing

**Python:**
```python
# Get sizing parameters (auto-created)
sizing_params = model.getSizingParameters()

# Heating sizing factor (oversizing)
sizing_params.setHeatingSizingFactor(1.25)  # 25% oversizing

# Cooling sizing factor
sizing_params.setCoolingSizingFactor(1.15)  # 15% oversizing

# Timesteps in averaging window (for peak load calculations)
sizing_params.setTimestepsinAveragingWindow(1)
```

**Ruby:**
```ruby
sizing_params = model.getSizingParameters

sizing_params.setHeatingSizingFactor(1.25)
sizing_params.setCoolingSizingFactor(1.15)
sizing_params.setTimestepsinAveragingWindow(1)
```

**Typical Sizing Factors:**

| Building Type | Heating Factor | Cooling Factor |
|--------------|----------------|----------------|
| Office | 1.20-1.25 | 1.10-1.15 |
| Retail | 1.15-1.20 | 1.10-1.15 |
| School | 1.25-1.30 | 1.15-1.20 |
| Hospital | 1.30-1.50 | 1.20-1.30 |
| Warehouse | 1.10-1.15 | 1.05-1.10 |

---

## 6. Convergence Limits

### Set Convergence Tolerances

**Python:**
```python
# Get building (convergence limits stored here)
building = model.getBuilding()

# Loads convergence tolerance (W)
building.setLoadsConvergenceToleranceValue(0.04)  # Default

# Temperature convergence tolerance (delta-C)
building.setTemperatureConvergenceToleranceValue(0.4)  # Default

# Tighter tolerances = more accurate but slower
# Looser tolerances = faster but less accurate
```

**Ruby:**
```ruby
building = model.getBuilding

building.setLoadsConvergenceToleranceValue(0.04)
building.setTemperatureConvergenceToleranceValue(0.4)
```

---

## 7. Output Variables

### Add Output Variables

**Python:**
```python
# Add zone temperature output (hourly)
output_var = openstudio.model.OutputVariable("Zone Mean Air Temperature", model)
output_var.setReportingFrequency("Hourly")
output_var.setKeyValue("*")  # All zones

# Add facility electricity (monthly)
elec_output = openstudio.model.OutputVariable("Facility Total Purchased Electricity Energy", model)
elec_output.setReportingFrequency("Monthly")

# Add HVAC air system output (timestep)
hvac_output = openstudio.model.OutputVariable("Air System Total Heating Energy", model)
hvac_output.setReportingFrequency("Timestep")
hvac_output.setKeyValue("Main Air Loop")  # Specific air loop
```

**Ruby:**
```ruby
output_var = OpenStudio::Model::OutputVariable.new("Zone Mean Air Temperature", model)
output_var.setReportingFrequency("Hourly")
output_var.setKeyValue("*")

elec_output = OpenStudio::Model::OutputVariable.new("Facility Total Purchased Electricity Energy", model)
elec_output.setReportingFrequency("Monthly")
```

**Reporting Frequencies:**
- `Detailed` - Every timestep
- `Timestep` - Every timestep
- `Hourly` - Every hour
- `Daily` - Daily totals
- `Monthly` - Monthly totals
- `RunPeriod` - Total for run period
- `Annual` - Annual total

**Common Output Variables:**

| Category | Variable Name |
|----------|--------------|
| **Zone** | Zone Mean Air Temperature |
| | Zone Air Relative Humidity |
| | Zone People Occupant Count |
| **Energy** | Facility Total Purchased Electricity Energy |
| | Facility Total Natural Gas Energy |
| | Heating Coil Total Heating Energy |
| | Cooling Coil Total Cooling Energy |
| **HVAC** | Air System Total Heating Energy |
| | Air System Total Cooling Energy |
| | Fan Electric Energy |

---

### Add Meters

**Python:**
```python
# Add electricity meter
elec_meter = openstudio.model.OutputMeter(model)
elec_meter.setName("Electricity:Facility")
elec_meter.setReportingFrequency("Hourly")

# Add gas meter
gas_meter = openstudio.model.OutputMeter(model)
gas_meter.setName("NaturalGas:Facility")
gas_meter.setReportingFrequency("Hourly")

# Add end-use meters
lighting_meter = openstudio.model.OutputMeter(model)
lighting_meter.setName("InteriorLights:Electricity")
lighting_meter.setReportingFrequency("Hourly")
```

**Ruby:**
```ruby
elec_meter = OpenStudio::Model::OutputMeter.new(model)
elec_meter.setName("Electricity:Facility")
elec_meter.setReportingFrequency("Hourly")

gas_meter = OpenStudio::Model::OutputMeter.new(model)
gas_meter.setName("NaturalGas:Facility")
gas_meter.setReportingFrequency("Hourly")
```

**Common Meters:**

| Meter Name | Description |
|-----------|-------------|
| `Electricity:Facility` | Total facility electricity |
| `NaturalGas:Facility` | Total facility natural gas |
| `Heating:Electricity` | Electricity for heating |
| `Cooling:Electricity` | Electricity for cooling |
| `InteriorLights:Electricity` | Interior lighting |
| `InteriorEquipment:Electricity` | Plug loads |
| `Fans:Electricity` | Fan energy |
| `Pumps:Electricity` | Pump energy |

---

## 8. Weather File

### Set Weather File

**Python:**
```python
# Set weather file
epw_file = openstudio.EpwFile("/path/to/weather.epw")
weather_file = openstudio.model.WeatherFile.setWeatherFile(model, epw_file)

# Or from file path
weather_file_path = "/path/to/CAN_ON_Toronto.716240_CWEC2016.epw"
weather_file = openstudio.model.WeatherFile.setWeatherFile(model, weather_file_path)

# Get weather file info
wf = model.getWeatherFile()
print(f"City: {wf.city()}")
print(f"State/Province: {wf.stateProvinceRegion()}")
print(f"Country: {wf.country()}")
print(f"Latitude: {wf.latitude()}")
print(f"Longitude: {wf.longitude()}")
```

**Ruby:**
```ruby
epw_file = OpenStudio::EpwFile.new("/path/to/weather.epw")
weather_file = OpenStudio::Model::WeatherFile.setWeatherFile(model, epw_file)

wf = model.getWeatherFile
puts "City: #{wf.city}"
puts "Latitude: #{wf.latitude}"
```

---

## 9. Design Days

### Add Design Days from DDY File

**Python:**
```python
# Load design days from DDY file
ddy_file_path = "/path/to/CAN_ON_Toronto.716240_CWEC2016.ddy"

# Read DDY file
ddy_idf = openstudio.IdfFile.load(ddy_file_path).get()

# Extract design days
workspace = openstudio.Workspace(ddy_idf)
reverse_translator = openstudio.energyplus.ReverseTranslator()
ddy_model = reverse_translator.translateWorkspace(workspace)

# Copy design days to model
for design_day in ddy_model.getDesignDays():
    design_day_clone = design_day.clone(model).to_DesignDay().get()
    print(f"Added design day: {design_day_clone.name().get()}")
```

**Ruby:**
```ruby
ddy_file_path = "/path/to/CAN_ON_Toronto.716240_CWEC2016.ddy"

ddy_idf = OpenStudio::IdfFile.load(ddy_file_path).get
workspace = OpenStudio::Workspace.new(ddy_idf)
reverse_translator = OpenStudio::EnergyPlus::ReverseTranslator.new
ddy_model = reverse_translator.translateWorkspace(workspace)

ddy_model.getDesignDays.each do |design_day|
  design_day_clone = design_day.clone(model).to_DesignDay.get
  puts "Added design day: #{design_day_clone.name.get}"
end
```

---

### Create Design Day Manually

**Python:**
```python
# Create heating design day
heating_dd = openstudio.model.DesignDay(model)
heating_dd.setName("Toronto Heating 99.6% Design Day")
heating_dd.setDayType("WinterDesignDay")
heating_dd.setMaximumDryBulbTemperature(-18.0)  # °C
heating_dd.setDailyDryBulbTemperatureRange(0.0)
heating_dd.setHumidityIndicatingType("Wetbulb")
heating_dd.setWetBulbOrDewPointAtMaximumDryBulb(-20.0)
heating_dd.setBarometricPressure(101325.0)  # Pa
heating_dd.setWindSpeed(5.3)  # m/s
heating_dd.setWindDirection(270)  # degrees

# Create cooling design day
cooling_dd = openstudio.model.DesignDay(model)
cooling_dd.setName("Toronto Cooling 0.4% Design Day")
cooling_dd.setDayType("SummerDesignDay")
cooling_dd.setMaximumDryBulbTemperature(31.0)  # °C
cooling_dd.setDailyDryBulbTemperatureRange(10.0)
cooling_dd.setHumidityIndicatingType("Wetbulb")
cooling_dd.setWetBulbOrDewPointAtMaximumDryBulb(23.0)
cooling_dd.setBarometricPressure(101325.0)
cooling_dd.setWindSpeed(5.2)
cooling_dd.setWindDirection(240)
cooling_dd.setSolarModelIndicator("ASHRAETau")
cooling_dd.setAshraeTaub(0.455)
cooling_dd.setAshraeTaud(2.050)
```

**Ruby:**
```ruby
heating_dd = OpenStudio::Model::DesignDay.new(model)
heating_dd.setName("Toronto Heating 99.6% Design Day")
heating_dd.setDayType("WinterDesignDay")
heating_dd.setMaximumDryBulbTemperature(-18.0)
heating_dd.setDailyDryBulbTemperatureRange(0.0)
heating_dd.setWindSpeed(5.3)
```

---

## 10. Output Control Settings

### Configure Tabular Reports

**Python:**
```python
# Get output control table style
output_control_table = model.getOutputControlTableStyle()

# Set report format
output_control_table.setColumnSeparator("Comma")  # CSV format
# Options: Comma, Tab, Fixed, HTML, XML

# Configure which tables to generate
output_table_summary = model.getOutputTableSummaryReports()

# Add summary reports
output_table_summary.addSummaryReport("AllSummary")
# Options: AllSummary, AnnualBuildingUtilityPerformanceSummary,
#          InputVerificationandResultsSummary, etc.
```

**Ruby:**
```ruby
output_control_table = model.getOutputControlTableStyle
output_control_table.setColumnSeparator("Comma")

output_table_summary = model.getOutputTableSummaryReports
output_table_summary.addSummaryReport("AllSummary")
```

---

## Quick Reference

### Key Settings Summary

| Setting | Object | Recommended Value |
|---------|--------|------------------|
| Timestep | `Timestep` | 4-6 per hour |
| Run period | `RunPeriod` | Jan 1 - Dec 31 |
| Solar distribution | `SimulationControl` | FullExteriorWithReflections |
| Shadow calc | `ShadowCalculation` | AverageOverDaysInFrequency, 20 days |
| Sizing factor (heat) | `SizingParameters` | 1.20-1.25 |
| Sizing factor (cool) | `SizingParameters` | 1.10-1.15 |

### Output Frequency Guide

| Frequency | File Size | Use Case |
|-----------|-----------|----------|
| Detailed/Timestep | Very large | Controls analysis, sub-hourly |
| Hourly | Large | Standard analysis, calibration |
| Daily | Medium | Daily patterns |
| Monthly | Small | Utility bill comparison |
| RunPeriod/Annual | Very small | Summary only |

### Common Simulation Configurations

**Quick Testing:**
```python
timestep.setNumberOfTimestepsPerHour(4)
sim_control.setRunSimulationforSizingPeriods(True)
sim_control.setRunSimulationforWeatherFileRunPeriods(False)  # Skip annual
```

**Standard Annual:**
```python
timestep.setNumberOfTimestepsPerHour(4)
run_period.setBeginMonth(1)
run_period.setEndMonth(12)
sim_control.setSolarDistribution("FullExteriorWithReflections")
```

**Detailed Analysis:**
```python
timestep.setNumberOfTimestepsPerHour(6)
sim_control.setSolarDistribution("FullInteriorAndExteriorWithReflections")
shadow_calc.setCalculationMethod("TimestepFrequency")
```

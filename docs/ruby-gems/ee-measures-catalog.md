# OpenStudio Energy Efficiency Measures Catalog

**Purpose:** Collection of 25+ energy efficiency retrofit measures for envelope, HVAC, lighting, and controls improvements.

**Repository:** https://github.com/canmet-energy/openstudio-ee-gem.git (tag: develop)

**When to use:** Model energy efficiency retrofits, evaluate savings potential, create retrofit packages for existing buildings.

---

## Categories

1. **Envelope Improvements** - Insulation, windows, air sealing
2. **HVAC Improvements** - Equipment upgrades, controls, economizers
3. **Lighting Improvements** - LED retrofits, controls, daylighting
4. **Controls & Automation** - Advanced controls, BAS upgrades

---

## 1. Envelope Improvements

### ImproveExteriorWallInsulation
**Purpose:** Add insulation to exterior walls
**Arguments:**
- `target_r_value_ip` (double) - Target R-value (ft²·°F·hr/BTU)
- `insulation_cost_per_area_ip` (double) - $/ft² installed cost
- `expected_life` (int) - Years

**Example:**
```ruby
# Upgrade walls to R-20
measure.setArgument('target_r_value_ip', 20.0)
measure.setArgument('insulation_cost_per_area_ip', 3.50)
measure.setArgument('expected_life', 30)
```

### ImproveRoofInsulation
**Purpose:** Add insulation to roof
**Arguments:**
- `target_r_value_ip` (double) - Target R-value (ft²·°F·hr/BTU)
- `insulation_cost_per_area_ip` (double) - $/ft²
- `expected_life` (int) - Years

**Example:**
```ruby
# Upgrade roof to R-30
measure.setArgument('target_r_value_ip', 30.0)
measure.setArgument('insulation_cost_per_area_ip', 2.80)
measure.setArgument('expected_life', 25)
```

### ReplaceWindowsWithHighPerformance
**Purpose:** Replace windows with high-performance glazing
**Arguments:**
- `target_u_value_ip` (double) - Target U-value (BTU/ft²·°F·hr)
- `target_shgc` (double) - Target solar heat gain coefficient (0.0 to 1.0)
- `target_vlt` (double) - Target visible light transmittance (0.0 to 1.0)
- `window_cost_per_area_ip` (double) - $/ft²
- `expected_life` (int) - Years

**Example:**
```ruby
# Install double-pane low-e windows
measure.setArgument('target_u_value_ip', 0.30)  # U-0.30
measure.setArgument('target_shgc', 0.35)
measure.setArgument('target_vlt', 0.60)
measure.setArgument('window_cost_per_area_ip', 35.0)
measure.setArgument('expected_life', 25)
```

### AddWindowFilmToReduceSolarGain
**Purpose:** Apply solar control film to existing windows
**Arguments:**
- `shgc_reduction_percent` (double) - SHGC reduction (0 to 100%)
- `vlt_reduction_percent` (double) - VLT reduction (0 to 100%)
- `film_cost_per_area_ip` (double) - $/ft²
- `expected_life` (int) - Years

**Example:**
```ruby
# Add reflective film: 40% SHGC reduction, 20% VLT reduction
measure.setArgument('shgc_reduction_percent', 40.0)
measure.setArgument('vlt_reduction_percent', 20.0)
measure.setArgument('film_cost_per_area_ip', 6.50)
measure.setArgument('expected_life', 15)
```

### ReduceInfiltrationByPercentage
**Purpose:** Air sealing to reduce infiltration
**Arguments:**
- `infiltration_reduction_percent` (double) - Reduction % (0 to 100)
- `air_sealing_cost_per_area_ip` (double) - $/ft² floor area
- `expected_life` (int) - Years

**Example:**
```ruby
# 30% infiltration reduction through air sealing
measure.setArgument('infiltration_reduction_percent', 30.0)
measure.setArgument('air_sealing_cost_per_area_ip', 0.75)
measure.setArgument('expected_life', 20)
```

### AddCoolRoof
**Purpose:** Apply cool roof coating to reduce cooling loads
**Arguments:**
- `target_solar_absorptance` (double) - Solar absorptance (0.0 to 1.0)
- `target_thermal_emittance` (double) - Thermal emittance (0.0 to 1.0)
- `coating_cost_per_area_ip` (double) - $/ft²
- `expected_life` (int) - Years

**Example:**
```ruby
# Apply cool roof coating (high reflectance)
measure.setArgument('target_solar_absorptance', 0.25)  # 75% reflective
measure.setArgument('target_thermal_emittance', 0.90)
measure.setArgument('coating_cost_per_area_ip', 1.50)
measure.setArgument('expected_life', 15)
```

---

## 2. HVAC Improvements

### ReplaceBoilerWithHighEfficiency
**Purpose:** Replace existing boiler with high-efficiency model
**Arguments:**
- `boiler_thermal_efficiency` (double) - Thermal efficiency (0.0 to 1.0)
- `boiler_type` (choice) - NaturalGas, PropaneGas, FuelOilNo1, FuelOilNo2
- `boiler_cost_per_btu_per_hr` (double) - $/Btu/hr capacity
- `expected_life` (int) - Years

**Example:**
```ruby
# Install condensing gas boiler (95% efficiency)
measure.setArgument('boiler_thermal_efficiency', 0.95)
measure.setArgument('boiler_type', 'NaturalGas')
measure.setArgument('boiler_cost_per_btu_per_hr', 15.0)
measure.setArgument('expected_life', 20)
```

### ReplaceChillerWithHighEfficiency
**Purpose:** Replace existing chiller with high-efficiency model
**Arguments:**
- `chiller_cop` (double) - Coefficient of performance
- `chiller_type` (choice) - WaterCooled, AirCooled, EvaporativelyCooled
- `chiller_cost_per_ton` (double) - $/ton cooling capacity
- `expected_life` (int) - Years

**Example:**
```ruby
# Install high-efficiency water-cooled chiller (COP 6.0)
measure.setArgument('chiller_cop', 6.0)
measure.setArgument('chiller_type', 'WaterCooled')
measure.setArgument('chiller_cost_per_ton', 800.0)
measure.setArgument('expected_life', 20)
```

### AddVariableFrequencyDrivesToFans
**Purpose:** Add VFDs to constant-volume fans
**Arguments:**
- `fan_power_reduction_percent` (double) - Estimated power reduction %
- `vfd_cost_per_hp` (double) - $/hp motor capacity
- `expected_life` (int) - Years

**Example:**
```ruby
# Add VFDs to fans (30% power reduction)
measure.setArgument('fan_power_reduction_percent', 30.0)
measure.setArgument('vfd_cost_per_hp', 120.0)
measure.setArgument('expected_life', 15)
```

### AddVariableFrequencyDrivesToPumps
**Purpose:** Add VFDs to constant-speed pumps
**Arguments:**
- `pump_power_reduction_percent` (double) - Estimated power reduction %
- `vfd_cost_per_hp` (double) - $/hp motor capacity
- `expected_life` (int) - Years

**Example:**
```ruby
# Add VFDs to pumps (25% power reduction)
measure.setArgument('pump_power_reduction_percent', 25.0)
measure.setArgument('vfd_cost_per_hp', 120.0)
measure.setArgument('expected_life', 15)
```

### AddOrImproveEconomizer
**Purpose:** Add or improve economizer control on air handlers
**Arguments:**
- `economizer_control_type` (choice) - DifferentialDryBulb, FixedDryBulb, DifferentialEnthalpy, FixedEnthalpy
- `economizer_maximum_limit_dry_bulb_temperature_f` (double) - High limit (°F)
- `economizer_cost_per_air_loop` (double) - $ per air loop
- `expected_life` (int) - Years

**Example:**
```ruby
# Add differential dry-bulb economizer
measure.setArgument('economizer_control_type', 'DifferentialDryBulb')
measure.setArgument('economizer_maximum_limit_dry_bulb_temperature_f', 75.0)
measure.setArgument('economizer_cost_per_air_loop', 3500.0)
measure.setArgument('expected_life', 15)
```

### AddDemandControlledVentilation
**Purpose:** Add CO2-based demand-controlled ventilation
**Arguments:**
- `co2_setpoint_ppm` (double) - CO2 setpoint (ppm)
- `dcv_cost_per_zone` (double) - $ per zone
- `expected_life` (int) - Years

**Example:**
```ruby
# Add DCV with 800 ppm setpoint
measure.setArgument('co2_setpoint_ppm', 800.0)
measure.setArgument('dcv_cost_per_zone', 750.0)
measure.setArgument('expected_life', 15)
```

### AddEnergyRecoveryVentilator
**Purpose:** Add energy recovery ventilation (ERV) to air systems
**Arguments:**
- `sensible_effectiveness` (double) - Sensible effectiveness (0.0 to 1.0)
- `latent_effectiveness` (double) - Latent effectiveness (0.0 to 1.0)
- `erv_cost_per_cfm` (double) - $/CFM capacity
- `expected_life` (int) - Years

**Example:**
```ruby
# Add ERV with 75% sensible, 65% latent effectiveness
measure.setArgument('sensible_effectiveness', 0.75)
measure.setArgument('latent_effectiveness', 0.65)
measure.setArgument('erv_cost_per_cfm', 3.50)
measure.setArgument('expected_life', 20)
```

### ImproveAirHandlerControls
**Purpose:** Optimize air handler control sequences
**Arguments:**
- `enable_optimal_start` (bool) - Enable optimal start/stop
- `enable_night_setback` (bool) - Enable night setback
- `enable_supply_air_temp_reset` (bool) - Enable SAT reset
- `controls_upgrade_cost` (double) - $ total cost
- `expected_life` (int) - Years

**Example:**
```ruby
measure.setArgument('enable_optimal_start', true)
measure.setArgument('enable_night_setback', true)
measure.setArgument('enable_supply_air_temp_reset', true)
measure.setArgument('controls_upgrade_cost', 5000.0)
measure.setArgument('expected_life', 15)
```

### ReplaceRTUWithHighEfficiency
**Purpose:** Replace packaged rooftop units with high-efficiency models
**Arguments:**
- `cooling_eer` (double) - Energy efficiency ratio (Btu/Wh)
- `heating_efficiency` (double) - Heating efficiency (0.0 to 1.0)
- `rtu_cost_per_ton` (double) - $/ton cooling capacity
- `expected_life` (int) - Years

**Example:**
```ruby
# Replace with 13 EER, 90% efficient RTU
measure.setArgument('cooling_eer', 13.0)
measure.setArgument('heating_efficiency', 0.90)
measure.setArgument('rtu_cost_per_ton', 600.0)
measure.setArgument('expected_life', 15)
```

---

## 3. Lighting Improvements

### ReplaceLightingWithLED
**Purpose:** Replace existing lighting with LED fixtures
**Arguments:**
- `lighting_power_reduction_percent` (double) - Power reduction % (0 to 100)
- `led_cost_per_watt_saved` (double) - $/W saved
- `expected_life` (int) - Years

**Example:**
```ruby
# LED retrofit: 50% power reduction
measure.setArgument('lighting_power_reduction_percent', 50.0)
measure.setArgument('led_cost_per_watt_saved', 1.20)
measure.setArgument('expected_life', 15)
```

### AddLightingOccupancySensors
**Purpose:** Add occupancy sensors to control lighting
**Arguments:**
- `space_types` (choice) - Space types to apply sensors (or "All")
- `energy_savings_percent` (double) - Expected savings % (0 to 100)
- `sensor_cost_per_space` (double) - $ per space
- `expected_life` (int) - Years

**Example:**
```ruby
# Add occupancy sensors to offices and restrooms
measure.setArgument('space_types', 'Office,Restroom')
measure.setArgument('energy_savings_percent', 25.0)
measure.setArgument('sensor_cost_per_space', 150.0)
measure.setArgument('expected_life', 10)
```

### AddDaylightingControls
**Purpose:** Add daylight sensors and dimming controls
**Arguments:**
- `illuminance_setpoint_lux` (double) - Target illuminance (lux)
- `daylight_savings_percent` (double) - Expected savings % (0 to 100)
- `sensor_cost_per_zone` (double) - $ per daylit zone
- `expected_life` (int) - Years

**Example:**
```ruby
# Add daylighting with 300 lux setpoint
measure.setArgument('illuminance_setpoint_lux', 300.0)
measure.setArgument('daylight_savings_percent', 30.0)
measure.setArgument('sensor_cost_per_zone', 800.0)
measure.setArgument('expected_life', 15)
```

### ImplementLightingScheduleOptimization
**Purpose:** Optimize lighting schedules based on actual occupancy
**Arguments:**
- `schedule_adjustment_percent` (double) - Operating hours reduction %
- `cost` (double) - $ implementation cost
- `expected_life` (int) - Years

**Example:**
```ruby
# Reduce lighting hours by 15%
measure.setArgument('schedule_adjustment_percent', 15.0)
measure.setArgument('cost', 1000.0)
measure.setArgument('expected_life', 5)
```

---

## 4. Controls & Automation

### InstallBuildingAutomationSystem
**Purpose:** Install or upgrade building automation system (BAS)
**Arguments:**
- `enable_optimal_start_stop` (bool) - Enable optimal start/stop
- `enable_night_setback` (bool) - Enable night setback
- `enable_demand_limiting` (bool) - Enable demand limiting
- `enable_fault_detection` (bool) - Enable fault detection and diagnostics
- `bas_cost_per_point` (double) - $ per control point
- `number_of_points` (int) - Total control points
- `expected_life` (int) - Years

**Example:**
```ruby
measure.setArgument('enable_optimal_start_stop', true)
measure.setArgument('enable_night_setback', true)
measure.setArgument('enable_demand_limiting', true)
measure.setArgument('enable_fault_detection', true)
measure.setArgument('bas_cost_per_point', 250.0)
measure.setArgument('number_of_points', 150)
measure.setArgument('expected_life', 15)
```

### ExpandThermostatSetbackRange
**Purpose:** Widen heating/cooling setpoint deadband for savings
**Arguments:**
- `heating_setback_f` (double) - Heating setback temperature (°F)
- `cooling_setup_f` (double) - Cooling setup temperature (°F)
- `setback_start_hour` (int) - Hour to start setback (0-23)
- `setback_end_hour` (int) - Hour to end setback (0-23)
- `cost` (double) - $ implementation cost
- `expected_life` (int) - Years

**Example:**
```ruby
# Setback to 60°F heating, 85°F cooling during unoccupied hours
measure.setArgument('heating_setback_f', 60.0)
measure.setArgument('cooling_setup_f', 85.0)
measure.setArgument('setback_start_hour', 18)
measure.setArgument('setback_end_hour', 6)
measure.setArgument('cost', 500.0)
```

### AddPlugLoadControls
**Purpose:** Add controls to reduce plug loads during unoccupied hours
**Arguments:**
- `plug_load_reduction_percent` (double) - Unoccupied reduction % (0 to 100)
- `control_cost_per_receptacle` (double) - $ per controlled outlet
- `number_of_receptacles` (int) - Controlled receptacles
- `expected_life` (int) - Years

**Example:**
```ruby
# Control plug loads: 50% reduction when unoccupied
measure.setArgument('plug_load_reduction_percent', 50.0)
measure.setArgument('control_cost_per_receptacle', 35.0)
measure.setArgument('number_of_receptacles', 200)
measure.setArgument('expected_life', 10)
```

### AddRefrigerantSubcooling
**Purpose:** Add subcooling to refrigeration/cooling systems
**Arguments:**
- `subcooling_temperature_delta_f` (double) - Subcooling delta-T (°F)
- `cost_per_ton` (double) - $/ton cooling capacity
- `expected_life` (int) - Years

**Example:**
```ruby
measure.setArgument('subcooling_temperature_delta_f', 10.0)
measure.setArgument('cost_per_ton', 150.0)
measure.setArgument('expected_life', 15)
```

---

## 5. Retrofit Package Examples

### Example 1: Small Office Lighting & Envelope Package

```ruby
# Measure 1: LED lighting retrofit
led_retrofit = ReplaceLightingWithLED.new
led_retrofit.setArgument('lighting_power_reduction_percent', 50.0)
led_retrofit.setArgument('led_cost_per_watt_saved', 1.20)

# Measure 2: Occupancy sensors
occ_sensors = AddLightingOccupancySensors.new
occ_sensors.setArgument('space_types', 'All')
occ_sensors.setArgument('energy_savings_percent', 25.0)

# Measure 3: Air sealing
air_sealing = ReduceInfiltrationByPercentage.new
air_sealing.setArgument('infiltration_reduction_percent', 30.0)

# Measure 4: Roof insulation
roof_insulation = ImproveRoofInsulation.new
roof_insulation.setArgument('target_r_value_ip', 30.0)

# Total package cost: ~$25,000
# Estimated savings: 25-30% energy reduction
```

### Example 2: Medium Office HVAC Package

```ruby
# Measure 1: High-efficiency chiller
new_chiller = ReplaceChillerWithHighEfficiency.new
new_chiller.setArgument('chiller_cop', 6.0)
new_chiller.setArgument('chiller_type', 'WaterCooled')

# Measure 2: VFDs on fans
fan_vfds = AddVariableFrequencyDrivesToFans.new
fan_vfds.setArgument('fan_power_reduction_percent', 30.0)

# Measure 3: VFDs on pumps
pump_vfds = AddVariableFrequencyDrivesToPumps.new
pump_vfds.setArgument('pump_power_reduction_percent', 25.0)

# Measure 4: Economizer upgrade
economizer = AddOrImproveEconomizer.new
economizer.setArgument('economizer_control_type', 'DifferentialDryBulb')

# Measure 5: DCV
dcv = AddDemandControlledVentilation.new
dcv.setArgument('co2_setpoint_ppm', 800.0)

# Total package cost: ~$180,000
# Estimated savings: 30-35% HVAC energy reduction
```

### Example 3: Deep Energy Retrofit Package

```ruby
# Envelope measures
wall_insulation = ImproveExteriorWallInsulation.new
wall_insulation.setArgument('target_r_value_ip', 20.0)

roof_insulation = ImproveRoofInsulation.new
roof_insulation.setArgument('target_r_value_ip', 40.0)

new_windows = ReplaceWindowsWithHighPerformance.new
new_windows.setArgument('target_u_value_ip', 0.25)
new_windows.setArgument('target_shgc', 0.30)

air_sealing = ReduceInfiltrationByPercentage.new
air_sealing.setArgument('infiltration_reduction_percent', 50.0)

# HVAC measures
high_eff_boiler = ReplaceBoilerWithHighEfficiency.new
high_eff_boiler.setArgument('boiler_thermal_efficiency', 0.95)

high_eff_chiller = ReplaceChillerWithHighEfficiency.new
high_eff_chiller.setArgument('chiller_cop', 6.5)

erv = AddEnergyRecoveryVentilator.new
erv.setArgument('sensible_effectiveness', 0.80)
erv.setArgument('latent_effectiveness', 0.70)

# Lighting measures
led_retrofit = ReplaceLightingWithLED.new
led_retrofit.setArgument('lighting_power_reduction_percent', 60.0)

daylight_controls = AddDaylightingControls.new
daylight_controls.setArgument('illuminance_setpoint_lux', 300.0)

# Controls measures
bas_upgrade = InstallBuildingAutomationSystem.new
bas_upgrade.setArgument('enable_optimal_start_stop', true)
bas_upgrade.setArgument('enable_fault_detection', true)

# Total package cost: ~$500,000 - $1,000,000
# Estimated savings: 50-60% total energy reduction
```

---

## Quick Reference

### Typical Energy Savings by Measure

| Measure Category | Typical Savings | Simple Payback |
|-----------------|-----------------|----------------|
| LED lighting | 40-60% lighting energy | 2-5 years |
| Occupancy sensors | 20-30% lighting energy | 3-7 years |
| VFDs on fans/pumps | 20-40% fan/pump energy | 3-8 years |
| High-efficiency chiller | 20-35% cooling energy | 5-12 years |
| Economizer | 10-25% cooling energy | 2-6 years |
| DCV | 10-20% ventilation energy | 4-10 years |
| ERV | 15-30% heating/cooling energy | 8-15 years |
| Window replacement | 10-25% heating/cooling energy | 15-30 years |
| Roof insulation | 10-20% heating/cooling energy | 8-15 years |
| BAS upgrade | 10-30% total energy | 3-8 years |

### Measure Priority by Building Type

**Office Buildings:**
1. LED lighting + controls
2. HVAC economizer
3. VFDs on fans/pumps
4. BAS upgrade
5. Window replacement

**Retail:**
1. LED lighting
2. Demand-controlled ventilation
3. High-efficiency HVAC
4. Envelope improvements
5. Daylighting controls

**Schools:**
1. Lighting upgrades
2. HVAC controls optimization
3. Envelope improvements
4. Occupancy sensors
5. Energy recovery ventilation

**Hotels:**
1. Guestroom controls
2. LED lighting
3. High-efficiency boilers/chillers
4. Envelope improvements
5. Pool dehumidification

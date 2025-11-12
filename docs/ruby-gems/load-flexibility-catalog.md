# OpenStudio Load Flexibility Measures Catalog

**Purpose:** Collection of 5 measures for load shifting and thermal energy storage to enable demand response and time-of-use optimization.

**Repository:** https://github.com/canmet-energy/openstudio-load-flexibility-measures-gem.git (tag: develop)

**When to use:** Model demand response strategies, evaluate time-of-use rate savings, shift loads to off-peak periods, integrate thermal storage.

---

## Load Flexibility Strategies

1. **Ice/Chilled Water Storage** - Shift cooling loads to nighttime
2. **Heat Pump Water Heater (HPWH) Controls** - Shift DHW loads
3. **Precooling/Preheating** - Use building thermal mass
4. **Schedule Shifting** - Modify operation schedules
5. **Demand Limiting** - Cap peak demand

---

## 1. Ice Thermal Storage

### AddIceThermalStorage
**Purpose:** Add ice storage system to shift cooling loads to off-peak hours
**Arguments:**
- `storage_capacity_ton_hrs` (double) - Storage capacity (ton-hours)
- `charge_schedule_name` (string) - Charging schedule (typically nighttime)
- `discharge_schedule_name` (string) - Discharge schedule (typically daytime)
- `ice_storage_type` (choice) - IceOnCoilInternal, IceOnCoilExternal, IceOnCoilDetailed
- `storage_cost_per_ton_hr` (double) - $/ton-hour installed cost
- `expected_life` (int) - Years

**Example:**
```ruby
# Add 500 ton-hour ice storage system
measure.setArgument('storage_capacity_ton_hrs', 500.0)
measure.setArgument('charge_schedule_name', 'Ice Charge Schedule')  # 10 PM - 6 AM
measure.setArgument('discharge_schedule_name', 'Ice Discharge Schedule')  # 6 AM - 6 PM
measure.setArgument('ice_storage_type', 'IceOnCoilInternal')
measure.setArgument('storage_cost_per_ton_hr', 200.0)
measure.setArgument('expected_life', 20)
```

**Use Case:**
```ruby
# Typical ice storage workflow:
# 1. Size storage based on peak cooling load
# 2. Create charging schedule (off-peak hours)
# 3. Create discharge schedule (on-peak hours)
# 4. Apply time-of-use rate to calculate savings

# Example: Office building with 200-ton peak cooling
# Storage sized at 1,200 ton-hours (6 hours × 200 tons)
# Charge 10 PM - 6 AM (off-peak at $0.06/kWh)
# Discharge 12 PM - 6 PM (on-peak at $0.25/kWh)
# Potential savings: 30-50% cooling energy cost
```

---

## 2. Chilled Water Storage

### AddChilledWaterThermalStorage
**Purpose:** Add chilled water tank to shift cooling loads
**Arguments:**
- `storage_capacity_gal` (double) - Tank capacity (gallons)
- `tank_setpoint_temperature_f` (double) - Storage temperature (°F)
- `charge_schedule_name` (string) - Charging schedule
- `discharge_schedule_name` (string) - Discharge schedule
- `storage_cost_per_gallon` (double) - $/gallon installed cost
- `expected_life` (int) - Years

**Example:**
```ruby
# Add 30,000-gallon chilled water storage
measure.setArgument('storage_capacity_gal', 30000.0)
measure.setArgument('tank_setpoint_temperature_f', 42.0)
measure.setArgument('charge_schedule_name', 'CW Charge Schedule')
measure.setArgument('discharge_schedule_name', 'CW Discharge Schedule')
measure.setArgument('storage_cost_per_gallon', 2.50)
measure.setArgument('expected_life', 25)
```

**Sizing Guide:**
```ruby
# Rule of thumb: 10-15 gallons per ton-hour
# Example: 200-ton peak × 6 hours = 1,200 ton-hours
# Storage needed: 1,200 × 12 = 14,400 gallons

# Temperature differential affects capacity:
# ΔT = 15°F (typical): 10-12 gal/ton-hr
# ΔT = 20°F (aggressive): 7-9 gal/ton-hr
# ΔT = 10°F (conservative): 15-18 gal/ton-hr
```

---

## 3. Heat Pump Water Heater Controls

### AddHPWHLoadShifting
**Purpose:** Control heat pump water heater to shift DHW loads to off-peak
**Arguments:**
- `preheat_start_hour` (int) - Hour to start preheating (0-23)
- `preheat_duration_hours` (int) - Preheating duration (hours)
- `preheat_temperature_boost_f` (double) - Temperature boost during preheat (°F)
- `lockout_start_hour` (int) - Hour to start lockout (0-23)
- `lockout_duration_hours` (int) - Lockout duration (hours)
- `minimum_lockout_temperature_f` (double) - Minimum temp during lockout (°F)

**Example:**
```ruby
# Preheat DHW before peak period, lockout during peak
measure.setArgument('preheat_start_hour', 4)  # 4 AM
measure.setArgument('preheat_duration_hours', 4)  # Until 8 AM
measure.setArgument('preheat_temperature_boost_f', 10.0)  # Boost to 150°F

measure.setArgument('lockout_start_hour', 12)  # 12 PM
measure.setArgument('lockout_duration_hours', 6)  # Until 6 PM
measure.setArgument('minimum_lockout_temperature_f', 120.0)  # Don't go below 120°F
```

**Strategy:**
```ruby
# Three-period control strategy:
# 1. Off-peak charging (12 AM - 6 AM):
#    - Heat to maximum setpoint (160°F)
#    - Maximize thermal storage in tank

# 2. On-peak lockout (12 PM - 6 PM):
#    - Disable HPWH compressor
#    - Use stored energy in tank
#    - Backup resistance heat only if temp drops too low

# 3. Shoulder period (6 PM - 12 AM):
#    - Normal operation
#    - Maintain standard setpoint (140°F)

# Typical savings: 20-40% HPWH energy cost reduction
```

---

## 4. Precooling/Preheating

### AddPrecoolingPreconditioningControl
**Purpose:** Use building thermal mass for load shifting via precooling
**Arguments:**
- `precool_start_hour` (int) - Hour to start precooling (0-23)
- `precool_duration_hours` (int) - Precooling duration
- `precool_setpoint_adjustment_f` (double) - Temperature reduction (°F)
- `demand_limiting_start_hour` (int) - Hour to start demand limiting
- `demand_limiting_duration_hours` (int) - Demand limiting duration
- `demand_limiting_setpoint_increase_f` (double) - Temperature increase (°F)

**Example:**
```ruby
# Precool building before peak period
measure.setArgument('precool_start_hour', 4)  # 4 AM
measure.setArgument('precool_duration_hours', 5)  # Until 9 AM
measure.setArgument('precool_setpoint_adjustment_f', -3.0)  # Cool to 71°F

# Relax cooling during peak period
measure.setArgument('demand_limiting_start_hour', 14)  # 2 PM
measure.setArgument('demand_limiting_duration_hours', 4)  # Until 6 PM
measure.setArgument('demand_limiting_setpoint_increase_f', 3.0)  # Allow 77°F
```

**Thermal Mass Strategy:**
```ruby
# Step 1: Assess building thermal mass
# High thermal mass (concrete, masonry):
#   - Precool 4-5°F below setpoint
#   - Float 3-4°F above setpoint during peak
#   - Effective load shift: 30-50%

# Medium thermal mass (typical construction):
#   - Precool 2-3°F below setpoint
#   - Float 2-3°F above setpoint during peak
#   - Effective load shift: 20-30%

# Low thermal mass (lightweight):
#   - Precool 1-2°F below setpoint
#   - Float 1-2°F above setpoint during peak
#   - Effective load shift: 10-20%

# Step 2: Verify occupant comfort
# - Ensure temperature stays within ASHRAE 55 comfort zone
# - Typical acceptable range: 67-79°F (20-26°C)

# Step 3: Coordinate with occupancy
# - Precool during unoccupied hours (night/early morning)
# - Float during partially occupied periods
# - Return to normal setpoint before full occupancy
```

---

## 5. Schedule Shifting

### ShiftScheduleForDemandResponse
**Purpose:** Shift equipment/process schedules to off-peak periods
**Arguments:**
- `schedule_names` (string) - Comma-separated schedule names
- `shift_hours` (double) - Hours to shift (positive = later)
- `apply_on_weekdays` (bool) - Apply shift on weekdays
- `apply_on_weekends` (bool) - Apply shift on weekends

**Example:**
```ruby
# Shift plug loads and equipment to off-peak
measure.setArgument('schedule_names', 'Office Equipment Schedule,Kitchen Equipment Schedule')
measure.setArgument('shift_hours', -2.0)  # Start 2 hours earlier
measure.setArgument('apply_on_weekdays', true)
measure.setArgument('apply_on_weekends', false)
```

**Load Shifting Applications:**
```ruby
# Commercial kitchen:
# - Shift prep work to off-peak morning hours
# - Original schedule: 11 AM - 2 PM, 5 PM - 8 PM
# - Shifted schedule: 9 AM - 12 PM, 3 PM - 6 PM
# - Savings: Avoid peak demand charges

# Data center:
# - Shift batch processing to nighttime
# - Original: Distributed throughout day
# - Shifted: 10 PM - 6 AM
# - Savings: 40-60% computing energy cost

# Manufacturing:
# - Shift production to night shift
# - Original: 7 AM - 3 PM
# - Shifted: 11 PM - 7 AM
# - Savings: Avoid demand charges + lower TOU rates

# Pool/spa heating:
# - Heat pool during off-peak hours only
# - Original: Maintain 78°F continuously
# - Shifted: Heat 10 PM - 6 AM, float to 75°F during day
# - Savings: 50-70% pool heating cost
```

---

## Complete Workflow Examples

### Example 1: Office Building Load Flexibility Package

```ruby
# Building: 50,000 ft² office, 200-ton peak cooling
# Goal: Reduce demand charges and TOU energy costs

# Measure 1: Ice thermal storage
ice_storage = AddIceThermalStorage.new
ice_storage.setArgument('storage_capacity_ton_hrs', 1200.0)
ice_storage.setArgument('charge_schedule_name', 'Ice Charge (10 PM - 6 AM)')
ice_storage.setArgument('discharge_schedule_name', 'Ice Discharge (12 PM - 6 PM)')

# Measure 2: Precooling
precooling = AddPrecoolingPreconditioningControl.new
precooling.setArgument('precool_start_hour', 5)
precooling.setArgument('precool_duration_hours', 4)
precooling.setArgument('precool_setpoint_adjustment_f', -3.0)
precooling.setArgument('demand_limiting_start_hour', 14)
precooling.setArgument('demand_limiting_duration_hours', 4)
precooling.setArgument('demand_limiting_setpoint_increase_f', 3.0)

# Results:
# - Peak demand reduction: 40-60% during on-peak hours
# - Energy cost savings: 30-45% cooling costs
# - Simple payback: 5-8 years (depends on rate structure)
```

### Example 2: Hotel Load Flexibility Package

```ruby
# Building: 150-room hotel
# Goal: Shift DHW and cooling loads

# Measure 1: HPWH load shifting
hpwh_control = AddHPWHLoadShifting.new
hpwh_control.setArgument('preheat_start_hour', 3)
hpwh_control.setArgument('preheat_duration_hours', 5)
hpwh_control.setArgument('preheat_temperature_boost_f', 15.0)
hpwh_control.setArgument('lockout_start_hour', 12)
hpwh_control.setArgument('lockout_duration_hours', 6)

# Measure 2: Chilled water storage
cw_storage = AddChilledWaterThermalStorage.new
cw_storage.setArgument('storage_capacity_gal', 20000.0)
cw_storage.setArgument('tank_setpoint_temperature_f', 42.0)

# Measure 3: Pool/spa schedule shifting
shift_pool = ShiftScheduleForDemandResponse.new
shift_pool.setArgument('schedule_names', 'Pool Heating Schedule,Spa Heating Schedule')
shift_pool.setArgument('shift_hours', -8.0)  # Heat overnight

# Results:
# - DHW cost reduction: 25-35%
# - Cooling cost reduction: 30-40%
# - Pool/spa cost reduction: 60-70%
```

### Example 3: Data Center Load Flexibility

```ruby
# Building: 10,000 ft² data center
# Goal: Shift computing loads and maximize cooling efficiency

# Measure 1: Ice thermal storage (high capacity)
ice_storage = AddIceThermalStorage.new
ice_storage.setArgument('storage_capacity_ton_hrs', 2400.0)  # 24 hours × 100 tons
ice_storage.setArgument('charge_schedule_name', 'Full Off-Peak Charge')

# Measure 2: Schedule shifting for batch processing
shift_compute = ShiftScheduleForDemandResponse.new
shift_compute.setArgument('schedule_names', 'Batch Processing Schedule,Backup Schedule')
shift_compute.setArgument('shift_hours', 12.0)  # Move to night

# Measure 3: Aggressive precooling
precool = AddPrecoolingPreconditioningControl.new
precool.setArgument('precool_start_hour', 22)  # 10 PM
precool.setArgument('precool_duration_hours', 8)  # Until 6 AM
precool.setArgument('precool_setpoint_adjustment_f', -5.0)  # Very cold

# Results:
# - Peak demand reduction: 60-80%
# - Energy cost savings: 50-70%
# - Improved PUE during peak hours
```

---

## Economic Analysis

### Time-of-Use Rate Assumptions

| Period | Hours | Typical Rate | Strategy |
|--------|-------|--------------|----------|
| **Off-Peak** | 10 PM - 6 AM | $0.06-0.08/kWh | Charge storage, precool |
| **Shoulder** | 6 AM - 12 PM, 6 PM - 10 PM | $0.10-0.15/kWh | Normal operation |
| **On-Peak** | 12 PM - 6 PM | $0.20-0.30/kWh | Discharge storage, float setpoint |

### Demand Charge Assumptions

| Building Type | Typical Demand Charge | Load Flexibility Impact |
|--------------|----------------------|------------------------|
| Office | $15-25/kW | 30-60% reduction |
| Retail | $10-20/kW | 20-40% reduction |
| Hotel | $12-22/kW | 25-50% reduction |
| Data Center | $20-35/kW | 40-80% reduction |

### Simple Payback Estimates

| Measure | Installed Cost Range | Annual Savings | Simple Payback |
|---------|---------------------|----------------|----------------|
| Ice storage | $150-250/ton-hr | 30-50% cooling cost | 5-10 years |
| Chilled water storage | $2-4/gallon | 25-45% cooling cost | 7-12 years |
| HPWH controls | $500-1,500 per unit | 20-40% DHW cost | 1-3 years |
| Precooling controls | $1,000-5,000 | 15-30% cooling cost | 2-5 years |
| Schedule shifting | $500-2,000 | 10-60% (varies) | 1-4 years |

---

## Quick Reference

### Load Flexibility Potential by End Use

| End Use | Flexibility Potential | Storage Method | Typical Shift Duration |
|---------|---------------------|---------------|----------------------|
| Space cooling | High | Ice/chilled water, thermal mass | 4-12 hours |
| Space heating | Medium | Hot water, thermal mass | 2-8 hours |
| DHW | High | Tank thermal mass | 6-12 hours |
| Refrigeration | Medium | Product thermal mass | 2-6 hours |
| Pool heating | Very high | Water thermal mass | 12-24 hours |
| EV charging | Very high | Battery storage | 6-12 hours |
| Batch processes | High | Schedule shifting | 8-16 hours |

### Best Candidates for Load Flexibility

**High Suitability:**
- Buildings with time-of-use rates + demand charges
- High cooling loads (> 100 tons)
- Significant thermal mass
- Flexible occupancy schedules
- Large DHW loads

**Medium Suitability:**
- Moderate cooling loads (20-100 tons)
- Standard construction
- Fixed occupancy schedules
- Moderate DHW loads

**Low Suitability:**
- Small buildings (< 10,000 ft²)
- Minimal cooling/heating loads
- Critical 24/7 operations (hospitals, emergency services)
- Flat electricity rates (no TOU or demand charges)

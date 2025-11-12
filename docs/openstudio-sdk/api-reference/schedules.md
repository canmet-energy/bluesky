# Schedules API Reference

Complete reference for creating and managing schedules in OpenStudio SDK (Python & Ruby).

---

## Object Hierarchy

```
Model
└── Schedule (abstract)
    ├── ScheduleConstant              # Single constant value (24/7)
    ├── ScheduleCompact               # Text-based schedule definition
    ├── ScheduleRuleset               # Rule-based schedule (most flexible)
    │   ├── ScheduleDay               # Daily schedule pattern
    │   ├── ScheduleRule              # When to apply a ScheduleDay
    │   └── DefaultScheduleDay        # Default pattern
    └── ScheduleFile                  # External CSV file

Model
└── ScheduleTypeLimits               # Define valid value ranges and units
```

---

## 1. Schedule Type Limits

**Purpose:** Define the valid range and type of values for a schedule

### Common Schedule Type Limits

| Type | Lower Limit | Upper Limit | Unit Type | Use For |
|------|-------------|-------------|-----------|---------|
| Fractional | 0.0 | 1.0 | Dimensionless | Lighting/equipment multipliers |
| On/Off | 0 | 1 | Discrete | Binary controls |
| Temperature | -60 | 200 | Temperature | Thermostat setpoints (°C) |
| Activity Level | 0 | 1000 | ActivityLevel | Occupant activity (W/person) |
| Humidity | 0 | 100 | Percent | Humidity setpoints |

### Create Schedule Type Limits

**Python:**
```python
import openstudio

model = openstudio.model.Model()

# Fractional (0-1) for lighting/equipment schedules
fractional = openstudio.model.ScheduleTypeLimits(model)
fractional.setName("Fractional")
fractional.setLowerLimitValue(0.0)
fractional.setUpperLimitValue(1.0)
fractional.setNumericType("Continuous")

# On/Off (0 or 1) for binary controls
on_off = openstudio.model.ScheduleTypeLimits(model)
on_off.setName("On/Off")
on_off.setLowerLimitValue(0)
on_off.setUpperLimitValue(1)
on_off.setNumericType("Discrete")

# Temperature for thermostats
temperature = openstudio.model.ScheduleTypeLimits(model)
temperature.setName("Temperature")
temperature.setLowerLimitValue(-60.0)
temperature.setUpperLimitValue(200.0)
temperature.setNumericType("Continuous")
temperature.setUnitType("Temperature")
```

**Ruby:**
```ruby
require 'openstudio'

model = OpenStudio::Model::Model.new

fractional = OpenStudio::Model::ScheduleTypeLimits.new(model)
fractional.setName("Fractional")
fractional.setLowerLimitValue(0.0)
fractional.setUpperLimitValue(1.0)
fractional.setNumericType("Continuous")

on_off = OpenStudio::Model::ScheduleTypeLimits.new(model)
on_off.setName("On/Off")
on_off.setLowerLimitValue(0)
on_off.setUpperLimitValue(1)
on_off.setNumericType("Discrete")

temperature = OpenStudio::Model::ScheduleTypeLimits.new(model)
temperature.setName("Temperature")
temperature.setLowerLimitValue(-60.0)
temperature.setUpperLimitValue(200.0)
temperature.setNumericType("Continuous")
temperature.setUnitType("Temperature")
```

---

## 2. Schedule Constant

**Purpose:** Single value, always on (24/7/365)

**Python:**
```python
# Create always-on schedule (value = 1.0)
always_on = openstudio.model.ScheduleConstant(model)
always_on.setName("Always On")
always_on.setValue(1.0)

# Create always-off schedule
always_off = openstudio.model.ScheduleConstant(model)
always_off.setName("Always Off")
always_off.setValue(0.0)

# Create constant temperature setpoint
heating_setpoint = openstudio.model.ScheduleConstant(model)
heating_setpoint.setName("Heating 20C")
heating_setpoint.setValue(20.0)

# Optional: Set schedule type limits
fractional_limits = model.getScheduleTypeLimitsByName("Fractional").get()
always_on.setScheduleTypeLimits(fractional_limits)
```

**Ruby:**
```ruby
always_on = OpenStudio::Model::ScheduleConstant.new(model)
always_on.setName("Always On")
always_on.setValue(1.0)

always_off = OpenStudio::Model::ScheduleConstant.new(model)
always_off.setName("Always Off")
always_off.setValue(0.0)

heating_setpoint = OpenStudio::Model::ScheduleConstant.new(model)
heating_setpoint.setName("Heating 20C")
heating_setpoint.setValue(20.0)
```

---

## 3. Schedule Compact

**Purpose:** Text-based schedule definition (legacy, but still common)

**Python:**
```python
# Create office hours schedule (8 AM - 6 PM weekdays)
office_hours = openstudio.model.ScheduleCompact(model)
office_hours.setName("Office Hours")

# Set schedule type limits
fractional = model.getScheduleTypeLimitsByName("Fractional").get()
office_hours.setScheduleTypeLimits(fractional)

# Define schedule using compact syntax
# Format: Through: [date], For: [days], Until: [time], [value]
office_hours.setToConstantValue(0.0)  # Start with all zeros

# Note: Python doesn't have great support for ScheduleCompact
# Prefer ScheduleRuleset for Python
```

**Ruby (better ScheduleCompact support):**
```ruby
office_hours = OpenStudio::Model::ScheduleCompact.new(model)
office_hours.setName("Office Hours")

fractional = model.getScheduleTypeLimitsByName("Fractional").get
office_hours.setScheduleTypeLimits(fractional)

# Add schedule data
office_hours.extensibleGroups.each { |eg| eg.remove }  # Clear existing

# Through December 31 (all year)
office_hours.addExtensibleGroup(["Through", "12/31"])

# Weekdays
office_hours.addExtensibleGroup(["For", "Weekdays"])
office_hours.addExtensibleGroup(["Until", "08:00", "0.0"])
office_hours.addExtensibleGroup(["Until", "18:00", "1.0"])
office_hours.addExtensibleGroup(["Until", "24:00", "0.0"])

# Weekends
office_hours.addExtensibleGroup(["For", "Weekends"])
office_hours.addExtensibleGroup(["Until", "24:00", "0.0"])

# Holidays
office_hours.addExtensibleGroup(["For", "Holidays"])
office_hours.addExtensibleGroup(["Until", "24:00", "0.0"])
```

**Note:** ScheduleCompact is harder to work with programmatically. **Use ScheduleRuleset instead for most cases.**

---

## 4. Schedule Ruleset (Recommended)

**Purpose:** Rule-based schedules with default day + exceptions (most flexible)

### Basic Schedule Ruleset

**Python:**
```python
# Create schedule ruleset
office_lighting = openstudio.model.ScheduleRuleset(model)
office_lighting.setName("Office Lighting Schedule")

# Set schedule type limits
fractional = model.getScheduleTypeLimitsByName("Fractional").get()
office_lighting.setScheduleTypeLimits(fractional)

# Create default day schedule (applies when no rules match)
default_day = office_lighting.defaultDaySchedule()
default_day.setName("Office Lighting Default")

# Add time/value pairs (24-hour time)
default_day.addValue(openstudio.Time(0, 8, 0, 0), 0.0)   # Midnight - 8 AM: off
default_day.addValue(openstudio.Time(0, 18, 0, 0), 1.0)  # 8 AM - 6 PM: on
default_day.addValue(openstudio.Time(0, 24, 0, 0), 0.0)  # 6 PM - Midnight: off
```

**Ruby:**
```ruby
office_lighting = OpenStudio::Model::ScheduleRuleset.new(model)
office_lighting.setName("Office Lighting Schedule")

fractional = model.getScheduleTypeLimitsByName("Fractional").get
office_lighting.setScheduleTypeLimits(fractional)

default_day = office_lighting.defaultDaySchedule
default_day.setName("Office Lighting Default")

default_day.addValue(OpenStudio::Time.new(0, 8, 0, 0), 0.0)
default_day.addValue(OpenStudio::Time.new(0, 18, 0, 0), 1.0)
default_day.addValue(OpenStudio::Time.new(0, 24, 0, 0), 0.0)
```

---

### Schedule Ruleset with Weekday/Weekend Rules

**Python:**
```python
# Create schedule
occupancy = openstudio.model.ScheduleRuleset(model)
occupancy.setName("Office Occupancy")

# Default day (weekdays)
default_day = occupancy.defaultDaySchedule()
default_day.setName("Weekday Occupancy")
default_day.addValue(openstudio.Time(0, 8, 0, 0), 0.0)   # Off until 8 AM
default_day.addValue(openstudio.Time(0, 12, 0, 0), 1.0)  # Full occupancy 8-12
default_day.addValue(openstudio.Time(0, 13, 0, 0), 0.5)  # Lunch 12-1 PM
default_day.addValue(openstudio.Time(0, 17, 0, 0), 1.0)  # Full occupancy 1-5 PM
default_day.addValue(openstudio.Time(0, 24, 0, 0), 0.0)  # Off after 5 PM

# Weekend rule
weekend_rule = openstudio.model.ScheduleRule(occupancy)
weekend_rule.setName("Weekend Rule")

# Apply to weekends
weekend_rule.setApplySaturday(True)
weekend_rule.setApplySunday(True)

# Create weekend day schedule (all zeros)
weekend_day = weekend_rule.daySchedule()
weekend_day.setName("Weekend Occupancy")
weekend_day.addValue(openstudio.Time(0, 24, 0, 0), 0.0)  # Off all day
```

**Ruby:**
```ruby
occupancy = OpenStudio::Model::ScheduleRuleset.new(model)
occupancy.setName("Office Occupancy")

# Default day (weekdays)
default_day = occupancy.defaultDaySchedule
default_day.setName("Weekday Occupancy")
default_day.addValue(OpenStudio::Time.new(0, 8, 0, 0), 0.0)
default_day.addValue(OpenStudio::Time.new(0, 12, 0, 0), 1.0)
default_day.addValue(OpenStudio::Time.new(0, 13, 0, 0), 0.5)
default_day.addValue(OpenStudio::Time.new(0, 17, 0, 0), 1.0)
default_day.addValue(OpenStudio::Time.new(0, 24, 0, 0), 0.0)

# Weekend rule
weekend_rule = OpenStudio::Model::ScheduleRule.new(occupancy)
weekend_rule.setName("Weekend Rule")
weekend_rule.setApplySaturday(true)
weekend_rule.setApplySunday(true)

weekend_day = weekend_rule.daySchedule
weekend_day.setName("Weekend Occupancy")
weekend_day.addValue(OpenStudio::Time.new(0, 24, 0, 0), 0.0)
```

---

### Schedule Ruleset with Date Range

**Python:**
```python
# Create schedule
hvac_schedule = openstudio.model.ScheduleRuleset(model)
hvac_schedule.setName("HVAC Availability")

# Default: HVAC on during business hours
default_day = hvac_schedule.defaultDaySchedule()
default_day.addValue(openstudio.Time(0, 6, 0, 0), 0.0)   # Off until 6 AM
default_day.addValue(openstudio.Time(0, 20, 0, 0), 1.0)  # On 6 AM - 8 PM
default_day.addValue(openstudio.Time(0, 24, 0, 0), 0.0)  # Off 8 PM - midnight

# Summer rule (May 1 - Sept 30): extended hours
summer_rule = openstudio.model.ScheduleRule(hvac_schedule)
summer_rule.setName("Summer Rule")

# Set date range
start_date = openstudio.model.YearDescription.makeDate(5, 1)   # May 1
end_date = openstudio.model.YearDescription.makeDate(9, 30)    # Sept 30
summer_rule.setStartDate(start_date)
summer_rule.setEndDate(end_date)

# Apply to all days
summer_rule.setApplyAllDays(True)

# Summer schedule: on 5 AM - 10 PM
summer_day = summer_rule.daySchedule()
summer_day.addValue(openstudio.Time(0, 5, 0, 0), 0.0)
summer_day.addValue(openstudio.Time(0, 22, 0, 0), 1.0)
summer_day.addValue(openstudio.Time(0, 24, 0, 0), 0.0)
```

**Ruby:**
```ruby
hvac_schedule = OpenStudio::Model::ScheduleRuleset.new(model)
hvac_schedule.setName("HVAC Availability")

default_day = hvac_schedule.defaultDaySchedule
default_day.addValue(OpenStudio::Time.new(0, 6, 0, 0), 0.0)
default_day.addValue(OpenStudio::Time.new(0, 20, 0, 0), 1.0)
default_day.addValue(OpenStudio::Time.new(0, 24, 0, 0), 0.0)

summer_rule = OpenStudio::Model::ScheduleRule.new(hvac_schedule)
summer_rule.setName("Summer Rule")

start_date = OpenStudio::Model::YearDescription.makeDate(5, 1)
end_date = OpenStudio::Model::YearDescription.makeDate(9, 30)
summer_rule.setStartDate(start_date)
summer_rule.setEndDate(end_date)
summer_rule.setApplyAllDays(true)

summer_day = summer_rule.daySchedule
summer_day.addValue(OpenStudio::Time.new(0, 5, 0, 0), 0.0)
summer_day.addValue(OpenStudio::Time.new(0, 22, 0, 0), 1.0)
summer_day.addValue(OpenStudio::Time.new(0, 24, 0, 0), 0.0)
```

---

## 5. Common Schedule Patterns

### Always On (1.0 constant)

**Python:**
```python
always_on = openstudio.model.ScheduleConstant(model)
always_on.setName("Always On")
always_on.setValue(1.0)
```

---

### Office Hours (8 AM - 6 PM Weekdays)

**Python:**
```python
def create_office_hours_schedule(model):
    schedule = openstudio.model.ScheduleRuleset(model)
    schedule.setName("Office Hours 8-6")

    # Weekdays: 8 AM - 6 PM
    default_day = schedule.defaultDaySchedule()
    default_day.addValue(openstudio.Time(0, 8, 0, 0), 0.0)
    default_day.addValue(openstudio.Time(0, 18, 0, 0), 1.0)
    default_day.addValue(openstudio.Time(0, 24, 0, 0), 0.0)

    # Weekend: all off
    weekend_rule = openstudio.model.ScheduleRule(schedule)
    weekend_rule.setApplySaturday(True)
    weekend_rule.setApplySunday(True)
    weekend_day = weekend_rule.daySchedule()
    weekend_day.addValue(openstudio.Time(0, 24, 0, 0), 0.0)

    return schedule
```

**Ruby:**
```ruby
def create_office_hours_schedule(model)
  schedule = OpenStudio::Model::ScheduleRuleset.new(model)
  schedule.setName("Office Hours 8-6")

  default_day = schedule.defaultDaySchedule
  default_day.addValue(OpenStudio::Time.new(0, 8, 0, 0), 0.0)
  default_day.addValue(OpenStudio::Time.new(0, 18, 0, 0), 1.0)
  default_day.addValue(OpenStudio::Time.new(0, 24, 0, 0), 0.0)

  weekend_rule = OpenStudio::Model::ScheduleRule.new(schedule)
  weekend_rule.setApplySaturday(true)
  weekend_rule.setApplySunday(true)
  weekend_day = weekend_rule.daySchedule
  weekend_day.addValue(OpenStudio::Time.new(0, 24, 0, 0), 0.0)

  schedule
end
```

---

### Retail Hours (10 AM - 9 PM, 7 days/week)

**Python:**
```python
def create_retail_hours_schedule(model):
    schedule = openstudio.model.ScheduleRuleset(model)
    schedule.setName("Retail Hours 10-9")

    # All days: 10 AM - 9 PM
    default_day = schedule.defaultDaySchedule()
    default_day.addValue(openstudio.Time(0, 10, 0, 0), 0.0)
    default_day.addValue(openstudio.Time(0, 21, 0, 0), 1.0)
    default_day.addValue(openstudio.Time(0, 24, 0, 0), 0.0)

    return schedule
```

---

### Dual Setpoint (Heating/Cooling)

**Python:**
```python
def create_heating_setpoint_schedule(model):
    """Heating setpoint: 20°C occupied, 15°C unoccupied"""
    schedule = openstudio.model.ScheduleRuleset(model)
    schedule.setName("Heating Setpoint")

    # Weekdays: occupied 6 AM - 10 PM
    default_day = schedule.defaultDaySchedule()
    default_day.addValue(openstudio.Time(0, 6, 0, 0), 15.0)   # Setback
    default_day.addValue(openstudio.Time(0, 22, 0, 0), 20.0)  # Occupied
    default_day.addValue(openstudio.Time(0, 24, 0, 0), 15.0)  # Setback

    # Weekend: setback all day
    weekend_rule = openstudio.model.ScheduleRule(schedule)
    weekend_rule.setApplySaturday(True)
    weekend_rule.setApplySunday(True)
    weekend_day = weekend_rule.daySchedule()
    weekend_day.addValue(openstudio.Time(0, 24, 0, 0), 15.0)

    return schedule

def create_cooling_setpoint_schedule(model):
    """Cooling setpoint: 24°C occupied, 30°C unoccupied"""
    schedule = openstudio.model.ScheduleRuleset(model)
    schedule.setName("Cooling Setpoint")

    # Weekdays: occupied 6 AM - 10 PM
    default_day = schedule.defaultDaySchedule()
    default_day.addValue(openstudio.Time(0, 6, 0, 0), 30.0)   # Setup
    default_day.addValue(openstudio.Time(0, 22, 0, 0), 24.0)  # Occupied
    default_day.addValue(openstudio.Time(0, 24, 0, 0), 30.0)  # Setup

    # Weekend: setup all day
    weekend_rule = openstudio.model.ScheduleRule(schedule)
    weekend_rule.setApplySaturday(True)
    weekend_rule.setApplySunday(True)
    weekend_day = weekend_rule.daySchedule()
    weekend_day.addValue(openstudio.Time(0, 24, 0, 0), 30.0)

    return schedule
```

---

### Seasonal Schedule (Winter/Summer)

**Python:**
```python
def create_seasonal_schedule(model):
    """Different patterns for heating/cooling seasons"""
    schedule = openstudio.model.ScheduleRuleset(model)
    schedule.setName("Seasonal Operations")

    # Default (shoulder season)
    default_day = schedule.defaultDaySchedule()
    default_day.addValue(openstudio.Time(0, 24, 0, 0), 0.5)

    # Winter rule (Nov 1 - Mar 31)
    winter_rule = openstudio.model.ScheduleRule(schedule)
    winter_rule.setName("Winter Rule")
    winter_rule.setStartDate(openstudio.model.YearDescription.makeDate(11, 1))
    winter_rule.setEndDate(openstudio.model.YearDescription.makeDate(3, 31))
    winter_rule.setApplyAllDays(True)
    winter_day = winter_rule.daySchedule()
    winter_day.addValue(openstudio.Time(0, 24, 0, 0), 1.0)

    # Summer rule (June 1 - Aug 31)
    summer_rule = openstudio.model.ScheduleRule(schedule)
    summer_rule.setName("Summer Rule")
    summer_rule.setStartDate(openstudio.model.YearDescription.makeDate(6, 1))
    summer_rule.setEndDate(openstudio.model.YearDescription.makeDate(8, 31))
    summer_rule.setApplyAllDays(True)
    summer_day = summer_rule.daySchedule()
    summer_day.addValue(openstudio.Time(0, 24, 0, 0), 0.8)

    return schedule
```

---

## 6. Querying Schedule Values

### Get Schedule Values at Specific Times

**Python:**
```python
schedule = model.getScheduleRulesetByName("Office Lighting Schedule").get()

# Get value at specific date/time
jan_15_10am = openstudio.DateTime(openstudio.Date(1, 15), openstudio.Time(0, 10, 0, 0))
value = schedule.getValue(jan_15_10am)
print(f"Value at Jan 15, 10 AM: {value}")

# Get values throughout a day
day_schedule = schedule.getDaySchedules(openstudio.Date(1, 15), openstudio.Date(1, 15))[0]
times = day_schedule.times()
values = day_schedule.values()

for i in range(len(times)):
    print(f"  Until {times[i]}: {values[i]}")
```

**Ruby:**
```ruby
schedule = model.getScheduleRulesetByName("Office Lighting Schedule").get

jan_15_10am = OpenStudio::DateTime.new(OpenStudio::Date.new(1, 15), OpenStudio::Time.new(0, 10, 0, 0))
value = schedule.getValue(jan_15_10am)
puts "Value at Jan 15, 10 AM: #{value}"

day_schedule = schedule.getDaySchedules(OpenStudio::Date.new(1, 15), OpenStudio::Date.new(1, 15))[0]
times = day_schedule.times
values = day_schedule.values

times.each_with_index do |time, i|
  puts "  Until #{time}: #{values[i]}"
end
```

---

## 7. Modifying Existing Schedules

### Clone and Modify Schedule

**Python:**
```python
# Get existing schedule
original = model.getScheduleRulesetByName("Office Lighting").get()

# Clone it
modified = original.clone(model).to_ScheduleRuleset().get()
modified.setName("Office Lighting - Modified")

# Modify default day
default_day = modified.defaultDaySchedule()
default_day.clearValues()  # Clear existing values

# Set new pattern (7 AM - 7 PM instead of 8-6)
default_day.addValue(openstudio.Time(0, 7, 0, 0), 0.0)
default_day.addValue(openstudio.Time(0, 19, 0, 0), 1.0)
default_day.addValue(openstudio.Time(0, 24, 0, 0), 0.0)
```

**Ruby:**
```ruby
original = model.getScheduleRulesetByName("Office Lighting").get
modified = original.clone(model).to_ScheduleRuleset.get
modified.setName("Office Lighting - Modified")

default_day = modified.defaultDaySchedule
default_day.clearValues

default_day.addValue(OpenStudio::Time.new(0, 7, 0, 0), 0.0)
default_day.addValue(OpenStudio::Time.new(0, 19, 0, 0), 1.0)
default_day.addValue(OpenStudio::Time.new(0, 24, 0, 0), 0.0)
```

---

### Scale Schedule Values

**Python:**
```python
def scale_schedule(schedule_ruleset, multiplier):
    """Scale all values in a ScheduleRuleset by a multiplier"""

    # Scale default day
    default_day = schedule_ruleset.defaultDaySchedule()
    times = default_day.times()
    values = default_day.values()

    default_day.clearValues()
    for i in range(len(times)):
        scaled_value = min(values[i] * multiplier, 1.0)  # Cap at 1.0
        default_day.addValue(times[i], scaled_value)

    # Scale all rules
    for rule in schedule_ruleset.scheduleRules():
        day_schedule = rule.daySchedule()
        times = day_schedule.times()
        values = day_schedule.values()

        day_schedule.clearValues()
        for i in range(len(times)):
            scaled_value = min(values[i] * multiplier, 1.0)
            day_schedule.addValue(times[i], scaled_value)

# Usage
lighting_schedule = model.getScheduleRulesetByName("Office Lighting").get()
scale_schedule(lighting_schedule, 0.8)  # Reduce by 20%
```

---

## 8. Time Object

### Creating Time Objects

**Python:**
```python
# Time format: (days, hours, minutes, seconds)
time_8am = openstudio.Time(0, 8, 0, 0)
time_1230pm = openstudio.Time(0, 12, 30, 0)
time_6pm = openstudio.Time(0, 18, 0, 0)
time_midnight = openstudio.Time(0, 24, 0, 0)

# Or from total hours
time_945am = openstudio.Time(0, 9, 45, 0)   # 9:45 AM

# Or from total seconds
time_noon = openstudio.Time(0, 0, 0, 12 * 3600)  # 12:00 PM
```

**Ruby:**
```ruby
time_8am = OpenStudio::Time.new(0, 8, 0, 0)
time_1230pm = OpenStudio::Time.new(0, 12, 30, 0)
time_6pm = OpenStudio::Time.new(0, 18, 0, 0)
time_midnight = OpenStudio::Time.new(0, 24, 0, 0)
```

---

## Quick Reference

### Schedule Type Quick Lookup

| Need | Class | Best For |
|------|-------|----------|
| Constant value (24/7) | `ScheduleConstant` | Always-on equipment |
| Simple daily pattern | `ScheduleRuleset` | Most schedules |
| Text-based definition | `ScheduleCompact` | Legacy models (avoid) |
| External CSV file | `ScheduleFile` | Measured data, complex patterns |

### Key Methods

| Operation | Python/Ruby Method |
|-----------|-------------------|
| Create schedule | `ScheduleRuleset(model)` or `ScheduleConstant(model)` |
| Set default day | `schedule.defaultDaySchedule()` |
| Add time/value | `day_schedule.addValue(time, value)` |
| Create rule | `ScheduleRule(schedule_ruleset)` |
| Set weekday | `rule.setApplyMonday(True)` through `setApplyFriday(True)` |
| Set weekend | `rule.setApplySaturday(True)`, `setApplySunday(True)` |
| Set date range | `rule.setStartDate(date)`, `rule.setEndDate(date)` |
| Get value | `schedule.getValue(datetime)` |
| Clone schedule | `schedule.clone(model)` |

### Common Time Values

| Time | Code |
|------|------|
| Midnight | `Time(0, 0, 0, 0)` or `Time(0, 24, 0, 0)` |
| 6 AM | `Time(0, 6, 0, 0)` |
| 8 AM | `Time(0, 8, 0, 0)` |
| Noon | `Time(0, 12, 0, 0)` |
| 5 PM | `Time(0, 17, 0, 0)` |
| 6 PM | `Time(0, 18, 0, 0)` |
| 10 PM | `Time(0, 22, 0, 0)` |

### Schedule Rule Priority

Rules are applied in this order (highest priority first):
1. Rules with specific dates (priority 1-99, lower number = higher priority)
2. Default day schedule (lowest priority)

To set priority: `rule.setRuleIndex(0)` (0 = highest priority)

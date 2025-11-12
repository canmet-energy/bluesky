# Thermal Zones API Reference

Complete reference for thermal zones, thermostats, and zone equipment in OpenStudio SDK (Python & Ruby).

---

## Object Hierarchy

```
Model
└── ThermalZone
    ├── ThermostatSetpointDualSetpoint
    │   ├── Heating Schedule
    │   └── Cooling Schedule
    ├── ZoneHVACComponent (optional zone equipment)
    │   ├── ZoneHVACPackagedTerminalAirConditioner
    │   ├── ZoneHVACFourPipeFanCoil
    │   ├── ZoneHVACBaseboardConvectiveElectric
    │   └── ... (other zone HVAC)
    └── Spaces (one or more)
```

---

## 1. Thermal Zones

### Create Thermal Zone

**Python:**
```python
import openstudio

model = openstudio.model.Model()

# Create thermal zone
zone = openstudio.model.ThermalZone(model)
zone.setName("Main Zone")

# Optional: Set multiplier (for identical zones)
zone.setMultiplier(1)

# Optional: Set zone volume (auto-calculated if not set)
# zone.setVolume(300.0)  # m³

# Optional: Set ceiling height
# zone.setCeilingHeight(3.0)  # m
```

**Ruby:**
```ruby
require 'openstudio'

model = OpenStudio::Model::Model.new

zone = OpenStudio::Model::ThermalZone.new(model)
zone.setName("Main Zone")
zone.setMultiplier(1)
```

---

### Assign Space to Thermal Zone

**Python:**
```python
# Create space
space = openstudio.model.Space(model)
space.setName("Main Space")

# Assign to thermal zone
space.setThermalZone(zone)

# Or create multiple spaces in one zone
space2 = openstudio.model.Space(model)
space2.setName("Adjacent Space")
space2.setThermalZone(zone)  # Same zone
```

**Ruby:**
```ruby
space = OpenStudio::Model::Space.new(model)
space.setName("Main Space")
space.setThermalZone(zone)

space2 = OpenStudio::Model::Space.new(model)
space2.setName("Adjacent Space")
space2.setThermalZone(zone)
```

---

## 2. Thermostats

### Create Dual Setpoint Thermostat

**Python:**
```python
# Create heating schedule (20°C occupied, 15°C unoccupied)
heating_schedule = openstudio.model.ScheduleRuleset(model)
heating_schedule.setName("Heating Setpoint")

default_day = heating_schedule.defaultDaySchedule()
default_day.addValue(openstudio.Time(0, 6, 0, 0), 15.0)   # Setback until 6 AM
default_day.addValue(openstudio.Time(0, 22, 0, 0), 20.0)  # Occupied 6 AM - 10 PM
default_day.addValue(openstudio.Time(0, 24, 0, 0), 15.0)  # Setback after 10 PM

# Create cooling schedule (24°C occupied, 30°C unoccupied)
cooling_schedule = openstudio.model.ScheduleRuleset(model)
cooling_schedule.setName("Cooling Setpoint")

default_day = cooling_schedule.defaultDaySchedule()
default_day.addValue(openstudio.Time(0, 6, 0, 0), 30.0)   # Setup until 6 AM
default_day.addValue(openstudio.Time(0, 22, 0, 0), 24.0)  # Occupied 6 AM - 10 PM
default_day.addValue(openstudio.Time(0, 24, 0, 0), 30.0)  # Setup after 10 PM

# Create thermostat
thermostat = openstudio.model.ThermostatSetpointDualSetpoint(model)
thermostat.setName("Zone Thermostat")
thermostat.setHeatingSetpointTemperatureSchedule(heating_schedule)
thermostat.setCoolingSetpointTemperatureSchedule(cooling_schedule)

# Assign to zone
zone.setThermostatSetpointDualSetpoint(thermostat)
```

**Ruby:**
```ruby
heating_schedule = OpenStudio::Model::ScheduleRuleset.new(model)
heating_schedule.setName("Heating Setpoint")

default_day = heating_schedule.defaultDaySchedule
default_day.addValue(OpenStudio::Time.new(0, 6, 0, 0), 15.0)
default_day.addValue(OpenStudio::Time.new(0, 22, 0, 0), 20.0)
default_day.addValue(OpenStudio::Time.new(0, 24, 0, 0), 15.0)

cooling_schedule = OpenStudio::Model::ScheduleRuleset.new(model)
cooling_schedule.setName("Cooling Setpoint")

default_day = cooling_schedule.defaultDaySchedule
default_day.addValue(OpenStudio::Time.new(0, 6, 0, 0), 30.0)
default_day.addValue(OpenStudio::Time.new(0, 22, 0, 0), 24.0)
default_day.addValue(OpenStudio::Time.new(0, 24, 0, 0), 30.0)

thermostat = OpenStudio::Model::ThermostatSetpointDualSetpoint.new(model)
thermostat.setName("Zone Thermostat")
thermostat.setHeatingSetpointTemperatureSchedule(heating_schedule)
thermostat.setCoolingSetpointTemperatureSchedule(cooling_schedule)

zone.setThermostatSetpointDualSetpoint(thermostat)
```

### Typical Setpoints

**Office:**
- Heating occupied: 20-21°C (68-70°F)
- Heating unoccupied: 15-16°C (59-61°F)
- Cooling occupied: 24-25°C (75-77°F)
- Cooling unoccupied: 28-30°C (82-86°F)

**Retail:**
- Heating occupied: 20-21°C
- Cooling occupied: 24°C

**Residential:**
- Heating: 21°C (70°F)
- Cooling: 24°C (75°F)

---

## 3. Zone Equipment

### Add Baseboard Heater

**Python:**
```python
# Create always-on schedule
always_on = openstudio.model.ScheduleConstant(model)
always_on.setName("Always On")
always_on.setValue(1.0)

# Create electric baseboard
baseboard = openstudio.model.ZoneHVACBaseboardConvectiveElectric(model)
baseboard.setName("Electric Baseboard")
baseboard.setNominalCapacity(2000.0)  # W
baseboard.setEfficiency(1.0)          # 100% efficient

# Add to thermal zone
baseboard.addToThermalZone(zone)
```

**Ruby:**
```ruby
always_on = OpenStudio::Model::ScheduleConstant.new(model)
always_on.setName("Always On")
always_on.setValue(1.0)

baseboard = OpenStudio::Model::ZoneHVACBaseboardConvectiveElectric.new(model)
baseboard.setName("Electric Baseboard")
baseboard.setNominalCapacity(2000.0)
baseboard.setEfficiency(1.0)

baseboard.addToThermalZone(zone)
```

---

### Add PTAC (Packaged Terminal AC)

**Python:**
```python
# Create fan
fan = openstudio.model.FanConstantVolume(model, always_on)
fan.setName("PTAC Fan")
fan.setFanEfficiency(0.6)
fan.setPressureRise(75.0)  # Pa

# Create heating coil (electric)
heating_coil = openstudio.model.CoilHeatingElectric(model, always_on)
heating_coil.setName("PTAC Heating Coil")
heating_coil.setEfficiency(1.0)

# Create cooling coil (DX)
cooling_coil = openstudio.model.CoilCoolingDXSingleSpeed(model, always_on)
cooling_coil.setName("PTAC Cooling Coil")

# Create PTAC
ptac = openstudio.model.ZoneHVACPackagedTerminalAirConditioner(
    model, always_on, fan, heating_coil, cooling_coil
)
ptac.setName("PTAC Unit")

# Add to zone
ptac.addToThermalZone(zone)
```

**Ruby:**
```ruby
fan = OpenStudio::Model::FanConstantVolume.new(model, always_on)
fan.setFanEfficiency(0.6)
fan.setPressureRise(75.0)

heating_coil = OpenStudio::Model::CoilHeatingElectric.new(model, always_on)
heating_coil.setEfficiency(1.0)

cooling_coil = OpenStudio::Model::CoilCoolingDXSingleSpeed.new(model, always_on)

ptac = OpenStudio::Model::ZoneHVACPackagedTerminalAirConditioner.new(
  model, always_on, fan, heating_coil, cooling_coil
)

ptac.addToThermalZone(zone)
```

---

### Add Four-Pipe Fan Coil

**Python:**
```python
# Create fan
fan = openstudio.model.FanConstantVolume(model, always_on)

# Create hot water heating coil
heating_coil = openstudio.model.CoilHeatingWater(model, always_on)

# Create chilled water cooling coil
cooling_coil = openstudio.model.CoilCoolingWater(model, always_on)

# Create fan coil
fan_coil = openstudio.model.ZoneHVACFourPipeFanCoil(
    model, always_on, fan, cooling_coil, heating_coil
)
fan_coil.setName("Four-Pipe Fan Coil")

# Optional: Set capacity control method
fan_coil.setCapacityControlMethod("CyclingFan")  # or "VariableFanVariableFlow"

# Add to zone
fan_coil.addToThermalZone(zone)

# Note: Must connect to plant loops (see HVAC patterns guide)
```

**Ruby:**
```ruby
fan = OpenStudio::Model::FanConstantVolume.new(model, always_on)
heating_coil = OpenStudio::Model::CoilHeatingWater.new(model, always_on)
cooling_coil = OpenStudio::Model::CoilCoolingWater.new(model, always_on)

fan_coil = OpenStudio::Model::ZoneHVACFourPipeFanCoil.new(
  model, always_on, fan, cooling_coil, heating_coil
)

fan_coil.addToThermalZone(zone)
```

---

## 4. Ideal Air Loads

### Add Ideal Air Loads (for Testing)

**Python:**
```python
# Create ideal air loads system (no equipment modeling)
ideal_loads = openstudio.model.ZoneHVACIdealLoadsAirSystem(model)
ideal_loads.setName("Ideal Loads")

# Optional: Set limits
ideal_loads.setMaximumHeatingSupplyAirTemperature(50.0)  # °C
ideal_loads.setMinimumCoolingSupplyAirTemperature(13.0)  # °C
ideal_loads.setMaximumHeatingSupplyAirHumidityRatio(0.015)  # kg-H2O/kg-air
ideal_loads.setMinimumCoolingSupplyAirHumidityRatio(0.008)

# Optional: Enable economizer
ideal_loads.setOutdoorAirEconomizerType("DifferentialDryBulb")

# Optional: Enable demand-controlled ventilation
ideal_loads.setDemandControlledVentilationType("OccupancySchedule")

# Add to zone
ideal_loads.addToThermalZone(zone)
```

**Ruby:**
```ruby
ideal_loads = OpenStudio::Model::ZoneHVACIdealLoadsAirSystem.new(model)
ideal_loads.setName("Ideal Loads")

ideal_loads.setMaximumHeatingSupplyAirTemperature(50.0)
ideal_loads.setMinimumCoolingSupplyAirTemperature(13.0)

ideal_loads.setOutdoorAirEconomizerType("DifferentialDryBulb")
ideal_loads.setDemandControlledVentilationType("OccupancySchedule")

ideal_loads.addToThermalZone(zone)
```

**When to use:**
- Quick load calculations
- Testing geometry/loads without HVAC complexity
- Debugging building envelope issues
- NOT for final energy analysis

---

## 5. Zone Properties

### Sizing Parameters

**Python:**
```python
# Get or create sizing zone object
sizing_zone = zone.sizingZone()

# Heating sizing
sizing_zone.setZoneHeatingDesignSupplyAirTemperature(40.0)  # °C
sizing_zone.setZoneHeatingSizingFactor(1.25)  # 25% safety factor

# Cooling sizing
sizing_zone.setZoneCoolingDesignSupplyAirTemperature(13.0)  # °C
sizing_zone.setZoneCoolingSizingFactor(1.15)  # 15% safety factor

# Outdoor air
sizing_zone.setDesignZoneAirDistributionEffectiveness(1.0)
```

**Ruby:**
```ruby
sizing_zone = zone.sizingZone

sizing_zone.setZoneHeatingDesignSupplyAirTemperature(40.0)
sizing_zone.setZoneHeatingSizingFactor(1.25)

sizing_zone.setZoneCoolingDesignSupplyAirTemperature(13.0)
sizing_zone.setZoneCoolingSizingFactor(1.15)

sizing_zone.setDesignZoneAirDistributionEffectiveness(1.0)
```

---

### Zone Multiplier

**Purpose:** Model one zone representing multiple identical zones

**Python:**
```python
# Model hotel with 10 identical floors
typical_floor_zone = openstudio.model.ThermalZone(model)
typical_floor_zone.setName("Typical Guestroom Floor")
typical_floor_zone.setMultiplier(10)  # Represents 10 floors

# Energy results will be multiplied by 10
```

**Ruby:**
```ruby
typical_floor_zone = OpenStudio::Model::ThermalZone.new(model)
typical_floor_zone.setName("Typical Guestroom Floor")
typical_floor_zone.setMultiplier(10)
```

---

## 6. Querying Zone Information

### Get Zone Floor Area and Volume

**Python:**
```python
zone = model.getThermalZones()[0]

# Get floor area (sum of all spaces in zone)
floor_area = zone.floorArea()  # m²

# Get volume (auto-calculated or set manually)
volume = zone.airVolume()      # m³

# Get number of spaces
spaces = zone.spaces()
num_spaces = len(spaces)

print(f"Zone: {zone.name().get()}")
print(f"  Floor area: {floor_area:.2f} m²")
print(f"  Volume: {volume:.2f} m³")
print(f"  Spaces: {num_spaces}")
```

**Ruby:**
```ruby
zone = model.getThermalZones[0]

floor_area = zone.floorArea
volume = zone.airVolume
num_spaces = zone.spaces.size

puts "Zone: #{zone.name.get}"
puts "  Floor area: #{floor_area.round(2)} m²"
puts "  Volume: #{volume.round(2)} m³"
puts "  Spaces: #{num_spaces}"
```

---

### Get Zone Equipment

**Python:**
```python
zone = model.getThermalZones()[0]

# Get all zone equipment
equipment_list = zone.equipment()

print(f"Zone equipment ({len(equipment_list)} items):")
for equipment in equipment_list:
    print(f"  - {equipment.name().get()}")

# Check for specific equipment type
has_baseboard = False
for equipment in equipment_list:
    baseboard = equipment.to_ZoneHVACBaseboardConvectiveElectric()
    if baseboard.is_initialized():
        has_baseboard = True
        break

print(f"Has baseboard: {has_baseboard}")
```

**Ruby:**
```ruby
zone = model.getThermalZones[0]

equipment_list = zone.equipment

puts "Zone equipment (#{equipment_list.size} items):"
equipment_list.each do |equipment|
  puts "  - #{equipment.name.get}"
end
```

---

## 7. Common Zone Patterns

### Pattern 1: Single Zone per Space

```python
# One thermal zone per space (maximum HVAC control)
for space in model.getSpaces():
    zone = openstudio.model.ThermalZone(model)
    zone.setName(f"{space.name().get()} Zone")
    space.setThermalZone(zone)

    # Add thermostat to each zone
    thermostat = create_thermostat(model)  # Your function
    zone.setThermostatSetpointDualSetpoint(thermostat)
```

---

### Pattern 2: Core/Perimeter Zoning

```python
# Separate zones for core and perimeter
core_zone = openstudio.model.ThermalZone(model)
core_zone.setName("Core Zone")

perimeter_zones = {
    'North': openstudio.model.ThermalZone(model),
    'East': openstudio.model.ThermalZone(model),
    'South': openstudio.model.ThermalZone(model),
    'West': openstudio.model.ThermalZone(model)
}

# Assign spaces based on name
for space in model.getSpaces():
    space_name = space.name().get()

    if 'Core' in space_name:
        space.setThermalZone(core_zone)
    elif 'North' in space_name:
        space.setThermalZone(perimeter_zones['North'])
    elif 'East' in space_name:
        space.setThermalZone(perimeter_zones['East'])
    elif 'South' in space_name:
        space.setThermalZone(perimeter_zones['South'])
    elif 'West' in space_name:
        space.setThermalZone(perimeter_zones['West'])
```

---

### Pattern 3: Whole Building Single Zone

```python
# Simple single-zone model
building_zone = openstudio.model.ThermalZone(model)
building_zone.setName("Whole Building")

# Assign all spaces to one zone
for space in model.getSpaces():
    space.setThermalZone(building_zone)

# Add thermostat
thermostat = create_dual_setpoint_thermostat(model, 20.0, 24.0)
building_zone.setThermostatSetpointDualSetpoint(thermostat)

# Add ideal loads for quick analysis
ideal_loads = openstudio.model.ZoneHVACIdealLoadsAirSystem(model)
ideal_loads.addToThermalZone(building_zone)
```

---

## Quick Reference

### Zone Equipment Types

| Equipment | Use Case | Heating | Cooling |
|-----------|----------|---------|---------|
| `ZoneHVACIdealLoadsAirSystem` | Testing, loads analysis | Ideal | Ideal |
| `ZoneHVACPackagedTerminalAirConditioner` | Hotels, apartments | Electric/Gas | DX |
| `ZoneHVACFourPipeFanCoil` | Offices with central plant | Hot water | Chilled water |
| `ZoneHVACBaseboardConvectiveElectric` | Perimeter heating only | Electric | None |
| `ZoneHVACBaseboardConvectiveWater` | Perimeter heating only | Hot water | None |
| `ZoneHVACUnitHeater` | Warehouses, garages | Gas/Electric/Water | None |

### Key Methods

| Operation | Python/Ruby Method |
|-----------|-------------------|
| Create zone | `ThermalZone(model)` |
| Add space to zone | `space.setThermalZone(zone)` |
| Create thermostat | `ThermostatSetpointDualSetpoint(model)` |
| Set thermostat | `zone.setThermostatSetpointDualSetpoint(thermostat)` |
| Add equipment | `equipment.addToThermalZone(zone)` |
| Set multiplier | `zone.setMultiplier(10)` |
| Get floor area | `zone.floorArea()` |
| Get volume | `zone.airVolume()` |

### Typical Setpoint Ranges

| Application | Heating Occupied (°C) | Heating Unoccupied (°C) | Cooling Occupied (°C) | Cooling Unoccupied (°C) |
|------------|---------------------|----------------------|---------------------|----------------------|
| Office | 20-21 | 15-16 | 24-25 | 28-30 |
| Retail | 20-21 | 16-18 | 24 | 28 |
| School | 20-21 | 15 | 24 | 28 |
| Residential | 21 | 18 | 24 | 26 |
| Warehouse | 15-18 | 10 | 27 | 32 |

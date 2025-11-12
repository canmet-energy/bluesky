# Loads & Internal Gains API Reference

Complete reference for creating internal loads (people, lights, equipment, infiltration, ventilation) in OpenStudio SDK (Python & Ruby).

---

## Object Hierarchy

```
Model
├── SpaceType                          # Template with default loads
│   ├── People
│   ├── Lights
│   ├── ElectricEquipment
│   ├── GasEquipment
│   ├── SpaceInfiltrationDesignFlowRate
│   └── DesignSpecificationOutdoorAir
│
└── Space                              # Actual building space
    ├── People                         # Can override SpaceType
    ├── Lights
    ├── ElectricEquipment
    ├── GasEquipment
    ├── SpaceInfiltrationDesignFlowRate
    └── SpaceInfiltrationEffectiveLeakageArea
```

---

## 1. People

### Create People Load

**Python:**
```python
import openstudio

model = openstudio.model.Model()

# Create people definition
people_definition = openstudio.model.PeopleDefinition(model)
people_definition.setName("Office People Definition")

# Method 1: People per floor area (people/m²)
people_definition.setPeopleperSpaceFloorArea(0.05)  # 0.05 people/m² = 20 m²/person

# OR Method 2: Space floor area per person (m²/person)
# people_definition.setSpaceFloorAreaperPerson(20.0)  # 20 m²/person

# OR Method 3: Number of people (absolute)
# people_definition.setNumberofPeople(50)

# Set activity level (W/person)
people_definition.setMeanRadiantTemperatureCalculationType("ZoneAveraged")
people_definition.setSensibleHeatFraction(0.6)  # 60% sensible, 40% latent

# Create people instance
people = openstudio.model.People(people_definition)
people.setName("Office People")

# Set schedule
occupancy_schedule = model.getScheduleByName("Office Occupancy").get()
people.setNumberofPeopleSchedule(occupancy_schedule)

# Set activity level schedule (W/person)
activity_schedule = openstudio.model.ScheduleConstant(model)
activity_schedule.setName("Office Activity")
activity_schedule.setValue(120.0)  # W/person (seated office work)
people.setActivityLevelSchedule(activity_schedule)

# Assign to space or space type
space = openstudio.model.Space(model)
people.setSpace(space)
# OR assign to space type:
# office_space_type = openstudio.model.SpaceType(model)
# people.setSpaceType(office_space_type)
```

**Ruby:**
```ruby
require 'openstudio'

model = OpenStudio::Model::Model.new

people_definition = OpenStudio::Model::PeopleDefinition.new(model)
people_definition.setName("Office People Definition")
people_definition.setPeopleperSpaceFloorArea(0.05)
people_definition.setSensibleHeatFraction(0.6)

people = OpenStudio::Model::People.new(people_definition)
people.setName("Office People")

occupancy_schedule = model.getScheduleByName("Office Occupancy").get
people.setNumberofPeopleSchedule(occupancy_schedule)

activity_schedule = OpenStudio::Model::ScheduleConstant.new(model)
activity_schedule.setName("Office Activity")
activity_schedule.setValue(120.0)
people.setActivityLevelSchedule(activity_schedule)

space = OpenStudio::Model::Space.new(model)
people.setSpace(space)
```

### Activity Levels (W/person)

| Activity | Heat Gain (W/person) | Use Case |
|----------|---------------------|----------|
| Seated, quiet | 100 | Theater, library |
| Seated, light work | 120 | Office, classroom |
| Standing, light work | 160 | Retail, lab |
| Light bench work | 235 | Workshop |
| Moderate activity | 295 | Warehouse, gymnasium |
| Heavy work | 440 | Factory, heavy labor |

---

## 2. Lights

### Create Lighting Load

**Python:**
```python
# Create lighting definition
lighting_definition = openstudio.model.LightsDefinition(model)
lighting_definition.setName("Office Lighting Definition")

# Method 1: Watts per floor area (W/m²)
lighting_definition.setWattsperSpaceFloorArea(10.0)  # W/m²

# OR Method 2: Watts per person (W/person)
# lighting_definition.setWattsperPerson(100.0)

# OR Method 3: Lighting level (absolute watts)
# lighting_definition.setLightingLevel(5000.0)  # W

# Create lighting instance
lights = openstudio.model.Lights(lighting_definition)
lights.setName("Office Lighting")

# Set schedule
lighting_schedule = model.getScheduleByName("Office Lighting Schedule").get()
lights.setSchedule(lighting_schedule)

# Set fractions (must sum to ≤ 1.0)
lights.setFractionRadiant(0.42)      # Radiant fraction
lights.setFractionVisible(0.18)      # Visible fraction
lights.setReturnAirFraction(0.0)     # Return air fraction (for return air plenums)

# Assign to space
space = model.getSpaces()[0]
lights.setSpace(space)
```

**Ruby:**
```ruby
lighting_definition = OpenStudio::Model::LightsDefinition.new(model)
lighting_definition.setName("Office Lighting Definition")
lighting_definition.setWattsperSpaceFloorArea(10.0)

lights = OpenStudio::Model::Lights.new(lighting_definition)
lights.setName("Office Lighting")

lighting_schedule = model.getScheduleByName("Office Lighting Schedule").get
lights.setSchedule(lighting_schedule)

lights.setFractionRadiant(0.42)
lights.setFractionVisible(0.18)
lights.setReturnAirFraction(0.0)

space = model.getSpaces[0]
lights.setSpace(space)
```

### Lighting Power Densities (W/m²)

**NECB 2020:**

| Space Type | LPD (W/m²) |
|-----------|-----------|
| Office - Open | 9.7 |
| Office - Enclosed | 11.0 |
| Conference Room | 11.8 |
| Corridor | 5.4 |
| Washroom | 9.0 |
| Retail - Sales | 16.1 |
| School - Classroom | 11.7 |
| Warehouse - Storage | 8.1 |

**ASHRAE 90.1-2019:**

| Building Type | Space Type | LPD (W/m²) |
|--------------|-----------|-----------|
| Office | Open Office | 8.6 |
| Office | Enclosed Office | 10.3 |
| Office | Conference | 11.8 |
| Retail | Sales Area | 14.0 |
| School | Classroom | 11.3 |
| Warehouse | Storage | 7.5 |

---

## 3. Electric Equipment

### Create Electric Equipment Load

**Python:**
```python
# Create equipment definition
equipment_definition = openstudio.model.ElectricEquipmentDefinition(model)
equipment_definition.setName("Office Equipment Definition")

# Method 1: Watts per floor area (W/m²)
equipment_definition.setWattsperSpaceFloorArea(10.0)  # W/m²

# OR Method 2: Watts per person (W/person)
# equipment_definition.setWattsperPerson(200.0)

# OR Method 3: Equipment level (absolute watts)
# equipment_definition.setDesignLevel(3000.0)  # W

# Create equipment instance
equipment = openstudio.model.ElectricEquipment(equipment_definition)
equipment.setName("Office Equipment")

# Set schedule
equipment_schedule = model.getScheduleByName("Office Equipment Schedule").get()
equipment.setSchedule(equipment_schedule)

# Set fractions (must sum to 1.0)
equipment.setFractionRadiant(0.5)    # Radiant fraction
equipment.setFractionLatent(0.0)     # Latent fraction (moisture release)
equipment.setFractionLost(0.0)       # Lost fraction (vented outside)

# Assign to space
equipment.setSpace(space)
```

**Ruby:**
```ruby
equipment_definition = OpenStudio::Model::ElectricEquipmentDefinition.new(model)
equipment_definition.setName("Office Equipment Definition")
equipment_definition.setWattsperSpaceFloorArea(10.0)

equipment = OpenStudio::Model::ElectricEquipment.new(equipment_definition)
equipment.setName("Office Equipment")

equipment_schedule = model.getScheduleByName("Office Equipment Schedule").get
equipment.setSchedule(equipment_schedule)

equipment.setFractionRadiant(0.5)
equipment.setFractionLatent(0.0)
equipment.setFractionLost(0.0)

equipment.setSpace(space)
```

### Electric Equipment Power Densities (W/m²)

| Space Type | EPD (W/m²) | Typical Equipment |
|-----------|-----------|-------------------|
| Office - Open | 8-12 | Computers, printers, phones |
| Office - Enclosed | 10-15 | Computer, monitor, task light |
| Conference Room | 5-10 | AV equipment, laptop |
| Data Center | 100-500 | Servers, networking |
| Lab | 15-30 | Instruments, equipment |
| Kitchen | 20-50 | Appliances, cooking equipment |
| Retail | 2-5 | POS systems, displays |

---

## 4. Gas Equipment

### Create Gas Equipment Load

**Python:**
```python
# Create gas equipment definition
gas_equipment_definition = openstudio.model.GasEquipmentDefinition(model)
gas_equipment_definition.setName("Kitchen Gas Equipment")

# Watts per floor area (W/m²)
gas_equipment_definition.setWattsperSpaceFloorArea(50.0)

# Create gas equipment instance
gas_equipment = openstudio.model.GasEquipment(gas_equipment_definition)
gas_equipment.setName("Gas Cooking Equipment")

# Set schedule
gas_schedule = model.getScheduleByName("Kitchen Gas Schedule").get()
gas_equipment.setSchedule(gas_schedule)

# Set fractions
gas_equipment.setFractionRadiant(0.3)
gas_equipment.setFractionLatent(0.2)   # Moisture from combustion
gas_equipment.setFractionLost(0.5)     # Vented outside via exhaust hood

# Assign to space
gas_equipment.setSpace(space)
```

**Ruby:**
```ruby
gas_equipment_definition = OpenStudio::Model::GasEquipmentDefinition.new(model)
gas_equipment_definition.setName("Kitchen Gas Equipment")
gas_equipment_definition.setWattsperSpaceFloorArea(50.0)

gas_equipment = OpenStudio::Model::GasEquipment.new(gas_equipment_definition)
gas_equipment.setName("Gas Cooking Equipment")

gas_schedule = model.getScheduleByName("Kitchen Gas Schedule").get
gas_equipment.setSchedule(gas_schedule)

gas_equipment.setFractionRadiant(0.3)
gas_equipment.setFractionLatent(0.2)
gas_equipment.setFractionLost(0.5)

gas_equipment.setSpace(space)
```

---

## 5. Infiltration

### Method 1: Design Flow Rate

**Python:**
```python
# Create infiltration
infiltration = openstudio.model.SpaceInfiltrationDesignFlowRate(model)
infiltration.setName("Infiltration")

# Method 1: Flow per exterior surface area (m³/s/m²)
infiltration.setFlowperExteriorSurfaceArea(0.0003)  # m³/s/m² @ 75 Pa

# OR Method 2: Flow per exterior wall area (m³/s/m²)
# infiltration.setFlowperExteriorWallArea(0.0006)

# OR Method 3: Air changes per hour (ACH)
# infiltration.setAirChangesperHour(0.5)

# OR Method 4: Flow per floor area (m³/s/m²)
# infiltration.setFlowperSpaceFloorArea(0.0001)

# Set schedule
infiltration_schedule = openstudio.model.ScheduleConstant(model)
infiltration_schedule.setName("Infiltration Schedule")
infiltration_schedule.setValue(1.0)  # Always on
infiltration.setSchedule(infiltration_schedule)

# Set coefficients (flow = A + B*ΔT + C*WindSpeed + D*WindSpeed²)
# Default: constant flow
infiltration.setConstantTermCoefficient(1.0)
infiltration.setTemperatureTermCoefficient(0.0)
infiltration.setVelocityTermCoefficient(0.0)
infiltration.setVelocitySquaredTermCoefficient(0.0)

# Assign to space
infiltration.setSpace(space)
```

**Ruby:**
```ruby
infiltration = OpenStudio::Model::SpaceInfiltrationDesignFlowRate.new(model)
infiltration.setName("Infiltration")
infiltration.setFlowperExteriorSurfaceArea(0.0003)

infiltration_schedule = OpenStudio::Model::ScheduleConstant.new(model)
infiltration_schedule.setName("Infiltration Schedule")
infiltration_schedule.setValue(1.0)
infiltration.setSchedule(infiltration_schedule)

infiltration.setConstantTermCoefficient(1.0)
infiltration.setTemperatureTermCoefficient(0.0)
infiltration.setVelocityTermCoefficient(0.0)
infiltration.setVelocitySquaredTermCoefficient(0.0)

infiltration.setSpace(space)
```

### Infiltration Rates

**NECB (@ 75 Pa):**
- 0.25 L/s/m² exterior surface area = 0.00025 m³/s/m²

**ASHRAE 90.1:**
- 1.25 CFM/ft² @ 75 Pa = 0.00063 m³/s/m²

**Typical ACH Values:**
- Very tight (new construction): 0.1-0.3 ACH
- Tight (retrofit): 0.3-0.5 ACH
- Average: 0.5-1.0 ACH
- Leaky (old buildings): 1.0-2.0 ACH

**Conversion:**
- 1 CFM @ 75 Pa = 0.000472 m³/s
- 1 ACH = (Volume × ACH) / 3600 m³/s

---

### Method 2: Effective Leakage Area

**Python:**
```python
# Create infiltration based on effective leakage area
infiltration_ela = openstudio.model.SpaceInfiltrationEffectiveLeakageArea(model)
infiltration_ela.setName("Infiltration ELA")

# Effective leakage area (cm²)
infiltration_ela.setEffectiveAirLeakageArea(500.0)  # cm²

# Stack and wind coefficients
infiltration_ela.setStackCoefficient(0.000145)      # Default for 1-story
infiltration_ela.setWindCoefficient(0.000319)       # Default for 1-story

# Set schedule
infiltration_ela.setSchedule(infiltration_schedule)

# Assign to space
infiltration_ela.setSpace(space)
```

**Ruby:**
```ruby
infiltration_ela = OpenStudio::Model::SpaceInfiltrationEffectiveLeakageArea.new(model)
infiltration_ela.setName("Infiltration ELA")
infiltration_ela.setEffectiveAirLeakageArea(500.0)
infiltration_ela.setStackCoefficient(0.000145)
infiltration_ela.setWindCoefficient(0.000319)
infiltration_ela.setSchedule(infiltration_schedule)
infiltration_ela.setSpace(space)
```

---

## 6. Outdoor Air Ventilation

### Create Ventilation Specification

**Python:**
```python
# Create outdoor air specification
outdoor_air = openstudio.model.DesignSpecificationOutdoorAir(model)
outdoor_air.setName("Office Ventilation")

# Method 1: Sum (per person + per area)
outdoor_air.setOutdoorAirMethod("Sum")

# Per person (m³/s/person)
outdoor_air.setOutdoorAirFlowperPerson(0.0025)  # 2.5 L/s/person

# Per floor area (m³/s/m²)
outdoor_air.setOutdoorAirFlowperFloorArea(0.0003)  # 0.3 L/s/m²

# OR Method 2: Maximum (max of per person or per area)
# outdoor_air.setOutdoorAirMethod("Maximum")

# OR Method 3: Flow per area only
# outdoor_air.setOutdoorAirMethod("Flow/Area")
# outdoor_air.setOutdoorAirFlowperFloorArea(0.0008)

# OR Method 4: Flow per person only
# outdoor_air.setOutdoorAirMethod("Flow/Person")
# outdoor_air.setOutdoorAirFlowperPerson(0.0025)

# OR Method 5: Air changes per hour
# outdoor_air.setOutdoorAirMethod("AirChanges/Hour")
# outdoor_air.setOutdoorAirFlowAirChangesperHour(0.5)

# Set schedule (optional, typically always on)
oa_schedule = openstudio.model.ScheduleConstant(model)
oa_schedule.setName("Ventilation Schedule")
oa_schedule.setValue(1.0)
outdoor_air.setOutdoorAirFlowRateFractionSchedule(oa_schedule)

# Assign to space
space.setDesignSpecificationOutdoorAir(outdoor_air)
```

**Ruby:**
```ruby
outdoor_air = OpenStudio::Model::DesignSpecificationOutdoorAir.new(model)
outdoor_air.setName("Office Ventilation")
outdoor_air.setOutdoorAirMethod("Sum")
outdoor_air.setOutdoorAirFlowperPerson(0.0025)
outdoor_air.setOutdoorAirFlowperFloorArea(0.0003)

oa_schedule = OpenStudio::Model::ScheduleConstant.new(model)
oa_schedule.setName("Ventilation Schedule")
oa_schedule.setValue(1.0)
outdoor_air.setOutdoorAirFlowRateFractionSchedule(oa_schedule)

space.setDesignSpecificationOutdoorAir(outdoor_air)
```

### Ventilation Rates

**NECB 2020:**

| Space Type | L/s/person | L/s/m² |
|-----------|-----------|--------|
| Office | 2.5 | 0.3 |
| Conference Room | 2.5 | 0.3 |
| Classroom | 3.0 | 0.3 |
| Retail | 2.5 | 0.3 |
| Gymnasium | 7.5 | - |
| Corridor | - | 0.3 |

**ASHRAE 62.1-2019:**

| Space Type | CFM/person | CFM/ft² | L/s/person | L/s/m² |
|-----------|-----------|---------|-----------|--------|
| Office | 5 | 0.06 | 2.5 | 0.3 |
| Conference Room | 5 | 0.06 | 2.5 | 0.3 |
| Classroom | 10 | 0.12 | 5.0 | 0.6 |
| Retail | 7.5 | 0.12 | 3.8 | 0.6 |

**Conversion:**
- 1 CFM = 0.000472 m³/s = 0.472 L/s
- 1 CFM/ft² = 0.00508 m³/s/m² = 5.08 L/s/m²

---

## 7. Space Types (Load Templates)

### Create Space Type with All Loads

**Python:**
```python
# Create space type
office_space_type = openstudio.model.SpaceType(model)
office_space_type.setName("Office - Open Office")

# Add people
people_definition = openstudio.model.PeopleDefinition(model)
people_definition.setName("Office People")
people_definition.setPeopleperSpaceFloorArea(0.05)  # 20 m²/person

people = openstudio.model.People(people_definition)
people.setSpaceType(office_space_type)
people.setNumberofPeopleSchedule(occupancy_schedule)

# Add lighting
lighting_definition = openstudio.model.LightsDefinition(model)
lighting_definition.setName("Office Lighting")
lighting_definition.setWattsperSpaceFloorArea(10.0)  # W/m²

lights = openstudio.model.Lights(lighting_definition)
lights.setSpaceType(office_space_type)
lights.setSchedule(lighting_schedule)
lights.setFractionRadiant(0.42)
lights.setFractionVisible(0.18)

# Add electric equipment
equipment_definition = openstudio.model.ElectricEquipmentDefinition(model)
equipment_definition.setName("Office Equipment")
equipment_definition.setWattsperSpaceFloorArea(10.0)  # W/m²

equipment = openstudio.model.ElectricEquipment(equipment_definition)
equipment.setSpaceType(office_space_type)
equipment.setSchedule(equipment_schedule)
equipment.setFractionRadiant(0.5)

# Add infiltration
infiltration = openstudio.model.SpaceInfiltrationDesignFlowRate(model)
infiltration.setSpaceType(office_space_type)
infiltration.setFlowperExteriorSurfaceArea(0.0003)
infiltration.setSchedule(infiltration_schedule)

# Add ventilation
outdoor_air = openstudio.model.DesignSpecificationOutdoorAir(model)
outdoor_air.setName("Office Ventilation")
outdoor_air.setOutdoorAirMethod("Sum")
outdoor_air.setOutdoorAirFlowperPerson(0.0025)
outdoor_air.setOutdoorAirFlowperFloorArea(0.0003)
office_space_type.setDesignSpecificationOutdoorAir(outdoor_air)

# Assign space type to spaces
for space in model.getSpaces():
    space.setSpaceType(office_space_type)
```

**Ruby:**
```ruby
office_space_type = OpenStudio::Model::SpaceType.new(model)
office_space_type.setName("Office - Open Office")

# People
people_definition = OpenStudio::Model::PeopleDefinition.new(model)
people_definition.setPeopleperSpaceFloorArea(0.05)

people = OpenStudio::Model::People.new(people_definition)
people.setSpaceType(office_space_type)
people.setNumberofPeopleSchedule(occupancy_schedule)

# Lighting
lighting_definition = OpenStudio::Model::LightsDefinition.new(model)
lighting_definition.setWattsperSpaceFloorArea(10.0)

lights = OpenStudio::Model::Lights.new(lighting_definition)
lights.setSpaceType(office_space_type)
lights.setSchedule(lighting_schedule)

# Equipment
equipment_definition = OpenStudio::Model::ElectricEquipmentDefinition.new(model)
equipment_definition.setWattsperSpaceFloorArea(10.0)

equipment = OpenStudio::Model::ElectricEquipment.new(equipment_definition)
equipment.setSpaceType(office_space_type)
equipment.setSchedule(equipment_schedule)

# Infiltration
infiltration = OpenStudio::Model::SpaceInfiltrationDesignFlowRate.new(model)
infiltration.setSpaceType(office_space_type)
infiltration.setFlowperExteriorSurfaceArea(0.0003)

# Ventilation
outdoor_air = OpenStudio::Model::DesignSpecificationOutdoorAir.new(model)
outdoor_air.setOutdoorAirMethod("Sum")
outdoor_air.setOutdoorAirFlowperPerson(0.0025)
outdoor_air.setOutdoorAirFlowperFloorArea(0.0003)
office_space_type.setDesignSpecificationOutdoorAir(outdoor_air)

# Assign to spaces
model.getSpaces.each do |space|
  space.setSpaceType(office_space_type)
end
```

---

## 8. Querying Loads

### Get Total Loads for Space

**Python:**
```python
space = model.getSpaces()[0]
floor_area = space.floorArea()

# Get people
people_instances = space.people()
total_people = 0.0
for people in people_instances:
    people_definition = people.definition().to_PeopleDefinition().get()
    if people_definition.peopleperSpaceFloorArea().is_initialized():
        people_per_area = people_definition.peopleperSpaceFloorArea().get()
        total_people += people_per_area * floor_area

print(f"Total people: {total_people:.1f}")

# Get lighting power
lights_instances = space.lights()
total_lighting_power = 0.0
for lights in lights_instances:
    lighting_definition = lights.definition().to_LightsDefinition().get()
    if lighting_definition.wattsperSpaceFloorArea().is_initialized():
        watts_per_area = lighting_definition.wattsperSpaceFloorArea().get()
        total_lighting_power += watts_per_area * floor_area

print(f"Total lighting power: {total_lighting_power:.0f} W")
print(f"Lighting power density: {total_lighting_power / floor_area:.1f} W/m²")
```

**Ruby:**
```ruby
space = model.getSpaces[0]
floor_area = space.floorArea

# Get people
total_people = 0.0
space.people.each do |people|
  people_definition = people.definition.to_PeopleDefinition.get
  if people_definition.peopleperSpaceFloorArea.is_initialized
    people_per_area = people_definition.peopleperSpaceFloorArea.get
    total_people += people_per_area * floor_area
  end
end

puts "Total people: #{total_people.round(1)}"

# Get lighting power
total_lighting_power = 0.0
space.lights.each do |lights|
  lighting_definition = lights.definition.to_LightsDefinition.get
  if lighting_definition.wattsperSpaceFloorArea.is_initialized
    watts_per_area = lighting_definition.wattsperSpaceFloorArea.get
    total_lighting_power += watts_per_area * floor_area
  end
end

puts "Total lighting power: #{total_lighting_power.round(0)} W"
puts "LPD: #{(total_lighting_power / floor_area).round(1)} W/m²"
```

---

## Quick Reference

### Load Types Quick Lookup

| Load Type | Class | Typical Units |
|-----------|-------|--------------|
| Occupants | `People` | people/m² or m²/person |
| Lighting | `Lights` | W/m² |
| Plug loads | `ElectricEquipment` | W/m² |
| Gas equipment | `GasEquipment` | W/m² |
| Infiltration | `SpaceInfiltrationDesignFlowRate` | m³/s/m² or ACH |
| Ventilation | `DesignSpecificationOutdoorAir` | L/s/person, L/s/m² |

### Key Methods

| Operation | Python/Ruby Method |
|-----------|-------------------|
| Create definition | `PeopleDefinition(model)`, `LightsDefinition(model)`, etc. |
| Create instance | `People(definition)`, `Lights(definition)`, etc. |
| Set density | `setPeopleperSpaceFloorArea()`, `setWattsperSpaceFloorArea()` |
| Set schedule | `setSchedule(schedule)` or `setNumberofPeopleSchedule(schedule)` |
| Assign to space | `load.setSpace(space)` |
| Assign to space type | `load.setSpaceType(space_type)` |

### Typical Office Load Summary (NECB 2020)

| Load | Value | Units |
|------|-------|-------|
| People | 0.05 | people/m² (20 m²/person) |
| Activity | 120 | W/person |
| Lighting | 9.7 | W/m² |
| Equipment | 10.0 | W/m² |
| Infiltration | 0.00025 | m³/s/m² @ 75 Pa |
| Ventilation | 2.5 + 0.3 | L/s/person + L/s/m² |

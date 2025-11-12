# OpenStudio SDK API Reference

Domain-specific API references for OpenStudio SDK (Python & Ruby). Organized by modeling workflow rather than alphabetically.

---

## Available References

### 1. Materials & Constructions
**File:** [materials-constructions.md](materials-constructions.md)

**Covers:**
- Standard opaque materials (thermal properties)
- Massless materials (R-value only)
- Air gaps
- Fenestration materials (simple glazing, detailed glazing, gas fills)
- Layered constructions
- Construction sets
- Material properties tables
- U-factor calculations

**When to use:** Creating building envelope, defining thermal properties, managing construction libraries

---

### 2. Schedules
**File:** [schedules.md](schedules.md)

**Covers:**
- Schedule type limits
- ScheduleConstant (always-on/off)
- ScheduleCompact (text-based, legacy)
- ScheduleRuleset (rule-based, recommended)
- Time objects
- Common schedule patterns (office hours, retail, seasonal)
- Querying and modifying schedules

**When to use:** Creating occupancy patterns, equipment schedules, thermostat setpoints, lighting schedules

---

### 3. Loads & Internal Gains
**File:** [loads-internal-gains.md](loads-internal-gains.md)

**Covers:**
- People (occupancy, activity levels)
- Lights (lighting power density)
- Electric equipment (plug loads)
- Gas equipment
- Infiltration (design flow rate, effective leakage area)
- Outdoor air ventilation
- Space types (load templates)
- Load density tables (NECB, ASHRAE)

**When to use:** Defining internal loads, setting occupancy, configuring ventilation, creating space type libraries

---

### 4. Surfaces & Geometry
**File:** [surfaces-geometry.md](surfaces-geometry.md)

**Covers:**
- Points and vertices
- Surfaces (walls, floors, roofs)
- Sub-surfaces (windows, doors, skylights)
- Shading surfaces (overhangs, neighboring buildings)
- Vertex ordering rules (counter-clockwise from outside)
- Surface matching and intersecting
- Window-to-wall ratio
- Geometry transformations

**When to use:** Creating building geometry, adding windows, creating shading, matching interior surfaces

---

### 5. Thermal Zones
**File:** [thermal-zones.md](thermal-zones.md)

**Covers:**
- Creating thermal zones
- Assigning spaces to zones
- Dual setpoint thermostats (heating/cooling)
- Zone equipment (baseboard, PTAC, fan coil)
- Ideal air loads (for testing)
- Zone sizing parameters
- Zone multipliers
- Common zoning patterns (core/perimeter, single zone)

**When to use:** Organizing spaces into HVAC zones, adding thermostats, adding zone equipment, setting up zone controls

---

### 6. Simulation Settings
**File:** [simulation-settings.md](simulation-settings.md)

**Covers:**
- Run period (annual, seasonal, custom)
- Timestep (timesteps per hour)
- Simulation control (solar distribution, warmup days)
- Shadow calculation
- Sizing parameters (oversizing factors)
- Convergence limits
- Output variables and meters
- Weather files
- Design days
- Output control settings

**When to use:** Configuring simulation, setting output variables, adding design days, controlling simulation accuracy

---

## Quick Navigation by Task

### I need to create...

**Building envelope:**
→ [materials-constructions.md](materials-constructions.md)

**Occupancy and loads:**
→ [loads-internal-gains.md](loads-internal-gains.md)

**Operating schedules:**
→ [schedules.md](schedules.md)

**Building geometry:**
→ [surfaces-geometry.md](surfaces-geometry.md)

**HVAC zones:**
→ [thermal-zones.md](thermal-zones.md)

**Simulation configuration:**
→ [simulation-settings.md](simulation-settings.md)

---

### I need to set...

**Thermostat setpoints:**
→ [thermal-zones.md](thermal-zones.md) → Section 2

**Window properties:**
→ [materials-constructions.md](materials-constructions.md) → Section 4

**Lighting schedule:**
→ [schedules.md](schedules.md) → Section 4 (Schedule Ruleset)

**Infiltration rate:**
→ [loads-internal-gains.md](loads-internal-gains.md) → Section 5

**Window-to-wall ratio:**
→ [surfaces-geometry.md](surfaces-geometry.md) → Section 3

**Simulation timestep:**
→ [simulation-settings.md](simulation-settings.md) → Section 2

---

### I need to query...

**Construction U-factor:**
→ [materials-constructions.md](materials-constructions.md) → Section 8

**Schedule values at specific time:**
→ [schedules.md](schedules.md) → Section 6

**Zone floor area:**
→ [thermal-zones.md](thermal-zones.md) → Section 6

**Surface orientation:**
→ [surfaces-geometry.md](surfaces-geometry.md) → Section 5

**Total lighting power:**
→ [loads-internal-gains.md](loads-internal-gains.md) → Section 8

---

## Typical Modeling Workflow

### 1. Basic Model Setup
1. Create model: `model = openstudio.model.Model()`
2. Set weather file → [simulation-settings.md](simulation-settings.md) § 8
3. Set run period → [simulation-settings.md](simulation-settings.md) § 1
4. Set timestep → [simulation-settings.md](simulation-settings.md) § 2

### 2. Define Materials & Constructions
1. Create schedule type limits → [schedules.md](schedules.md) § 1
2. Create materials → [materials-constructions.md](materials-constructions.md) § 1-4
3. Create constructions → [materials-constructions.md](materials-constructions.md) § 5
4. Create construction sets → [materials-constructions.md](materials-constructions.md) § 6

### 3. Create Building Geometry
1. Create spaces → [surfaces-geometry.md](surfaces-geometry.md)
2. Create surfaces (walls, floors, roofs) → [surfaces-geometry.md](surfaces-geometry.md) § 2
3. Add windows/doors → [surfaces-geometry.md](surfaces-geometry.md) § 3
4. Add shading → [surfaces-geometry.md](surfaces-geometry.md) § 4
5. Match interior surfaces → [surfaces-geometry.md](surfaces-geometry.md) § 5

### 4. Assign Loads & Schedules
1. Create schedules → [schedules.md](schedules.md) § 4 (ScheduleRuleset)
2. Create space types → [loads-internal-gains.md](loads-internal-gains.md) § 7
3. Add people → [loads-internal-gains.md](loads-internal-gains.md) § 1
4. Add lights → [loads-internal-gains.md](loads-internal-gains.md) § 2
5. Add equipment → [loads-internal-gains.md](loads-internal-gains.md) § 3-4
6. Add infiltration → [loads-internal-gains.md](loads-internal-gains.md) § 5
7. Add ventilation → [loads-internal-gains.md](loads-internal-gains.md) § 6

### 5. Create Thermal Zones
1. Create thermal zones → [thermal-zones.md](thermal-zones.md) § 1
2. Assign spaces to zones → [thermal-zones.md](thermal-zones.md) § 1
3. Create thermostats → [thermal-zones.md](thermal-zones.md) § 2
4. Add zone equipment (optional) → [thermal-zones.md](thermal-zones.md) § 3-4

### 6. Configure Simulation
1. Set simulation control → [simulation-settings.md](simulation-settings.md) § 3
2. Set shadow calculation → [simulation-settings.md](simulation-settings.md) § 4
3. Add output variables → [simulation-settings.md](simulation-settings.md) § 7
4. Add design days → [simulation-settings.md](simulation-settings.md) § 9

### 7. Save and Run
1. Save model: `model.save('model.osm', True)`
2. Run simulation via OpenStudio CLI

---

## Code Examples by Language

### Python Examples

All references include Python code examples using:
```python
import openstudio

model = openstudio.model.Model()
```

**Python-specific notes:**
- Use `openstudio.` prefix for classes
- Use `.get()` to unwrap optional values
- Use `openstudio.Point3dVector()` for vertex arrays

---

### Ruby Examples

All references include Ruby code examples using:
```ruby
require 'openstudio'

model = OpenStudio::Model::Model.new
```

**Ruby-specific notes:**
- Use `OpenStudio::` prefix for classes
- Use `.get` to unwrap optional values
- Use `OpenStudio::Point3dVector.new` and `<<` for vertex arrays

---

## Common Patterns Across Domains

### Creating Objects

**Pattern:**
```python
# Python
definition = openstudio.model.ObjectDefinition(model)
definition.setProperty(value)

instance = openstudio.model.Object(definition)
instance.setSchedule(schedule)
instance.setSpace(space)  # or setSpaceType(space_type)
```

```ruby
# Ruby
definition = OpenStudio::Model::ObjectDefinition.new(model)
definition.setProperty(value)

instance = OpenStudio::Model::Object.new(definition)
instance.setSchedule(schedule)
instance.setSpace(space)
```

---

### Querying Collections

**Python:**
```python
# Get all objects of a type
objects = model.getObjectType()  # Returns array

# Iterate
for obj in objects:
    print(obj.name().get())

# Get by name
obj = model.getObjectTypeByName("Name").get()
```

**Ruby:**
```ruby
# Get all objects
objects = model.getObjectType  # Returns array

# Iterate
objects.each do |obj|
  puts obj.name.get
end

# Get by name
obj = model.getObjectTypeByName("Name").get
```

---

### Optional Values

**Python:**
```python
# Check if optional value exists
if obj.propertyName().is_initialized():
    value = obj.propertyName().get()
else:
    print("Property not set")
```

**Ruby:**
```ruby
# Check if optional value exists
if obj.propertyName.is_initialized
  value = obj.propertyName.get
else
  puts "Property not set"
end
```

---

## Unit Conventions

### SI Units (Used in OpenStudio)

| Property | Unit |
|----------|------|
| Length | meters (m) |
| Area | square meters (m²) |
| Volume | cubic meters (m³) |
| Temperature | Celsius (°C) |
| Power | Watts (W) |
| Energy | Joules (J) or Watt-hours (Wh) |
| Thermal conductivity | W/m-K |
| Thermal resistance | m²-K/W |
| U-factor | W/m²-K |
| Density | kg/m³ |
| Specific heat | J/kg-K |
| Airflow | m³/s or L/s |
| Pressure | Pascals (Pa) |

### Common Conversions

**Temperature:**
- °F = (°C × 1.8) + 32
- °C = (°F - 32) / 1.8

**R-value:**
- R(SI) = R(IP) / 5.678
- R(IP) = R(SI) × 5.678

**U-factor:**
- U(SI) = U(IP) / 0.176
- U(IP) = U(SI) × 0.176

**Airflow:**
- 1 CFM = 0.000472 m³/s = 0.472 L/s
- 1 L/s = 2.12 CFM

**Power density:**
- 1 W/ft² = 10.764 W/m²
- 1 W/m² = 0.0929 W/ft²

---

## Related Documentation

**Patterns and examples:**
- `/docs/openstudio-sdk/geometry-patterns.md` - Complete geometry examples
- `/docs/openstudio-sdk/hvac-patterns.md` - Complete HVAC system examples

**Quick reference:**
- `/docs/quick-reference/python-cheatsheet.md` - Top 20 Python operations
- `/docs/quick-reference/ruby-cheatsheet.md` - Top 20 Ruby operations

**NECB-specific:**
- `/docs/necb/necb-guide.md` - NECB geometry creation and space types

**Error solutions:**
- `/docs/error-solutions/openstudio-errors.md` - Common OpenStudio SDK errors

---

## Index by OpenStudio Class

| Class | Reference File | Section |
|-------|---------------|---------|
| `AirGap` | materials-constructions.md | § 3 |
| `Construction` | materials-constructions.md | § 5 |
| `DefaultConstructionSet` | materials-constructions.md | § 6 |
| `DesignDay` | simulation-settings.md | § 9 |
| `DesignSpecificationOutdoorAir` | loads-internal-gains.md | § 6 |
| `ElectricEquipment` | loads-internal-gains.md | § 3 |
| `GasEquipment` | loads-internal-gains.md | § 4 |
| `Lights` | loads-internal-gains.md | § 2 |
| `Material` | materials-constructions.md | § 1-4 |
| `OutputMeter` | simulation-settings.md | § 7 |
| `OutputVariable` | simulation-settings.md | § 7 |
| `People` | loads-internal-gains.md | § 1 |
| `Point3d` | surfaces-geometry.md | § 1 |
| `RunPeriod` | simulation-settings.md | § 1 |
| `Schedule` | schedules.md | § 2-4 |
| `ScheduleConstant` | schedules.md | § 2 |
| `ScheduleRuleset` | schedules.md | § 4 |
| `ShadingSurface` | surfaces-geometry.md | § 4 |
| `SimulationControl` | simulation-settings.md | § 3 |
| `Space` | surfaces-geometry.md | § 2 |
| `SpaceInfiltrationDesignFlowRate` | loads-internal-gains.md | § 5 |
| `SpaceType` | loads-internal-gains.md | § 7 |
| `StandardGlazing` | materials-constructions.md | § 4 |
| `StandardOpaqueMaterial` | materials-constructions.md | § 1 |
| `SubSurface` | surfaces-geometry.md | § 3 |
| `Surface` | surfaces-geometry.md | § 2 |
| `ThermalZone` | thermal-zones.md | § 1 |
| `ThermostatSetpointDualSetpoint` | thermal-zones.md | § 2 |
| `Timestep` | simulation-settings.md | § 2 |
| `WeatherFile` | simulation-settings.md | § 8 |
| `ZoneHVAC*` | thermal-zones.md | § 3-4 |

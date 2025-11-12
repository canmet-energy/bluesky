# NECB (National Energy Code of Canada for Buildings) Guide

**Purpose:** Create NECB-compliant building models using openstudio-standards geometry creation methods and NECB space type assignment.

**Repository:** https://github.com/NREL/openstudio-standards.git (tag: v0.8.4)

**When to use:** Canadian building energy code compliance, NECB baseline modeling, Canadian climate zones.

---

## NECB Versions

| Version | Year | Status | Use For |
|---------|------|--------|---------|
| NECB2011 | 2011 | Legacy | Historical baselines |
| NECB2015 | 2015 | Active | Current compliance in some provinces |
| NECB2017 | 2017 | Active | Common baseline |
| NECB2020 | 2020 | Current | Latest code, best practice |

---

## 1. Geometry Creation Methods

**Source:** `openstudio-standards/lib/openstudio-standards/geometry/create_shape.rb`

### Method Overview

| Method | Purpose | Complexity |
|--------|---------|------------|
| `create_shape_rectangle` | Simple rectangular footprint | Low |
| `create_shape_courtyard` | Rectangular with interior courtyard | Medium |
| `create_shape_l` | L-shaped footprint | Medium |
| `create_shape_t` | T-shaped footprint | Medium |
| `create_shape_u` | U-shaped footprint | Medium |
| `create_shape_h` | H-shaped footprint (two bars + connector) | High |
| `create_shape_bar` | Single bar with core/perimeter zones | Medium |

---

### create_shape_rectangle

**Purpose:** Create simple rectangular building with perimeter/core zoning

**Arguments:**
```ruby
model                     # OpenStudio Model object
length                    # Building length (m)
width                     # Building width (m)
num_floors                # Number of floors
floor_to_floor_height     # Floor-to-floor height (m)
plenum_height             # Plenum height (m), 0 for no plenum
perimeter_zone_depth      # Perimeter zone depth (m)
```

**Example:**
```ruby
require 'openstudio-standards'

model = OpenStudio::Model::Model.new

# Create 50m × 30m, 3-story office building
OpenstudioStandards::Geometry.create_shape_rectangle(
  model,
  50.0,                    # length (m)
  30.0,                    # width (m)
  3,                       # num_floors
  3.8,                     # floor_to_floor_height (m)
  0.6,                     # plenum_height (m)
  4.5                      # perimeter_zone_depth (m)
)

# Result: 3 floors × (4 perimeter zones + 1 core zone) = 15 thermal zones
# Plus 3 plenum spaces above each floor
```

**Zoning Pattern:**
```
Floor plan view:
┌─────────────────────────────────────┐
│  North Perimeter (4.5m deep)        │
├──────┬────────────────────┬─────────┤
│ West │                    │  East   │
│ Peri │   Core Zone        │  Peri   │
│ meter│                    │  meter  │
├──────┴────────────────────┴─────────┤
│  South Perimeter (4.5m deep)        │
└─────────────────────────────────────┘
```

---

### create_shape_courtyard

**Purpose:** Rectangular building with interior courtyard (atrium/open space)

**Arguments:**
```ruby
model
length                    # Overall building length (m)
width                     # Overall building width (m)
courtyard_length          # Courtyard length (m)
courtyard_width           # Courtyard width (m)
num_floors
floor_to_floor_height
plenum_height
perimeter_zone_depth
```

**Example:**
```ruby
# Create 80m × 60m building with 20m × 15m courtyard
OpenstudioStandards::Geometry.create_shape_courtyard(
  model,
  80.0,                    # building length
  60.0,                    # building width
  20.0,                    # courtyard length
  15.0,                    # courtyard width
  4,                       # num_floors
  4.0,                     # floor_to_floor_height
  0.5,                     # plenum_height
  4.5                      # perimeter_zone_depth
)

# Result: 4 floors with zones around courtyard perimeter
# Courtyard provides daylighting to interior zones
```

**Zoning Pattern:**
```
Floor plan view:
┌───────────────────────────────────────┐
│  North Perimeter                      │
├────┬──────────────────────┬───────────┤
│West│ ┌──────────────────┐ │ East Peri │
│Peri│ │   Courtyard      │ │           │
│    │ │   (open to sky)  │ │           │
│    │ └──────────────────┘ │           │
├────┴──────────────────────┴───────────┤
│  South Perimeter                      │
└───────────────────────────────────────┘
```

---

### create_shape_l

**Purpose:** L-shaped building footprint

**Arguments:**
```ruby
model
length                    # Length of horizontal bar (m)
width                     # Width of horizontal bar (m)
lower_end_length          # Length of vertical bar (m)
lower_end_width           # Width of vertical bar (m)
num_floors
floor_to_floor_height
plenum_height
perimeter_zone_depth
```

**Example:**
```ruby
# Create L-shaped building: 40m × 20m bar + 30m × 15m bar
OpenstudioStandards::Geometry.create_shape_l(
  model,
  40.0,                    # horizontal bar length
  20.0,                    # horizontal bar width
  30.0,                    # vertical bar length
  15.0,                    # vertical bar width
  2,                       # num_floors
  3.5,                     # floor_to_floor_height
  0.6,                     # plenum_height
  4.5                      # perimeter_zone_depth
)

# Result: L-shaped footprint with perimeter zones on exterior
```

**Footprint:**
```
┌────────────────────────────┐
│  Horizontal Bar (40m×20m)  │
│                            │
└─────┬──────────────────────┘
      │ Vertical Bar
      │ (30m × 15m)
      │
      │
      └──────────┘
```

---

### create_shape_bar

**Purpose:** Single rectangular bar with simplified core/perimeter zoning

**Arguments:**
```ruby
model
length
width
num_floors
floor_to_floor_height
plenum_height
perimeter_zone_depth
party_wall_stories_north  # Number of stories with party wall (0 = no party wall)
party_wall_stories_south
party_wall_stories_east
party_wall_stories_west
```

**Example:**
```ruby
# Create bar building with party wall on north side (row house, attached building)
OpenstudioStandards::Geometry.create_shape_bar(
  model,
  60.0,                    # length
  15.0,                    # width
  3,                       # num_floors
  3.5,                     # floor_to_floor_height
  0.5,                     # plenum_height
  4.5,                     # perimeter_zone_depth
  3,                       # party_wall_stories_north (all 3 floors)
  0,                       # party_wall_stories_south (none)
  0,                       # party_wall_stories_east (none)
  0                        # party_wall_stories_west (none)
)

# Result: Bar building with north wall as adiabatic (party wall)
# Useful for attached buildings, row houses, multi-unit residential
```

**Party Wall Use Cases:**
- Row houses / townhomes
- Multi-unit residential buildings
- Retail strip malls
- Office buildings with shared walls

---

## 2. NECB Space Types

**Source:** `openstudio-standards` library includes NECB space type definitions

### NECB Building Types

| Building Type | NECB Code | Typical Use |
|--------------|-----------|-------------|
| Office | `Office` | Commercial office buildings |
| Retail | `Retail` | Retail stores, shopping centers |
| School | `School` | Primary and secondary schools |
| Assembly | `Assembly` | Theaters, auditoriums, places of worship |
| Warehouse | `Warehouse` | Storage, distribution centers |
| Food Service | `Food Service` | Restaurants, cafeterias |
| Health Care | `Health Care` | Clinics, medical offices |
| Residential | `Residential` | Multi-unit residential buildings |
| Hotel/Motel | `Hotel/Motel` | Hotels, motels, dormitories |

### NECB Space Type Categories

**Office Space Types:**
- `Office - Open Office`
- `Office - Enclosed Office`
- `Office - Lobby`
- `Office - Conference Room`
- `Office - Washroom`
- `Office - Corridor`
- `Office - Stair`
- `Office - Storage`
- `Office - Mechanical/Electrical Room`

**Retail Space Types:**
- `Retail - Sales Area`
- `Retail - Mall Concourse`
- `Retail - Storage`
- `Retail - Washroom`
- `Retail - Office`

**School Space Types:**
- `School - Classroom`
- `School - Corridor`
- `School - Gymnasium`
- `School - Library`
- `School - Cafeteria`
- `School - Office`
- `School - Washroom`
- `School - Mechanical`

---

### Assigning NECB Space Types

**Method 1: Create Space Type and Assign to Space**

```ruby
require 'openstudio-standards'

# Load NECB standards
standard = Standard.build('NECB2020')

# Create model and geometry
model = OpenStudio::Model::Model.new
OpenstudioStandards::Geometry.create_shape_rectangle(
  model, 40.0, 30.0, 3, 3.8, 0.6, 4.5
)

# Get spaces from model
spaces = model.getSpaces

# Assign space types based on location
spaces.each do |space|
  space_name = space.name.get.to_s

  if space_name.include?('Core')
    # Assign open office to core zones
    space_type = standard.model_add_space_type(
      model,
      'NECB2020',
      'Office',
      'Office - Open Office'
    )
    space.setSpaceType(space_type)

  elsif space_name.include?('Perimeter')
    # Assign enclosed office to perimeter zones
    space_type = standard.model_add_space_type(
      model,
      'NECB2020',
      'Office',
      'Office - Enclosed Office'
    )
    space.setSpaceType(space_type)
  end
end
```

**Method 2: Apply Default NECB Space Types for Building Type**

```ruby
require 'openstudio-standards'

standard = Standard.build('NECB2020')
model = OpenStudio::Model::Model.new

# Create geometry
OpenstudioStandards::Geometry.create_shape_rectangle(
  model, 50.0, 30.0, 2, 3.8, 0.6, 4.5
)

# Apply default NECB office space types
standard.model_apply_prototype_hvac_assumptions(model, 'Office', 'NECB HDD Method')

# This automatically assigns:
# - Core zones → Open Office
# - Perimeter zones → Enclosed Office (or mixed based on building size)
# - Applies NECB lighting, equipment, occupancy densities
# - Applies NECB schedules
```

**Method 3: Manual Space Type Assignment with NECB Loads**

```ruby
require 'openstudio-standards'

standard = Standard.build('NECB2020')
model = OpenStudio::Model::Model.new

# Create space type
space_type = OpenStudio::Model::SpaceType.new(model)
space_type.setName('Office - Open Office - NECB2020')

# Get NECB requirements for this space type
space_type_properties = standard.space_type_get_standards_data(space_type)

# Apply NECB loads
standard.space_type_apply_internal_loads(
  space_type,
  true,  # set_people
  true,  # set_lights
  true,  # set_electric_equipment
  true,  # set_gas_equipment
  true,  # set_ventilation
  true,  # set_infiltration
  true   # set_space_shw
)

# Apply NECB schedules
standard.space_type_apply_internal_load_schedules(
  space_type,
  true,  # set_people
  true,  # set_lights
  true,  # set_electric_equipment
  true,  # set_gas_equipment
  true   # set_ventilation
)

# Assign to spaces
spaces = model.getSpaces
spaces.each do |space|
  space.setSpaceType(space_type)
end
```

---

## 3. NECB Space Type Load Densities

### Office Space Types (NECB2020)

| Space Type | Lighting (W/m²) | Equipment (W/m²) | People (m²/person) | Ventilation (L/s/person) |
|-----------|----------------|-----------------|-------------------|------------------------|
| Open Office | 9.7 | 10.0 | 10.0 | 2.5 |
| Enclosed Office | 11.0 | 10.0 | 15.0 | 2.5 |
| Conference Room | 11.8 | 10.0 | 2.0 | 2.5 |
| Lobby | 6.5 | 1.0 | 10.0 | 2.5 |
| Corridor | 5.4 | 0.0 | - | 0.3 (L/s/m²) |
| Washroom | 9.0 | 0.0 | - | 25.0 (L/s/WC) |
| Storage | 8.1 | 0.0 | - | 0.3 (L/s/m²) |

### Retail Space Types (NECB2020)

| Space Type | Lighting (W/m²) | Equipment (W/m²) | People (m²/person) | Ventilation (L/s/person) |
|-----------|----------------|-----------------|-------------------|------------------------|
| Sales Area | 16.1 | 3.0 | 5.0 | 2.5 |
| Mall Concourse | 10.8 | 0.0 | 10.0 | 2.5 |
| Storage | 8.1 | 0.0 | - | 0.3 (L/s/m²) |

### School Space Types (NECB2020)

| Space Type | Lighting (W/m²) | Equipment (W/m²) | People (m²/person) | Ventilation (L/s/person) |
|-----------|----------------|-----------------|-------------------|------------------------|
| Classroom | 11.7 | 6.5 | 2.0 | 3.0 |
| Corridor | 5.4 | 0.0 | - | 0.3 (L/s/m²) |
| Gymnasium | 10.8 | 0.0 | 5.0 | 7.5 |
| Library | 12.9 | 10.0 | 5.0 | 2.5 |
| Cafeteria | 11.8 | 10.0 | 2.0 | 3.8 |

---

## 4. NECB Construction Sets

### Applying NECB Constructions

```ruby
require 'openstudio-standards'

standard = Standard.build('NECB2020')
model = OpenStudio::Model::Model.new

# Create geometry first
OpenstudioStandards::Geometry.create_shape_rectangle(
  model, 50.0, 30.0, 3, 3.8, 0.6, 4.5
)

# Set climate zone (required for NECB construction selection)
climate_zone = 'NECB HDD Method'  # or specific zone: '6', '7A', etc.

# Apply NECB construction set
standard.model_apply_constructions(model, climate_zone, '')

# This applies:
# - Exterior wall constructions (R-values per NECB Table 3.2.1.3)
# - Roof constructions (R-values per NECB Table 3.2.1.4)
# - Window constructions (U-values, SHGC per NECB Table 3.2.1.6)
# - Door constructions
# - Ground contact constructions
```

### NECB Climate Zones

| Climate Zone | HDD (Heating Degree Days) | Example Cities |
|-------------|---------------------------|----------------|
| 4 | < 3000 | Vancouver, Victoria |
| 5 | 3000-3999 | Toronto, Halifax |
| 6 | 4000-4999 | Ottawa, Montreal, Quebec City |
| 7A | 5000-5999 | Winnipeg, Saskatoon |
| 7B | 6000-6999 | Edmonton, Calgary |
| 8 | ≥ 7000 | Yellowknife, Whitehorse |

### NECB Construction Requirements (NECB2020)

**Exterior Wall R-Values (RSI = m²·K/W):**

| Climate Zone | Effective R-Value (RSI) | R-Value (Imperial) |
|-------------|------------------------|-------------------|
| 4 | 2.61 | R-14.8 |
| 5 | 2.97 | R-16.9 |
| 6 | 3.43 | R-19.5 |
| 7A | 3.60 | R-20.4 |
| 7B | 3.78 | R-21.5 |
| 8 | 3.96 | R-22.5 |

**Roof R-Values (RSI):**

| Climate Zone | Effective R-Value (RSI) | R-Value (Imperial) |
|-------------|------------------------|-------------------|
| 4 | 3.52 | R-20.0 |
| 5 | 3.87 | R-22.0 |
| 6 | 4.40 | R-25.0 |
| 7A | 5.28 | R-30.0 |
| 7B | 5.46 | R-31.0 |
| 8 | 5.64 | R-32.0 |

**Window Requirements (NECB2020):**

| Climate Zone | Max U-Value (W/m²·K) | Max SHGC |
|-------------|---------------------|----------|
| 4 | 2.00 | 0.40 |
| 5 | 1.90 | 0.40 |
| 6 | 1.80 | 0.40 |
| 7A | 1.70 | 0.40 |
| 7B | 1.60 | 0.40 |
| 8 | 1.50 | 0.40 |

---

## 5. NECB HVAC Systems

### Applying NECB HVAC

```ruby
require 'openstudio-standards'

standard = Standard.build('NECB2020')
model = OpenStudio::Model::Model.new

# Create geometry and assign space types
OpenstudioStandards::Geometry.create_shape_rectangle(
  model, 50.0, 30.0, 3, 3.8, 0.6, 4.5
)

# Apply NECB HVAC system based on building type and size
standard.model_add_hvac(
  model,
  'Office',              # building_type
  'NECB HDD Method',     # climate_zone
  'Electricity',         # primary_heating_fuel: Electricity, NaturalGas, or FuelOilNo2
  'NECB_Default'         # system_type: use NECB rules for system selection
)

# NECB automatically selects system based on:
# - Building floor area
# - Building height
# - Climate zone
# - Primary heating fuel
```

### NECB System Selection Rules (NECB2020)

**System 1: PTAC/PTHP (Packaged Terminal Units)**
- **Use when:** Individual zones, small buildings
- **Heating:** Electric resistance or heat pump
- **Cooling:** DX cooling
- **Ventilation:** DOAS or unit ventilation

**System 2: Residential Furnace/AC**
- **Use when:** Residential buildings, low-rise
- **Heating:** Gas furnace or electric baseboard
- **Cooling:** Split AC or none
- **Ventilation:** HRV/ERV

**System 3: PSZ-AC (Packaged Single Zone)**
- **Use when:** Single-story retail, warehouse
- **Heating:** Gas furnace or electric
- **Cooling:** DX cooling
- **Ventilation:** Packaged unit or DOAS

**System 4: VAV with Reheat**
- **Use when:** Multi-story office, large buildings (> 5,000 m²)
- **Heating:** Hot water or electric reheat
- **Cooling:** Chilled water or DX
- **Ventilation:** Central air handler with economizer

**System 5: Boiler + Radiant + DOAS**
- **Use when:** High heating loads, warehouse, industrial
- **Heating:** Hydronic radiant + boiler
- **Cooling:** None or minimal
- **Ventilation:** DOAS

**System 6: Multi-Zone RTU**
- **Use when:** Retail, schools, small commercial
- **Heating:** Gas or electric
- **Cooling:** DX cooling
- **Ventilation:** Economizer + DOAS

### NECB HVAC Efficiency Requirements (NECB2020)

**Gas Furnaces:**
- Combustion efficiency: ≥ 90% (condensing)

**Boilers:**
- < 733 kW: ≥ 90% combustion efficiency
- ≥ 733 kW: ≥ 85% combustion efficiency

**Air-Cooled Chillers:**
- < 528 kW: COP ≥ 2.8 (EER ≥ 9.5)
- ≥ 528 kW: COP ≥ 2.9 (EER ≥ 9.9)

**Water-Cooled Chillers:**
- COP ≥ 5.0 (kW/ton ≤ 0.70)

**Unitary AC (< 19 kW):**
- SEER ≥ 14

**Heat Pumps (Air Source):**
- Heating COP ≥ 2.0 (at 8.3°C outdoor)
- Cooling EER ≥ 11.0

---

## 6. Complete NECB Workflow Examples

### Example 1: NECB2020 Office Building from Scratch

```ruby
require 'openstudio-standards'

# Initialize
standard = Standard.build('NECB2020')
model = OpenStudio::Model::Model.new

# Step 1: Set building properties
building = model.getBuilding
building.setName('NECB2020 Office Example')

# Set climate (Montreal, Zone 6)
climate_zone = 'NECB HDD Method'
weather_file = 'CAN_QC_Montreal-Trudeau.Intl.AP.716270_CWEC2016.epw'

# Step 2: Create geometry (50m × 30m, 4 floors)
OpenstudioStandards::Geometry.create_shape_rectangle(
  model,
  50.0,                    # length (m)
  30.0,                    # width (m)
  4,                       # num_floors
  3.8,                     # floor_to_floor_height (m)
  0.6,                     # plenum_height (m)
  4.5                      # perimeter_zone_depth (m)
)

# Result: 4 floors × 5 zones (4 perimeter + 1 core) = 20 thermal zones

# Step 3: Assign NECB office space types
spaces = model.getSpaces
spaces.each do |space|
  space_name = space.name.get.to_s

  # Assign space type based on zone location
  if space_name.include?('Core')
    space_type = standard.model_add_space_type(
      model, 'NECB2020', 'Office', 'Office - Open Office'
    )
  elsif space_name.include?('Perimeter')
    space_type = standard.model_add_space_type(
      model, 'NECB2020', 'Office', 'Office - Enclosed Office'
    )
  end

  space.setSpaceType(space_type) if space_type
end

# Step 4: Apply NECB construction set
standard.model_apply_constructions(model, climate_zone, '')

# Step 5: Add NECB-compliant HVAC
standard.model_add_hvac(
  model,
  'Office',              # building_type
  climate_zone,
  'NaturalGas',          # primary_heating_fuel
  'NECB_Default'         # auto-select system type
)

# Step 6: Apply NECB schedules and loads
# (already applied with space types in Step 3)

# Step 7: Add service hot water
standard.model_add_swh(
  model,
  'Office',              # building_type
  climate_zone,
  'NaturalGas'           # swh_fuel_type
)

# Step 8: Add exterior lights
standard.model_add_exterior_lights(
  model,
  'Office',              # building_type
  climate_zone,
  ''                     # exterior_lighting_zone
)

# Step 9: Set weather file
epw_file = OpenStudio::EpwFile.new(weather_file)
OpenStudio::Model::WeatherFile.setWeatherFile(model, epw_file)

# Step 10: Save model
model.save('necb2020_office.osm', true)

puts "NECB2020 office building created:"
puts "  Floor area: #{building.floorArea.round(0)} m²"
puts "  Thermal zones: #{model.getThermalZones.size}"
puts "  Space types assigned: #{model.getSpaceTypes.size}"
```

---

### Example 2: NECB L-Shaped Retail Building

```ruby
require 'openstudio-standards'

standard = Standard.build('NECB2020')
model = OpenStudio::Model::Model.new

building = model.getBuilding
building.setName('NECB2020 Retail L-Shape')

# Create L-shaped geometry
OpenstudioStandards::Geometry.create_shape_l(
  model,
  60.0,                    # horizontal bar length
  25.0,                    # horizontal bar width
  40.0,                    # vertical bar length
  20.0,                    # vertical bar width
  1,                       # num_floors (single story retail)
  4.5,                     # floor_to_floor_height (higher ceilings)
  0.0,                     # plenum_height (no plenum)
  6.0                      # perimeter_zone_depth (deeper for retail)
)

# Assign retail space types
spaces = model.getSpaces
spaces.each do |space|
  space_name = space.name.get.to_s

  if space_name.include?('Core')
    # Core = sales area
    space_type = standard.model_add_space_type(
      model, 'NECB2020', 'Retail', 'Retail - Sales Area'
    )
  elsif space_name.include?('Perimeter')
    # Perimeter = also sales area for retail
    space_type = standard.model_add_space_type(
      model, 'NECB2020', 'Retail', 'Retail - Sales Area'
    )
  end

  space.setSpaceType(space_type) if space_type
end

# Apply NECB constructions (Vancouver, Zone 4)
standard.model_apply_constructions(model, 'NECB HDD Method', '')

# Add HVAC (electric heat pump for mild climate)
standard.model_add_hvac(
  model,
  'Retail',
  'NECB HDD Method',
  'Electricity',         # heat pump
  'NECB_Default'
)

# Save
model.save('necb2020_retail_l_shape.osm', true)
```

---

### Example 3: NECB School with Courtyard

```ruby
require 'openstudio-standards'

standard = Standard.build('NECB2020')
model = OpenStudio::Model::Model.new

building = model.getBuilding
building.setName('NECB2020 School with Courtyard')

# Create courtyard geometry (for daylighting)
OpenstudioStandards::Geometry.create_shape_courtyard(
  model,
  100.0,                   # building length
  80.0,                    # building width
  30.0,                    # courtyard length
  25.0,                    # courtyard width
  2,                       # num_floors
  4.0,                     # floor_to_floor_height
  0.5,                     # plenum_height
  6.0                      # perimeter_zone_depth
)

# Assign school space types
# In real scenario, you'd assign different space types to different spaces
# (classrooms, corridors, gym, cafeteria, etc.)
# This example assigns classrooms to all spaces
spaces = model.getSpaces
classroom_space_type = standard.model_add_space_type(
  model, 'NECB2020', 'School', 'School - Classroom'
)

spaces.each do |space|
  space.setSpaceType(classroom_space_type)
end

# Apply NECB constructions (Calgary, Zone 7B)
standard.model_apply_constructions(model, 'NECB HDD Method', '')

# Add HVAC (natural gas heating)
standard.model_add_hvac(
  model,
  'School',
  'NECB HDD Method',
  'NaturalGas',
  'NECB_Default'
)

# Add service hot water
standard.model_add_swh(model, 'School', 'NECB HDD Method', 'NaturalGas')

# Save
model.save('necb2020_school_courtyard.osm', true)
```

---

### Example 4: Mixed-Use Building (Office + Retail)

```ruby
require 'openstudio-standards'

standard = Standard.build('NECB2020')
model = OpenStudio::Model::Model.new

# Create 3-story building: retail on ground floor, office on floors 2-3
OpenstudioStandards::Geometry.create_shape_rectangle(
  model, 50.0, 30.0, 3, 3.8, 0.6, 4.5
)

# Assign space types by floor
spaces = model.getSpaces.sort_by { |s| s.name.get.to_s }

# Create space types
retail_space_type = standard.model_add_space_type(
  model, 'NECB2020', 'Retail', 'Retail - Sales Area'
)
office_open_space_type = standard.model_add_space_type(
  model, 'NECB2020', 'Office', 'Office - Open Office'
)
office_enclosed_space_type = standard.model_add_space_type(
  model, 'NECB2020', 'Office', 'Office - Enclosed Office'
)

spaces.each do |space|
  space_name = space.name.get.to_s

  if space_name.include?('Floor 1')
    # Ground floor = retail
    space.setSpaceType(retail_space_type)

  elsif space_name.include?('Floor 2') || space_name.include?('Floor 3')
    # Upper floors = office
    if space_name.include?('Core')
      space.setSpaceType(office_open_space_type)
    else
      space.setSpaceType(office_enclosed_space_type)
    end
  end
end

# Apply NECB constructions
standard.model_apply_constructions(model, 'NECB HDD Method', '')

# Add HVAC (will create appropriate systems for mixed-use)
standard.model_add_hvac(
  model,
  'Office',              # primary building type
  'NECB HDD Method',
  'NaturalGas',
  'NECB_Default'
)

# Save
model.save('necb2020_mixed_use.osm', true)
```

---

## 7. NECB Compliance Checks

### Energy Performance Compliance

```ruby
require 'openstudio-standards'

standard = Standard.build('NECB2020')

# After simulation, check compliance
sql_path = 'run/eplusout.sql'
sql = OpenStudio::SqlFile.new(sql_path)

if sql.connectionOpen
  model.setSqlFile(sql)

  # Get total site energy
  total_site_energy = sql.totalSiteEnergy.get  # J
  floor_area = model.getBuilding.floorArea.get # m²

  # Calculate EUI
  eui = (total_site_energy / floor_area / 1000.0).round(1)  # kWh/m²

  puts "NECB Performance:"
  puts "  Total Site Energy: #{(total_site_energy / 3.6e9).round(0)} GJ"
  puts "  Floor Area: #{floor_area.round(0)} m²"
  puts "  EUI: #{eui} kWh/m²"

  # NECB doesn't prescribe specific EUI targets (performance path allows trade-offs)
  # Compliance is typically via prescriptive requirements or energy cost comparison

  sql.close
end
```

### Unmet Hours Check (NECB Requirements)

```ruby
# NECB requires unmet hours < 300 hours per year

# Get unmet hours from SQL
if sql.connectionOpen
  # Heating unmet hours
  heating_unmet = sql.hoursHeatingSetpointNotMet
  if heating_unmet.is_initialized
    heating_unmet_hours = heating_unmet.get
  else
    heating_unmet_hours = 0
  end

  # Cooling unmet hours
  cooling_unmet = sql.hoursCoolingSetpointNotMet
  if cooling_unmet.is_initialized
    cooling_unmet_hours = cooling_unmet.get
  else
    cooling_unmet_hours = 0
  end

  total_unmet = heating_unmet_hours + cooling_unmet_hours

  puts "\nNECB Unmet Hours Check:"
  puts "  Heating unmet: #{heating_unmet_hours.round(0)} hours"
  puts "  Cooling unmet: #{cooling_unmet_hours.round(0)} hours"
  puts "  Total unmet: #{total_unmet.round(0)} hours"
  puts "  NECB limit: 300 hours"

  if total_unmet <= 300
    puts "  ✓ PASSES NECB unmet hours requirement"
  else
    puts "  ✗ FAILS NECB unmet hours requirement"
  end
end
```

---

## Quick Reference

### Most Common NECB Workflows

| Task | Method/Code |
|------|------------|
| Create rectangular building | `OpenstudioStandards::Geometry.create_shape_rectangle` |
| Create L-shaped building | `OpenstudioStandards::Geometry.create_shape_l` |
| Create courtyard building | `OpenstudioStandards::Geometry.create_shape_courtyard` |
| Assign NECB space type | `standard.model_add_space_type(model, 'NECB2020', building_type, space_type)` |
| Apply NECB constructions | `standard.model_apply_constructions(model, climate_zone, '')` |
| Add NECB HVAC | `standard.model_add_hvac(model, building_type, climate_zone, fuel, 'NECB_Default')` |
| Add service hot water | `standard.model_add_swh(model, building_type, climate_zone, fuel)` |

### NECB Building Type Codes

| Code | Building Type |
|------|--------------|
| `Office` | Office buildings |
| `Retail` | Retail stores |
| `School` | Educational facilities |
| `Assembly` | Theaters, auditoriums |
| `Warehouse` | Storage, distribution |
| `Food Service` | Restaurants, cafeterias |
| `Health Care` | Medical facilities |
| `Residential` | Multi-unit residential |
| `Hotel/Motel` | Hotels, motels |

### Canadian Climate Zones

| Zone | HDD Range | Example Cities |
|------|-----------|----------------|
| 4 | < 3000 | Vancouver, Victoria |
| 5 | 3000-3999 | Toronto, Halifax |
| 6 | 4000-4999 | Ottawa, Montreal, Quebec City |
| 7A | 5000-5999 | Winnipeg, Saskatoon |
| 7B | 6000-6999 | Edmonton, Calgary |
| 8 | ≥ 7000 | Yellowknife, Whitehorse |

### NECB Primary Heating Fuel Options

| Fuel Type | Code | Common Use |
|-----------|------|------------|
| Natural Gas | `NaturalGas` | Most common in urban areas |
| Electricity | `Electricity` | BC, Quebec (hydro), heat pumps |
| Fuel Oil #2 | `FuelOilNo2` | Remote areas, backup |
| Propane | `PropaneGas` | Rural areas |
| District Heating | `DistrictHeating` | Downtown cores |

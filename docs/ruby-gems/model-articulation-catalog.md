# OpenStudio Model Articulation Measures Catalog

**Purpose:** Collection of 45+ measures for creating prototype buildings, bar geometry, space type assignment, and model articulation.

**Repository:** https://github.com/canmet-energy/openstudio-model-articulation-gem.git (tag: develop)

**When to use:** Generate building models from scratch, create DOE/NECB prototypes, assign space types, modify building geometry.

---

## Categories

1. **Bar Buildings** - Simple parametric box/bar geometry
2. **Prototype Buildings** - DOE commercial reference buildings, NECB archetypes
3. **Space Type Assignment** - Apply templates and space types
4. **Geometry Manipulation** - Slicing, stacking, orientation

---

## 1. Bar Buildings

### CreateBarBuilding
**Purpose:** Create simple rectangular/L-shaped building with parametric inputs
**Arguments:**
- `bldg_type_a` (choice) - Primary building type (Office, Retail, etc.)
- `bldg_type_b` (choice) - Secondary building type (for mixed-use)
- `bldg_type_c` (choice) - Tertiary building type
- `bldg_type_d` (choice) - Quaternary building type
- `total_bldg_floor_area` (double) - Total floor area (m²)
- `ns_to_ew_ratio` (double) - North-south to east-west length ratio
- `num_floors` (int) - Number of floors
- `floor_to_floor_height` (double) - Floor-to-floor height (m)
- `plenum_height` (double) - Plenum height (m), 0 for no plenum
- `perimeter_zone_depth` (double) - Perimeter zone depth (m)
- `wwr` (double) - Window-to-wall ratio (0.0 to 0.95)
- `party_wall_fraction` (double) - Fraction of walls that are party walls
- `party_wall_stories_north` (int) - Stories against party wall (north)
- `party_wall_stories_south` (int)
- `party_wall_stories_east` (int)
- `party_wall_stories_west` (int)
- `bottom_story_ground_exposed_floor` (bool) - Ground contact
- `top_story_exterior_exposed_roof` (bool) - Exposed roof
- `bar_division_method` (choice) - Single Space Type, Multiple Space Types, Building Type Ratios

**Example:**
```ruby
# Create 5,000 m² office building, 3 floors, 40% WWR
measure.setArgument('bldg_type_a', 'Office')
measure.setArgument('total_bldg_floor_area', 5000.0)
measure.setArgument('ns_to_ew_ratio', 1.5)
measure.setArgument('num_floors', 3)
measure.setArgument('floor_to_floor_height', 3.8)
measure.setArgument('plenum_height', 0.6)
measure.setArgument('perimeter_zone_depth', 4.5)
measure.setArgument('wwr', 0.40)
measure.setArgument('bar_division_method', 'Multiple Space Types')
```

### CreateBarFromSpaceTypeRatios
**Purpose:** Create bar building with custom space type mix
**Arguments:**
- `bldg_type_a` (choice) - Building type
- `total_bldg_floor_area` (double) - Total area (m²)
- `num_floors` (int)
- `floor_to_floor_height` (double)
- `space_type_hash_string` (string) - JSON with space type ratios

**Example:**
```ruby
# Mixed-use building: 60% office, 30% retail, 10% storage
space_types = '{
  "Office - OpenOffice": 0.60,
  "Retail - WholeBuilding": 0.30,
  "Warehouse - Storage": 0.10
}'
measure.setArgument('space_type_hash_string', space_types)
measure.setArgument('total_bldg_floor_area', 10000.0)
measure.setArgument('num_floors', 4)
```

### CreateBarFromBuildingTypeRatios
**Purpose:** Create bar building with multiple building types
**Arguments:**
- `bldg_type_a` (choice) - First building type
- `bldg_type_a_fract_bldg_area` (double) - Fraction of area (0.0 to 1.0)
- `bldg_type_b` (choice) - Second building type
- `bldg_type_b_fract_bldg_area` (double)
- `total_bldg_floor_area` (double)
- `num_floors` (int)
- `floor_to_floor_height` (double)

**Example:**
```ruby
# 70% office, 30% retail
measure.setArgument('bldg_type_a', 'Office')
measure.setArgument('bldg_type_a_fract_bldg_area', 0.70)
measure.setArgument('bldg_type_b', 'Retail')
measure.setArgument('bldg_type_b_fract_bldg_area', 0.30)
measure.setArgument('total_bldg_floor_area', 8000.0)
```

---

## 2. Prototype Buildings

### CreateDOEPrototypeBuilding
**Purpose:** Create DOE commercial reference building model
**Arguments:**
- `template` (choice) - 90.1-2004, 90.1-2007, 90.1-2010, 90.1-2013, 90.1-2016, 90.1-2019
- `building_type` (choice) - SmallOffice, MediumOffice, LargeOffice, RetailStandalone, RetailStripmall, PrimarySchool, SecondarySchool, Outpatient, Hospital, SmallHotel, LargeHotel, Warehouse, QuickServiceRestaurant, FullServiceRestaurant, MidriseApartment, HighriseApartment
- `climate_zone` (choice) - ASHRAE 169-2013-1A through 8B
- `add_constructions` (bool) - Add construction set
- `add_space_type_loads` (bool) - Add loads
- `add_hvac` (bool) - Add HVAC systems
- `add_swh` (bool) - Add service hot water
- `add_thermostat` (bool) - Add thermostats

**Example:**
```ruby
# Create ASHRAE 90.1-2019 medium office in climate zone 6A
measure.setArgument('template', '90.1-2019')
measure.setArgument('building_type', 'MediumOffice')
measure.setArgument('climate_zone', 'ASHRAE 169-2013-6A')
measure.setArgument('add_constructions', true)
measure.setArgument('add_space_type_loads', true)
measure.setArgument('add_hvac', true)
measure.setArgument('add_swh', true)
measure.setArgument('add_thermostat', true)
```

### CreateNECBPrototypeBuilding
**Purpose:** Create NECB (National Energy Code of Canada for Buildings) archetype
**Arguments:**
- `template` (choice) - NECB2011, NECB2015, NECB2017, NECB2020
- `building_type` (choice) - FullServiceRestaurant, HighriseApartment, Hospital, LargeHotel, LargeOffice, MediumOffice, MidriseApartment, Outpatient, PrimarySchool, QuickServiceRestaurant, RetailStandalone, RetailStripmall, SecondarySchool, SmallHotel, SmallOffice, Warehouse
- `epw_file` (choice) - Canadian weather file
- `primary_heating_fuel` (choice) - Electricity, NaturalGas, DistrictHeating
- `dcv_type` (choice) - No DCV, DCV, DCV + Economizer

**Example:**
```ruby
# Create NECB 2020 small office in Toronto with natural gas heat
measure.setArgument('template', 'NECB2020')
measure.setArgument('building_type', 'SmallOffice')
measure.setArgument('epw_file', 'CAN_ON_Toronto.716240_CWEC2016.epw')
measure.setArgument('primary_heating_fuel', 'NaturalGas')
measure.setArgument('dcv_type', 'DCV')
```

### CreateTypicalBuildingFromModel
**Purpose:** Create typical building from existing seed model
**Arguments:**
- `template` (choice) - 90.1-2004 through 90.1-2019, NECB2011 through NECB2020
- `add_constructions` (bool)
- `add_space_type_loads` (bool)
- `add_hvac` (bool)
- `add_swh` (bool)
- `remove_objects` (bool) - Remove existing objects before applying

**Example:**
```ruby
# Convert existing model to ASHRAE 90.1-2019 typical building
measure.setArgument('template', '90.1-2019')
measure.setArgument('add_constructions', true)
measure.setArgument('add_space_type_loads', true)
measure.setArgument('add_hvac', true)
measure.setArgument('remove_objects', true)
```

---

## 3. Space Type Assignment

### BlendedSpaceTypeFromModel
**Purpose:** Create weighted average space type from entire model
**Arguments:**
- `blend_method` (choice) - FloorArea, ExteriorArea, ExteriorWallArea, Volume

**Example:**
```ruby
# Create blended space type weighted by floor area
measure.setArgument('blend_method', 'FloorArea')
```

### SpaceTypeAndConstructionSetWizard
**Purpose:** Interactive wizard to assign space types and construction sets
**Arguments:**
- `set_runperiod` (bool) - Set run period to annual
- `template` (choice) - 90.1-2004 through 90.1-2019, NECB2011 through NECB2020
- `climate_zone` (choice) - ASHRAE climate zone

**Example:**
```ruby
measure.setArgument('template', 'NECB2017')
measure.setArgument('climate_zone', 'ASHRAE 169-2013-7A')
measure.setArgument('set_runperiod', true)
```

### AssignSpaceTypeToBuilding
**Purpose:** Assign single space type to entire building
**Arguments:**
- `space_type_name` (choice) - Space type from model

**Example:**
```ruby
measure.setArgument('space_type_name', 'Office - OpenOffice')
```

### CreateTypicalDOEBuildingSpaceTypes
**Purpose:** Add DOE space types to model without geometry
**Arguments:**
- `template` (choice) - DOE template
- `building_type` (choice) - DOE building type

**Example:**
```ruby
# Add small office space types to model
measure.setArgument('template', '90.1-2019')
measure.setArgument('building_type', 'SmallOffice')
```

### CreateNECBSpaceTypes
**Purpose:** Add NECB space types to model
**Arguments:**
- `template` (choice) - NECB2011 through NECB2020
- `building_type` (choice) - NECB building type

**Example:**
```ruby
measure.setArgument('template', 'NECB2020')
measure.setArgument('building_type', 'MediumOffice')
```

---

## 4. Geometry Manipulation

### RadianceForwardTranslator
**Purpose:** Translate OpenStudio model to Radiance format for daylighting
**Arguments:** (auto-configures from model)

**Example:**
```ruby
# Translates geometry, materials, and windows for Radiance simulation
```

### AddOverhangsByProjectionFactor
**Purpose:** Add overhangs to windows based on projection factor
**Arguments:**
- `projection_factor` (double) - Overhang depth / window height ratio
- `facade` (choice) - North, South, East, West, All

**Example:**
```ruby
# Add overhangs to south windows (0.5 = half window height)
measure.setArgument('projection_factor', 0.5)
measure.setArgument('facade', 'South')
```

### AddRooftopPV
**Purpose:** Add simple PV system on roof
**Arguments:**
- `fraction_of_surface` (double) - Roof fraction covered (0.0 to 1.0)
- `cell_efficiency` (double) - PV cell efficiency
- `inverter_efficiency` (double) - Inverter efficiency

**Example:**
```ruby
measure.setArgument('fraction_of_surface', 0.75)
measure.setArgument('cell_efficiency', 0.19)
measure.setArgument('inverter_efficiency', 0.96)
```

### CreateGeometryFromFloorprint
**Purpose:** Create 3D geometry from 2D floor plan
**Arguments:**
- `floorprint_path` (string) - Path to floor plan file (gbXML, IDF, etc.)
- `num_floors` (int)
- `floor_to_floor_height` (double)

**Example:**
```ruby
measure.setArgument('floorprint_path', 'floorplan.gbxml')
measure.setArgument('num_floors', 5)
measure.setArgument('floor_to_floor_height', 3.5)
```

### SetWindowToWallRatioByFacade
**Purpose:** Set WWR independently for each facade
**Arguments:**
- `wwr_north` (double) - North WWR (0.0 to 0.95)
- `wwr_south` (double)
- `wwr_east` (double)
- `wwr_west` (double)
- `wwr_roofs` (double) - Skylight fraction

**Example:**
```ruby
# Passive solar design: high south, low north
measure.setArgument('wwr_north', 0.20)
measure.setArgument('wwr_south', 0.50)
measure.setArgument('wwr_east', 0.30)
measure.setArgument('wwr_west', 0.30)
measure.setArgument('wwr_roofs', 0.03)
```

### SurfaceMatching
**Purpose:** Automatically match interior surfaces between spaces
**Arguments:**
- `intersect_surfaces` (bool) - Intersect overlapping surfaces

**Example:**
```ruby
measure.setArgument('intersect_surfaces', true)
```

### BarAspectRatioStudy
**Purpose:** Parametric study of bar building aspect ratios
**Arguments:**
- `aspect_ratio_start` (double) - Starting N-S/E-W ratio
- `aspect_ratio_end` (double) - Ending ratio
- `aspect_ratio_step` (double) - Step size

**Example:**
```ruby
# Test aspect ratios from 0.5 to 2.0
measure.setArgument('aspect_ratio_start', 0.5)
measure.setArgument('aspect_ratio_end', 2.0)
measure.setArgument('aspect_ratio_step', 0.25)
```

### BarOrientationStudy
**Purpose:** Parametric study of building orientation
**Arguments:**
- `rotation_start` (double) - Starting rotation (degrees)
- `rotation_end` (double) - Ending rotation
- `rotation_step` (double) - Step size

**Example:**
```ruby
# Test orientations from 0° to 270° in 45° steps
measure.setArgument('rotation_start', 0.0)
measure.setArgument('rotation_end', 270.0)
measure.setArgument('rotation_step', 45.0)
```

### BarWindowToWallRatioStudy
**Purpose:** Parametric study of window-to-wall ratios
**Arguments:**
- `wwr_start` (double) - Starting WWR
- `wwr_end` (double) - Ending WWR
- `wwr_step` (double) - Step size

**Example:**
```ruby
# Test WWR from 20% to 60% in 10% steps
measure.setArgument('wwr_start', 0.20)
measure.setArgument('wwr_end', 0.60)
measure.setArgument('wwr_step', 0.10)
```

### AddDaylightingControls
**Purpose:** Add daylighting sensors to spaces
**Arguments:**
- `space_names` (choice) - Spaces to add sensors (or "*" for all)
- `sensor_1_frac` (double) - Fraction of lights controlled by sensor 1
- `sensor_2_frac` (double) - Fraction of lights controlled by sensor 2
- `height` (double) - Sensor height above floor (m)
- `setpoint` (double) - Illuminance setpoint (lux)

**Example:**
```ruby
measure.setArgument('space_names', '*')
measure.setArgument('sensor_1_frac', 0.5)
measure.setArgument('sensor_2_frac', 0.5)
measure.setArgument('height', 0.762)  # 30 inches
measure.setArgument('setpoint', 300.0)
```

### AddOutputDiagnostics
**Purpose:** Add EnergyPlus diagnostic output
**Arguments:**
- `diagnostics` (choice) - DisplayExtraWarnings, DisplayAdvancedReportVariables, etc.

**Example:**
```ruby
measure.setArgument('diagnostics', 'DisplayExtraWarnings')
```

### SetNECBConstructionSet
**Purpose:** Apply NECB construction set to building
**Arguments:**
- `template` (choice) - NECB2011 through NECB2020
- `climate_zone` (choice) - Canadian climate zones 4-8

**Example:**
```ruby
measure.setArgument('template', 'NECB2017')
measure.setArgument('climate_zone', '6')
```

### ReplaceModel
**Purpose:** Replace current model with another model file
**Arguments:**
- `model_path` (string) - Path to replacement OSM file

**Example:**
```ruby
measure.setArgument('model_path', 'baseline_model.osm')
```

### ShadowCalculation
**Purpose:** Configure shadow calculation settings
**Arguments:**
- `calculation_method` (choice) - AverageOverDaysInFrequency, TimestepFrequency
- `calculation_frequency` (int) - Days between calculations
- `maximum_figures` (int) - Max figures in shadow overlap calculations

**Example:**
```ruby
measure.setArgument('calculation_method', 'TimestepFrequency')
measure.setArgument('calculation_frequency', 20)
measure.setArgument('maximum_figures', 15000)
```

---

## 5. Complete Workflow Examples

### Example 1: Create DOE Prototype + Modify WWR

```ruby
# Step 1: Create DOE prototype
create_prototype = CreateDOEPrototypeBuilding.new
create_prototype.setArgument('template', '90.1-2019')
create_prototype.setArgument('building_type', 'MediumOffice')
create_prototype.setArgument('climate_zone', 'ASHRAE 169-2013-5A')
create_prototype.setArgument('add_constructions', true)
create_prototype.setArgument('add_hvac', true)

# Step 2: Modify WWR for passive solar
set_wwr = SetWindowToWallRatioByFacade.new
set_wwr.setArgument('wwr_north', 0.25)
set_wwr.setArgument('wwr_south', 0.45)
set_wwr.setArgument('wwr_east', 0.30)
set_wwr.setArgument('wwr_west', 0.30)

# Step 3: Add daylighting controls
add_daylight = AddDaylightingControls.new
add_daylight.setArgument('space_names', '*')
add_daylight.setArgument('setpoint', 300.0)
```

### Example 2: Create Custom Bar Building with NECB Standards

```ruby
# Step 1: Create bar geometry
create_bar = CreateBarBuilding.new
create_bar.setArgument('bldg_type_a', 'Office')
create_bar.setArgument('total_bldg_floor_area', 3500.0)
create_bar.setArgument('ns_to_ew_ratio', 1.8)
create_bar.setArgument('num_floors', 2)
create_bar.setArgument('floor_to_floor_height', 4.0)
create_bar.setArgument('wwr', 0.35)
create_bar.setArgument('bar_division_method', 'Multiple Space Types')

# Step 2: Apply NECB standards
apply_necb = CreateTypicalBuildingFromModel.new
apply_necb.setArgument('template', 'NECB2020')
apply_necb.setArgument('add_constructions', true)
apply_necb.setArgument('add_space_type_loads', true)
apply_necb.setArgument('add_hvac', true)

# Step 3: Match surfaces
surface_match = SurfaceMatching.new
surface_match.setArgument('intersect_surfaces', true)

# Step 4: Add rooftop PV
add_pv = AddRooftopPV.new
add_pv.setArgument('fraction_of_surface', 0.60)
add_pv.setArgument('cell_efficiency', 0.19)
```

### Example 3: Parametric Study - Orientation + WWR

```ruby
# Create base bar building
create_bar = CreateBarBuilding.new
create_bar.setArgument('bldg_type_a', 'SmallOffice')
create_bar.setArgument('total_bldg_floor_area', 500.0)
create_bar.setArgument('num_floors', 1)

# Parametric orientation study (8 orientations)
orientation_study = BarOrientationStudy.new
orientation_study.setArgument('rotation_start', 0.0)
orientation_study.setArgument('rotation_end', 315.0)
orientation_study.setArgument('rotation_step', 45.0)

# Parametric WWR study (5 WWR values)
wwr_study = BarWindowToWallRatioStudy.new
wwr_study.setArgument('wwr_start', 0.20)
wwr_study.setArgument('wwr_end', 0.60)
wwr_study.setArgument('wwr_step', 0.10)

# Total combinations: 8 orientations × 5 WWR = 40 models
```

---

## Quick Reference

### Most Used Measures

| Measure | Purpose | Common Use Case |
|---------|---------|-----------------|
| `CreateBarBuilding` | Simple parametric geometry | Fast model generation |
| `CreateDOEPrototypeBuilding` | DOE reference building | Baseline models, compliance |
| `CreateNECBPrototypeBuilding` | Canadian archetype | NECB compliance, Canadian projects |
| `SetWindowToWallRatioByFacade` | Facade-specific WWR | Passive solar design |
| `AddDaylightingControls` | Daylighting sensors | Energy efficiency, lighting controls |
| `AddOverhangsByProjectionFactor` | Window shading | Cooling load reduction |
| `SurfaceMatching` | Match interior surfaces | Multi-zone models |
| `CreateTypicalBuildingFromModel` | Apply standards to seed | Convert existing models |

### Building Type Options (DOE)

| Type | Use Case | Typical Size |
|------|----------|-------------|
| `SmallOffice` | 1-2 story office | < 2,500 m² |
| `MediumOffice` | 3-5 story office | 2,500-25,000 m² |
| `LargeOffice` | High-rise office | > 25,000 m² |
| `RetailStandalone` | Big-box retail | Variable |
| `PrimarySchool` | Elementary school | ~7,000 m² |
| `SecondarySchool` | High school | ~20,000 m² |
| `SmallHotel` | Limited-service hotel | ~4,000 m² |
| `LargeHotel` | Full-service hotel | ~11,000 m² |
| `Warehouse` | Unheated storage | Variable |
| `QuickServiceRestaurant` | Fast food | ~200 m² |
| `MidriseApartment` | 3-5 story residential | ~3,000 m² |

### Template Options

| Template | Standard | Typical Use |
|----------|----------|-------------|
| `90.1-2004` | ASHRAE 90.1-2004 | Legacy baseline |
| `90.1-2007` | ASHRAE 90.1-2007 | LEED 2009 baseline |
| `90.1-2010` | ASHRAE 90.1-2010 | Common baseline |
| `90.1-2013` | ASHRAE 90.1-2013 | LEED v4 baseline |
| `90.1-2016` | ASHRAE 90.1-2016 | Modern baseline |
| `90.1-2019` | ASHRAE 90.1-2019 | Current baseline |
| `NECB2011` | NECB 2011 | Canadian baseline |
| `NECB2015` | NECB 2015 | Canadian baseline |
| `NECB2017` | NECB 2017 | Canadian baseline |
| `NECB2020` | NECB 2020 | Current Canadian |

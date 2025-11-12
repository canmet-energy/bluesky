# Materials & Constructions API Reference

Complete reference for creating materials, constructions, and construction sets in OpenStudio SDK (Python & Ruby).

---

## Object Hierarchy

```
Model
└── ConstructionBase (abstract)
    ├── Construction                    # Layered construction
    ├── ConstructionWithInternalSource  # Radiant systems
    ├── ConstructionAirBoundary         # Air walls
    └── WindowDataFile                  # Complex fenestration

Model
└── Material (abstract)
    ├── OpaqueMaterial (abstract)
    │   ├── StandardOpaqueMaterial      # Most common
    │   ├── MasslessOpaqueMaterial      # R-value only
    │   ├── AirGap                      # Air space
    │   └── RoofVegetation              # Green roofs
    │
    ├── FenestrationMaterial (abstract)
    │   ├── SimpleGlazing               # Simple window (U, SHGC, VLT)
    │   ├── StandardGlazing             # Detailed glass layer
    │   ├── RefractionExtinctionGlazing # Advanced glass
    │   ├── Gas                         # Gas fill (air, argon, etc.)
    │   └── GasMixture                  # Mixed gas fills
    │
    └── ShadingMaterial (abstract)
        ├── Blind
        ├── Shade
        └── Screen

Model
└── DefaultConstructionSet
    ├── DefaultSurfaceConstructions     # Walls, floors, roofs
    ├── DefaultSubSurfaceConstructions  # Windows, doors, skylights
    └── DefaultGroundContactSurfaceConstructions
```

---

## 1. Standard Opaque Materials

### Create Material with Thermal Properties

**Python:**
```python
import openstudio

model = openstudio.model.Model()

# Create standard opaque material
insulation = openstudio.model.StandardOpaqueMaterial(model)
insulation.setName("XPS Insulation")
insulation.setRoughness("Rough")
insulation.setThickness(0.10)           # meters
insulation.setConductivity(0.029)       # W/m-K
insulation.setDensity(35.0)             # kg/m³
insulation.setSpecificHeat(1400.0)      # J/kg-K

# Optional properties
insulation.setThermalAbsorptance(0.9)   # default 0.9
insulation.setSolarAbsorptance(0.7)     # default 0.7
insulation.setVisibleAbsorptance(0.7)   # default 0.7
```

**Ruby:**
```ruby
require 'openstudio'

model = OpenStudio::Model::Model.new

insulation = OpenStudio::Model::StandardOpaqueMaterial.new(model)
insulation.setName("XPS Insulation")
insulation.setRoughness("Rough")
insulation.setThickness(0.10)
insulation.setConductivity(0.029)
insulation.setDensity(35.0)
insulation.setSpecificHeat(1400.0)

insulation.setThermalAbsorptance(0.9)
insulation.setSolarAbsorptance(0.7)
insulation.setVisibleAbsorptance(0.7)
```

### Roughness Values

| Value | Use Case |
|-------|----------|
| `VeryRough` | Brick, concrete block |
| `Rough` | Concrete, stucco |
| `MediumRough` | Wood siding |
| `MediumSmooth` | Smooth plaster |
| `Smooth` | Glass, painted metal |
| `VerySmooth` | Polished metal |

### Common Material Properties

**Insulation Materials:**

| Material | Conductivity (W/m-K) | Density (kg/m³) | Specific Heat (J/kg-K) |
|----------|---------------------|-----------------|----------------------|
| XPS (Extruded Polystyrene) | 0.029 | 35 | 1400 |
| EPS (Expanded Polystyrene) | 0.038 | 25 | 1400 |
| Polyurethane Foam | 0.026 | 30 | 1400 |
| Mineral Wool | 0.040 | 100 | 840 |
| Fiberglass Batt | 0.040 | 12 | 840 |
| Cellulose | 0.039 | 50 | 840 |

**Structural Materials:**

| Material | Conductivity (W/m-K) | Density (kg/m³) | Specific Heat (J/kg-K) |
|----------|---------------------|-----------------|----------------------|
| Concrete (normal weight) | 1.95 | 2400 | 900 |
| Concrete (lightweight) | 0.53 | 1280 | 840 |
| Brick | 0.89 | 1920 | 790 |
| Wood (softwood) | 0.12 | 510 | 1380 |
| Wood (hardwood) | 0.16 | 720 | 1255 |
| Steel | 45.0 | 7800 | 500 |
| Gypsum Board | 0.16 | 800 | 1090 |

---

## 2. Massless Opaque Materials

**Purpose:** Simplified material with R-value only (no thermal mass)

**Python:**
```python
# Create massless material (R-value only)
insulation = openstudio.model.MasslessOpaqueMaterial(model)
insulation.setName("R-20 Insulation")
insulation.setRoughness("Rough")
insulation.setThermalResistance(3.52)   # m²-K/W (R-20 in IP units)

# Optional
insulation.setThermalAbsorptance(0.9)
insulation.setSolarAbsorptance(0.7)
```

**Ruby:**
```ruby
insulation = OpenStudio::Model::MasslessOpaqueMaterial.new(model)
insulation.setName("R-20 Insulation")
insulation.setRoughness("Rough")
insulation.setThermalResistance(3.52)
```

**R-Value Conversion:**
- R-value (IP) = R-value (SI) × 5.678
- Example: R-20 IP = 3.52 SI

---

## 3. Air Gap Materials

**Purpose:** Air spaces within constructions

**Python:**
```python
air_gap = openstudio.model.AirGap(model)
air_gap.setName("Air Space 25mm")
air_gap.setThermalResistance(0.18)  # m²-K/W
```

**Ruby:**
```ruby
air_gap = OpenStudio::Model::AirGap.new(model)
air_gap.setName("Air Space 25mm")
air_gap.setThermalResistance(0.18)
```

**Common Air Gap R-Values (m²-K/W):**

| Air Gap Thickness | Horizontal Heat Flow | Upward Heat Flow | Downward Heat Flow |
|------------------|---------------------|------------------|-------------------|
| 13 mm (0.5 in) | 0.16 | 0.16 | 0.17 |
| 20 mm (0.75 in) | 0.17 | 0.16 | 0.19 |
| 40 mm (1.5 in) | 0.18 | 0.16 | 0.22 |
| 90 mm (3.5 in) | 0.18 | 0.16 | 0.23 |

---

## 4. Fenestration Materials

### Simple Glazing (Easiest)

**Python:**
```python
# Simple window - just U-factor, SHGC, VLT
simple_glazing = openstudio.model.SimpleGlazing(model)
simple_glazing.setName("U-0.35 SHGC-0.30 Window")
simple_glazing.setUFactor(2.0)                  # W/m²-K
simple_glazing.setSolarHeatGainCoefficient(0.30)
simple_glazing.setVisibleTransmittance(0.60)    # optional
```

**Ruby:**
```ruby
simple_glazing = OpenStudio::Model::SimpleGlazing.new(model)
simple_glazing.setName("U-0.35 SHGC-0.30 Window")
simple_glazing.setUFactor(2.0)
simple_glazing.setSolarHeatGainCoefficient(0.30)
simple_glazing.setVisibleTransmittance(0.60)
```

**U-Factor Conversion:**
- U-factor (IP: Btu/ft²·°F·hr) = U-factor (SI: W/m²-K) × 0.176
- Example: U-0.30 IP = 1.70 W/m²-K

**Common Window Performance:**

| Window Type | U-Factor (W/m²-K) | SHGC | VLT |
|------------|------------------|------|-----|
| Single pane, clear | 5.8 | 0.86 | 0.90 |
| Double pane, clear | 2.7 | 0.76 | 0.81 |
| Double pane, low-e | 1.7 | 0.40 | 0.70 |
| Double pane, low-e, argon | 1.5 | 0.30 | 0.60 |
| Triple pane, low-e, argon | 1.0 | 0.25 | 0.50 |

---

### Standard Glazing (Detailed)

**Python:**
```python
# Create glass layer
glass = openstudio.model.StandardGlazing(model)
glass.setName("6mm Clear Glass")
glass.setOpticalDataType("SpectralAverage")
glass.setThickness(0.006)                       # meters
glass.setSolarTransmittance(0.775)
glass.setFrontSideSolarReflectanceatNormalIncidence(0.071)
glass.setBackSideSolarReflectanceatNormalIncidence(0.071)
glass.setVisibleTransmittance(0.881)
glass.setFrontSideVisibleReflectanceatNormalIncidence(0.080)
glass.setBackSideVisibleReflectanceatNormalIncidence(0.080)
glass.setInfraredTransmittance(0.0)
glass.setFrontSideInfraredHemisphericalEmissivity(0.84)
glass.setBackSideInfraredHemisphericalEmissivity(0.84)
glass.setConductivity(0.9)                      # W/m-K

# Create gas layer
argon = openstudio.model.Gas(model)
argon.setName("Argon 13mm")
argon.setGasType("Argon")
argon.setThickness(0.013)                       # meters
```

**Ruby:**
```ruby
glass = OpenStudio::Model::StandardGlazing.new(model)
glass.setName("6mm Clear Glass")
glass.setOpticalDataType("SpectralAverage")
glass.setThickness(0.006)
glass.setSolarTransmittance(0.775)
glass.setFrontSideSolarReflectanceatNormalIncidence(0.071)
glass.setBackSideSolarReflectanceatNormalIncidence(0.071)
glass.setVisibleTransmittance(0.881)
glass.setFrontSideVisibleReflectanceatNormalIncidence(0.080)
glass.setBackSideVisibleReflectanceatNormalIncidence(0.080)
glass.setInfraredTransmittance(0.0)
glass.setFrontSideInfraredHemisphericalEmissivity(0.84)
glass.setBackSideInfraredHemisphericalEmissivity(0.84)
glass.setConductivity(0.9)

argon = OpenStudio::Model::Gas.new(model)
argon.setName("Argon 13mm")
argon.setGasType("Argon")
argon.setThickness(0.013)
```

**Gas Types:**
- `Air` - default
- `Argon` - better performance
- `Krypton` - best performance
- `Xenon` - rarely used
- `Custom` - specify properties

---

## 5. Constructions (Layered Assemblies)

### Opaque Construction

**Python:**
```python
# Create materials (outside to inside)
exterior_finish = openstudio.model.StandardOpaqueMaterial(model)
exterior_finish.setName("Stucco")
exterior_finish.setThickness(0.025)
exterior_finish.setConductivity(0.72)
exterior_finish.setDensity(1856)
exterior_finish.setSpecificHeat(840)

insulation = openstudio.model.StandardOpaqueMaterial(model)
insulation.setName("XPS 100mm")
insulation.setThickness(0.10)
insulation.setConductivity(0.029)
insulation.setDensity(35)
insulation.setSpecificHeat(1400)

gypsum = openstudio.model.StandardOpaqueMaterial(model)
gypsum.setName("Gypsum Board")
gypsum.setThickness(0.0127)
gypsum.setConductivity(0.16)
gypsum.setDensity(800)
gypsum.setSpecificHeat(1090)

# Create construction (outside to inside layer order)
wall_construction = openstudio.model.Construction(model)
wall_construction.setName("Exterior Wall Construction")

layers = openstudio.model.MaterialVector()
layers.append(exterior_finish)
layers.append(insulation)
layers.append(gypsum)

wall_construction.setLayers(layers)
```

**Ruby:**
```ruby
# Create materials
exterior_finish = OpenStudio::Model::StandardOpaqueMaterial.new(model)
exterior_finish.setName("Stucco")
exterior_finish.setThickness(0.025)
exterior_finish.setConductivity(0.72)
exterior_finish.setDensity(1856)
exterior_finish.setSpecificHeat(840)

insulation = OpenStudio::Model::StandardOpaqueMaterial.new(model)
insulation.setName("XPS 100mm")
insulation.setThickness(0.10)
insulation.setConductivity(0.029)
insulation.setDensity(35)
insulation.setSpecificHeat(1400)

gypsum = OpenStudio::Model::StandardOpaqueMaterial.new(model)
gypsum.setName("Gypsum Board")
gypsum.setThickness(0.0127)
gypsum.setConductivity(0.16)
gypsum.setDensity(800)
gypsum.setSpecificHeat(1090)

# Create construction
wall_construction = OpenStudio::Model::Construction.new(model)
wall_construction.setName("Exterior Wall Construction")
wall_construction.setLayers([exterior_finish, insulation, gypsum])
```

**IMPORTANT:** Layer order is **outside to inside** (exterior to interior)

---

### Fenestration Construction

**Python:**
```python
# Simple glazing construction (single layer)
simple_glazing = openstudio.model.SimpleGlazing(model)
simple_glazing.setName("U-1.7 SHGC-0.40")
simple_glazing.setUFactor(1.7)
simple_glazing.setSolarHeatGainCoefficient(0.40)

window_construction = openstudio.model.Construction(model)
window_construction.setName("Double Pane Window")

layers = openstudio.model.MaterialVector()
layers.append(simple_glazing)
window_construction.setLayers(layers)
```

**Python (detailed glazing with gas):**
```python
# Multi-layer glazing construction
outer_glass = openstudio.model.StandardGlazing(model)
outer_glass.setName("6mm Low-E Glass")
outer_glass.setThickness(0.006)
# ... (set all properties as shown above)

gas_fill = openstudio.model.Gas(model)
gas_fill.setName("Argon 13mm")
gas_fill.setGasType("Argon")
gas_fill.setThickness(0.013)

inner_glass = openstudio.model.StandardGlazing(model)
inner_glass.setName("6mm Clear Glass")
inner_glass.setThickness(0.006)
# ... (set all properties)

# Create construction (outside to inside)
window_construction = openstudio.model.Construction(model)
window_construction.setName("Double Pane Low-E Argon")

layers = openstudio.model.MaterialVector()
layers.append(outer_glass)
layers.append(gas_fill)
layers.append(inner_glass)

window_construction.setLayers(layers)
```

**Ruby:**
```ruby
simple_glazing = OpenStudio::Model::SimpleGlazing.new(model)
simple_glazing.setName("U-1.7 SHGC-0.40")
simple_glazing.setUFactor(1.7)
simple_glazing.setSolarHeatGainCoefficient(0.40)

window_construction = OpenStudio::Model::Construction.new(model)
window_construction.setName("Double Pane Window")
window_construction.setLayers([simple_glazing])
```

---

## 6. Construction Sets

### Create Default Construction Set

**Python:**
```python
# Create constructions first (as shown above)
# Assume: wall_construction, roof_construction, floor_construction,
#         window_construction, door_construction

# Create default construction set
construction_set = openstudio.model.DefaultConstructionSet(model)
construction_set.setName("Building Construction Set")

# Exterior surface constructions
ext_surfaces = openstudio.model.DefaultSurfaceConstructions(model)
ext_surfaces.setWallConstruction(wall_construction)
ext_surfaces.setRoofCeilingConstruction(roof_construction)
ext_surfaces.setFloorConstruction(floor_construction)
construction_set.setDefaultExteriorSurfaceConstructions(ext_surfaces)

# Interior surface constructions
int_surfaces = openstudio.model.DefaultSurfaceConstructions(model)
int_surfaces.setWallConstruction(interior_wall_construction)
int_surfaces.setRoofCeilingConstruction(interior_ceiling_construction)
int_surfaces.setFloorConstruction(interior_floor_construction)
construction_set.setDefaultInteriorSurfaceConstructions(int_surfaces)

# Ground contact constructions
ground_surfaces = openstudio.model.DefaultSurfaceConstructions(model)
ground_surfaces.setFloorConstruction(slab_construction)
ground_surfaces.setWallConstruction(basement_wall_construction)
construction_set.setDefaultGroundContactSurfaceConstructions(ground_surfaces)

# Sub-surface (window/door) constructions
sub_surfaces = openstudio.model.DefaultSubSurfaceConstructions(model)
sub_surfaces.setFixedWindowConstruction(window_construction)
sub_surfaces.setOperableWindowConstruction(window_construction)
sub_surfaces.setDoorConstruction(door_construction)
sub_surfaces.setGlassDoorConstruction(glass_door_construction)
sub_surfaces.setSkylightConstruction(skylight_construction)
construction_set.setDefaultExteriorSubSurfaceConstructions(sub_surfaces)
```

**Ruby:**
```ruby
construction_set = OpenStudio::Model::DefaultConstructionSet.new(model)
construction_set.setName("Building Construction Set")

# Exterior surfaces
ext_surfaces = OpenStudio::Model::DefaultSurfaceConstructions.new(model)
ext_surfaces.setWallConstruction(wall_construction)
ext_surfaces.setRoofCeilingConstruction(roof_construction)
ext_surfaces.setFloorConstruction(floor_construction)
construction_set.setDefaultExteriorSurfaceConstructions(ext_surfaces)

# Interior surfaces
int_surfaces = OpenStudio::Model::DefaultSurfaceConstructions.new(model)
int_surfaces.setWallConstruction(interior_wall_construction)
int_surfaces.setRoofCeilingConstruction(interior_ceiling_construction)
int_surfaces.setFloorConstruction(interior_floor_construction)
construction_set.setDefaultInteriorSurfaceConstructions(int_surfaces)

# Ground contact
ground_surfaces = OpenStudio::Model::DefaultSurfaceConstructions.new(model)
ground_surfaces.setFloorConstruction(slab_construction)
ground_surfaces.setWallConstruction(basement_wall_construction)
construction_set.setDefaultGroundContactSurfaceConstructions(ground_surfaces)

# Sub-surfaces
sub_surfaces = OpenStudio::Model::DefaultSubSurfaceConstructions.new(model)
sub_surfaces.setFixedWindowConstruction(window_construction)
sub_surfaces.setOperableWindowConstruction(window_construction)
sub_surfaces.setDoorConstruction(door_construction)
sub_surfaces.setGlassDoorConstruction(glass_door_construction)
sub_surfaces.setSkylightConstruction(skylight_construction)
construction_set.setDefaultExteriorSubSurfaceConstructions(sub_surfaces)
```

---

### Assign Construction Set

**Python:**
```python
# Assign to entire building
building = model.getBuilding()
building.setDefaultConstructionSet(construction_set)

# Or assign to specific space type
office_space_type = openstudio.model.SpaceType(model)
office_space_type.setName("Office Space Type")
office_space_type.setDefaultConstructionSet(construction_set)

# Or assign directly to space
space = openstudio.model.Space(model)
space.setDefaultConstructionSet(construction_set)
```

**Ruby:**
```ruby
# Assign to building
building = model.getBuilding
building.setDefaultConstructionSet(construction_set)

# Assign to space type
office_space_type = OpenStudio::Model::SpaceType.new(model)
office_space_type.setName("Office Space Type")
office_space_type.setDefaultConstructionSet(construction_set)

# Assign to space
space = OpenStudio::Model::Space.new(model)
space.setDefaultConstructionSet(construction_set)
```

---

## 7. Assigning Constructions to Surfaces

### Method 1: Via Construction Set (Recommended)

**Python:**
```python
# Set construction set at building level
building = model.getBuilding()
building.setDefaultConstructionSet(construction_set)

# All surfaces without explicit construction will use construction set
```

**Ruby:**
```ruby
building = model.getBuilding
building.setDefaultConstructionSet(construction_set)
```

---

### Method 2: Direct Assignment to Surface

**Python:**
```python
# Get specific surface
surfaces = model.getSurfaces()
for surface in surfaces:
    if surface.surfaceType() == "Wall" and surface.outsideBoundaryCondition() == "Outdoors":
        surface.setConstruction(wall_construction)
    elif surface.surfaceType() == "RoofCeiling" and surface.outsideBoundaryCondition() == "Outdoors":
        surface.setConstruction(roof_construction)
```

**Ruby:**
```ruby
model.getSurfaces.each do |surface|
  if surface.surfaceType == "Wall" && surface.outsideBoundaryCondition == "Outdoors"
    surface.setConstruction(wall_construction)
  elsif surface.surfaceType == "RoofCeiling" && surface.outsideBoundaryCondition == "Outdoors"
    surface.setConstruction(roof_construction)
  end
end
```

---

### Method 3: Assign to Sub-Surface (Window/Door)

**Python:**
```python
# Get sub-surfaces (windows, doors)
sub_surfaces = model.getSubSurfaces()
for sub_surface in sub_surfaces:
    if sub_surface.subSurfaceType() == "FixedWindow":
        sub_surface.setConstruction(window_construction)
    elif sub_surface.subSurfaceType() == "Door":
        sub_surface.setConstruction(door_construction)
```

**Ruby:**
```ruby
model.getSubSurfaces.each do |sub_surface|
  if sub_surface.subSurfaceType == "FixedWindow"
    sub_surface.setConstruction(window_construction)
  elsif sub_surface.subSurfaceType == "Door"
    sub_surface.setConstruction(door_construction)
  end
end
```

---

## 8. Querying Construction Properties

### Get Construction Layers

**Python:**
```python
construction = model.getConstructionByName("Exterior Wall Construction").get()

# Get layers
layers = construction.layers()

print(f"Construction: {construction.name().get()}")
print(f"Number of layers: {len(layers)}")

for i, layer in enumerate(layers):
    print(f"  Layer {i+1}: {layer.name().get()}")

    # Check if it's a StandardOpaqueMaterial
    std_material = layer.to_StandardOpaqueMaterial()
    if std_material.is_initialized():
        mat = std_material.get()
        print(f"    Thickness: {mat.thickness()} m")
        print(f"    Conductivity: {mat.conductivity()} W/m-K")
```

**Ruby:**
```ruby
construction = model.getConstructionByName("Exterior Wall Construction").get

layers = construction.layers

puts "Construction: #{construction.name.get}"
puts "Number of layers: #{layers.size}"

layers.each_with_index do |layer, i|
  puts "  Layer #{i+1}: #{layer.name.get}"

  std_material = layer.to_StandardOpaqueMaterial
  if std_material.is_initialized
    mat = std_material.get
    puts "    Thickness: #{mat.thickness} m"
    puts "    Conductivity: #{mat.conductivity} W/m-K"
  end
end
```

---

### Calculate U-Factor

**Python:**
```python
# Get construction thermal properties
construction = model.getConstructionByName("Exterior Wall Construction").get()

# U-factor requires film coefficients
# For typical wall: exterior film = 25 W/m²-K, interior film = 7.7 W/m²-K
film_coefficients = openstudio.FilmResistanceType("StillAir_HorizontalSurface_HeatFlowsUpward")

# Get thermal conductance (doesn't include film coefficients)
thermal_conductance = construction.thermalConductance()
if thermal_conductance.is_initialized():
    conductance = thermal_conductance.get()
    print(f"Thermal conductance: {conductance:.3f} W/m²-K")

    # Calculate U-factor (approximate, with typical film coefficients)
    r_exterior_film = 1.0 / 25.0  # m²-K/W
    r_interior_film = 1.0 / 7.7   # m²-K/W
    r_construction = 1.0 / conductance
    r_total = r_exterior_film + r_construction + r_interior_film
    u_factor = 1.0 / r_total

    print(f"U-factor: {u_factor:.3f} W/m²-K")
    print(f"R-value: {r_total:.2f} m²-K/W (R-{r_total * 5.678:.1f} IP)")
```

**Ruby:**
```ruby
construction = model.getConstructionByName("Exterior Wall Construction").get

thermal_conductance = construction.thermalConductance
if thermal_conductance.is_initialized
  conductance = thermal_conductance.get
  puts "Thermal conductance: #{conductance.round(3)} W/m²-K"

  r_exterior_film = 1.0 / 25.0
  r_interior_film = 1.0 / 7.7
  r_construction = 1.0 / conductance
  r_total = r_exterior_film + r_construction + r_interior_film
  u_factor = 1.0 / r_total

  puts "U-factor: #{u_factor.round(3)} W/m²-K"
  puts "R-value: #{r_total.round(2)} m²-K/W (R-#{(r_total * 5.678).round(1)} IP)"
end
```

---

## 9. Complete Construction Examples

### High-Performance Wall (NECB Zone 6)

**Python:**
```python
# Target: R-19.5 (RSI 3.43)

# Exterior finish
stucco = openstudio.model.StandardOpaqueMaterial(model)
stucco.setName("Stucco 25mm")
stucco.setThickness(0.025)
stucco.setConductivity(0.72)
stucco.setDensity(1856)
stucco.setSpecificHeat(840)

# Insulation
xps = openstudio.model.StandardOpaqueMaterial(model)
xps.setName("XPS 120mm")
xps.setThickness(0.12)
xps.setConductivity(0.029)
xps.setDensity(35)
xps.setSpecificHeat(1400)

# Structural layer
concrete = openstudio.model.StandardOpaqueMaterial(model)
concrete.setName("Concrete 200mm")
concrete.setThickness(0.20)
concrete.setConductivity(1.95)
concrete.setDensity(2400)
concrete.setSpecificHeat(900)

# Interior finish
gypsum = openstudio.model.StandardOpaqueMaterial(model)
gypsum.setName("Gypsum 13mm")
gypsum.setThickness(0.0127)
gypsum.setConductivity(0.16)
gypsum.setDensity(800)
gypsum.setSpecificHeat(1090)

# Create construction
wall = openstudio.model.Construction(model)
wall.setName("NECB Zone 6 Exterior Wall")
wall.setLayers([stucco, xps, concrete, gypsum])
```

---

### Triple-Pane Window (NECB Zone 6)

**Python:**
```python
# Approach 1: Simple glazing (easiest)
window = openstudio.model.SimpleGlazing(model)
window.setName("NECB Zone 6 Window U-1.8")
window.setUFactor(1.8)          # W/m²-K (max for Zone 6)
window.setSolarHeatGainCoefficient(0.40)
window.setVisibleTransmittance(0.50)

window_construction = openstudio.model.Construction(model)
window_construction.setName("Triple Pane Low-E Argon")
window_construction.setLayers([window])
```

---

### Roof Assembly with Insulation

**Python:**
```python
# Built-up roof
roofing = openstudio.model.StandardOpaqueMaterial(model)
roofing.setName("Roofing Membrane 10mm")
roofing.setThickness(0.01)
roofing.setConductivity(0.16)
roofing.setDensity(1120)
roofing.setSpecificHeat(1460)
roofing.setSolarAbsorptance(0.85)  # Dark roof

# Insulation
polyiso = openstudio.model.StandardOpaqueMaterial(model)
polyiso.setName("Polyisocyanurate 150mm")
polyiso.setThickness(0.15)
polyiso.setConductivity(0.026)
polyiso.setDensity(30)
polyiso.setSpecificHeat(1400)

# Roof deck
plywood = openstudio.model.StandardOpaqueMaterial(model)
plywood.setName("Plywood 19mm")
plywood.setThickness(0.019)
plywood.setConductivity(0.12)
plywood.setDensity(540)
plywood.setSpecificHeat(1210)

# Air space
air_space = openstudio.model.AirGap(model)
air_space.setName("Air Space")
air_space.setThermalResistance(0.18)

# Ceiling finish
gypsum = openstudio.model.StandardOpaqueMaterial(model)
gypsum.setName("Gypsum 13mm")
gypsum.setThickness(0.0127)
gypsum.setConductivity(0.16)
gypsum.setDensity(800)
gypsum.setSpecificHeat(1090)

# Create construction
roof = openstudio.model.Construction(model)
roof.setName("Roof Assembly R-30")
roof.setLayers([roofing, polyiso, plywood, air_space, gypsum])
```

---

## Quick Reference

### Material Types Quick Lookup

| Need | Class |
|------|-------|
| Standard insulation/structural | `StandardOpaqueMaterial` |
| R-value only (no mass) | `MasslessOpaqueMaterial` |
| Air space | `AirGap` |
| Simple window (U, SHGC only) | `SimpleGlazing` |
| Detailed glass layer | `StandardGlazing` |
| Gas fill (argon, etc.) | `Gas` |

### Key Methods

| Operation | Python/Ruby Method |
|-----------|-------------------|
| Create material | `Material.new(model)` or `Material(model)` |
| Set layer order | `construction.setLayers([mat1, mat2, ...])` |
| Assign to building | `building.setDefaultConstructionSet(set)` |
| Assign to surface | `surface.setConstruction(construction)` |
| Get layers | `construction.layers()` |
| Calculate U-factor | `construction.thermalConductance()` |

### Unit Conversions

| Property | SI → IP |
|----------|---------|
| R-value | × 5.678 |
| U-factor | × 0.176 |
| Conductivity (k) | × 0.5778 (W/m-K → Btu·in/hr·ft²·°F) |
| Thickness | × 39.37 (m → in) |

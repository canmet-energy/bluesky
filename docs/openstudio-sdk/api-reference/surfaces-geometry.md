# Surfaces & Geometry API Reference

Complete reference for creating and manipulating surfaces, sub-surfaces, and shading in OpenStudio SDK (Python & Ruby).

---

## Object Hierarchy

```
Model
└── Space
    ├── Surface (walls, floors, roofs)
    │   └── SubSurface (windows, doors, skylights)
    └── ShadingSurfaceGroup
        └── ShadingSurface

Model
└── Building
    └── ShadingSurfaceGroup
        └── ShadingSurface (building shading, overhangs)

Model
└── Site
    └── ShadingSurfaceGroup
        └── ShadingSurface (site shading, trees, neighboring buildings)
```

---

## 1. Points and Vertices

### Create Point3d

**Python:**
```python
import openstudio

# Point3d(x, y, z) in meters
point1 = openstudio.Point3d(0, 0, 0)      # Origin
point2 = openstudio.Point3d(10, 0, 0)     # 10m along X
point3 = openstudio.Point3d(10, 10, 0)    # 10m X, 10m Y
point4 = openstudio.Point3d(0, 10, 0)     # 10m along Y

# Access coordinates
x = point1.x()  # 0.0
y = point1.y()  # 0.0
z = point1.z()  # 0.0
```

**Ruby:**
```ruby
require 'openstudio'

point1 = OpenStudio::Point3d.new(0, 0, 0)
point2 = OpenStudio::Point3d.new(10, 0, 0)
point3 = OpenStudio::Point3d.new(10, 10, 0)
point4 = OpenStudio::Point3d.new(0, 10, 0)

x = point1.x
y = point1.y
z = point1.z
```

### Create Vertex Vector

**Python:**
```python
# Create vector of vertices (counter-clockwise from outside)
vertices = openstudio.Point3dVector()
vertices.append(openstudio.Point3d(0, 0, 0))
vertices.append(openstudio.Point3d(10, 0, 0))
vertices.append(openstudio.Point3d(10, 10, 0))
vertices.append(openstudio.Point3d(0, 10, 0))
```

**Ruby:**
```ruby
vertices = OpenStudio::Point3dVector.new
vertices << OpenStudio::Point3d.new(0, 0, 0)
vertices << OpenStudio::Point3d.new(10, 0, 0)
vertices << OpenStudio::Point3d.new(10, 10, 0)
vertices << OpenStudio::Point3d.new(0, 10, 0)
```

---

## 2. Surfaces

### Surface Types

| Type | Use | Boundary Condition |
|------|-----|-------------------|
| `Wall` | Vertical surfaces | Outdoors, Ground, Adiabatic, Surface |
| `Floor` | Horizontal down-facing | Ground, Adiabatic, Surface |
| `RoofCeiling` | Horizontal up-facing | Outdoors, Adiabatic, Surface |

### Outside Boundary Conditions

| Condition | Meaning |
|-----------|---------|
| `Outdoors` | Exposed to weather |
| `Ground` | In contact with ground |
| `Adiabatic` | No heat transfer |
| `Surface` | Adjacent to another surface (interior wall) |

---

### Create Floor Surface

**Python:**
```python
# Floor vertices (counter-clockwise from above, Z=0)
floor_vertices = openstudio.Point3dVector()
floor_vertices.append(openstudio.Point3d(0, 0, 0))
floor_vertices.append(openstudio.Point3d(10, 0, 0))
floor_vertices.append(openstudio.Point3d(10, 10, 0))
floor_vertices.append(openstudio.Point3d(0, 10, 0))

# Create surface
floor = openstudio.model.Surface(floor_vertices, model)
floor.setName("Floor")
floor.setSurfaceType("Floor")
floor.setOutsideBoundaryCondition("Ground")

# Assign to space
space = openstudio.model.Space(model)
floor.setSpace(space)
```

**Ruby:**
```ruby
floor_vertices = OpenStudio::Point3dVector.new
floor_vertices << OpenStudio::Point3d.new(0, 0, 0)
floor_vertices << OpenStudio::Point3d.new(10, 0, 0)
floor_vertices << OpenStudio::Point3d.new(10, 10, 0)
floor_vertices << OpenStudio::Point3d.new(0, 10, 0)

floor = OpenStudio::Model::Surface.new(floor_vertices, model)
floor.setName("Floor")
floor.setSurfaceType("Floor")
floor.setOutsideBoundaryCondition("Ground")

space = OpenStudio::Model::Space.new(model)
floor.setSpace(space)
```

---

### Create Wall Surface

**Python:**
```python
# South wall (counter-clockwise from outside)
# Lower-left, lower-right, upper-right, upper-left
south_wall_vertices = openstudio.Point3dVector()
south_wall_vertices.append(openstudio.Point3d(0, 0, 0))      # Lower-left
south_wall_vertices.append(openstudio.Point3d(10, 0, 0))     # Lower-right
south_wall_vertices.append(openstudio.Point3d(10, 0, 3))     # Upper-right
south_wall_vertices.append(openstudio.Point3d(0, 0, 3))      # Upper-left

south_wall = openstudio.model.Surface(south_wall_vertices, model)
south_wall.setName("South Wall")
south_wall.setSurfaceType("Wall")
south_wall.setOutsideBoundaryCondition("Outdoors")
south_wall.setSpace(space)
```

**Ruby:**
```ruby
south_wall_vertices = OpenStudio::Point3dVector.new
south_wall_vertices << OpenStudio::Point3d.new(0, 0, 0)
south_wall_vertices << OpenStudio::Point3d.new(10, 0, 0)
south_wall_vertices << OpenStudio::Point3d.new(10, 0, 3)
south_wall_vertices << OpenStudio::Point3d.new(0, 0, 3)

south_wall = OpenStudio::Model::Surface.new(south_wall_vertices, model)
south_wall.setName("South Wall")
south_wall.setSurfaceType("Wall")
south_wall.setOutsideBoundaryCondition("Outdoors")
south_wall.setSpace(space)
```

---

### Create Roof Surface

**Python:**
```python
# Roof (counter-clockwise from outside = clockwise from above)
roof_vertices = openstudio.Point3dVector()
roof_vertices.append(openstudio.Point3d(0, 10, 3))   # Start upper-left
roof_vertices.append(openstudio.Point3d(10, 10, 3))  # Upper-right
roof_vertices.append(openstudio.Point3d(10, 0, 3))   # Lower-right
roof_vertices.append(openstudio.Point3d(0, 0, 3))    # Lower-left

roof = openstudio.model.Surface(roof_vertices, model)
roof.setName("Roof")
roof.setSurfaceType("RoofCeiling")
roof.setOutsideBoundaryCondition("Outdoors")
roof.setSpace(space)
```

---

## 3. Sub-Surfaces (Windows, Doors)

### Sub-Surface Types

| Type | Use |
|------|-----|
| `FixedWindow` | Non-operable window |
| `OperableWindow` | Operable window |
| `Door` | Opaque door |
| `GlassDoor` | Glass door |
| `Skylight` | Roof window |
| `OverheadDoor` | Garage door |
| `TubularDaylightDome` | Tubular skylight dome |
| `TubularDaylightDiffuser` | Tubular skylight diffuser |

---

### Create Window

**Python:**
```python
# Window must be on a wall surface
wall = model.getSurfaces()[0]  # Get existing wall

# Window vertices (relative to wall, counter-clockwise from outside)
# Bottom-left, bottom-right, top-right, top-left
window_vertices = openstudio.Point3dVector()
window_vertices.append(openstudio.Point3d(2, 0, 0.5))   # Bottom-left
window_vertices.append(openstudio.Point3d(8, 0, 0.5))   # Bottom-right
window_vertices.append(openstudio.Point3d(8, 0, 2.5))   # Top-right
window_vertices.append(openstudio.Point3d(2, 0, 2.5))   # Top-left

window = openstudio.model.SubSurface(window_vertices, model)
window.setName("South Window")
window.setSubSurfaceType("FixedWindow")
window.setSurface(wall)  # Assign to wall
```

**Ruby:**
```ruby
wall = model.getSurfaces[0]

window_vertices = OpenStudio::Point3dVector.new
window_vertices << OpenStudio::Point3d.new(2, 0, 0.5)
window_vertices << OpenStudio::Point3d.new(8, 0, 0.5)
window_vertices << OpenStudio::Point3d.new(8, 0, 2.5)
window_vertices << OpenStudio::Point3d.new(2, 0, 2.5)

window = OpenStudio::Model::SubSurface.new(window_vertices, model)
window.setName("South Window")
window.setSubSurfaceType("FixedWindow")
window.setSurface(wall)
```

---

### Create Door

**Python:**
```python
# Door on wall
door_vertices = openstudio.Point3dVector()
door_vertices.append(openstudio.Point3d(4, 0, 0))      # Bottom-left
door_vertices.append(openstudio.Point3d(5.5, 0, 0))    # Bottom-right
door_vertices.append(openstudio.Point3d(5.5, 0, 2.1))  # Top-right
door_vertices.append(openstudio.Point3d(4, 0, 2.1))    # Top-left

door = openstudio.model.SubSurface(door_vertices, model)
door.setName("Entry Door")
door.setSubSurfaceType("Door")
door.setSurface(wall)
```

**Ruby:**
```ruby
door_vertices = OpenStudio::Point3dVector.new
door_vertices << OpenStudio::Point3d.new(4, 0, 0)
door_vertices << OpenStudio::Point3d.new(5.5, 0, 0)
door_vertices << OpenStudio::Point3d.new(5.5, 0, 2.1)
door_vertices << OpenStudio::Point3d.new(4, 0, 2.1)

door = OpenStudio::Model::SubSurface.new(door_vertices, model)
door.setName("Entry Door")
door.setSubSurfaceType("Door")
door.setSurface(wall)
```

---

### Set Window-to-Wall Ratio

**Python:**
```python
def set_wwr_on_surface(surface, wwr):
    """Set window-to-wall ratio on a surface"""
    # Remove existing sub-surfaces
    for sub_surface in surface.subSurfaces():
        sub_surface.remove()

    # Set new WWR
    surface.setWindowToWallRatio(wwr)

# Usage
south_wall = model.getSurfaceByName("South Wall").get()
set_wwr_on_surface(south_wall, 0.40)  # 40% WWR
```

**Ruby:**
```ruby
def set_wwr_on_surface(surface, wwr)
  # Remove existing sub-surfaces
  surface.subSurfaces.each(&:remove)

  # Set new WWR
  surface.setWindowToWallRatio(wwr)
end

south_wall = model.getSurfaceByName("South Wall").get
set_wwr_on_surface(south_wall, 0.40)
```

---

## 4. Shading Surfaces

### Shading Types

| Level | Use | Moves With |
|-------|-----|-----------|
| `Space` | Overhangs, fins attached to building | Space |
| `Building` | Building-level shading | Building |
| `Site` | Trees, neighboring buildings | Site (fixed) |

---

### Create Overhang (Space Shading)

**Python:**
```python
# Create shading surface group attached to space
space = model.getSpaces()[0]
shading_group = openstudio.model.ShadingSurfaceGroup(model)
shading_group.setName("Window Overhangs")
shading_group.setSpace(space)

# Create overhang above window
# Overhang projects 1m out from wall at Z=2.5m
overhang_vertices = openstudio.Point3dVector()
overhang_vertices.append(openstudio.Point3d(2, 0, 2.5))
overhang_vertices.append(openstudio.Point3d(2, -1, 2.5))  # Projects 1m out
overhang_vertices.append(openstudio.Point3d(8, -1, 2.5))
overhang_vertices.append(openstudio.Point3d(8, 0, 2.5))

overhang = openstudio.model.ShadingSurface(overhang_vertices, model)
overhang.setName("South Window Overhang")
overhang.setShadingSurfaceGroup(shading_group)
```

**Ruby:**
```ruby
space = model.getSpaces[0]
shading_group = OpenStudio::Model::ShadingSurfaceGroup.new(model)
shading_group.setName("Window Overhangs")
shading_group.setSpace(space)

overhang_vertices = OpenStudio::Point3dVector.new
overhang_vertices << OpenStudio::Point3d.new(2, 0, 2.5)
overhang_vertices << OpenStudio::Point3d.new(2, -1, 2.5)
overhang_vertices << OpenStudio::Point3d.new(8, -1, 2.5)
overhang_vertices << OpenStudio::Point3d.new(8, 0, 2.5)

overhang = OpenStudio::Model::ShadingSurface.new(overhang_vertices, model)
overhang.setName("South Window Overhang")
overhang.setShadingSurfaceGroup(shading_group)
```

---

### Create Site Shading (Neighboring Building)

**Python:**
```python
# Create site shading group
site_shading_group = openstudio.model.ShadingSurfaceGroup(model)
site_shading_group.setName("Neighboring Building")
site_shading_group.setShadingSurfaceType("Site")

# Create neighboring building (20m tall, 20m away)
neighbor_vertices = openstudio.Point3dVector()
neighbor_vertices.append(openstudio.Point3d(-20, 0, 0))
neighbor_vertices.append(openstudio.Point3d(-20, 30, 0))
neighbor_vertices.append(openstudio.Point3d(-20, 30, 20))
neighbor_vertices.append(openstudio.Point3d(-20, 0, 20))

neighbor_shading = openstudio.model.ShadingSurface(neighbor_vertices, model)
neighbor_shading.setName("Neighboring Building East Wall")
neighbor_shading.setShadingSurfaceGroup(site_shading_group)
```

**Ruby:**
```ruby
site_shading_group = OpenStudio::Model::ShadingSurfaceGroup.new(model)
site_shading_group.setName("Neighboring Building")
site_shading_group.setShadingSurfaceType("Site")

neighbor_vertices = OpenStudio::Point3dVector.new
neighbor_vertices << OpenStudio::Point3d.new(-20, 0, 0)
neighbor_vertices << OpenStudio::Point3d.new(-20, 30, 0)
neighbor_vertices << OpenStudio::Point3d.new(-20, 30, 20)
neighbor_vertices << OpenStudio::Point3d.new(-20, 0, 20)

neighbor_shading = OpenStudio::Model::ShadingSurface.new(neighbor_vertices, model)
neighbor_shading.setName("Neighboring Building East Wall")
neighbor_shading.setShadingSurfaceGroup(site_shading_group)
```

---

## 5. Geometry Utilities

### Check Surface Properties

**Python:**
```python
surface = model.getSurfaces()[0]

# Get properties
area = surface.grossArea()                    # m²
net_area = surface.netArea()                  # m² (minus sub-surfaces)
azimuth = surface.azimuth()                   # radians
tilt = surface.tilt()                         # radians
outward_normal = surface.outwardNormal()      # Vector3d

# Convert radians to degrees
import math
azimuth_deg = math.degrees(azimuth)
tilt_deg = math.degrees(tilt)

print(f"Area: {area:.2f} m²")
print(f"Azimuth: {azimuth_deg:.1f}°")
print(f"Tilt: {tilt_deg:.1f}°")
```

**Ruby:**
```ruby
surface = model.getSurfaces[0]

area = surface.grossArea
net_area = surface.netArea
azimuth = surface.azimuth
tilt = surface.tilt

azimuth_deg = OpenStudio.radToDeg(azimuth)
tilt_deg = OpenStudio.radToDeg(tilt)

puts "Area: #{area.round(2)} m²"
puts "Azimuth: #{azimuth_deg.round(1)}°"
puts "Tilt: #{tilt_deg.round(1)}°"
```

### Surface Orientation

| Azimuth (°) | Direction |
|------------|-----------|
| 0 | North |
| 90 | East |
| 180 | South |
| 270 | West |

| Tilt (°) | Orientation |
|---------|-------------|
| 0 | Horizontal (roof) |
| 90 | Vertical (wall) |
| 180 | Horizontal down (floor) |

---

### Match Interior Surfaces

**Python:**
```python
# Match interior surfaces between spaces
spaces = openstudio.model.SpaceVector()
for space in model.getSpaces():
    spaces.append(space)

# Match surfaces
openstudio.model.matchSurfaces(spaces)

# This finds adjacent surfaces and sets:
# - Outside boundary condition to "Surface"
# - Links surfaces together
```

**Ruby:**
```ruby
spaces = OpenStudio::Model::SpaceVector.new
model.getSpaces.each { |space| spaces << space }

OpenStudio::Model.matchSurfaces(spaces)
```

---

### Intersect Surfaces

**Python:**
```python
# Intersect overlapping surfaces
spaces = openstudio.model.SpaceVector()
for space in model.getSpaces():
    spaces.append(space)

openstudio.model.intersectSurfaces(spaces)

# This splits surfaces at intersections
```

**Ruby:**
```ruby
spaces = OpenStudio::Model::SpaceVector.new
model.getSpaces.each { |space| spaces << space }

OpenStudio::Model.intersectSurfaces(spaces)
```

---

## 6. Surface Transformations

### Rotate Building

**Python:**
```python
# Rotate entire building 45 degrees clockwise
import math

building = model.getBuilding()
degrees = 45.0
radians = math.radians(degrees)

# Rotate around Z-axis (vertical)
building.setNorthAxis(degrees)  # Sets north axis rotation
```

**Ruby:**
```ruby
building = model.getBuilding
degrees = 45.0

building.setNorthAxis(degrees)
```

---

## Quick Reference

### Vertex Order

**CRITICAL:** Counter-clockwise from outside looking at surface

**Floor (looking down):**
```
(0,10,0) ← (10,10,0)
   ↑          ↑
   |          |
(0,0,0) → (10,0,0)
```

**Wall (looking from outside):**
```
(0,0,3) → (10,0,3)  Upper
   ↑          ↑
   |          |
(0,0,0) → (10,0,0)  Lower
```

### Key Methods

| Operation | Python/Ruby Method |
|-----------|-------------------|
| Create surface | `Surface(vertices, model)` |
| Create sub-surface | `SubSurface(vertices, model)` |
| Set type | `setSurfaceType("Wall")`, `setSubSurfaceType("FixedWindow")` |
| Set boundary | `setOutsideBoundaryCondition("Outdoors")` |
| Assign to space | `surface.setSpace(space)` |
| Set WWR | `surface.setWindowToWallRatio(0.40)` |
| Match surfaces | `matchSurfaces(spaces)` |
| Get area | `surface.grossArea()`, `surface.netArea()` |

### Common Surface Types

| Type | Tilt | Boundary |
|------|------|----------|
| Exterior wall | 90° | Outdoors |
| Roof | 0° | Outdoors |
| Floor on grade | 180° | Ground |
| Interior wall | 90° | Surface (matched) |
| Interior ceiling | 0° | Surface (matched) |

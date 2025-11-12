# OpenStudio Geometry Patterns

Complete, runnable patterns for creating building geometry from scratch.

Each pattern is production-ready and can be adapted to your specific needs.

---

## Pattern 1: Simple Box Building (Single Zone)

**Use case:** Simplest complete building - one thermal zone, six surfaces (4 walls + floor + ceiling).

**Dimensions:** 10m × 10m × 3m high

### Python

```python
import openstudio

def create_simple_box_building():
    """Create a simple 10x10x3m single-zone building."""
    model = openstudio.model.Model()

    # Create thermal zone
    zone = openstudio.model.ThermalZone(model)
    zone.setName("Main Zone")

    # Create space
    space = openstudio.model.Space(model)
    space.setName("Main Space")
    space.setThermalZone(zone)

    # Floor (Z=0, counter-clockwise from above)
    floor_vertices = openstudio.Point3dVector()
    floor_vertices.append(openstudio.Point3d(0, 0, 0))
    floor_vertices.append(openstudio.Point3d(10, 0, 0))
    floor_vertices.append(openstudio.Point3d(10, 10, 0))
    floor_vertices.append(openstudio.Point3d(0, 10, 0))

    floor = openstudio.model.Surface(floor_vertices, model)
    floor.setName("Floor")
    floor.setSurfaceType("Floor")
    floor.setSpace(space)

    # Ceiling (Z=3, counter-clockwise from above)
    ceiling_vertices = openstudio.Point3dVector()
    ceiling_vertices.append(openstudio.Point3d(0, 10, 3))
    ceiling_vertices.append(openstudio.Point3d(10, 10, 3))
    ceiling_vertices.append(openstudio.Point3d(10, 0, 3))
    ceiling_vertices.append(openstudio.Point3d(0, 0, 3))

    ceiling = openstudio.model.Surface(ceiling_vertices, model)
    ceiling.setName("Ceiling")
    ceiling.setSurfaceType("RoofCeiling")
    ceiling.setSpace(space)

    # South Wall (Y=0, counter-clockwise from outside/south)
    south_vertices = openstudio.Point3dVector()
    south_vertices.append(openstudio.Point3d(0, 0, 3))
    south_vertices.append(openstudio.Point3d(0, 0, 0))
    south_vertices.append(openstudio.Point3d(10, 0, 0))
    south_vertices.append(openstudio.Point3d(10, 0, 3))

    south_wall = openstudio.model.Surface(south_vertices, model)
    south_wall.setName("South Wall")
    south_wall.setSurfaceType("Wall")
    south_wall.setSpace(space)

    # East Wall (X=10, counter-clockwise from outside/east)
    east_vertices = openstudio.Point3dVector()
    east_vertices.append(openstudio.Point3d(10, 0, 3))
    east_vertices.append(openstudio.Point3d(10, 0, 0))
    east_vertices.append(openstudio.Point3d(10, 10, 0))
    east_vertices.append(openstudio.Point3d(10, 10, 3))

    east_wall = openstudio.model.Surface(east_vertices, model)
    east_wall.setName("East Wall")
    east_wall.setSurfaceType("Wall")
    east_wall.setSpace(space)

    # North Wall (Y=10, counter-clockwise from outside/north)
    north_vertices = openstudio.Point3dVector()
    north_vertices.append(openstudio.Point3d(10, 10, 3))
    north_vertices.append(openstudio.Point3d(10, 10, 0))
    north_vertices.append(openstudio.Point3d(0, 10, 0))
    north_vertices.append(openstudio.Point3d(0, 10, 3))

    north_wall = openstudio.model.Surface(north_vertices, model)
    north_wall.setName("North Wall")
    north_wall.setSurfaceType("Wall")
    north_wall.setSpace(space)

    # West Wall (X=0, counter-clockwise from outside/west)
    west_vertices = openstudio.Point3dVector()
    west_vertices.append(openstudio.Point3d(0, 10, 3))
    west_vertices.append(openstudio.Point3d(0, 10, 0))
    west_vertices.append(openstudio.Point3d(0, 0, 0))
    west_vertices.append(openstudio.Point3d(0, 0, 3))

    west_wall = openstudio.model.Surface(west_vertices, model)
    west_wall.setName("West Wall")
    west_wall.setSurfaceType("Wall")
    west_wall.setSpace(space)

    return model

# Usage
model = create_simple_box_building()
model.save(openstudio.path("simple_box.osm"), True)
print("Simple box building created!")
```

### Ruby

```ruby
require 'openstudio'

def create_simple_box_building
  """Create a simple 10x10x3m single-zone building."""
  model = OpenStudio::Model::Model.new

  # Create thermal zone
  zone = OpenStudio::Model::ThermalZone.new(model)
  zone.setName("Main Zone")

  # Create space
  space = OpenStudio::Model::Space.new(model)
  space.setName("Main Space")
  space.setThermalZone(zone)

  # Floor
  floor_vertices = OpenStudio::Point3dVector.new
  floor_vertices << OpenStudio::Point3d.new(0, 0, 0)
  floor_vertices << OpenStudio::Point3d.new(10, 0, 0)
  floor_vertices << OpenStudio::Point3d.new(10, 10, 0)
  floor_vertices << OpenStudio::Point3d.new(0, 10, 0)

  floor = OpenStudio::Model::Surface.new(floor_vertices, model)
  floor.setName("Floor")
  floor.setSurfaceType("Floor")
  floor.setSpace(space)

  # Ceiling
  ceiling_vertices = OpenStudio::Point3dVector.new
  ceiling_vertices << OpenStudio::Point3d.new(0, 10, 3)
  ceiling_vertices << OpenStudio::Point3d.new(10, 10, 3)
  ceiling_vertices << OpenStudio::Point3d.new(10, 0, 3)
  ceiling_vertices << OpenStudio::Point3d.new(0, 0, 3)

  ceiling = OpenStudio::Model::Surface.new(ceiling_vertices, model)
  ceiling.setName("Ceiling")
  ceiling.setSurfaceType("RoofCeiling")
  ceiling.setSpace(space)

  # South Wall
  south_vertices = OpenStudio::Point3dVector.new
  south_vertices << OpenStudio::Point3d.new(0, 0, 3)
  south_vertices << OpenStudio::Point3d.new(0, 0, 0)
  south_vertices << OpenStudio::Point3d.new(10, 0, 0)
  south_vertices << OpenStudio::Point3d.new(10, 0, 3)

  south_wall = OpenStudio::Model::Surface.new(south_vertices, model)
  south_wall.setName("South Wall")
  south_wall.setSurfaceType("Wall")
  south_wall.setSpace(space)

  # East Wall
  east_vertices = OpenStudio::Point3dVector.new
  east_vertices << OpenStudio::Point3d.new(10, 0, 3)
  east_vertices << OpenStudio::Point3d.new(10, 0, 0)
  east_vertices << OpenStudio::Point3d.new(10, 10, 0)
  east_vertices << OpenStudio::Point3d.new(10, 10, 3)

  east_wall = OpenStudio::Model::Surface.new(east_vertices, model)
  east_wall.setName("East Wall")
  east_wall.setSurfaceType("Wall")
  east_wall.setSpace(space)

  # North Wall
  north_vertices = OpenStudio::Point3dVector.new
  north_vertices << OpenStudio::Point3d.new(10, 10, 3)
  north_vertices << OpenStudio::Point3d.new(10, 10, 0)
  north_vertices << OpenStudio::Point3d.new(0, 10, 0)
  north_vertices << OpenStudio::Point3d.new(0, 10, 3)

  north_wall = OpenStudio::Model::Surface.new(north_vertices, model)
  north_wall.setName("North Wall")
  north_wall.setSurfaceType("Wall")
  north_wall.setSpace(space)

  # West Wall
  west_vertices = OpenStudio::Point3dVector.new
  west_vertices << OpenStudio::Point3d.new(0, 10, 3)
  west_vertices << OpenStudio::Point3d.new(0, 10, 0)
  west_vertices << OpenStudio::Point3d.new(0, 0, 0)
  west_vertices << OpenStudio::Point3d.new(0, 0, 3)

  west_wall = OpenStudio::Model::Surface.new(west_vertices, model)
  west_wall.setName("West Wall")
  west_wall.setSurfaceType("Wall")
  west_wall.setSpace(space)

  return model
end

# Usage
model = create_simple_box_building
model.save(OpenStudio::Path.new("simple_box.osm"), true)
puts "Simple box building created!"
```

---

## Pattern 2: Multi-Zone Building (2 Floors, 4 Zones)

**Use case:** Building with multiple zones and floors using space transformations.

**Layout:** 2 floors, 2 zones per floor (20m × 10m × 3m per floor)

### Python

```python
import openstudio

def create_multi_zone_building():
    """Create a 2-floor, 4-zone building using transformations."""
    model = openstudio.model.Model()

    # Function to create a single zone (10x10x3m)
    def create_zone_space(model, name, x_offset, y_offset, z_offset):
        """Create a single zone with space transformation."""
        zone = openstudio.model.ThermalZone(model)
        zone.setName(name)

        space = openstudio.model.Space(model)
        space.setName(f"{name} Space")
        space.setThermalZone(zone)

        # Apply transformation
        translation = openstudio.Vector3d(x_offset, y_offset, z_offset)
        transform = openstudio.Transformation.translation(translation)
        space.setTransformation(transform)

        # Create surfaces in local coordinates (0,0,0 origin)
        # Floor
        floor_vertices = openstudio.Point3dVector()
        floor_vertices.append(openstudio.Point3d(0, 0, 0))
        floor_vertices.append(openstudio.Point3d(10, 0, 0))
        floor_vertices.append(openstudio.Point3d(10, 10, 0))
        floor_vertices.append(openstudio.Point3d(0, 10, 0))
        floor = openstudio.model.Surface(floor_vertices, model)
        floor.setName(f"{name} Floor")
        floor.setSurfaceType("Floor")
        floor.setSpace(space)

        # Ceiling
        ceiling_vertices = openstudio.Point3dVector()
        ceiling_vertices.append(openstudio.Point3d(0, 10, 3))
        ceiling_vertices.append(openstudio.Point3d(10, 10, 3))
        ceiling_vertices.append(openstudio.Point3d(10, 0, 3))
        ceiling_vertices.append(openstudio.Point3d(0, 0, 3))
        ceiling = openstudio.model.Surface(ceiling_vertices, model)
        ceiling.setName(f"{name} Ceiling")
        ceiling.setSurfaceType("RoofCeiling")
        ceiling.setSpace(space)

        # Walls (4 walls per zone)
        # South (Y=0)
        south_v = openstudio.Point3dVector()
        south_v.append(openstudio.Point3d(0, 0, 3))
        south_v.append(openstudio.Point3d(0, 0, 0))
        south_v.append(openstudio.Point3d(10, 0, 0))
        south_v.append(openstudio.Point3d(10, 0, 3))
        south = openstudio.model.Surface(south_v, model)
        south.setName(f"{name} South Wall")
        south.setSurfaceType("Wall")
        south.setSpace(space)

        # East (X=10)
        east_v = openstudio.Point3dVector()
        east_v.append(openstudio.Point3d(10, 0, 3))
        east_v.append(openstudio.Point3d(10, 0, 0))
        east_v.append(openstudio.Point3d(10, 10, 0))
        east_v.append(openstudio.Point3d(10, 10, 3))
        east = openstudio.model.Surface(east_v, model)
        east.setName(f"{name} East Wall")
        east.setSurfaceType("Wall")
        east.setSpace(space)

        # North (Y=10)
        north_v = openstudio.Point3dVector()
        north_v.append(openstudio.Point3d(10, 10, 3))
        north_v.append(openstudio.Point3d(10, 10, 0))
        north_v.append(openstudio.Point3d(0, 10, 0))
        north_v.append(openstudio.Point3d(0, 10, 3))
        north = openstudio.model.Surface(north_v, model)
        north.setName(f"{name} North Wall")
        north.setSurfaceType("Wall")
        north.setSpace(space)

        # West (X=0)
        west_v = openstudio.Point3dVector()
        west_v.append(openstudio.Point3d(0, 10, 3))
        west_v.append(openstudio.Point3d(0, 10, 0))
        west_v.append(openstudio.Point3d(0, 0, 0))
        west_v.append(openstudio.Point3d(0, 0, 3))
        west = openstudio.model.Surface(west_v, model)
        west.setName(f"{name} West Wall")
        west.setSurfaceType("Wall")
        west.setSpace(space)

        return zone, space

    # Create 4 zones (2x2 grid, 2 floors)
    # Floor 1
    z1_sw, s1_sw = create_zone_space(model, "Floor1 Southwest", 0, 0, 0)
    z1_se, s1_se = create_zone_space(model, "Floor1 Southeast", 10, 0, 0)

    # Floor 2
    z2_sw, s2_sw = create_zone_space(model, "Floor2 Southwest", 0, 0, 3)
    z2_se, s2_se = create_zone_space(model, "Floor2 Southeast", 10, 0, 3)

    print(f"Created {len(model.getThermalZones())} zones")
    print(f"Created {len(model.getSpaces())} spaces")
    print(f"Created {len(model.getSurfaces())} surfaces")

    return model

# Usage
model = create_multi_zone_building()
model.save(openstudio.path("multi_zone.osm"), True)
```

---

## Pattern 3: Adding Windows to Walls

**Use case:** Add windows to existing walls with proper sizing and positioning.

### Python

```python
def add_windows_to_building(model, window_to_wall_ratio=0.4):
    """
    Add windows to all exterior walls.

    Args:
        model: OpenStudio model
        window_to_wall_ratio: Window area / Wall area (0.0 to 1.0)
    """
    walls = model.getSurfaces()
    window_count = 0

    for wall in walls:
        # Only add windows to exterior walls
        if (wall.surfaceType() == "Wall" and
            wall.outsideBoundaryCondition() == "Outdoors"):

            # Get wall vertices
            vertices = wall.vertices()
            if len(vertices) != 4:
                continue  # Skip non-rectangular walls

            # Calculate wall dimensions
            p1 = vertices[0]
            p2 = vertices[1]
            p3 = vertices[2]

            # Width (bottom edge)
            width = ((p2.x() - p1.x())**2 +
                     (p2.y() - p1.y())**2 +
                     (p2.z() - p1.z())**2)**0.5

            # Height (left edge)
            height = ((p1.x() - p3.x())**2 +
                      (p1.y() - p3.y())**2 +
                      (p1.z() - p3.z())**2)**0.5

            # Calculate window size (centered, with margins)
            margin = 0.5  # 0.5m margin from edges
            sill_height = 0.9  # 0.9m from floor
            head_height = height - margin  # 0.5m from ceiling

            window_height = head_height - sill_height
            window_width = width * (window_to_wall_ratio**0.5) - 2*margin

            if window_width <= 0 or window_height <= 0:
                continue

            # Center window horizontally
            x_start = (width - window_width) / 2

            # Create window vertices (in wall's local coordinates)
            # Assuming rectangular wall with p1=top-left, p2=bottom-left, etc.
            window_vertices = openstudio.Point3dVector()

            # For a south-facing wall (simplified)
            # Top-left corner of window
            window_vertices.append(openstudio.Point3d(
                p2.x() + x_start,
                p2.y(),
                p2.z() + sill_height + window_height
            ))
            # Bottom-left
            window_vertices.append(openstudio.Point3d(
                p2.x() + x_start,
                p2.y(),
                p2.z() + sill_height
            ))
            # Bottom-right
            window_vertices.append(openstudio.Point3d(
                p2.x() + x_start + window_width,
                p2.y(),
                p2.z() + sill_height
            ))
            # Top-right
            window_vertices.append(openstudio.Point3d(
                p2.x() + x_start + window_width,
                p2.y(),
                p2.z() + sill_height + window_height
            ))

            # Create window
            window = openstudio.model.SubSurface(window_vertices, model)
            window.setName(f"{wall.name()} Window")
            window.setSubSurfaceType("FixedWindow")
            window.setSurface(wall)

            window_count += 1

    print(f"Added {window_count} windows to the building")
    return model

# Usage
model = openstudio.model.Model.load("simple_box.osm").get()
model = add_windows_to_building(model, window_to_wall_ratio=0.4)
model.save(openstudio.path("building_with_windows.osm"), True)
```

---

## Pattern 4: L-Shaped Building

**Use case:** Non-rectangular building footprints using multiple spaces.

### Python

```python
def create_l_shaped_building():
    """
    Create an L-shaped building (two connected rectangles).

    Layout:
        [Zone A: 10x10m]
        [Zone B: 10x5m]
    """
    model = openstudio.model.Model()

    # Zone A: 10m x 10m (southwest corner)
    zone_a = openstudio.model.ThermalZone(model)
    zone_a.setName("Zone A")

    space_a = openstudio.model.Space(model)
    space_a.setName("Space A")
    space_a.setThermalZone(zone_a)

    # Zone A floor (10x10m at origin)
    floor_a = openstudio.Point3dVector()
    floor_a.append(openstudio.Point3d(0, 0, 0))
    floor_a.append(openstudio.Point3d(10, 0, 0))
    floor_a.append(openstudio.Point3d(10, 10, 0))
    floor_a.append(openstudio.Point3d(0, 10, 0))

    floor_a_surface = openstudio.model.Surface(floor_a, model)
    floor_a_surface.setName("Floor A")
    floor_a_surface.setSurfaceType("Floor")
    floor_a_surface.setSpace(space_a)

    # Zone A walls (4 walls)
    # South wall (Y=0)
    south_a = openstudio.Point3dVector()
    south_a.append(openstudio.Point3d(0, 0, 3))
    south_a.append(openstudio.Point3d(0, 0, 0))
    south_a.append(openstudio.Point3d(10, 0, 0))
    south_a.append(openstudio.Point3d(10, 0, 3))
    wall = openstudio.model.Surface(south_a, model)
    wall.setName("South Wall A")
    wall.setSurfaceType("Wall")
    wall.setSpace(space_a)

    # East wall (X=10, Y=0 to 5) - partial wall, shared with Zone B
    east_a = openstudio.Point3dVector()
    east_a.append(openstudio.Point3d(10, 0, 3))
    east_a.append(openstudio.Point3d(10, 0, 0))
    east_a.append(openstudio.Point3d(10, 5, 0))
    east_a.append(openstudio.Point3d(10, 5, 3))
    wall = openstudio.model.Surface(east_a, model)
    wall.setName("East Wall A Partial")
    wall.setSurfaceType("Wall")
    wall.setSpace(space_a)

    # North wall (Y=10)
    north_a = openstudio.Point3dVector()
    north_a.append(openstudio.Point3d(10, 10, 3))
    north_a.append(openstudio.Point3d(10, 10, 0))
    north_a.append(openstudio.Point3d(0, 10, 0))
    north_a.append(openstudio.Point3d(0, 10, 3))
    wall = openstudio.model.Surface(north_a, model)
    wall.setName("North Wall A")
    wall.setSurfaceType("Wall")
    wall.setSpace(space_a)

    # West wall (X=0)
    west_a = openstudio.Point3dVector()
    west_a.append(openstudio.Point3d(0, 10, 3))
    west_a.append(openstudio.Point3d(0, 10, 0))
    west_a.append(openstudio.Point3d(0, 0, 0))
    west_a.append(openstudio.Point3d(0, 0, 3))
    wall = openstudio.model.Surface(west_a, model)
    wall.setName("West Wall A")
    wall.setSurfaceType("Wall")
    wall.setSpace(space_a)

    # Zone B: 10m x 5m (extends east from Zone A)
    zone_b = openstudio.model.ThermalZone(model)
    zone_b.setName("Zone B")

    space_b = openstudio.model.Space(model)
    space_b.setName("Space B")
    space_b.setThermalZone(zone_b)

    # Zone B floor (10x5m, extends from X=10 to X=20)
    floor_b = openstudio.Point3dVector()
    floor_b.append(openstudio.Point3d(10, 0, 0))
    floor_b.append(openstudio.Point3d(20, 0, 0))
    floor_b.append(openstudio.Point3d(20, 5, 0))
    floor_b.append(openstudio.Point3d(10, 5, 0))

    floor_b_surface = openstudio.model.Surface(floor_b, model)
    floor_b_surface.setName("Floor B")
    floor_b_surface.setSurfaceType("Floor")
    floor_b_surface.setSpace(space_b)

    # Zone B walls
    # South wall (Y=0)
    south_b = openstudio.Point3dVector()
    south_b.append(openstudio.Point3d(10, 0, 3))
    south_b.append(openstudio.Point3d(10, 0, 0))
    south_b.append(openstudio.Point3d(20, 0, 0))
    south_b.append(openstudio.Point3d(20, 0, 3))
    wall = openstudio.model.Surface(south_b, model)
    wall.setName("South Wall B")
    wall.setSurfaceType("Wall")
    wall.setSpace(space_b)

    # East wall (X=20)
    east_b = openstudio.Point3dVector()
    east_b.append(openstudio.Point3d(20, 0, 3))
    east_b.append(openstudio.Point3d(20, 0, 0))
    east_b.append(openstudio.Point3d(20, 5, 0))
    east_b.append(openstudio.Point3d(20, 5, 3))
    wall = openstudio.model.Surface(east_b, model)
    wall.setName("East Wall B")
    wall.setSurfaceType("Wall")
    wall.setSpace(space_b)

    # North wall (Y=5)
    north_b = openstudio.Point3dVector()
    north_b.append(openstudio.Point3d(20, 5, 3))
    north_b.append(openstudio.Point3d(20, 5, 0))
    north_b.append(openstudio.Point3d(10, 5, 0))
    north_b.append(openstudio.Point3d(10, 5, 3))
    wall = openstudio.model.Surface(north_b, model)
    wall.setName("North Wall B")
    wall.setSurfaceType("Wall")
    wall.setSpace(space_b)

    # Add ceilings for both zones
    ceiling_a = openstudio.Point3dVector()
    ceiling_a.append(openstudio.Point3d(0, 10, 3))
    ceiling_a.append(openstudio.Point3d(10, 10, 3))
    ceiling_a.append(openstudio.Point3d(10, 0, 3))
    ceiling_a.append(openstudio.Point3d(0, 0, 3))
    ceiling = openstudio.model.Surface(ceiling_a, model)
    ceiling.setName("Ceiling A")
    ceiling.setSurfaceType("RoofCeiling")
    ceiling.setSpace(space_a)

    ceiling_b = openstudio.Point3dVector()
    ceiling_b.append(openstudio.Point3d(10, 5, 3))
    ceiling_b.append(openstudio.Point3d(20, 5, 3))
    ceiling_b.append(openstudio.Point3d(20, 0, 3))
    ceiling_b.append(openstudio.Point3d(10, 0, 3))
    ceiling = openstudio.model.Surface(ceiling_b, model)
    ceiling.setName("Ceiling B")
    ceiling.setSurfaceType("RoofCeiling")
    ceiling.setSpace(space_b)

    print("L-shaped building created")
    print(f"  Zones: {len(model.getThermalZones())}")
    print(f"  Surfaces: {len(model.getSurfaces())}")

    return model

# Usage
model = create_l_shaped_building()
model.save(openstudio.path("l_shaped_building.osm"), True)
```

---

## Pattern 5: Parametric Building Function

**Use case:** Create buildings with variable dimensions programmatically.

### Python

```python
def create_parametric_building(length, width, height, num_floors=1):
    """
    Create a rectangular building with parametric dimensions.

    Args:
        length: Building length in X direction (meters)
        width: Building width in Y direction (meters)
        height: Floor height (meters)
        num_floors: Number of floors (default: 1)

    Returns:
        OpenStudio model
    """
    model = openstudio.model.Model()

    for floor_num in range(num_floors):
        z_offset = floor_num * height

        # Create zone for this floor
        zone = openstudio.model.ThermalZone(model)
        zone.setName(f"Floor {floor_num + 1} Zone")

        # Create space
        space = openstudio.model.Space(model)
        space.setName(f"Floor {floor_num + 1} Space")
        space.setThermalZone(zone)

        # Apply transformation for upper floors
        if z_offset > 0:
            translation = openstudio.Vector3d(0, 0, z_offset)
            transform = openstudio.Transformation.translation(translation)
            space.setTransformation(transform)

        # Floor
        floor_v = openstudio.Point3dVector()
        floor_v.append(openstudio.Point3d(0, 0, 0))
        floor_v.append(openstudio.Point3d(length, 0, 0))
        floor_v.append(openstudio.Point3d(length, width, 0))
        floor_v.append(openstudio.Point3d(0, width, 0))
        floor = openstudio.model.Surface(floor_v, model)
        floor.setName(f"Floor {floor_num + 1}")
        floor.setSurfaceType("Floor")
        floor.setSpace(space)

        # Ceiling
        ceiling_v = openstudio.Point3dVector()
        ceiling_v.append(openstudio.Point3d(0, width, height))
        ceiling_v.append(openstudio.Point3d(length, width, height))
        ceiling_v.append(openstudio.Point3d(length, 0, height))
        ceiling_v.append(openstudio.Point3d(0, 0, height))
        ceiling = openstudio.model.Surface(ceiling_v, model)
        ceiling.setName(f"Ceiling {floor_num + 1}")
        ceiling.setSurfaceType("RoofCeiling")
        ceiling.setSpace(space)

        # Four walls
        # South
        south_v = openstudio.Point3dVector()
        south_v.append(openstudio.Point3d(0, 0, height))
        south_v.append(openstudio.Point3d(0, 0, 0))
        south_v.append(openstudio.Point3d(length, 0, 0))
        south_v.append(openstudio.Point3d(length, 0, height))
        south = openstudio.model.Surface(south_v, model)
        south.setName(f"Floor {floor_num + 1} South Wall")
        south.setSurfaceType("Wall")
        south.setSpace(space)

        # East
        east_v = openstudio.Point3dVector()
        east_v.append(openstudio.Point3d(length, 0, height))
        east_v.append(openstudio.Point3d(length, 0, 0))
        east_v.append(openstudio.Point3d(length, width, 0))
        east_v.append(openstudio.Point3d(length, width, height))
        east = openstudio.model.Surface(east_v, model)
        east.setName(f"Floor {floor_num + 1} East Wall")
        east.setSurfaceType("Wall")
        east.setSpace(space)

        # North
        north_v = openstudio.Point3dVector()
        north_v.append(openstudio.Point3d(length, width, height))
        north_v.append(openstudio.Point3d(length, width, 0))
        north_v.append(openstudio.Point3d(0, width, 0))
        north_v.append(openstudio.Point3d(0, width, height))
        north = openstudio.model.Surface(north_v, model)
        north.setName(f"Floor {floor_num + 1} North Wall")
        north.setSurfaceType("Wall")
        north.setSpace(space)

        # West
        west_v = openstudio.Point3dVector()
        west_v.append(openstudio.Point3d(0, width, height))
        west_v.append(openstudio.Point3d(0, width, 0))
        west_v.append(openstudio.Point3d(0, 0, 0))
        west_v.append(openstudio.Point3d(0, 0, height))
        west = openstudio.model.Surface(west_v, model)
        west.setName(f"Floor {floor_num + 1} West Wall")
        west.setSurfaceType("Wall")
        west.setSpace(space)

    print(f"Created {length}m × {width}m × {height}m building with {num_floors} floor(s)")
    print(f"  Total zones: {len(model.getThermalZones())}")
    print(f"  Total surfaces: {len(model.getSurfaces())}")

    return model

# Usage examples
small_building = create_parametric_building(8, 6, 2.7)
large_building = create_parametric_building(50, 30, 4, num_floors=5)

small_building.save(openstudio.path("small_building.osm"), True)
large_building.save(openstudio.path("large_building.osm"), True)
```

---

## Key Geometry Concepts

### Vertex Ordering Rules

**Always counter-clockwise when viewed from outside:**

```
Floor (viewed from above/outside the building):
  3 ←---- 2
  |       ↑
  ↓       |
  0 ---→  1

Wall (viewed from outside the building):
  0 ←---- 3
  |       ↑
  ↓       |
  1 ---→  2
```

### Space Transformations

Transformations position spaces in the model without redefining vertices:

```python
# No transformation - space at origin (0, 0, 0)
space1 = openstudio.model.Space(model)

# Translate 10m in X direction
space2 = openstudio.model.Space(model)
translation = openstudio.Vector3d(10, 0, 0)
transform = openstudio.Transformation.translation(translation)
space2.setTransformation(transform)

# Both spaces use same vertex coordinates,
# but space2 is positioned 10m east of space1
```

### Common Pitfalls

1. **Wrong vertex order** - Clockwise instead of counter-clockwise
2. **Orphaned surfaces** - Not assigned to a space
3. **Overlapping geometry** - Two surfaces occupying same space
4. **Non-planar surfaces** - Vertices not in same plane
5. **Missing surfaces** - Incomplete enclosure (no ceiling, etc.)

---

## See Also

- **Quick reference:** `docs/quick-reference/python-cheatsheet.md`, `ruby-cheatsheet.md`
- **HVAC patterns:** `docs/openstudio-sdk/hvac-patterns.md`
- **Error debugging:** `docs/error-solutions/openstudio-errors.md`
- **Complete examples:** `examples/02_ruby_necb_compliance/`, `examples/03_python_ruby_interop/`

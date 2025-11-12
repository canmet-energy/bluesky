# OpenStudio HVAC System Patterns

Complete, runnable patterns for common HVAC systems.

Each pattern is production-ready and can be adapted to your specific needs.

---

## Pattern 1: Ideal Air Loads (Testing/Sizing)

**Use case:** Quick testing, load calculations, or baseline without detailed HVAC.

**System:** Infinite heating/cooling capacity, perfect control.

### Python

```python
import openstudio

def add_ideal_air_loads(model):
    """Add ideal air loads to all thermal zones."""
    zones = model.getThermalZones()

    for zone in zones:
        # Create ideal air loads object
        ideal_loads = openstudio.model.ZoneHVACIdealLoadsAirSystem(model)
        ideal_loads.setName(f"{zone.name()} Ideal Loads")

        # Optional: Set limits
        ideal_loads.setMaximumHeatingSupplyAirTemperature(50.0)  # °C
        ideal_loads.setMinimumCoolingSupplyAirTemperature(13.0)  # °C
        ideal_loads.setMaximumHeatingSupplyAirHumidityRatio(0.015)  # kg-H2O/kg-air
        ideal_loads.setMinimumCoolingSupplyAirHumidityRatio(0.008)

        # Add to zone
        ideal_loads.addToThermalZone(zone)

    print(f"Added ideal air loads to {len(zones)} zones")
    return model

# Usage
model = openstudio.model.Model.load("building.osm").get()
model = add_ideal_air_loads(model)
model.save(openstudio.path("building_with_ideal_loads.osm"), True)
```

**When to use:**
- Quick load calculations
- Comparing envelope options
- Validating geometry before adding real HVAC
- Educational/demonstration purposes

---

## Pattern 2: PSZ-AC (Packaged Single Zone Air Conditioner)

**Use case:** Small commercial buildings, each zone has own packaged unit.

**Components:** Fan → Heating Coil → DX Cooling Coil → Zone

### Python

```python
import openstudio

def add_psz_ac_system(model, zone):
    """
    Add Packaged Single Zone (PSZ-AC) system to a zone.

    Components:
    - Constant volume fan
    - Electric or gas heating coil
    - DX single-speed cooling coil
    - Single zone reheat setpoint manager
    """
    # Create air loop
    air_loop = openstudio.model.AirLoopHVAC(model)
    air_loop.setName(f"{zone.name()} PSZ-AC")

    # Create always-on schedule
    always_on = openstudio.model.ScheduleConstant(model)
    always_on.setName("Always On")
    always_on.setValue(1.0)

    # Create fan
    fan = openstudio.model.FanConstantVolume(model, always_on)
    fan.setName(f"{zone.name()} Supply Fan")
    fan.setFanEfficiency(0.6)
    fan.setPressureRise(500.0)  # Pa
    fan.setMotorEfficiency(0.9)

    # Create heating coil (electric)
    heating_coil = openstudio.model.CoilHeatingElectric(model, always_on)
    heating_coil.setName(f"{zone.name()} Heating Coil")
    heating_coil.setEfficiency(1.0)

    # Alternative: Gas heating coil
    # heating_coil = openstudio.model.CoilHeatingGas(model, always_on)
    # heating_coil.setGasBurnerEfficiency(0.8)

    # Create cooling coil (DX single speed)
    cooling_coil = openstudio.model.CoilCoolingDXSingleSpeed(model, always_on)
    cooling_coil.setName(f"{zone.name()} DX Cooling Coil")

    # Add components to air loop in order
    supply_inlet = air_loop.supplyInletNode()
    fan.addToNode(supply_inlet)
    heating_coil.addToNode(supply_inlet)
    cooling_coil.addToNode(supply_inlet)

    # Create air terminal (uncontrolled - packaged unit serves single zone)
    terminal = openstudio.model.AirTerminalSingleDuctUncontrolled(model, always_on)
    terminal.setName(f"{zone.name()} Terminal")

    # Connect zone to air loop
    air_loop.addBranchForZone(zone, terminal.to_StraightComponent())

    # Add setpoint manager (REQUIRED!)
    setpoint_mgr = openstudio.model.SetpointManagerSingleZoneReheat(model)
    setpoint_mgr.setName(f"{zone.name()} Setpoint Manager")
    setpoint_mgr.setControlZone(zone)
    setpoint_mgr.setMinimumSupplyAirTemperature(13.0)  # °C
    setpoint_mgr.setMaximumSupplyAirTemperature(50.0)  # °C

    supply_outlet = air_loop.supplyOutletNode()
    setpoint_mgr.addToNode(supply_outlet)

    print(f"Added PSZ-AC system to {zone.name()}")
    return air_loop

# Usage
model = openstudio.model.Model.load("building.osm").get()
zones = model.getThermalZones()

for zone in zones:
    add_psz_ac_system(model, zone)

model.save(openstudio.path("building_with_psz.osm"), True)
```

---

## Pattern 3: VAV with Reheat (Variable Air Volume)

**Use case:** Large commercial buildings with varying loads across zones.

**Components:** VAV Fan → Cooling Coil → VAV Terminals (with reheat) → Zones

### Python

```python
import openstudio

def add_vav_system(model, zones):
    """
    Add Variable Air Volume (VAV) system serving multiple zones.

    Components:
    - Variable speed fan
    - Chilled water or DX cooling coil
    - VAV terminals with hot water reheat coils
    """
    # Create air loop
    air_loop = openstudio.model.AirLoopHVAC(model)
    air_loop.setName("VAV System")

    # Create schedules
    always_on = openstudio.model.ScheduleConstant(model)
    always_on.setValue(1.0)

    # Create variable speed fan
    fan = openstudio.model.FanVariableVolume(model, always_on)
    fan.setName("VAV Supply Fan")
    fan.setFanEfficiency(0.65)
    fan.setPressureRise(1000.0)  # Pa (higher than constant volume)
    fan.setMotorEfficiency(0.9)
    fan.setFanPowerMinimumFlowRateInputMethod("Fraction")
    fan.setFanPowerMinimumFlowFraction(0.25)  # 25% minimum flow

    # Create cooling coil (DX two-speed for VAV)
    cooling_coil = openstudio.model.CoilCoolingDXTwoSpeed(model, always_on)
    cooling_coil.setName("VAV Cooling Coil")

    # Add components to supply side
    supply_inlet = air_loop.supplyInletNode()
    fan.addToNode(supply_inlet)
    cooling_coil.addToNode(supply_inlet)

    # Add setpoint manager (scheduled reset for VAV)
    # Create reset schedule (55-60°F / 13-16°C)
    sched = openstudio.model.ScheduleConstant(model)
    sched.setValue(13.0)  # °C supply air temp

    setpoint_mgr = openstudio.model.SetpointManagerScheduled(model, sched)
    setpoint_mgr.setName("VAV Supply Air Temp Manager")

    supply_outlet = air_loop.supplyOutletNode()
    setpoint_mgr.addToNode(supply_outlet)

    # Add VAV terminals with reheat to each zone
    for zone in zones:
        # Create electric reheat coil for terminal
        reheat_coil = openstudio.model.CoilHeatingElectric(model, always_on)
        reheat_coil.setName(f"{zone.name()} Reheat Coil")

        # Create VAV terminal with reheat
        terminal = openstudio.model.AirTerminalSingleDuctVAVReheat(
            model, always_on, reheat_coil
        )
        terminal.setName(f"{zone.name()} VAV Terminal")
        terminal.setZoneMinimumAirFlowMethod("Constant")
        terminal.setConstantMinimumAirFlowFraction(0.3)  # 30% minimum

        # Connect zone to air loop
        air_loop.addBranchForZone(zone, terminal.to_StraightComponent())

    print(f"Added VAV system serving {len(zones)} zones")
    return air_loop

# Usage
model = openstudio.model.Model.load("building.osm").get()
zones = model.getThermalZones()

# Group zones that should be served by same VAV system
vav_system = add_vav_system(model, zones)

model.save(openstudio.path("building_with_vav.osm"), True)
```

---

## Pattern 4: PTAC (Packaged Terminal Air Conditioner)

**Use case:** Hotels, apartments, individual zone control.

**Components:** Zone equipment (no air loop) - each zone has wall-mounted unit.

### Python

```python
import openstudio

def add_ptac_system(model, zone):
    """
    Add Packaged Terminal Air Conditioner (PTAC) to a zone.

    Components:
    - Zone HVAC equipment (not air loop)
    - Fan
    - Heating coil
    - DX cooling coil
    """
    # Create schedules
    always_on = openstudio.model.ScheduleConstant(model)
    always_on.setValue(1.0)

    # Create fan (on/off for PTAC)
    fan = openstudio.model.FanOnOff(model, always_on)
    fan.setName(f"{zone.name()} PTAC Fan")
    fan.setFanEfficiency(0.5)  # Lower efficiency for small unit
    fan.setPressureRise(75.0)  # Pa (much lower than air loop)

    # Create heating coil (typically electric for PTAC)
    heating_coil = openstudio.model.CoilHeatingElectric(model, always_on)
    heating_coil.setName(f"{zone.name()} PTAC Heating")

    # Create cooling coil (DX single speed)
    cooling_coil = openstudio.model.CoilCoolingDXSingleSpeed(model, always_on)
    cooling_coil.setName(f"{zone.name()} PTAC Cooling")

    # Create PTAC unit
    ptac = openstudio.model.ZoneHVACPackagedTerminalAirConditioner(
        model, always_on, fan, heating_coil, cooling_coil
    )
    ptac.setName(f"{zone.name()} PTAC")
    ptac.setSupplyAirFlowRateDuringCoolingOperation(0.5)  # m³/s
    ptac.setSupplyAirFlowRateDuringHeatingOperation(0.5)
    ptac.setSupplyAirFlowRateWhenNoCoolingorHeatingisNeeded(0.3)
    ptac.setOutdoorAirFlowRateDuringCoolingOperation(0.1)  # m³/s
    ptac.setOutdoorAirFlowRateDuringHeatingOperation(0.1)
    ptac.setOutdoorAirFlowRateWhenNoCoolingorHeatingisNeeded(0.05)

    # Add to zone
    ptac.addToThermalZone(zone)

    print(f"Added PTAC to {zone.name()}")
    return ptac

# Usage
model = openstudio.model.Model.load("building.osm").get()
zones = model.getThermalZones()

for zone in zones:
    add_ptac_system(model, zone)

model.save(openstudio.path("building_with_ptac.osm"), True)
```

---

## Pattern 5: Baseboard Heating (No Cooling)

**Use case:** Residential, mild climates, heating-only.

**Components:** Zone equipment - baseboard heaters (electric or hot water).

### Python

```python
import openstudio

def add_baseboard_heating(model, zone, fuel_type="electric"):
    """
    Add baseboard heating to a zone.

    Args:
        model: OpenStudio model
        zone: Thermal zone
        fuel_type: "electric" or "hot_water"
    """
    # Create schedules
    always_on = openstudio.model.ScheduleConstant(model)
    always_on.setValue(1.0)

    if fuel_type == "electric":
        # Electric baseboard
        baseboard = openstudio.model.ZoneHVACBaseboardConvectiveElectric(model)
        baseboard.setName(f"{zone.name()} Electric Baseboard")
        baseboard.setAvailabilitySchedule(always_on)
        baseboard.setNominalCapacity(2000.0)  # Watts (will autosize)
        baseboard.setEfficiency(1.0)

    elif fuel_type == "hot_water":
        # Hot water baseboard (requires plant loop - see Pattern 6)
        baseboard = openstudio.model.ZoneHVACBaseboardConvectiveWater(model)
        baseboard.setName(f"{zone.name()} HW Baseboard")
        baseboard.setAvailabilitySchedule(always_on)

        # Create heating coil
        heating_coil = openstudio.model.CoilHeatingWaterBaseboard(model)
        heating_coil.setName(f"{zone.name()} BB Coil")
        baseboard.setHeatingCoil(heating_coil)

        # Note: Must connect to hot water plant loop (see Pattern 6)

    # Add to zone
    baseboard.addToThermalZone(zone)

    print(f"Added {fuel_type} baseboard to {zone.name()}")
    return baseboard

# Usage
model = openstudio.model.Model.load("building.osm").get()
zones = model.getThermalZones()

for zone in zones:
    add_baseboard_heating(model, zone, fuel_type="electric")

model.save(openstudio.path("building_with_baseboard.osm"), True)
```

---

## Pattern 6: Plant Loop (Boiler for Hot Water)

**Use case:** Central heating plant serving multiple zones via hot water.

**Components:** Boiler → Pump → Hot Water Loop → Zone Equipment

### Python

```python
import openstudio

def add_hot_water_plant_loop(model):
    """
    Create hot water plant loop with boiler.

    Returns:
        plant_loop: Hot water plant loop object
    """
    # Create plant loop
    plant_loop = openstudio.model.PlantLoop(model)
    plant_loop.setName("Hot Water Loop")

    # Set plant loop temperatures
    plant_loop.setMaximumLoopTemperature(100.0)  # °C
    plant_loop.setMinimumLoopTemperature(10.0)   # °C

    # Create sizing object
    sizing_plant = plant_loop.sizingPlant()
    sizing_plant.setLoopType("Heating")
    sizing_plant.setDesignLoopExitTemperature(82.0)  # °C (180°F)
    sizing_plant.setLoopDesignTemperatureDifference(11.0)  # °C (20°F)

    # Create setpoint manager for supply
    hw_temp_sch = openstudio.model.ScheduleConstant(model)
    hw_temp_sch.setName("HW Temp")
    hw_temp_sch.setValue(82.0)  # °C

    setpoint_mgr = openstudio.model.SetpointManagerScheduled(model, hw_temp_sch)
    setpoint_mgr.setName("HW Loop Setpoint Manager")
    setpoint_mgr.addToNode(plant_loop.supplyOutletNode())

    # Create boiler
    boiler = openstudio.model.BoilerHotWater(model)
    boiler.setName("Natural Gas Boiler")
    boiler.setFuelType("NaturalGas")
    boiler.setNominalThermalEfficiency(0.8)
    boiler.setNominalCapacity(100000.0)  # Watts (will autosize)

    # Add boiler to supply side
    plant_loop.addSupplyBranchForComponent(boiler)

    # Create pump
    pump = openstudio.model.PumpVariableSpeed(model)
    pump.setName("HW Circulation Pump")
    pump.setRatedFlowRate(0.001)  # m³/s (will autosize)
    pump.setRatedPumpHead(179352.0)  # Pa (60 ft head)
    pump.setMotorEfficiency(0.9)

    # Add pump to supply inlet
    pump.addToNode(plant_loop.supplyInletNode())

    print("Created hot water plant loop with boiler")
    return plant_loop

def connect_baseboard_to_plant_loop(model, zone, plant_loop):
    """Connect hot water baseboard to plant loop."""
    # Create baseboard with hot water coil
    always_on = openstudio.model.ScheduleConstant(model)
    always_on.setValue(1.0)

    baseboard = openstudio.model.ZoneHVACBaseboardConvectiveWater(model)
    baseboard.setName(f"{zone.name()} HW Baseboard")
    baseboard.setAvailabilitySchedule(always_on)

    heating_coil = openstudio.model.CoilHeatingWaterBaseboard(model)
    heating_coil.setName(f"{zone.name()} BB Coil")
    baseboard.setHeatingCoil(heating_coil)

    # Add baseboard to zone
    baseboard.addToThermalZone(zone)

    # Connect coil to plant loop (CRITICAL!)
    plant_loop.addDemandBranchForComponent(heating_coil)

    print(f"Connected {zone.name()} baseboard to plant loop")

# Usage
model = openstudio.model.Model.load("building.osm").get()

# Create hot water plant loop
hw_loop = add_hot_water_plant_loop(model)

# Connect all zones to the plant loop
zones = model.getThermalZones()
for zone in zones:
    connect_baseboard_to_plant_loop(model, zone, hw_loop)

model.save(openstudio.path("building_with_hw_plant.osm"), True)
```

---

## Complete HVAC + Building Example

### Complete PSZ-AC Building (Python)

```python
import openstudio

def create_complete_psz_building():
    """Create complete building with geometry + PSZ-AC HVAC."""
    model = openstudio.model.Model()

    # === GEOMETRY ===
    # Create zone and space
    zone = openstudio.model.ThermalZone(model)
    zone.setName("Office Zone")

    space = openstudio.model.Space(model)
    space.setName("Office Space")
    space.setThermalZone(zone)

    # Create simple box (10x10x3m) - see geometry-patterns.md for details
    # Floor
    floor_v = openstudio.Point3dVector()
    floor_v.append(openstudio.Point3d(0, 0, 0))
    floor_v.append(openstudio.Point3d(10, 0, 0))
    floor_v.append(openstudio.Point3d(10, 10, 0))
    floor_v.append(openstudio.Point3d(0, 10, 0))
    floor = openstudio.model.Surface(floor_v, model)
    floor.setSurfaceType("Floor")
    floor.setSpace(space)

    # ... (create ceiling and 4 walls - see Pattern 1 in geometry-patterns.md)

    # === THERMOSTAT ===
    heating_sch = openstudio.model.ScheduleConstant(model)
    heating_sch.setValue(20.0)
    cooling_sch = openstudio.model.ScheduleConstant(model)
    cooling_sch.setValue(24.0)

    thermostat = openstudio.model.ThermostatSetpointDualSetpoint(model)
    thermostat.setHeatingSetpointTemperatureSchedule(heating_sch)
    thermostat.setCoolingSetpointTemperatureSchedule(cooling_sch)
    zone.setThermostatSetpointDualSetpoint(thermostat)

    # === HVAC (PSZ-AC) ===
    air_loop = openstudio.model.AirLoopHVAC(model)
    always_on = openstudio.model.ScheduleConstant(model)
    always_on.setValue(1.0)

    # Fan
    fan = openstudio.model.FanConstantVolume(model, always_on)
    fan.setPressureRise(500.0)

    # Heating coil
    heating_coil = openstudio.model.CoilHeatingElectric(model, always_on)

    # Cooling coil
    cooling_coil = openstudio.model.CoilCoolingDXSingleSpeed(model, always_on)

    # Add to air loop
    supply_inlet = air_loop.supplyInletNode()
    fan.addToNode(supply_inlet)
    heating_coil.addToNode(supply_inlet)
    cooling_coil.addToNode(supply_inlet)

    # Terminal
    terminal = openstudio.model.AirTerminalSingleDuctUncontrolled(model, always_on)
    air_loop.addBranchForZone(zone, terminal.to_StraightComponent())

    # Setpoint manager
    setpoint_mgr = openstudio.model.SetpointManagerSingleZoneReheat(model)
    setpoint_mgr.setControlZone(zone)
    setpoint_mgr.addToNode(air_loop.supplyOutletNode())

    # === SIMULATION SETTINGS ===
    sim_control = model.getSimulationControl()
    sim_control.setRunSimulationforSizingPeriods(True)

    timestep = model.getTimestep()
    timestep.setNumberOfTimestepsPerHour(4)

    print("Complete PSZ-AC building created")
    return model

# Usage
model = create_complete_psz_building()
model.save(openstudio.path("complete_psz_building.osm"), True)
```

---

## HVAC System Comparison

| System | Zones Served | Complexity | Use Case | Energy Efficiency |
|--------|--------------|------------|----------|-------------------|
| **Ideal Loads** | Any | Very Low | Testing only | N/A |
| **PSZ-AC** | 1 per system | Low | Small commercial | Moderate |
| **VAV** | Multiple | High | Large commercial | Good |
| **PTAC** | 1 per unit | Low | Hotels, apartments | Moderate-Low |
| **Baseboard** | 1 per zone | Very Low | Residential, heating | Good (electric), Excellent (HW) |
| **Plant Loop** | Multiple | High | Central plants | Excellent |

---

## Key HVAC Concepts

### Node Connections

HVAC components connect via nodes. Flow must be continuous:

```
Supply Inlet Node → Fan → Coil → Coil → Supply Outlet Node → Zones
```

### Setpoint Managers

**Every air loop MUST have a setpoint manager** on the supply outlet node:

```python
# WRONG - No setpoint manager
air_loop = openstudio.model.AirLoopHVAC(model)
# Add components...
# Missing setpoint manager!

# CORRECT
setpoint_mgr = openstudio.model.SetpointManagerSingleZoneReheat(model)
setpoint_mgr.setControlZone(zone)
setpoint_mgr.addToNode(air_loop.supplyOutletNode())  # REQUIRED!
```

### Autosizing

Most HVAC components can autosize:

```python
fan = openstudio.model.FanConstantVolume(model, schedule)
# Don't set maximum flow rate - let it autosize
# OR explicitly set to autosize
# fan.autosizeMaximumFlowRate()
```

Run EnergyPlus with sizing periods to calculate autosized values.

---

## Common HVAC Pitfalls

1. **Missing setpoint manager** - Air loop won't control properly
2. **Components in wrong order** - Fan should be first on supply side
3. **No thermostat** - Zone won't be controlled
4. **No demand components** - Plant loop with boiler but no loads
5. **Forgot to connect zone** - Air loop created but zone not connected

---

## See Also

- **Quick reference:** `docs/quick-reference/python-cheatsheet.md`, `ruby-cheatsheet.md`
- **Geometry patterns:** `docs/openstudio-sdk/geometry-patterns.md`
- **Error debugging:** `docs/error-solutions/openstudio-errors.md`, `energyplus-errors.md`
- **NECB systems:** `docs/openstudio-standards/necb-guide.md` (Phase 3)
- **Complete examples:** `examples/02_ruby_necb_compliance/` (uses openstudio-standards)

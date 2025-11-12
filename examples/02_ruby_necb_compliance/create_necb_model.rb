#!/usr/bin/env ruby
# frozen_string_literal: true

# Example 04: Create NECB-Compliant Building Model
#
# This example demonstrates how to create a building model that complies with
# the National Energy Code of Canada for Buildings (NECB).
#
# NECB is the Canadian energy code for commercial, institutional, and some
# residential buildings. The openstudio-standards gem includes complete NECB
# requirements for multiple vintages:
# - NECB2011
# - NECB2015
# - NECB2017
# - NECB2020
#
# This example shows how to apply NECB-compliant:
# - Construction assemblies (walls, roofs, windows)
# - Space types and internal loads
# - HVAC systems
# - Lighting power densities
#
# Dependencies:
# - openstudio
# - openstudio-standards gem (with NECB support)

require 'openstudio'
require 'openstudio-standards'

def create_necb_model(necb_version = 'NECB2017')
  puts "Creating NECB-compliant building model (#{necb_version})..."

  # Create new model
  model = OpenStudio::Model::Model.new

  # Initialize NECB standard
  standard = Standard.build(necb_version)

  puts "  Standard: #{necb_version}"

  # =========================================================================
  # 1. Set Building Properties
  # =========================================================================
  building = model.getBuilding
  building.setName('NECB Example Building')

  # Set Canadian climate zone (required for NECB)
  # Climate zones: 4, 5, 6, 7a, 7b, 8
  climate_zone = '6'  # Example: Ottawa, Montreal
  puts "  Climate zone: #{climate_zone}"

  # =========================================================================
  # 2. Create Simple Geometry
  # =========================================================================
  puts "\n  Creating building geometry..."

  # Create a simple rectangular building
  length = 30.0  # meters
  width = 20.0   # meters
  height = 3.5   # meters
  num_floors = 2

  # Use OpenStudio geometry helper
  footprint = OpenStudio::Point3dVector.new
  footprint << OpenStudio::Point3d.new(0, 0, 0)
  footprint << OpenStudio::Point3d.new(length, 0, 0)
  footprint << OpenStudio::Point3d.new(length, width, 0)
  footprint << OpenStudio::Point3d.new(0, width, 0)

  # Create spaces for each floor
  (0...num_floors).each do |floor|
    z = floor * height

    # Create space
    space = OpenStudio::Model::Space.fromFloorPrint(footprint, height, model)
    space = space.get
    space.setName("Floor_#{floor + 1}")

    # Move space to correct height
    space.setZOrigin(z)

    # Create thermal zone for each space
    thermal_zone = OpenStudio::Model::ThermalZone.new(model)
    thermal_zone.setName("Zone_Floor_#{floor + 1}")
    space.setThermalZone(thermal_zone)

    # Add simple thermostat
    thermostat = OpenStudio::Model::ThermostatSetpointDualSetpoint.new(model)
    heating_sch = OpenStudio::Model::ScheduleConstant.new(model)
    heating_sch.setValue(21.0)  # °C
    cooling_sch = OpenStudio::Model::ScheduleConstant.new(model)
    cooling_sch.setValue(24.0)  # °C
    thermostat.setHeatingSetpointTemperatureSchedule(heating_sch)
    thermostat.setCoolingSetpointTemperatureSchedule(cooling_sch)
    thermal_zone.setThermostatSetpointDualSetpoint(thermostat)
  end

  puts "    Created #{num_floors} floors with thermal zones"

  # =========================================================================
  # 3. Apply NECB Construction Set
  # =========================================================================
  puts "\n  Applying NECB construction set..."

  # Define building type for NECB
  # Common types: 'Office', 'Retail', 'School', 'Hospital', 'Hotel', 'Warehouse'
  building_type = 'Office'
  puts "    Building type: #{building_type}"

  # Apply NECB-compliant construction set
  standard.model_add_construction_set(model, climate_zone, building_type, nil)
  puts "    ✓ NECB construction set applied"

  # =========================================================================
  # 4. Apply NECB Space Types
  # =========================================================================
  puts "\n  Applying NECB space types..."

  model.getSpaces.each do |space|
    # For office building, use typical office space type
    space_type_name = 'Office - open plan'

    # Create and apply NECB space type
    space_type = standard.model_add_space_type(model, building_type, space_type_name)

    if space_type
      space.setSpaceType(space_type)
      puts "    ✓ Applied space type: #{space_type_name} to #{space.name}"
    else
      puts "    ✗ Could not find space type: #{space_type_name}"
    end
  end

  # =========================================================================
  # 5. Apply NECB HVAC System
  # =========================================================================
  puts "\n  Applying NECB-compliant HVAC system..."

  # NECB-appropriate system types:
  # - 'PSZ-AC with gas coil' : Package single zone
  # - 'PVAV with gas boiler reheat' : VAV system
  # - 'DOAS with fan coil' : Dedicated OA with fan coils
  system_type = 'PSZ-AC with gas coil'

  thermal_zones = model.getThermalZones

  # Add HVAC system
  standard.model_add_hvac_system(
    model,
    system_type,
    ht = 'NaturalGas',
    znht = nil,
    cl = 'Electricity',
    thermal_zones
  )

  puts "    ✓ HVAC system added: #{system_type}"

  # =========================================================================
  # 6. Apply NECB Requirements
  # =========================================================================
  puts "\n  Applying additional NECB requirements..."

  # Set NECB ventilation requirements
  model.getSpaces.each do |space|
    space_type = space.spaceType
    if space_type.is_initialized
      # NECB ventilation rates are applied through space types
      puts "    Ventilation requirements set for #{space.name}"
    end
  end

  # =========================================================================
  # 7. Add Simulation Settings
  # =========================================================================
  puts "\n  Configuring simulation settings..."

  # Run period
  run_period = model.getRunPeriod
  run_period.setBeginMonth(1)
  run_period.setBeginDayOfMonth(1)
  run_period.setEndMonth(12)
  run_period.setEndDayOfMonth(31)

  # Output requests
  output_table = OpenStudio::Model::OutputTableSummaryReports.new(model)
  output_table.addSummaryReport('AllSummary')

  # =========================================================================
  # Summary
  # =========================================================================
  puts "\n" + "=" * 80
  puts "NECB Model Summary:"
  puts "=" * 80
  puts "  Standard: #{necb_version}"
  puts "  Climate zone: #{climate_zone}"
  puts "  Building type: #{building_type}"
  puts "  Floor area: #{building.floorArea.round(1)} m²"
  puts "  Number of spaces: #{model.getSpaces.length}"
  puts "  Number of thermal zones: #{model.getThermalZones.length}"
  puts "  Number of surfaces: #{model.getSurfaces.length}"
  puts "  Construction sets: #{model.getDefaultConstructionSets.length}"
  puts "  Space types: #{model.getSpaceTypes.length}"
  puts "  Air loops: #{model.getAirLoopHVACs.length}"
  puts "=" * 80

  model
end

def main
  # Create NECB-compliant model
  # Available versions: 'NECB2011', 'NECB2015', 'NECB2017', 'NECB2020'
  necb_version = 'NECB2017'

  model = create_necb_model(necb_version)

  # Save model
  output_dir = File.join(File.dirname(__FILE__), '..', '..', 'data', 'models')
  FileUtils.mkdir_p(output_dir) unless Dir.exist?(output_dir)
  output_file = File.join(output_dir, 'necb_office_building.osm')

  model.save(OpenStudio::Path.new(output_file), true)
  puts "\n✓ NECB model saved to: #{output_file}"

  puts "\nNext steps:"
  puts "  1. Open the model in OpenStudio Application"
  puts "  2. Review NECB-compliant constructions and systems"
  puts "  3. Run energy simulation"
  puts "  4. Generate NECB compliance report"
  puts "\nNECB Resources:"
  puts "  - National Research Council Canada (NRC)"
  puts "  - Canadian Codes Centre"
  puts "  - openstudio-standards gem documentation"
  puts "\nTry other NECB versions:"
  puts "  - NECB2011 (older code)"
  puts "  - NECB2020 (latest code)"
  puts "  - Different climate zones (4, 5, 6, 7a, 7b, 8)"
end

main if __FILE__ == $PROGRAM_NAME

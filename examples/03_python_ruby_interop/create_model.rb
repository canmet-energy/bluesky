#!/usr/bin/env ruby
# frozen_string_literal: true

# Interop Example - Part 1: Ruby creates model with openstudio-standards
#
# This Ruby script leverages openstudio-standards to create a building model,
# then passes it to Python for parametric analysis.

require 'openstudio'
require 'openstudio-standards'
require 'json'

def create_standards_based_model
  model = OpenStudio::Model::Model.new
  standard = Standard.build('NECB2017')

  # Create simple geometry
  length = 20.0
  width = 15.0
  height = 3.0

  footprint = OpenStudio::Point3dVector.new
  footprint << OpenStudio::Point3d.new(0, 0, 0)
  footprint << OpenStudio::Point3d.new(length, 0, 0)
  footprint << OpenStudio::Point3d.new(length, width, 0)
  footprint << OpenStudio::Point3d.new(0, width, 0)

  space = OpenStudio::Model::Space.fromFloorPrint(footprint, height, model).get
  thermal_zone = OpenStudio::Model::ThermalZone.new(model)
  space.setThermalZone(thermal_zone)

  # Apply NECB standards
  standard.model_add_construction_set(model, '6', 'Office', nil)
  space_type = standard.model_add_space_type(model, 'Office', 'Office - open plan')
  space.setSpaceType(space_type) if space_type

  # Add HVAC
  standard.model_add_hvac_system(model, 'PSZ-AC with gas coil', 'NaturalGas', nil, 'Electricity', [thermal_zone])

  model
end

def main
  puts "Creating NECB-based model with Ruby..."
  model = create_standards_based_model

  # Save model
  output_dir = File.join(File.dirname(__FILE__), 'output')
  Dir.mkdir(output_dir) unless Dir.exist?(output_dir)

  model_path = File.join(output_dir, 'baseline_model.osm')
  model.save(OpenStudio::Path.new(model_path), true)

  # Write metadata for Python
  metadata = {
    'model_path' => model_path,
    'standard' => 'NECB2017',
    'building_type' => 'Office',
    'floor_area_m2' => model.getBuilding.floorArea
  }

  File.write(File.join(output_dir, 'model_metadata.json'), JSON.pretty_generate(metadata))

  puts "✓ Model saved: #{model_path}"
  puts "✓ Metadata saved for Python analysis"
  puts metadata.to_json
end

main if __FILE__ == $PROGRAM_NAME

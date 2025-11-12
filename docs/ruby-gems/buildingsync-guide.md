# BuildingSync Gem Guide

**Purpose:** BuildingSync XML translator and API for OpenStudio integration. Converts between BuildingSync XML format and OpenStudio models, enabling standardized building data exchange and scenario modeling.

**Repository:** https://github.com/canmet-energy/BuildingSync-gem.git (tag: develop)

**When to use:**
- Import building data from BuildingSync XML to OpenStudio
- Export OpenStudio models to BuildingSync format
- Model energy efficiency scenarios (baseline vs retrofit packages)
- Integrate with ASHRAE Standard 211 workflows

**BuildingSync Standard:** ASHRAE Standard 211 data exchange format for commercial building energy audits.

---

## 1. BuildingSync XML Structure Overview

### Hierarchy

```
BuildingSync (root)
├── Facilities/
│   └── Facility/
│       ├── Sites/
│       │   └── Site/
│       │       └── Buildings/
│       │           └── Building/
│       │               ├── Sections/
│       │               │   └── Section/  # Thermal zones
│       │               ├── Systems/      # HVAC, lighting, etc.
│       │               └── Schedules/
│       └── Measures/          # Energy efficiency measures
│           └── Measure/
│               └── TechnologyCategories/
└── Scenarios/                 # Baseline, retrofit packages
    └── Scenario/
        ├── ScenarioType/      # PackageOfMeasures, Benchmark
        └── AllResourceTotals/ # Energy results
```

### Key Elements

| Element | Purpose | Maps to OpenStudio |
|---------|---------|-------------------|
| `Section` | Building section or thermal zone | `ThermalZone` |
| `System` | HVAC, lighting, or other system | `AirLoopHVAC`, `LightingSystem` |
| `Measure` | Energy efficiency measure | OpenStudio Measure |
| `Scenario` | Baseline or retrofit scenario | Workflow configuration |
| `AllResourceTotals` | Energy use results | `SqlFile` simulation results |

---

## 2. Translator Workflow

### XML → OpenStudio Model

```ruby
require 'buildingsync'
require 'openstudio'

# Load BuildingSync XML
xml_path = 'building.xml'
xml_doc = BuildingSync::BuildingSyncDoc.new(xml_path)

# Create translator
translator = BuildingSync::Translator.new(xml_doc)

# Translate to OpenStudio model
model = translator.create_openstudio_model()

# Save OSM
model.save('output.osm', true)

puts "Model created with #{model.getThermalZones.size} thermal zones"
```

### OpenStudio Model → XML

```ruby
require 'buildingsync'
require 'openstudio'

# Load OpenStudio model
translator = OpenStudio::OSVersion::VersionTranslator.new
model = translator.loadModel('model.osm').get

# Create BuildingSync document
xml_doc = BuildingSync::BuildingSyncDoc.new()

# Populate from model
xml_doc.add_facility_from_model(model)

# Write XML
xml_doc.write_to_file('building.xml')

puts "BuildingSync XML written to building.xml"
```

### Complete Import Workflow

```ruby
require 'buildingsync'
require 'openstudio'

def import_buildingsync(xml_path, osm_output_path, epw_path = nil)
  # 1. Load XML
  xml_doc = BuildingSync::BuildingSyncDoc.new(xml_path)

  # 2. Create translator with options
  translator_options = {
    create_all_schedules: true,
    create_space_types: true,
    set_default_constructions: true
  }
  translator = BuildingSync::Translator.new(xml_doc, translator_options)

  # 3. Translate to OpenStudio model
  model = translator.create_openstudio_model()

  # 4. Set weather file (optional)
  if epw_path
    epw_file = OpenStudio::EpwFile.new(epw_path)
    OpenStudio::Model::WeatherFile.setWeatherFile(model, epw_file)
  end

  # 5. Save model
  model.save(osm_output_path, true)

  return model
end

# Usage
model = import_buildingsync('audit.xml', 'model.osm', 'weather.epw')
```

---

## 3. Scenario Modeling

### Scenario Types

| Scenario Type | Purpose | Workflow |
|--------------|---------|----------|
| `Benchmark` | Baseline energy model | Import building as-is |
| `PackageOfMeasures` | Retrofit scenario | Apply measures to baseline |
| `Target` | Design target | Model with target features |

### Creating Baseline Scenario

```ruby
require 'buildingsync'

# Load BuildingSync XML
xml_doc = BuildingSync::BuildingSyncDoc.new('audit.xml')

# Get first facility
facility = xml_doc.get_facility()

# Create baseline scenario
scenario = BuildingSync::Scenario.new(xml_doc)
scenario.set_scenario_name('Baseline')
scenario.set_scenario_type('Benchmark')

# Link to facility
scenario.link_to_facility(facility)

# Create model for baseline
translator = BuildingSync::Translator.new(xml_doc, scenario_id: scenario.id)
baseline_model = translator.create_openstudio_model()

# Save baseline
baseline_model.save('baseline.osm', true)
```

### Creating Retrofit Package Scenario

```ruby
require 'buildingsync'

# Load BuildingSync XML with measures defined
xml_doc = BuildingSync::BuildingSyncDoc.new('audit_with_measures.xml')

# Get facility and baseline scenario
facility = xml_doc.get_facility()
baseline_scenario = xml_doc.get_scenario('Baseline')

# Create package of measures scenario
retrofit_scenario = BuildingSync::Scenario.new(xml_doc)
retrofit_scenario.set_scenario_name('LED Lighting + HVAC Upgrade')
retrofit_scenario.set_scenario_type('PackageOfMeasures')

# Add measures to scenario
measure_ids = [
  'Measure-LED-Lighting',      # Replace with LED
  'Measure-HVAC-VFD'            # Add VFDs to fans
]

measure_ids.each do |measure_id|
  retrofit_scenario.add_measure(measure_id)
end

# Create model with measures applied
translator = BuildingSync::Translator.new(xml_doc, scenario_id: retrofit_scenario.id)
retrofit_model = translator.create_openstudio_model()

# Save retrofit model
retrofit_model.save('retrofit.osm', true)
```

### Running Multiple Scenarios

```ruby
require 'buildingsync'
require 'openstudio'

def run_all_scenarios(xml_path, output_dir, epw_path)
  # Load XML
  xml_doc = BuildingSync::BuildingSyncDoc.new(xml_path)

  # Get all scenarios
  scenarios = xml_doc.get_scenarios()

  results = {}

  scenarios.each do |scenario|
    scenario_name = scenario.get_scenario_name()
    puts "Processing scenario: #{scenario_name}"

    # Create model for scenario
    translator = BuildingSync::Translator.new(xml_doc, scenario_id: scenario.id)
    model = translator.create_openstudio_model()

    # Set weather
    epw_file = OpenStudio::EpwFile.new(epw_path)
    OpenStudio::Model::WeatherFile.setWeatherFile(model, epw_file)

    # Save OSM
    osm_path = File.join(output_dir, "#{scenario_name}.osm")
    model.save(osm_path, true)

    # Create OSW for simulation
    osw = create_osw(osm_path, epw_path)
    osw_path = File.join(output_dir, "#{scenario_name}.osw")
    osw.saveAs(osw_path)

    # Run simulation
    system("openstudio run -w #{osw_path}")

    # Extract results
    sql_path = File.join(output_dir, 'run', 'eplusout.sql')
    if File.exist?(sql_path)
      sql = OpenStudio::SqlFile.new(sql_path)
      if sql.connectionOpen
        eui = sql.totalSiteEnergy.get / model.getBuilding.floorArea.get / 1000.0  # kWh/m²
        results[scenario_name] = { eui: eui }
        sql.close
      end
    end
  end

  return results
end

def create_osw(osm_path, epw_path)
  osw = OpenStudio::WorkflowJSON.new
  osw.setSeedFile(osm_path)
  osw.setWeatherFile(epw_path)
  return osw
end

# Usage
results = run_all_scenarios('audit.xml', 'scenarios', 'weather.epw')
results.each do |name, data|
  puts "#{name}: #{data[:eui].round(1)} kWh/m²"
end
```

---

## 4. Key API Methods

### BuildingSyncDoc Methods

```ruby
require 'buildingsync'

xml_doc = BuildingSync::BuildingSyncDoc.new('building.xml')

# Access elements
facility = xml_doc.get_facility()                    # Get first facility
facilities = xml_doc.get_facilities()                # Get all facilities
scenario = xml_doc.get_scenario('Scenario-1')       # Get scenario by ID
scenarios = xml_doc.get_scenarios()                  # Get all scenarios
measure = xml_doc.get_measure('Measure-LED')         # Get measure by ID

# Query elements
building = xml_doc.get_building('Building-1')
sections = xml_doc.get_sections()                    # All sections
systems = xml_doc.get_systems()                      # All systems

# Create new elements
new_scenario = BuildingSync::Scenario.new(xml_doc)
new_measure = BuildingSync::Measure.new(xml_doc)

# Write modified XML
xml_doc.write_to_file('modified.xml')
```

### Translator Methods

```ruby
require 'buildingsync'

xml_doc = BuildingSync::BuildingSyncDoc.new('building.xml')
translator = BuildingSync::Translator.new(xml_doc)

# Create model
model = translator.create_openstudio_model()

# Access translator info
translator_log = translator.get_log()                # Get translation messages
errors = translator.get_errors()                     # Get translation errors
warnings = translator.get_warnings()                 # Get translation warnings

# Check translation status
if translator.has_errors?
  puts "Translation failed:"
  errors.each { |e| puts "  - #{e}" }
else
  puts "Translation successful"
  warnings.each { |w| puts "  Warning: #{w}" }
end
```

### Scenario Methods

```ruby
require 'buildingsync'

xml_doc = BuildingSync::BuildingSyncDoc.new('building.xml')
scenario = xml_doc.get_scenario('Scenario-1')

# Get/set properties
name = scenario.get_scenario_name()
scenario.set_scenario_name('Updated Name')

type = scenario.get_scenario_type()                  # 'Benchmark', 'PackageOfMeasures', etc.
scenario.set_scenario_type('PackageOfMeasures')

# Measures
measures = scenario.get_measures()                   # Array of measure IDs
scenario.add_measure('Measure-LED')
scenario.remove_measure('Measure-Old')

# Results (if available)
if scenario.has_results?
  eui = scenario.get_eui()                           # kWh/m²/year
  total_energy = scenario.get_total_site_energy()    # kWh/year
  energy_cost = scenario.get_energy_cost()           # $/year
end
```

### Measure Methods

```ruby
require 'buildingsync'

xml_doc = BuildingSync::BuildingSyncDoc.new('building.xml')
measure = xml_doc.get_measure('Measure-LED')

# Get properties
name = measure.get_measure_name()
category = measure.get_technology_category()         # 'Lighting Improvements', etc.
description = measure.get_description()

# Set properties
measure.set_measure_name('LED Lighting Retrofit')
measure.set_technology_category('Lighting Improvements')
measure.set_description('Replace T8 fluorescent with LED')

# Get/set costs
installed_cost = measure.get_installed_cost()        # $
measure.set_installed_cost(15000.0)

# Get/set savings (if calculated)
annual_savings = measure.get_annual_savings()        # kWh/year
measure.set_annual_savings(25000.0)
```

---

## 5. Advanced Patterns

### Custom Translation Options

```ruby
require 'buildingsync'

# Define custom translator options
options = {
  # Schedule options
  create_all_schedules: true,              # Create schedules from XML
  default_schedule_type: 'Office',         # Fallback schedule type

  # Space type options
  create_space_types: true,                # Create space types
  set_default_constructions: true,         # Apply default constructions

  # Geometry options
  simplify_geometry: false,                # Keep detailed geometry
  set_floor_to_floor_height: 3.0,         # Default floor height (m)

  # System options
  create_hvac: true,                       # Create HVAC from XML
  create_service_hot_water: true,          # Create SHW systems

  # Output options
  debug_output: false,                     # Verbose logging
  keep_unmapped_elements: false            # Discard unmapped XML elements
}

# Create translator with options
xml_doc = BuildingSync::BuildingSyncDoc.new('building.xml')
translator = BuildingSync::Translator.new(xml_doc, options)
model = translator.create_openstudio_model()
```

### Extracting Specific Building Data

```ruby
require 'buildingsync'
require 'rexml/document'

def extract_building_characteristics(xml_path)
  xml_doc = BuildingSync::BuildingSyncDoc.new(xml_path)

  # Get facility and building
  facility = xml_doc.get_facility()
  building = xml_doc.get_building()

  characteristics = {}

  # Basic info
  characteristics[:name] = building.get_building_name()
  characteristics[:floor_area] = building.get_floor_area()           # m²
  characteristics[:year_built] = building.get_year_of_construction()
  characteristics[:num_floors] = building.get_number_of_floors()

  # Climate
  characteristics[:climate_zone] = building.get_climate_zone()
  characteristics[:postal_code] = building.get_postal_code()

  # Use type
  characteristics[:occupancy_classification] = building.get_occupancy_classification()

  # Sections (thermal zones)
  sections = xml_doc.get_sections()
  characteristics[:num_sections] = sections.size
  characteristics[:sections] = sections.map do |section|
    {
      name: section.get_section_name(),
      floor_area: section.get_floor_area(),
      occupancy_type: section.get_occupancy_classification()
    }
  end

  # Systems
  systems = xml_doc.get_systems()
  characteristics[:hvac_systems] = systems.select { |s| s.is_hvac_system? }.map do |sys|
    {
      name: sys.get_system_name(),
      type: sys.get_system_type()
    }
  end

  return characteristics
end

# Usage
data = extract_building_characteristics('audit.xml')
puts "Building: #{data[:name]}"
puts "Floor Area: #{data[:floor_area]} m²"
puts "Sections: #{data[:num_sections]}"
data[:sections].each do |section|
  puts "  - #{section[:name]}: #{section[:floor_area]} m²"
end
```

### Populating Results into XML

```ruby
require 'buildingsync'
require 'openstudio'

def populate_simulation_results(xml_path, scenario_id, sql_path, output_xml_path)
  # Load XML
  xml_doc = BuildingSync::BuildingSyncDoc.new(xml_path)
  scenario = xml_doc.get_scenario(scenario_id)

  # Load SQL results
  sql = OpenStudio::SqlFile.new(sql_path)

  if sql.connectionOpen
    # Extract results
    total_site_energy = sql.totalSiteEnergy.get / 3.6e9  # Convert J to GJ
    total_source_energy = sql.totalSourceEnergy.get / 3.6e9
    electricity = sql.electricityTotalEndUses.get / 3.6e9
    natural_gas = sql.naturalGasTotalEndUses.get / 3.6e9

    # Create AllResourceTotals
    resource_totals = BuildingSync::AllResourceTotals.new(xml_doc)

    # Add site energy
    site_energy = BuildingSync::ResourceTotal.new(xml_doc)
    site_energy.set_energy_resource('All')
    site_energy.set_resource_use(total_site_energy)
    site_energy.set_resource_units('GJ')
    resource_totals.add_resource_total(site_energy)

    # Add electricity
    electricity_total = BuildingSync::ResourceTotal.new(xml_doc)
    electricity_total.set_energy_resource('Electricity')
    electricity_total.set_resource_use(electricity)
    electricity_total.set_resource_units('GJ')
    resource_totals.add_resource_total(electricity_total)

    # Add natural gas
    gas_total = BuildingSync::ResourceTotal.new(xml_doc)
    gas_total.set_energy_resource('Natural gas')
    gas_total.set_resource_use(natural_gas)
    gas_total.set_resource_units('GJ')
    resource_totals.add_resource_total(gas_total)

    # Attach to scenario
    scenario.set_all_resource_totals(resource_totals)

    sql.close
  end

  # Write updated XML
  xml_doc.write_to_file(output_xml_path)

  puts "Results added to scenario #{scenario_id}"
end

# Usage
populate_simulation_results(
  'audit.xml',
  'Scenario-Baseline',
  'run/eplusout.sql',
  'audit_with_results.xml'
)
```

### Comparing Scenarios

```ruby
require 'buildingsync'

def compare_scenarios(xml_path, baseline_id, retrofit_ids)
  xml_doc = BuildingSync::BuildingSyncDoc.new(xml_path)

  # Get baseline results
  baseline = xml_doc.get_scenario(baseline_id)
  baseline_eui = baseline.get_eui()
  baseline_cost = baseline.get_energy_cost()

  puts "Baseline (#{baseline.get_scenario_name()}):"
  puts "  EUI: #{baseline_eui.round(1)} kWh/m²/year"
  puts "  Annual Cost: $#{baseline_cost.round(0)}"
  puts ""

  # Compare each retrofit
  retrofit_ids.each do |retrofit_id|
    retrofit = xml_doc.get_scenario(retrofit_id)
    retrofit_eui = retrofit.get_eui()
    retrofit_cost = retrofit.get_energy_cost()

    # Calculate savings
    energy_savings = ((baseline_eui - retrofit_eui) / baseline_eui * 100).round(1)
    cost_savings = (baseline_cost - retrofit_cost).round(0)

    puts "#{retrofit.get_scenario_name()}:"
    puts "  EUI: #{retrofit_eui.round(1)} kWh/m²/year (#{energy_savings}% savings)"
    puts "  Annual Cost: $#{retrofit_cost.round(0)} ($#{cost_savings}/year savings)"

    # Get measures in package
    measures = retrofit.get_measures()
    puts "  Measures: #{measures.size}"
    measures.each do |measure_id|
      measure = xml_doc.get_measure(measure_id)
      puts "    - #{measure.get_measure_name()}"
    end
    puts ""
  end
end

# Usage
compare_scenarios(
  'audit_with_results.xml',
  'Scenario-Baseline',
  ['Scenario-Lighting', 'Scenario-HVAC', 'Scenario-Deep-Retrofit']
)
```

---

## 6. Common Use Cases

### Use Case 1: Import Building Audit → Run Baseline Simulation

```ruby
require 'buildingsync'
require 'openstudio'

# 1. Import BuildingSync XML
xml_doc = BuildingSync::BuildingSyncDoc.new('audit.xml')
translator = BuildingSync::Translator.new(xml_doc)
model = translator.create_openstudio_model()

# 2. Set weather file
epw_file = OpenStudio::EpwFile.new('weather.epw')
OpenStudio::Model::WeatherFile.setWeatherFile(model, epw_file)

# 3. Save model
model.save('baseline.osm', true)

# 4. Create and run OSW
osw = OpenStudio::WorkflowJSON.new
osw.setSeedFile('baseline.osm')
osw.setWeatherFile('weather.epw')
osw.saveAs('baseline.osw')

system('openstudio run -w baseline.osw')

# 5. Check results
if File.exist?('run/eplusout.sql')
  sql = OpenStudio::SqlFile.new('run/eplusout.sql')
  if sql.connectionOpen
    eui = sql.totalSiteEnergy.get / model.getBuilding.floorArea.get / 1000.0
    puts "Baseline EUI: #{eui.round(1)} kWh/m²"
    sql.close
  end
end
```

### Use Case 2: Create Building from Scratch → Export to BuildingSync

```ruby
require 'buildingsync'
require 'openstudio'

# 1. Create OpenStudio model
model = OpenStudio::Model::Model.new

# 2. Build simple model
# (Use geometry patterns from geometry-patterns.md)
zone = OpenStudio::Model::ThermalZone.new(model)
zone.setName('Office Zone')

space = OpenStudio::Model::Space.new(model)
space.setName('Office Space')
space.setThermalZone(zone)

# ... (add geometry, HVAC, etc.)

# 3. Create BuildingSync document
xml_doc = BuildingSync::BuildingSyncDoc.new()

# 4. Populate from model
facility = xml_doc.add_facility_from_model(model)
facility.set_facility_name('My Office Building')

# 5. Create baseline scenario
scenario = BuildingSync::Scenario.new(xml_doc)
scenario.set_scenario_name('Baseline')
scenario.set_scenario_type('Benchmark')
scenario.link_to_facility(facility)

# 6. Write BuildingSync XML
xml_doc.write_to_file('exported_building.xml')

puts "BuildingSync XML exported to exported_building.xml"
```

### Use Case 3: Parametric Study with Multiple Measures

```ruby
require 'buildingsync'

# Define measure packages
packages = [
  {
    name: 'LED Lighting Only',
    measures: ['Measure-LED']
  },
  {
    name: 'HVAC Only',
    measures: ['Measure-HVAC-Economizer', 'Measure-HVAC-VFD']
  },
  {
    name: 'Combined Package',
    measures: ['Measure-LED', 'Measure-HVAC-Economizer', 'Measure-HVAC-VFD']
  }
]

# Load base XML
xml_doc = BuildingSync::BuildingSyncDoc.new('audit.xml')
facility = xml_doc.get_facility()

# Create scenario for each package
packages.each_with_index do |package, i|
  scenario = BuildingSync::Scenario.new(xml_doc)
  scenario.set_scenario_name(package[:name])
  scenario.set_scenario_type('PackageOfMeasures')
  scenario.link_to_facility(facility)

  # Add measures
  package[:measures].each do |measure_id|
    scenario.add_measure(measure_id)
  end

  # Create model
  translator = BuildingSync::Translator.new(xml_doc, scenario_id: scenario.id)
  model = translator.create_openstudio_model()

  # Save
  model.save("package_#{i + 1}.osm", true)

  puts "Created scenario: #{package[:name]}"
end

# Save updated XML with all scenarios
xml_doc.write_to_file('audit_with_packages.xml')
```

---

## Quick Reference

### Key Classes

| Class | Purpose | Common Methods |
|-------|---------|----------------|
| `BuildingSyncDoc` | XML document container | `get_facility()`, `get_scenarios()`, `write_to_file()` |
| `Translator` | XML ↔ OpenStudio converter | `create_openstudio_model()` |
| `Scenario` | Energy scenario (baseline/retrofit) | `get_scenario_name()`, `add_measure()`, `get_eui()` |
| `Measure` | Energy efficiency measure | `get_measure_name()`, `get_technology_category()` |

### Common Workflows

| Workflow | Entry Point | Output |
|----------|-------------|--------|
| Import XML → OSM | `Translator.new(xml_doc).create_openstudio_model()` | OpenStudio Model |
| Export OSM → XML | `xml_doc.add_facility_from_model(model)` | BuildingSync XML |
| Model scenario | `Translator.new(xml_doc, scenario_id: id)` | Scenario-specific Model |
| Extract results | `scenario.get_eui()`, `scenario.get_total_site_energy()` | Energy metrics |

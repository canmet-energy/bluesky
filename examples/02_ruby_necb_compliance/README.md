# Example 02: Ruby NECB Compliance Model

## What This Example Demonstrates

This example shows how to create a building model that complies with the National Energy Code of Canada for Buildings (NECB) using Ruby and the openstudio-standards gem.

**Key Capabilities:**
- NECB-compliant building model generation
- Canadian commercial building energy code compliance
- Automated application of code-required constructions, HVAC, and loads
- Climate-zone-specific requirements
- Standards-based building modeling

**Why This Matters:**
The openstudio-standards gem is a **Ruby-exclusive library** containing years of curated building code data. It's the most comprehensive source for:
- NECB (Canadian commercial buildings)
- ASHRAE 90.1 (US commercial buildings)
- DOE prototype buildings
- Title 24 (California)

There is no Python equivalent - this is where Ruby shines!

## Prerequisites

**Software:**
- Ruby 3.2.2+ (installed via rbenv)
- openstudio gem (installed)
- openstudio-standards gem v0.8.4+ (installed)

**Check Installation:**
```bash
ruby -e "require 'openstudio'; puts '✓ OpenStudio gem ready'"
ruby -e "require 'openstudio-standards'; puts '✓ openstudio-standards ready'"
gem list | grep openstudio-standards
```

## How to Run

```bash
# From repository root
ruby examples/02_ruby_necb_compliance/create_necb_model.rb
```

**What Happens:**
1. Creates simple rectangular building geometry (2 floors)
2. Applies NECB 2017 construction requirements for climate zone 6
3. Sets up office space types with code-compliant internal loads
4. Adds NECB-compliant HVAC system (PSZ-AC with gas heating)
5. Configures simulation settings
6. Saves complete model to `examples/data/models/necb_office_building.osm`

## Expected Output

```
examples/data/models/necb_office_building.osm
```

**Console output shows:**
- Building geometry created
- NECB standard applied (version, climate zone, building type)
- Construction set applied
- Space types assigned
- HVAC system added
- Model summary statistics

## Key Concepts

### NECB (National Energy Code of Canada for Buildings)
- Canadian energy code for commercial, institutional, and multi-unit residential
- Climate-zone-specific requirements (zones 4, 5, 6, 7a, 7b, 8)
- Prescriptive and performance compliance paths
- Updated versions: NECB 2011, 2015, 2017, 2020

### openstudio-standards Gem
- Maintained by NREL and Canadian partners
- Contains complete code requirements as data
- Provides methods to apply standards automatically
- **Ruby-only** - no Python port exists
- Includes DOE prototype buildings, ASHRAE 90.1, Title 24, etc.

### Climate Zones (Canadian)
- **Zone 4:** Coastal BC (Vancouver)
- **Zone 5:** Southern Ontario (Toronto)
- **Zone 6:** Ottawa, Montreal, Calgary (example uses this)
- **Zone 7a:** Northern prairies
- **Zone 7b:** Far north
- **Zone 8:** Arctic

### Building Types
Common types in openstudio-standards:
- Office (small, medium, large)
- Retail
- School (primary, secondary)
- Hospital
- Hotel
- Warehouse
- Apartment (high-rise, mid-rise)

## What You'll Learn

1. **NECB Compliance:** How to create code-compliant Canadian buildings
2. **openstudio-standards API:** Key methods and workflow
3. **Ruby OpenStudio SDK:** Native Ruby modeling approach
4. **Standards-Based Modeling:** Leveraging curated code data
5. **Climate Zone Application:** Climate-specific requirements

## Customization Options

Edit the script to modify:

```ruby
# Different NECB version
necb_version = 'NECB2020'  # Options: NECB2011, NECB2015, NECB2017, NECB2020

# Different climate zone
climate_zone = '5'  # Toronto area
climate_zone = '4'  # Vancouver area

# Different building type
building_type = 'Retail'        # Retail store
building_type = 'School'        # Educational facility
building_type = 'Hospital'      # Healthcare

# Different space type
space_type_name = 'Office - enclosed'  # Private offices
space_type_name = 'Corridor'           # Circulation
```

## Model Structure

The generated model includes:

**Geometry:**
- 2 floors
- 30m × 20m footprint
- 3.5m floor height
- Simple rectangular form

**Envelope:**
- NECB-compliant wall constructions (climate zone 6)
- NECB-compliant roof construction
- NECB-compliant window U-factors and SHGC

**Space Types:**
- Open plan office (with NECB lighting, equipment, occupancy)

**HVAC:**
- Packaged single-zone AC with gas heating
- NECB-compliant efficiency requirements
- Appropriate sizing

## Troubleshooting

**Gem not found:**
```bash
bundle install  # Install from Gemfile
gem install openstudio-standards -v 0.8.4
```

**Standard not found:**
- Verify NECB version is correct (2011, 2015, 2017, 2020)
- Check openstudio-standards gem version

**Space type not found:**
- Use valid space type names from standards
- Check building type matches space type

**Model won't simulate:**
- Open in OpenStudio Application to validate
- Check for geometry errors
- Ensure HVAC is complete

## Next Steps

- **Run simulation:** Use OpenStudio CLI or Application
- **Compare to baseline:** Create different NECB vintages
- **Try different building types:** Retail, school, hospital
- **Climate zone studies:** Compare requirements across zones
- **Performance path:** Add ECMs and compare to baseline
- **Python analysis:** Use interop example to analyze with pandas

## Related Resources

- NECB information: Canadian Codes Centre, NRC
- openstudio-standards: https://github.com/NREL/openstudio-standards
- OpenStudio documentation: https://openstudio-sdk-documentation.s3.amazonaws.com/
- National Building Code of Canada: NRC
- Climate zone maps: NRCan energy codes

## Why Ruby for NECB?

The openstudio-standards gem contains:
- Complete construction libraries for each NECB version
- Space type definitions with code-compliant loads
- HVAC system templates
- Prototype building generators
- Climate zone requirements

**This data doesn't exist in Python.** While you can use Python's OpenStudio bindings for modeling, you need Ruby to access the standards library. This is why the interop example (03) is valuable - create compliant models with Ruby, analyze with Python!

# Test Model Files

This directory contains test building models used by the example scripts.

## Required Files

To run the examples, you'll need to provide the following test files:

### 1. simple_house.h2k
A simple residential Hot2000 model file. You can:
- Create one using the Hot2000 GUI application
- Download sample files from NRCan's Hot2000 resources
- Use existing project files from your work

**Recommended characteristics:**
- Single family detached home
- Simple rectangular geometry
- Basic HVAC system
- Standard Canadian construction

### 2. simple_house.osm
A simple residential OpenStudio model. You can:
- Convert `simple_house.h2k` using the h2k-hpxml library
- Create using OpenStudio Application
- Generate programmatically using example scripts

**Recommended characteristics:**
- Single thermal zone
- Simple geometry (box shape)
- Basic constructions
- Ideal air loads or simple HVAC

### 3. small_office.osm
A small commercial OpenStudio model. You can:
- Download from BCL (Building Component Library)
- Create using OpenStudio Application
- Use DOE commercial reference building as starting point

**Recommended characteristics:**
- 1-2 story office building
- Multiple thermal zones
- Commercial HVAC system
- Standard office internal loads

## Getting Started Without Test Files

Many examples can create models from scratch and don't require pre-existing files. Start with these:

- `examples/python/openstudio/01_create_simple_model.py` - Creates a model programmatically
- `examples/ruby/openstudio/01_create_simple_model.rb` - Creates a model with Ruby

These examples will generate OSM files that you can then use as test data for other examples.

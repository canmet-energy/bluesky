# frozen_string_literal: true

source "https://rubygems.org"

# Ruby version (should match DEVCONTAINER_RUBY_VERSION in devcontainer.json)
ruby "~> 3.2.0"

# Development and testing gems
group :development, :test do
  gem "rake", "~> 13.0"
  gem "rspec", "~> 3.12"
  gem "rubocop", "~> 1.50", require: false
  gem "rubocop-performance", "~> 1.17", require: false
  gem "rubocop-rspec", "~> 2.20", require: false
end

# Building Energy Simulation gems
group :simulation do
  gem "rubyzip", "~> 2.3"
end

# OpenStudio Standards (Ruby gem from GitHub)
gem "openstudio-standards", git: "https://github.com/NREL/openstudio-standards.git", tag: "v0.8.4"
gem "openstudio-extension", git: "https://github.com/canmet-energy/openstudio-extension-gem.git", branch: "develop"
gem "openstudio-common-measures", git: "https://github.com/canmet-energy/openstudio-common-measures-gem.git", branch: "develop"
gem "openstudio-model-articulation", git: "https://github.com/canmet-energy/openstudio-model-articulation-gem.git", tag: "develop"
gem "openstudio-calibration", git: "https://github.com/canmet-energy/openstudio-calibration-gem.git", tag: "develop"
gem "openstudio-ee", git: "https://github.com/canmet-energy/openstudio-ee-gem.git", tag: "develop"
gem "openstudio-load-flexibility-measures", git: "https://github.com/canmet-energy/openstudio-load-flexibility-measures-gem.git", tag: "develop"
gem "buildingsync", git: "https://github.com/canmet-energy/BuildingSync-gem.git", tag: "develop"
# gem "openstudio-aedg", git: "https://github.com/NREL/openstudio-aedg-gem.git", tag: "v0.8.0" # Too old.
# gem "urbanopt-core", git: "https://github.com/urbanopt/urbanopt-core-gem.git", tag: "v1.1.0"
# gem "urbanopt-geojson", git: "https://github.com/urbanopt/urbanopt-geojson-gem.git", tag: "v1.1.0"
# gem "urbanopt-reporting", git: "https://github.com/urbanopt/urbanopt-reporting-gem.git", tag: "v1.1.0"





# Add your application gems here
# gem "rails", "~> 7.0"
# gem "sinatra", "~> 3.0"

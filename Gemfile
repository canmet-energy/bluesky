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

# Add your application gems here
# gem "rails", "~> 7.0"
# gem "sinatra", "~> 3.0"

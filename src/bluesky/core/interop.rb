# frozen_string_literal: true

# Interoperability utilities for calling Python from Ruby.
#
# This module provides helpers for Ruby scripts to execute Python code and exchange data.

require 'json'
require 'open3'

module Bluesky
  module Interop
    # Error raised when Python execution fails
    class PythonExecutionError < StandardError; end

    # Execute a Python script from Ruby
    #
    # @param script_path [String] Path to the Python script
    # @param args [Array<String>] Command-line arguments
    # @param input_data [Hash] Data to pass to Python via JSON (stdin)
    # @param timeout [Integer] Execution timeout in seconds
    # @return [Hash] Result data from Python (via JSON stdout)
    #
    # @example
    #   result = Bluesky::Interop.run_python_script(
    #     'analyze.py',
    #     input_data: { model_path: 'model.osm', metrics: ['energy', 'cost'] }
    #   )
    #   puts result['annual_energy']
    def self.run_python_script(script_path, args: [], input_data: nil, timeout: 300)
      raise "Python script not found: #{script_path}" unless File.exist?(script_path)

      # Build command
      cmd = ['python3', script_path] + args

      # Prepare input data as JSON
      stdin_data = input_data ? JSON.generate(input_data) : nil

      # Execute with timeout
      stdout, stderr, status = Open3.capture3(*cmd, stdin_data: stdin_data, timeout: timeout)

      unless status.success?
        raise PythonExecutionError, "Python script failed with exit code #{status.exitstatus}\nStdout: #{stdout}\nStderr: #{stderr}"
      end

      # Try to parse JSON output
      begin
        JSON.parse(stdout)
      rescue JSON::ParserError
        # If not JSON, return raw output
        { 'stdout' => stdout, 'stderr' => stderr }
      end
    rescue Timeout::Error
      raise PythonExecutionError, "Python script timed out after #{timeout} seconds"
    end

    # Call a specific Python function with arguments
    #
    # @param script_path [String] Path to Python script
    # @param function_name [String] Name of Python function to call
    # @param kwargs [Hash] Keyword arguments for the function
    # @return [Hash] Result from Python function
    #
    # @example
    #   result = Bluesky::Interop.call_python_function(
    #     'analysis.py',
    #     'calculate_metrics',
    #     model_path: 'model.osm',
    #     include_hourly: true
    #   )
    def self.call_python_function(script_path, function_name, **kwargs)
      input_data = {
        'function' => function_name,
        'args' => kwargs
      }

      run_python_script(script_path, input_data: input_data)
    end

    # Write data to JSON file for Python to read
    #
    # @param data [Hash] Data to write
    # @param exchange_path [String] Path to exchange file
    #
    # @example
    #   Bluesky::Interop.exchange_via_file(
    #     { model_path: 'model.osm', results: results_hash },
    #     'exchange.json'
    #   )
    def self.exchange_via_file(data, exchange_path)
      File.write(exchange_path, JSON.pretty_generate(data))
    end

    # Read data from JSON exchange file written by Python
    #
    # @param exchange_path [String] Path to exchange file
    # @return [Hash] Data from Python script
    def self.read_exchange_file(exchange_path)
      JSON.parse(File.read(exchange_path))
    end

    # Find Python executable in system PATH
    #
    # @return [String, nil] Path to Python, or nil if not found
    def self.find_python_executable
      %w[python3 python].each do |cmd|
        path = `which #{cmd}`.strip
        return path unless path.empty?
      end
      nil
    end

    # Check if a Python package is installed
    #
    # @param package_name [String] Name of the package (e.g., 'openstudio')
    # @return [Boolean] True if package is installed
    #
    # @example
    #   if Bluesky::Interop.check_python_package('h2k_hpxml')
    #     puts "H2K-HPXML library available"
    #   end
    def self.check_python_package(package_name)
      cmd = ['python3', '-c', "import #{package_name}"]
      _, _, status = Open3.capture3(*cmd)
      status.success?
    rescue StandardError
      false
    end
  end
end

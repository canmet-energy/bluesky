# Example 03: Python-Ruby Interoperability

## What This Example Demonstrates

This example shows how to leverage both Python and Ruby in a single workflow, combining the unique strengths of each language ecosystem.

**The Workflow:**
1. **Ruby script** creates NECB-compliant building model using openstudio-standards
2. **Python orchestrator** calls the Ruby script
3. **Ruby** returns model path and metadata via JSON
4. **Python** performs analysis (placeholder - extensible to pandas, visualization, ML)

**Why This Matters:**
- **Ruby has:** openstudio-standards (NECB, ASHRAE 90.1) - no Python equivalent
- **Python has:** pandas, matplotlib, scikit-learn, rich data science ecosystem
- **Together:** Create code-compliant baselines with Ruby, analyze with Python tools

This is the "best of both worlds" approach for building simulation applications.

## Prerequisites

**Software:**
- Python 3.12+ with openstudio package
- Ruby 3.2.2+ with openstudio and openstudio-standards gems
- Both languages must be installed and in PATH

**Check Installation:**
```bash
# Check Python
python -c "from bluesky.core.interop import run_ruby_script; print('✓ Python interop ready')"

# Check Ruby
ruby -e "require 'openstudio'; require 'openstudio-standards'; puts '✓ Ruby ready'"

# Check both can find each other
python -c "import subprocess; print('Ruby:', subprocess.run(['ruby', '--version'], capture_output=True, text=True).stdout.strip())"
ruby -e "puts 'Python: ' + %x(python --version).strip"
```

## How to Run

```bash
# From repository root
python examples/03_python_ruby_interop/runner.py
```

**What Happens:**
1. Python orchestrator starts
2. Calls Ruby script via subprocess
3. Ruby creates NECB 2017 office building
4. Ruby saves model and writes JSON metadata
5. Python reads metadata
6. Python performs analysis (currently placeholder)
7. Reports complete workflow

## Expected Output

```
examples/03_python_ruby_interop/output/
├── baseline_model.osm        # OpenStudio model (created by Ruby)
└── model_metadata.json       # Metadata for Python
```

**Console output shows:**
```
Python-Ruby Interop Workflow Example
================================================================================
This workflow demonstrates:
  1. Ruby creates NECB-compliant model (leveraging openstudio-standards)
  2. Python performs analysis (leveraging pandas/numpy ecosystem)

================================================================================
Step 1: Creating model with Ruby + openstudio-standards
================================================================================
Creating NECB-based model with Ruby...
✓ Model saved: .../baseline_model.osm
✓ Metadata saved for Python analysis

================================================================================
Step 2: Analyzing model with Python
================================================================================
Model: .../baseline_model.osm
Standard: NECB2017
Building type: Office
Floor area: 600.0 m²

Python can now:
  - Run parametric simulations
  - Analyze results with pandas
  - Create visualizations with matplotlib
  - Generate reports

================================================================================
Workflow Complete!
================================================================================
```

## Key Concepts

### Language Interoperability

**Why mix languages?**
- Each has unique, irreplaceable libraries
- openstudio-standards (Ruby-only)
- pandas/numpy/matplotlib/scikit-learn (Python ecosystem)

**How they communicate:**
- **Subprocess calls:** One language runs the other as subprocess
- **JSON exchange:** Structured data via stdin/stdout or files
- **File sharing:** Models saved to disk, paths exchanged

### Communication Methods

**Method 1: JSON via stdout (used here)**
```python
# Python calls Ruby
result = subprocess.run(['ruby', 'script.rb'], capture_output=True, text=True)
data = json.loads(result.stdout)
```

**Method 2: JSON file exchange (for complex data)**
```python
# Python writes input
with open('input.json', 'w') as f:
    json.dump({'param': value}, f)

# Ruby reads and processes
# Ruby writes output.json

# Python reads result
with open('output.json') as f:
    result = json.load(f)
```

### Interop Utilities

This example uses `src/bluesky/core/interop.py`:

```python
from bluesky.core.interop import run_ruby_script, read_exchange_file

# High-level: run Ruby script with data exchange
result = run_ruby_script(
    'create_model.rb',
    input_data={'climate_zone': '6', 'building_type': 'Office'}
)

# File-based exchange
exchange_via_file(data, 'exchange.json')
result = read_exchange_file('result.json')
```

Ruby equivalent: `src/bluesky/core/interop.rb`

## What You'll Learn

1. **Cross-Language Workflows:** How to orchestrate Python and Ruby
2. **JSON Communication:** Structured data exchange between languages
3. **Subprocess Management:** Running and controlling external processes
4. **Leveraging Ecosystems:** Using each language's unique strengths
5. **Error Handling:** Dealing with failures across language boundaries

## Customization Options

### Modify Ruby Model Creation

Edit `create_model.rb`:
```ruby
# Different NECB version
standard = Standard.build('NECB2020')

# Different building type
building_type = 'Retail'

# Different climate zone
climate_zone = '5'  # Toronto

# Add more data to metadata
metadata['custom_field'] = 'value'
```

### Extend Python Analysis

Edit `runner.py` to add real analysis:
```python
def step2_analyze_with_python(metadata):
    model_path = metadata["model_path"]

    # Load model
    model = openstudio.model.Model.load(model_path).get()

    # Run parametric variations
    variants = create_parametric_variants(model)
    results = run_batch_simulations(variants)

    # Analyze with pandas
    df = pd.DataFrame(results)
    df.to_csv('analysis_results.csv')

    # Create visualizations
    plot_energy_comparison(df)

    return df
```

## Common Interop Patterns

### Pattern 1: Ruby Baseline + Python Parametrics
```
Ruby: Create NECB baseline
Python: Generate 100 variants with different parameters
Python: Run simulations in parallel
Python: Analyze results with pandas
Python: Create visualizations
```

### Pattern 2: H2K Translation + Ruby Enhancement
```
Python: Translate H2K → HPXML → OSM (h2k-hpxml)
Ruby: Apply openstudio-standards to add compliant HVAC
Python: Run simulation and extract results
```

### Pattern 3: Dual-Engine Comparison
```
Python: Run Hot2000 simulation
Ruby: Run OpenStudio simulation
Python: Compare results with statistical analysis
```

### Pattern 4: ML-Driven Standards Application
```
Python: Train ML model on building features
Python: Predict optimal HVAC system
Ruby: Apply predicted system using openstudio-standards
Python: Validate performance
```

## Troubleshooting

**Ruby script not found:**
- Check path is correct
- Use absolute paths or Path(__file__).parent

**Ruby execution fails:**
- Test Ruby script independently: `ruby create_model.rb`
- Check Ruby gems are installed: `bundle install`
- Verify Ruby is in PATH: `which ruby`

**JSON parsing error:**
- Ruby script must output valid JSON to stdout
- Separate debug output to stderr: `STDERR.puts "debug message"`
- Use `JSON.generate()` in Ruby, `json.dumps()` in Python

**Python can't find interop module:**
- Ensure src/bluesky is in PYTHONPATH
- Or use: `sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))`

**Encoding issues:**
- Use UTF-8: `encoding='utf-8'` in Python file operations
- Ruby 3.2+ defaults to UTF-8

## Next Steps

- **Add real analysis:** Implement pandas-based result analysis
- **Parametric studies:** Generate variants in Python, use Ruby for standards
- **Visualization:** Add matplotlib plots of results
- **Batch processing:** Process multiple buildings through workflow
- **Error handling:** Add robust exception handling across languages
- **Performance:** Profile workflow, optimize slow steps

## Related Resources

- subprocess documentation: https://docs.python.org/3/library/subprocess.html
- JSON in Python: https://docs.python.org/3/library/json.html
- JSON in Ruby: https://ruby-doc.org/stdlib/libdoc/json/rdoc/JSON.html
- Open3 in Ruby: https://ruby-doc.org/stdlib/libdoc/open3/rdoc/Open3.html

## Real-World Use Cases

**Energy Consulting Firms:**
- Create code baselines (Ruby + NECB)
- Run parametric ECM analysis (Python)
- Generate client reports (Python + matplotlib)

**Building Portfolio Analysis:**
- Translate existing Hot2000 models (Python)
- Standardize with openstudio-standards (Ruby)
- Analyze portfolio performance (Python + pandas)

**Research Applications:**
- Use standards-based prototypes (Ruby)
- Apply machine learning optimization (Python)
- Statistical analysis of results (Python + scipy)

**Code Compliance:**
- Generate NECB reference building (Ruby)
- Model proposed design (Python or Ruby)
- Compare performance metrics (Python)

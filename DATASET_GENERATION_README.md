# Dataset Generation CLI Tool (Click-Based)

The `data_generation/generate_dataset.py` script has been completely rewritten using the Click framework to be fully automatable and callable from other repositories with a modern, user-friendly CLI interface.

## Features

### Modern Click-Based CLI Interface
- **Intuitive command syntax** with automatic validation
- **Colored output** with ✓, ✗, and ⚠ symbols for visual feedback
- **Comprehensive help** with default values automatically shown
- **Type validation** for all parameters (automatic conversion and error checking)
- **Boolean flag syntax** with `--flag/--no-flag` patterns
- **Controller type validation** with automatic suggestion of valid options
- **Tab completion support** (can be enabled for bash/zsh)

### Programmatic Interface
- **Python function** `generate_dataset_programmatic()` for direct integration
- **All CLI options available** as function parameters
- **Return value** indicates success/failure and output file path
- **Same core logic** as CLI but without Click dependencies

### Key Improvements

1. **Modern CLI Experience**
   - Click framework for professional command-line interface
   - Colored output for better visual feedback
   - Automatic validation with helpful error messages
   - Boolean flags with intuitive `--flag/--no-flag` syntax
   - Built-in help system with default values

2. **Robust Validation**
   - Controller types are validated automatically
   - Patient IDs are checked against available data
   - File paths and directories are validated
   - Type conversion happens automatically

3. **Automation-Friendly**
   - No hardcoded values - everything is configurable
   - Exit codes for success/failure detection
   - Quiet mode to suppress interactive output
   - Proper error handling and interruption support

4. **Development-Friendly**
   - Single patient testing (`--patient-id "adult#001"`)
   - Limited patient count (`--max-patients`)
   - Custom output directories
   - Executable script with shebang

5. **Integration-Ready**
   - Importable as Python module
   - Programmatic interface alongside CLI
   - Proper argument validation
   - Clear documentation and examples

## Usage Examples

### Command Line (Click Interface)

```bash
# Show comprehensive help with all options and defaults
python data_generation/generate_dataset.py --help

# Basic usage - all adult patients, default settings
python data_generation/generate_dataset.py

# Quick test with one patient (note: quotes needed for shell)
python data_generation/generate_dataset.py --patient-id "adult#001" --n-days 1

# Custom controller and parameters
python data_generation/generate_dataset.py --controller pid-automated --pid-p 0.001

# Generate for children with limited count
python data_generation/generate_dataset.py --patient-pattern child --max-patients 5

# Disable therapy settings computation (note the --no- prefix)
python data_generation/generate_dataset.py --no-compute-therapy-settings

# Automated mode with custom output and different devices
python data_generation/generate_dataset.py --output-dir /path/to/output --sensor Dexcom --pump Medtronic --quiet

# The CLI will show colored output like:
# ✓ Successfully generated dataset: /path/to/output/dataset.csv
# ✗ Error: Invalid controller type
# ⚠ Dataset generation interrupted by user
```

### Programmatic

```python
from data_generation.generate_dataset import generate_dataset_programmatic

# Generate dataset programmatically
result_file = generate_dataset_programmatic(
    n_days=7,
    controller='loop-temp-basal',
    patient_id='adult#001',
    output_dir='my_output',
    quiet=True
)

if result_file:
    print(f"Dataset generated: {result_file}")
```

## CLI Arguments (Click Interface)

All arguments include automatic validation and show default values in help:

- `--n-days INTEGER`: Number of simulation days (default: 56)
- `--controller [choice]`: Controller type with automatic validation
  - Choices: `bolus-basal`, `loop-temp-basal`, `loop-automatic-bolus`, `pid-automated`, `pid-bolus`
- `--patient-pattern TEXT`: Filter patients by prefix (adult, child, adolescent)
- `--patient-id TEXT`: Simulate specific patient (e.g., "adult#001")
- `--max-patients INTEGER`: Limit number of patients simulated
- `--output-dir TEXT`: Output directory (default: data_generation)
- `--filename-prefix TEXT`: Output filename prefix (default: simglucose-adults)
- `--compute-therapy-settings/--no-compute-therapy-settings`: Boolean flag for therapy calculation
- `--sensor TEXT`: CGM sensor type (default: GuardianRT)
- `--pump TEXT`: Insulin pump type (default: Insulet)
- `--pid-p/--pid-i/--pid-d FLOAT`: PID controller parameters with type validation
- `--results-path TEXT`: Intermediate results path (default: ./results)
- `--quiet`: Boolean flag to suppress progress output

### Click-Specific Features

- **Automatic type conversion**: `--n-days 7` converts to integer
- **Choice validation**: Invalid controllers show available options
- **Boolean flags**: `--quiet` vs `--no-quiet`, `--compute-therapy-settings` vs `--no-compute-therapy-settings`
- **Help system**: `--help` shows all options with defaults
- **Colored output**: Success (green ✓), errors (red ✗), warnings (yellow ⚠)

## Integration in Other Repositories

1. **As a Git Submodule**:
   ```bash
   git submodule add https://github.com/your-repo/simglucose.git
   python simglucose/data_generation/generate_dataset.py --help
   ```

2. **As a Python Package**:
   ```bash
   pip install simglucose
   python -m data_generation.generate_dataset --help
   ```

3. **Direct Script Copy**:
   Copy `data_generation/generate_dataset.py` and use directly with simglucose installed.

## Testing

The script includes comprehensive error handling and validation:
- Invalid controller types are rejected
- Missing patient IDs are caught
- File permission issues are handled gracefully
- Keyboard interruption is supported

Run the test suite:
```bash
python test_generate_cli.py
python example_usage.py
```
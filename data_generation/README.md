# Synthetic Diabetes Dataset Generator

Generate realistic synthetic glucose datasets using the simglucose simulator with a modern Click-based CLI interface.

## Quick Start

Generate a dataset with all adult patients (default 56 days per patient):
```bash
python data_generation/generate_dataset.py
```

Quick test with a single patient:
```bash
python data_generation/generate_dataset.py --patient-id "adult#001" --n-days 1
```

## CLI Interface

The script provides a comprehensive command-line interface with automatic validation and helpful error messages:

```bash
# Show all available options with defaults
python data_generation/generate_dataset.py --help
```

## Common Usage Examples

### 1. Development and Testing
```bash
# Single patient, 1 day - fastest for testing
python data_generation/generate_dataset.py --patient-id "adult#001" --n-days 1 --quiet

# Few patients, short duration
python data_generation/generate_dataset.py --max-patients 3 --n-days 7
```

### 2. Different Controllers
```bash
# Basal-bolus controller (manual insulin management)
python data_generation/generate_dataset.py --controller bolus-basal

# PID automated controller with custom parameters
python data_generation/generate_dataset.py --controller pid-automated --pid-p 0.001 --pid-i 0.0001

# Loop controller with automatic bolus recommendations
python data_generation/generate_dataset.py --controller loop-automatic-bolus
```

### 3. Different Patient Populations
```bash
# All adult patients (default)
python data_generation/generate_dataset.py --patient-pattern adult

# All child patients, limited to 5 for faster generation
python data_generation/generate_dataset.py --patient-pattern child --max-patients 5

# All adolescent patients
python data_generation/generate_dataset.py --patient-pattern adolescent
```

### 4. Custom Output and Settings
```bash
# Custom output directory and filename
python data_generation/generate_dataset.py --output-dir /path/to/datasets --filename-prefix my-study

# Use stored therapy settings instead of computing from TDD
python data_generation/generate_dataset.py --no-compute-therapy-settings

# Different sensor and pump devices
python data_generation/generate_dataset.py --sensor Dexcom --pump Medtronic
```

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--n-days` | INTEGER | 56 | Number of days to simulate per patient |
| `--controller` | CHOICE | loop-temp-basal | Controller type (see below) |
| `--patient-pattern` | TEXT | adult | Filter patients by prefix |
| `--patient-id` | TEXT | None | Simulate specific patient only |
| `--max-patients` | INTEGER | None | Limit number of patients |
| `--output-dir` | TEXT | data_generation | Output directory |
| `--filename-prefix` | TEXT | simglucose-adults | Output filename prefix |
| `--compute-therapy-settings` | BOOLEAN | True | Compute therapy from TDD |
| `--sensor` | TEXT | GuardianRT | CGM sensor type |
| `--pump` | TEXT | Insulet | Insulin pump type |
| `--pid-p/i/d` | FLOAT | Various | PID controller parameters |
| `--results-path` | TEXT | ./results | Intermediate results path |
| `--quiet` | FLAG | False | Suppress progress output |

### Controller Types

- **`bolus-basal`**: Manual basal-bolus insulin management
- **`loop-temp-basal`**: Loop algorithm with temporary basal adjustments (default)
- **`loop-automatic-bolus`**: Loop algorithm with automatic bolus delivery
- **`pid-automated`**: Fully automated PID controller
- **`pid-bolus`**: PID controller with manual bolus input

### Patient Populations

The simulator includes 30 virtual patients across three age groups:
- **Adults** (`adult#001` - `adult#010`): Age 18+ with adult physiology
- **Adolescents** (`adolescent#001` - `adolescent#010`): Age 12-18 with adolescent physiology  
- **Children** (`child#001` - `child#010`): Age 3-11 with pediatric physiology

## Output Dataset

The generated CSV contains the following columns:

| Column | Unit | Description |
|--------|------|-------------|
| `date` | timestamp | Simulation timestamp (5-minute intervals) |
| `id` | string | Patient identifier |
| `CGM` | mg/dL | Continuous glucose monitor reading |
| `carbs` | grams | Carbohydrate intake (converted from g/min) |
| `basal` | U/hr | Basal insulin rate |
| `bolus` | U | Bolus insulin dose (converted from U/min) |
| `insulin` | U | Total insulin delivery (converted from U/min) |
| `TDD` | U | Total daily dose of insulin |
| `scheduled_basal` | U/hr | Scheduled basal rate |
| `isf` | mg/dL/U | Insulin sensitivity factor |
| `cr` | g/U | Carbohydrate ratio |
| `insulin_type` | string | Insulin type (default: novolog) |
| `weight` | lbs | Patient weight (converted from kg) |
| `ice` | mg/dL | Insulin counteraction effect |
| `iob` | U | Insulin on board |

## Programmatic Usage

You can also use the dataset generator programmatically in your Python code:

```python
from data_generation.generate_dataset import generate_dataset_programmatic

# Generate a small test dataset
result_file = generate_dataset_programmatic(
    n_days=7,
    controller='bolus-basal',
    patient_id='adult#001',
    output_dir='my_datasets',
    quiet=True
)

if result_file:
    print(f"Dataset generated: {result_file}")
    
    # Load and analyze the dataset
    import pandas as pd
    df = pd.read_csv(result_file, index_col=0, parse_dates=True)
    print(f"Generated {len(df)} records over {df.index[-1] - df.index[0]}")
```

## Notes and Technical Details

### Instability

For some controllers and patients, the simulation can be highly unstable, meaning that a majority of the simulation will plateau on the floor or roof value of blood glucose. Common reasons are: 
- For the patients that are not adults. 
- For meal scenarios of high variance with respect to quantity and timing.



### Data Processing
- **Insulin and carbs** are converted from per-minute to appropriate units (U/hr for basal, U for bolus, grams for carbs)
- **Sampling rate** is 5 minutes throughout the simulation
- **Missing values** are dropped from the final dataset
- **Therapy settings** can either be computed from Total Daily Dose (TDD) using standard formulas or loaded from stored patient parameters

### Meal Variability
This version includes enhanced meal size variability compared to the original simulator. The standard deviation of generated meal sizes has been increased in `simglucose/simulation/scenario_gen.py` (variable `amount_sigma`) to create more realistic eating patterns.

### Patient Parameters
Patient parameters are stored in `simglucose/params/`:
- **`Quest.csv`**: Contains therapy settings (CR, CF, TDI) for each patient
- **`vpatient_params.csv`**: Contains physiological parameters (BW, etc.)

Where:
- **CR**: Carb ratio in g/U (grams of carbs per unit of insulin)
- **CF**: Correction factor (ISF) in mg/dL/U (glucose reduction per unit of insulin)  
- **TDI**: Total daily insulin in U (typical daily insulin requirement)

## Troubleshooting

### Common Issues

**Import errors**: Make sure simglucose is installed
```bash
pip install -e .  # Install in development mode
```

**Permission errors**: Ensure write access to output directory
```bash
mkdir -p /path/to/output && chmod 755 /path/to/output
```

**Patient not found**: Use quotes around patient IDs
```bash
# Correct
python data_generation/generate_dataset.py --patient-id "adult#001"

# Wrong (shell interprets #)
python data_generation/generate_dataset.py --patient-id adult#001
```

**Long simulation times**: Use fewer patients or days for testing
```bash
# Fast test
python data_generation/generate_dataset.py --max-patients 1 --n-days 1
```



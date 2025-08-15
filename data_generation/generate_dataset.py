#!/usr/bin/env python3

import os
import sys
import click
from datetime import timedelta, datetime
import pandas as pd

# Use importlib.resources instead of deprecated pkg_resources
try:
    from importlib.resources import files
    def get_resource_path(package, resource):
        return str(files(package) / resource)
except ImportError:
    # Fallback for older Python versions
    import pkg_resources
    def get_resource_path(package, resource):
        return pkg_resources.resource_filename(package, resource)

# Add the parent directory to Python path if needed
# This allows the script to be run from anywhere
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from simglucose.simulation.env import T1DSimEnv
    from simglucose.controller.basal_bolus_ctrller import BBController
    from simglucose.controller.pid_ctrller import PIDController
    from simglucose.controller.loop_ctrller import LoopController
    from simglucose.sensor.cgm import CGMSensor
    from simglucose.actuator.pump import InsulinPump
    from simglucose.patient.t1dpatient import T1DPatient
    from simglucose.simulation.scenario_gen import RandomScenario
    from simglucose.simulation.sim_engine import SimObj, sim
    import loop_to_python_api.api as loop_to_python_api
except ImportError as e:
    click.echo(click.style(f"✗ Import error: {e}", fg='red'))
    click.echo(click.style("Please ensure simglucose is properly installed:", fg='yellow'))
    click.echo("  pip install -e .")
    click.echo("  or run from the simglucose root directory")
    sys.exit(1)

CONTROLLER_TYPES = ['bolus-basal', 'loop-temp-basal', 'loop-automatic-bolus', 'pid-automated', 'pid-bolus']


def create_controller(controller_type, pid_p=0.000001, pid_i=0.00000005, pid_d=0.0):
    """Create a controller object based on the specified type and parameters."""
    controllers = {
        'bolus-basal': BBController(),
        'loop-temp-basal': LoopController(recommendation_type='tempBasal'),
        'loop-automatic-bolus': LoopController(recommendation_type='automaticBolus'),
        'pid-automated': PIDController(P=pid_p, I=pid_i, D=pid_d, is_fully_automated=True),
        'pid-bolus': PIDController(P=pid_p, I=pid_i, D=pid_d, is_fully_automated=False),
    }
    
    if controller_type not in controllers:
        raise ValueError(f"Unknown controller type: {controller_type}. Available: {list(controllers.keys())}")
    
    return controllers[controller_type]


def load_patient_data(patient_pattern='adult', patient_id=None, max_patients=None):
    """Load patient data and parameters, filtered by the given criteria."""
    # Get all patient ids and patient params
    USER_DATA_FILE = get_resource_path("simglucose", "params/Quest.csv")
    patient_data = pd.read_csv(USER_DATA_FILE)
    
    if patient_id:
        # Use specific patient ID
        if patient_id in patient_data['Name'].values:
            patient_ids = [patient_id]
        else:
            raise ValueError(f"Patient ID '{patient_id}' not found in the dataset")
    else:
        # Use pattern filtering
        patient_ids = [pid for pid in patient_data['Name'].unique() if pid.startswith(patient_pattern)]
        
        # Apply max_patients limit if specified
        if max_patients and len(patient_ids) > max_patients:
            patient_ids = patient_ids[:max_patients]
    
    PATIENT_PARA_FILE = get_resource_path("simglucose", "params/vpatient_params.csv")
    patient_parameters = pd.read_csv(PATIENT_PARA_FILE)
    
    return patient_data, patient_parameters, patient_ids


def generate_dataset_core(
    n_days, controller_type, patient_pattern, patient_id, max_patients, 
    output_dir, filename_prefix, compute_therapy_settings, sensor, pump, 
    pid_p, pid_i, pid_d, results_path, quiet
):
    """Core function to generate the dataset with the given configuration."""
    # Create controller
    controller = create_controller(controller_type, pid_p, pid_i, pid_d)
    
    # Load patient data
    patient_data, patient_parameters, patient_ids = load_patient_data(
        patient_pattern, patient_id, max_patients
    )
    
    if not patient_ids:
        if not quiet:
            click.echo(f"No patients found matching pattern: {patient_pattern}")
        return None
    
    # Set up timing
    now = datetime.now()
    start_time = datetime.combine(now.date(), datetime.min.time())
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(results_path, exist_ok=True)
    
    # Create filename with controller details
    controller_name = controller_type
    if controller_type in ['pid-automated', 'pid-bolus']:
        controller_name = f"{controller_type}-{pid_p}-{pid_i}-{pid_d}"
    
    save_file_name = os.path.join(
        output_dir, 
        f'{filename_prefix}_contr-{controller_name}_computed-settings-{compute_therapy_settings}_{n_days}-days.csv'
    )
    
    if not quiet:
        click.echo(f"Generating dataset with {len(patient_ids)} patients for {n_days} days")
        click.echo(f"Controller: {controller_name}")
        click.echo(f"Output file: {save_file_name}")
        click.echo("="*50)
    
    df = pd.DataFrame()
    
    for i, patient_id in enumerate(patient_ids, 1):
        # Create a simulation environment
        patient = T1DPatient.withName(patient_id)
        sensor = CGMSensor.withName(sensor)
        pump = InsulinPump.withName(pump)
        scenario = RandomScenario(start_time=start_time, seed=None)
        env = T1DSimEnv(patient, sensor, pump, scenario)

        patient_data_row = patient_data[patient_data['Name'] == patient_id].iloc[0]

        # Put them together to create a simulation object
        s = SimObj(env, controller, timedelta(days=n_days), animate=False, path=results_path)
        results = sim(s)

        results['age'] = patient_data_row['Age']
        results['id'] = patient_id

        # Create the final df
        formatted_df = results[['id', 'CGM', 'CHO', 'basal', 'bolus', 'insulin']].copy()
        formatted_df.rename(columns={'CHO': 'carbs', 'Age': 'age'}, inplace=True)
        formatted_df['carbs'] = formatted_df['carbs'] * 5  # From gram/min to grams
        formatted_df['insulin'] = formatted_df['insulin'] * 5  # From U/min to U

        # Delivered basal and bolus
        formatted_df['basal'] = formatted_df['basal'] * 60  # From U/min to U/hr
        formatted_df['bolus'] = formatted_df['bolus'] * 5  # From U/min to U

        formatted_df.dropna(inplace=True)

        if compute_therapy_settings:
            tdd = formatted_df['insulin'].resample('D').sum().mean()
            basal = tdd * 0.45 / 24  # Basal 45% of TDI
            isf = 1800 / tdd
            cr = (500 / tdd).round(2)
        else:
            tdd = patient_data_row['TDI']
            basal = formatted_df['basal'].mean()
            isf = patient_data_row['CF']
            cr = int(patient_data_row['CR'])

        formatted_df['TDD'] = tdd.round(2)
        formatted_df['scheduled_basal'] = basal.round(2)
        formatted_df['isf'] = isf.round(2)
        formatted_df['cr'] = cr
        formatted_df['insulin_type'] = 'novolog'  # Using a simple default

        # Add weight (from kg to Ibs)
        weight = patient_parameters[patient_parameters['Name'] == patient_id].iloc[0]['BW']
        formatted_df['weight'] = weight * 2.20462

        # Add iob and ice columns
        formatted_df = loop_to_python_api.add_insulin_counteraction_effect_to_df(formatted_df, basal, isf, cr)
        formatted_df = loop_to_python_api.add_insulin_on_board_to_df(formatted_df, basal, isf, cr)
        formatted_df['ice'] = (formatted_df['ice'] * 60 * 5).round(2)  # From mg/dL*s to mg/dL

        formatted_df.index.name = 'date'
        df = pd.concat([df, formatted_df])
        
        # Save intermediate results
        df.to_csv(save_file_name)

        if not quiet:
            click.echo(f"[{i}/{len(patient_ids)}] {patient_id} with controller {controller_name} finished processing")
            
            # Calculate and display metrics for current dataset
            tir = round(len(df[(df['CGM'] > 70) & (df['CGM'] < 180)]) / len(df) * 100) if len(df) > 0 else 0
            tar = round(len(df[df['CGM'] >= 180]) / len(df) * 100) if len(df) > 0 else 0
            tbr = round(len(df[df['CGM'] <= 70]) / len(df) * 100) if len(df) > 0 else 0
            
            click.echo(f"  Current dataset metrics: TIR {tir}%, TAR {tar}%, TBR {tbr}%")
            click.echo()

    # Final save
    df.to_csv(save_file_name)
    
    if not quiet:
        click.echo(f"Dataset generation completed!")
        click.echo(f"Final dataset saved to: {save_file_name}")
        click.echo(f"Total records: {len(df)}")
    
    return save_file_name


def generate_dataset_programmatic(
    n_days=56,
    controller='loop-temp-basal',
    patient_pattern='adult',
    patient_id=None,
    max_patients=None,
    output_dir='data_generation',
    filename_prefix='simglucose-adults',
    compute_therapy_settings=True,
    sensor='GuardianRT',
    pump='Insulet',
    pid_p=0.000001,
    pid_i=0.00000005,
    pid_d=0.0,
    results_path='./results',
    quiet=False
):
    """
    Programmatic interface for generating datasets without CLI.
    
    This function can be called from other Python scripts or packages.
    
    Returns:
        str: Path to the generated dataset file, or None if generation failed
    """
    return generate_dataset_core(
        n_days, controller, patient_pattern, patient_id, max_patients,
        output_dir, filename_prefix, compute_therapy_settings, sensor, pump,
        pid_p, pid_i, pid_d, results_path, quiet
    )


@click.command()
@click.option('--n-days', default=56, type=int, show_default=True, 
              help='Number of days of data to generate for each patient')
@click.option('--filename-prefix', default='simglucose-adults', show_default=True,
              help='Prefix for the output filename')
@click.option('--output-dir', default='data_generation', show_default=True,
              help='Directory to save the generated dataset')
@click.option('--results-path', default='./results', show_default=True,
              help='Path for intermediate simulation results')
@click.option('--controller', default='loop-temp-basal', show_default=True,
              type=click.Choice(CONTROLLER_TYPES), 
              help='Type of controller to use for simulation')
@click.option('--pid-p', default=0.000001, type=float, show_default=True,
              help='PID controller P parameter (only used with pid controllers)')
@click.option('--pid-i', default=0.00000005, type=float, show_default=True,
              help='PID controller I parameter (only used with pid controllers)')
@click.option('--pid-d', default=0.0, type=float, show_default=True,
              help='PID controller D parameter (only used with pid controllers)')
@click.option('--patient-pattern', default='adult', show_default=True,
              help='Pattern to filter patient IDs (e.g., "adult", "child", "adolescent")')
@click.option('--patient-id', default=None, 
              help='Specific patient ID to simulate (e.g., "adult#001"). If specified, only this patient will be simulated.')
@click.option('--max-patients', default=None, type=int,
              help='Maximum number of patients to simulate (useful for testing)')
@click.option('--compute-therapy-settings/--no-compute-therapy-settings', default=True,
              help='Compute therapy settings from TDD rather than using stored settings')
@click.option('--sensor', default='GuardianRT', show_default=True,
              help='CGM sensor type to use')
@click.option('--pump', default='Insulet', show_default=True,
              help='Insulin pump type to use')
@click.option('--quiet', is_flag=True, default=False,
              help='Suppress progress output')
def main(n_days, filename_prefix, output_dir, results_path, controller, 
         pid_p, pid_i, pid_d, patient_pattern, patient_id, max_patients,
         compute_therapy_settings, sensor, pump, quiet):
    """Generate synthetic glucose datasets using simglucose simulator."""
    try:
        result_file = generate_dataset_core(
            n_days, controller, patient_pattern, patient_id, max_patients,
            output_dir, filename_prefix, compute_therapy_settings, sensor, pump,
            pid_p, pid_i, pid_d, results_path, quiet
        )
        
        if result_file:
            if not quiet:
                click.echo(click.style(f"✓ Successfully generated dataset: {result_file}", fg='green'))
        else:
            click.echo(click.style("✗ Failed to generate dataset", fg='red'))
            sys.exit(1)
            
    except KeyboardInterrupt:
        click.echo(click.style("\n⚠ Dataset generation interrupted by user", fg='yellow'))
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"✗ Error generating dataset: {e}", fg='red'))
        sys.exit(1)


if __name__ == '__main__':
    main()

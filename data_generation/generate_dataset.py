from simglucose.simulation.env import T1DSimEnv
from simglucose.controller.basal_bolus_ctrller import BBController
from simglucose.controller.pid_ctrller import PIDController
from simglucose.controller.loop_ctrller import LoopController
from simglucose.sensor.cgm import CGMSensor
from simglucose.actuator.pump import InsulinPump
from simglucose.patient.t1dpatient import T1DPatient
from simglucose.simulation.scenario_gen import RandomScenario
from simglucose.simulation.sim_engine import SimObj, sim
from datetime import timedelta
from datetime import datetime
import pandas as pd
import pkg_resources
import loop_to_python_api.api as loop_to_python_api

# How many days of data to generate for each patient
N_DAYS = 7*8
FILENAME_PREFIX = 'simglucose-adults'

# Whether to compute the therapy settings from TDD (True), or to use the stored therapy settings for the user (False)
COMPUTE_THERAPY_SETTINGS = True
P = 0.000001
I = 0.00000005
D = 0
CONTROLLER = f'loop-temp-basal'

# Create a controller object
controllers = {
    f'pid-automated-{P}-{I}-{D}': PIDController(P=P, I=I, D=D, is_fully_automated=True),
    f'pid-bolus-{P}-{I}-{D}': PIDController(P=P, I=I, D=D, is_fully_automated=False),
    'bolus-basal': BBController(),
    'loop-temp-basal': LoopController(recommendation_type='tempBasal'),
    'loop-automatic-bolus': LoopController(recommendation_type='automaticBolus'),
}
controller = controllers[CONTROLLER]

# specify start_time as the beginning of today
now = datetime.now()
start_time = datetime.combine(now.date(), datetime.min.time())

# Get all patient ids and patient params
USER_DATA_FILE = pkg_resources.resource_filename(
    "simglucose", "params/Quest.csv"
)
patient_data = pd.read_csv(USER_DATA_FILE)
patient_ids = [pid for pid in patient_data['Name'].unique() if pid.startswith('adult')]

PATIENT_PARA_FILE = pkg_resources.resource_filename(
    "simglucose", "params/vpatient_params.csv"
)
patient_parameters = pd.read_csv(PATIENT_PARA_FILE)

# --------- Create Random Scenario --------------
# Specify results saving path
path = './results'
save_file_name = f'data_generation/{FILENAME_PREFIX}_contr-{CONTROLLER}_computed-settings-{COMPUTE_THERAPY_SETTINGS}_{N_DAYS}-days.csv'

df = pd.DataFrame()

for patient_id in patient_ids:
    # Create a simulation environment
    patient = T1DPatient.withName(patient_id)
    sensor = CGMSensor.withName('GuardianRT')  # Sensor params are the same as Dexcom, only sampling rate is different (here 5 minutes)
    pump = InsulinPump.withName('Insulet')
    scenario = RandomScenario(start_time=start_time, seed=None)
    env = T1DSimEnv(patient, sensor, pump, scenario)

    patient_data_row = patient_data[patient_data['Name'] == patient_id].iloc[0]

    # Put them together to create a simulation object
    s = SimObj(env, controller, timedelta(days=N_DAYS), animate=False, path=path)
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

    if COMPUTE_THERAPY_SETTINGS:
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
    df.to_csv(save_file_name)

    print(f"{patient_id} with controller {CONTROLLER} finished processing with results: ")
    print(f"TIR {round(len(df[(df['CGM'] > 70) & (df['CGM'] < 180)]) / len(df) * 100)}%")
    print(f"TAR {round(len(df[df['CGM'] >= 180]) / len(df) * 100)}%")
    print(f"TBR {round(len(df[df['CGM'] <= 70]) / len(df) * 100)}%")
    print('')

# TODO: Run in parallel
df.to_csv(save_file_name)

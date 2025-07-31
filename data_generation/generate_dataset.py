from simglucose.simulation.env import T1DSimEnv
from simglucose.controller.basal_bolus_ctrller import BBController
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
N_DAYS = 14

# specify start_time as the beginning of today
now = datetime.now()
start_time = datetime.combine(now.date(), datetime.min.time())

# Get all patient ids and patient params
USER_DATA_FILE = pkg_resources.resource_filename(
    "simglucose", "params/Quest.csv"
)
patient_data = pd.read_csv(USER_DATA_FILE)
patient_ids = patient_data['Name']
PATIENT_PARA_FILE = pkg_resources.resource_filename(
    "simglucose", "params/vpatient_params.csv"
)
patient_parameters = pd.read_csv(PATIENT_PARA_FILE)

# --------- Create Random Scenario --------------
# Specify results saving path
path = './results'

# Create a controller
controller = BBController()

df = pd.DataFrame()

for patient_id in patient_ids:
    # Create a simulation environment
    patient = T1DPatient.withName(patient_id)
    sensor = CGMSensor.withName('GuardianRT')  # Sensor params are the same as Dexcom, only sampling rate is different (here 5 minutes)
    pump = InsulinPump.withName('Insulet')
    scenario = RandomScenario(start_time=start_time, seed=None)
    env = T1DSimEnv(patient, sensor, pump, scenario)

    # Put them together to create a simulation object
    s = SimObj(env, controller, timedelta(days=N_DAYS), animate=False, path=path)
    results = sim(s)
    results['age'] = patient_data[patient_data['Name'] == patient_id].iloc[0]['Age']
    results['id'] = patient_id

    # Create the final df
    formatted_df = results[['id', 'CGM', 'CHO', 'insulin']]
    formatted_df.rename(columns={'CHO': 'carbs', 'Age': 'age'}, inplace=True)
    formatted_df['carbs'] = formatted_df['carbs'] * 5  # From gram/min to grams
    formatted_df['insulin'] = formatted_df['insulin'] * 5  # From U/min to U

    basal = formatted_df['insulin'].median() * 60 / 5  # Basal in U/hr
    formatted_df['scheduled_basal'] = basal
    formatted_df.dropna(inplace=True)

    # Delivered basal and bolus
    formatted_df['basal'] = basal
    formatted_df['bolus'] = (formatted_df['insulin'] - (formatted_df['basal'] / 12)).round(2)

    tdd = formatted_df['insulin'].resample('D').sum().mean()
    isf = 1800 / tdd
    cr = 500 / tdd
    formatted_df['TDD'] = tdd.round(2)
    formatted_df['isf'] = isf.round(2)
    formatted_df['cr'] = cr.round(2)
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

df.to_csv('data_generation/simglucose.csv')



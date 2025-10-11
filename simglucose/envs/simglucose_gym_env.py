from simglucose.simulation.env import T1DSimEnv as _T1DSimEnv
from simglucose.patient.t1dpatient import T1DPatient
from simglucose.sensor.cgm import CGMSensor
from simglucose.actuator.pump import InsulinPump
from simglucose.simulation.scenario_gen import RandomScenario
from simglucose.controller.base import Action
import numpy as np
import pkg_resources
import gym
from gym import spaces
from gym.utils import seeding
from datetime import datetime
import gymnasium


PATIENT_PARA_FILE = pkg_resources.resource_filename(
    "simglucose", "params/vpatient_params.csv"
)


class T1DSimEnv(gym.Env):
    """
    A wrapper of simglucose.simulation.env.T1DSimEnv to support gym API
    """

    metadata = {"render.modes": ["human"]}

    SENSOR_HARDWARE = "Dexcom"
    INSULIN_PUMP_HARDWARE = "Insulet"

    def __init__(
        self, patient_name=None, custom_scenario=None, reward_fun=None, seed=None
    ):
        """
        patient_name must be 'adolescent#001' to 'adolescent#010',
        or 'adult#001' to 'adult#010', or 'child#001' to 'child#010'
        """
        # have to hard code the patient_name, gym has some interesting
        # error when choosing the patient
        if patient_name is None:
            patient_name = ["adolescent#001"]

        self.patient_name = patient_name
        self.reward_fun = reward_fun
        self.np_random, _ = seeding.np_random(seed=seed)
        self.custom_scenario = custom_scenario
        self.env, _, _, _ = self._create_env()

    def step(self, action: float):
        act = Action(basal=action, bolus=0)
        if self.reward_fun is None:
            obs, reward, done, info = self.env.step(act)
        else:
            obs, reward, done, info = self.env.step(act, reward_fun=self.reward_fun)

        obs_array = np.array([obs.CGM])  # convert to numpy array
        reward = reward
        terminated = done
        truncated = False
        return obs_array, reward, terminated, truncated, info

    def _raw_reset(self):
        return self.env.reset()

    def reset(self, *, seed=None, options=None):
        self.np_random = np.random.default_rng(seed)
        self.env, seed2, seed3, seed4 = self._create_env()
        obs = self.env.reset()
        return obs, {"seeds": [seed, seed2, seed3, seed4]}

    def _create_env(self):
        # Derive a random seed. This gets passed as a uint, but gets
        # checked as an int elsewhere, so we need to keep it below
        # 2**31.
        base_seed = int(self.np_random.integers(0, 1000))

        # Step 2: deterministically derive seeds from one another
        def derive_seed(x):
            return abs(hash(int(x))) % (2 ** 31)

        seed2 = derive_seed(base_seed)
        seed3 = derive_seed(seed2 + 1)
        seed4 = derive_seed(seed3 + 1)

        hour = self.np_random.integers(low=0, high=24)
        start_time = datetime(2018, 1, 1, hour, 0, 0)

        if isinstance(self.patient_name, list):
            patient_name = self.np_random.choice(self.patient_name)
            patient = T1DPatient.withName(patient_name, random_init_bg=True, seed=seed4)
        else:
            patient = T1DPatient.withName(
                self.patient_name, random_init_bg=True, seed=seed4
            )

        if isinstance(self.custom_scenario, list):
            scenario = self.np_random.choice(self.custom_scenario)
        else:
            scenario = (
                RandomScenario(start_time=start_time, seed=seed3)
                if self.custom_scenario is None
                else self.custom_scenario
            )

        sensor = CGMSensor.withName(self.SENSOR_HARDWARE, seed=seed2)
        pump = InsulinPump.withName(self.INSULIN_PUMP_HARDWARE)
        env = _T1DSimEnv(patient, sensor, pump, scenario)
        return env, seed2, seed3, seed4

    def render(self):
        if self.render_mode == "human" and hasattr(self.env, "render"):
            self.env.render()

    def close(self):
        if hasattr(self.env, "close"):
            self.env.close()

    @property
    def action_space(self):
        ub = self.env.pump._params["max_basal"]
        return spaces.Box(low=0, high=ub, shape=(1,))

    @property
    def observation_space(self):
        return spaces.Box(low=0, high=1000, shape=(1,))

    @property
    def max_basal(self):
        return self.env.pump._params["max_basal"]


class T1DSimGymnaisumEnv(gymnasium.Env):
    metadata = {"render_modes": ["human"], "render_fps": 60}
    MAX_BG = 1000

    def __init__(
        self,
        patient_name=None,
        custom_scenario=None,
        reward_fun=None,
        seed=None,
        render_mode='human',
    ) -> None:
        super().__init__()
        self.render_mode = render_mode
        self.env = T1DSimEnv(
            patient_name=patient_name,
            custom_scenario=custom_scenario,
            reward_fun=reward_fun,
            seed=seed,
        )
        self.observation_space = gymnasium.spaces.Box(
            low=0, high=self.MAX_BG, shape=(1,), dtype=np.float32
        )
        self.action_space = gymnasium.spaces.Box(
            low=0, high=self.env.max_basal, shape=(1,), dtype=np.float32
        )

    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)
        return np.array([obs.CGM], dtype=np.float32), reward, terminated, truncated, info

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        obs, _, _, info = self.env._raw_reset()
        return np.array([obs.CGM], dtype=np.float32), info

    def render(self):
        if self.render_mode == "human":
            self.env.render()

    def close(self):
        self.env.close()

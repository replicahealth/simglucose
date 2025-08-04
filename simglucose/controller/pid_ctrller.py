from simglucose.controller.basal_bolus_ctrller import BBController
from .base import Action
import logging

logger = logging.getLogger(__name__)


class PIDController(BBController):
    def __init__(self, P=1, I=0, D=0, target=140, is_fully_automated=True):
        super(PIDController, self).__init__(target=target)
        self.P = P
        self.I = I
        self.D = D
        self.target = target
        self.integrated_state = 0
        self.prev_state = 0
        self.is_fully_automated = is_fully_automated

    def policy(self, observation, reward, done, **kwargs):
        sample_time = kwargs.get('sample_time')

        # BG is the only state for this PID controller
        bg = observation.CGM
        control_input = self.P * (bg - self.target) + \
            self.I * self.integrated_state + \
            self.D * (bg - self.prev_state) / sample_time

        logger.info('Control input: {}'.format(control_input))

        # update the states
        self.prev_state = bg
        self.integrated_state += (bg - self.target) * sample_time
        logger.info('prev state: {}'.format(self.prev_state))
        logger.info('integrated state: {}'.format(self.integrated_state))

        # return the action
        if self.is_fully_automated:
            action = Action(basal=control_input, bolus=0)
            return action
        else:
            bb_action = super(PIDController, self).policy(observation, reward, done, **kwargs)
            action = Action(basal=bb_action.basal, bolus=bb_action.bolus)
            return action

    def reset(self):
        self.integrated_state = 0
        self.prev_state = 0

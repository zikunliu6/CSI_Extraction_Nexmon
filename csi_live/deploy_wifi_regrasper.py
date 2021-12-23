import gym
from gym import error, spaces, utils
from gym.utils import seeding
import envs
import time
import io
import numpy as np
import torch
import matplotlib.pyplot as plt
import pickle
from pathlib import Path
from tqdm import tqdm
from envs.utils.csi_reader import *

from absl import app
from absl import flags
from train_wifi_regrasper import WifiReGraspNet

FLAGS = flags.FLAGS

flags.DEFINE_string('locobot_ip', None, 'IP address of LoCoBot.')
flags.DEFINE_string('locobot_user', 'locobot', 'Username for LoCoBot.')
flags.DEFINE_string('locobot_pwd', 'locobot', 'Password for LoCoBot.')
flags.DEFINE_string('monitor_ip', None, 'IP address of monitor.')
flags.DEFINE_string('monitor_user', 'root', 'Username for monitor.')
flags.DEFINE_string('monitor_pwd', 'toor', 'Password for monitor.')
flags.DEFINE_enum('chip', None, ['4358', '43455c0'], \
                  'Wifi card. Possible options are 4358 for Nexus 6P, 43455c0 for Raspberry Pi 4.')
flags.DEFINE_string('csi_params', \
                    'ZtgBEQAAAQDcpjKZ5CkAAAAAAAAAAAAAAAAAAAAAAAAAAA==',\
                    'CSI parameter string from makecsiparams.')
                    # -c 100/40 -C 1 -N 1 -m dc:a6:32:99:e4:29
                    # channel 100, bandwidth 40MHz, core 1, stream 1, pi1

flags.DEFINE_multi_float('yaw_range', [-np.pi/2,np.pi/2], 'Range of yaw values in radians.', lower_bound=-np.pi/2, upper_bound=np.pi/2)
flags.DEFINE_multi_float('joint1_range', [0,0], 'Range of joint1 values in radians.', lower_bound=0, upper_bound=0)
flags.DEFINE_multi_float('pitch_range', [-np.pi/2,np.pi/2], 'Range of pitch values in radians.', lower_bound=-np.pi/2, upper_bound=np.pi/2)
flags.DEFINE_multi_float('joint2_range', [-np.pi/2,np.pi/2], 'Range of joint2 values in radians.', lower_bound=-np.pi/2, upper_bound=np.pi/2)
flags.DEFINE_multi_float('roll_range', [-np.pi/2,np.pi/2], 'Range of roll values in radians.', lower_bound=-np.pi/2, upper_bound=np.pi/2)

flags.DEFINE_integer('n_regrasps', 10, 'Number of steps to perform in the stochastic greedy search.', lower_bound=1)
flags.DEFINE_integer('n_samples', 10, 'Number of actions samples to predict best grasp.', lower_bound=1)
flags.DEFINE_integer('n_frames', 100, 'Number of frames to capture per position.', lower_bound=1)
flags.DEFINE_integer('reset_every', 5, 'Set arm to home position every few steps.',lower_bound=1)
flags.DEFINE_float('action_stdev', np.pi/8, 'Determines how large each randomized action should be.', lower_bound=0)

flags.mark_flag_as_required('locobot_ip')
flags.mark_flag_as_required('monitor_ip')
flags.mark_flag_as_required('chip')

device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
# Don't use joint1, it is cursed!
def valid_joints(joints):
    yaw, joint1, pitch, joint2, roll = joints
    if not (FLAGS.yaw_range[0] <= yaw <= FLAGS.yaw_range[1]):
        return False
    # if not (FLAGS.joint1_range[0] <= joint1 <= FLAGS.joint1_range[1]):
    #     return False
    if not (FLAGS.pitch_range[0] <= pitch <= FLAGS.pitch_range[1]):
        return False
    if not (FLAGS.joint2_range[0] <= joint2 <= FLAGS.joint2_range[1]):
        return False
    if not (FLAGS.roll_range[0] <= roll <= FLAGS.roll_range[1]):
        return False

    return True

# Pick random action within a norm-ball
def sample_spherical():
    # Sample direction on unit sphere.
    vec = np.random.randn(4)
    vec /= np.linalg.norm(vec)

    # Scale by action_stdev
    vec *= np.random.normal(scale=FLAGS.action_stdev)
    return np.array([vec[0],0,vec[1],vec[2],vec[3]])
def get_spectrogram(csi):
    """Quality metric for CSI array.

    Args:
        csi: An n_frames x b complex Numpy array of CSI values.

    Returns:
        108 x 1 spectrogram of magnitude over all frequency bins. 
    """
    data_carriers = csi[:, data_bins[csi.shape[1]]]
    return np.mean(np.abs(data_carriers),0)

def main(_):

    roboap = gym.make('RoboAP-v1')
    roboap.reset()

    grasp_net = WifiReGraspNet()
    state_dict = torch.load('./checkpoints/regrasper_model_500.pt')['model_state_dict']
    grasp_net.load_state_dict(state_dict)

    # Number of steps of stochastic greedy search to perform
    for i in tqdm(range(FLAGS.n_regrasps)):

        # Get and save current joints and CSI
        current_joints, current_csi = roboap.render('csi', FLAGS.n_frames)
        current_spectrogram = get_spectrogram(current_csi)

        #At each step, sample n feasible actions
        n = FLAGS.n_samples
        actions = []
        while n>0:
            action = sample_spherical()
            if valid_joints(current_joints + action):
                actions.append(action)
                n -= 1
            else:
                continue
        
        #Infer the best action to take based on the magnitude of the success probability
        inference_batch = [[current_joints, current_spectrogram, action] for action in actions]
        batch_loader = torch.utils.data.DataLoader(inference_batch, batch_size = len(inference_batch))
        
        with torch.no_grad():
            predictions = grasp_net.infer(batch_loader)
        
        #If none of the actions seem-favourable, stop the search
        if max(predictions[:,1] - predictions[:,0]) <= 0:
            print('No further improvement obtainable. Exiting here. ')
            break
        best_action = actions[predictions[:,1].argmax(0)]
        
        # Move arm to next joint.
        roboap.step_joints(current_joints + best_action)

        # Get and save current joints and CSI
        next_joints, next_csi = roboap.render('csi', FLAGS.n_frames)
        next_spectrogram = get_spectrogram(next_csi)

        prev_quality, new_quality = get_quality(current_csi), get_quality(next_csi)
        print('Difference in absolute quality is', new_quality,prev_quality, new_quality - prev_quality)

if __name__ == '__main__':
    app.run(main)
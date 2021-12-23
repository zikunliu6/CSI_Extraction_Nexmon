import gym
from gym import error, spaces, utils
from gym.utils import seeding
import envs
import time
import io
import numpy as np
import matplotlib.pyplot as plt
import pickle
from pathlib import Path
from tqdm import tqdm
from envs.utils.csi_reader import *

from absl import app
from absl import flags

FLAGS = flags.FLAGS

flags.DEFINE_string('locobot_ip', None, 'IP address of LoCoBot.')
flags.DEFINE_string('locobot_user', None, 'Username for LoCoBot.')
flags.DEFINE_string('locobot_pwd', None, 'Password for LoCoBot.')
flags.DEFINE_string('monitor_ip', None, 'IP address of monitor.')
flags.DEFINE_string('monitor_user', None, 'Username for monitor.')
flags.DEFINE_string('monitor_pwd', None, 'Password for monitor.')
flags.DEFINE_enum('chip', None, ['4358', '43455c0', '4366c0'], 'Wifi card. Possible options are 4358 for Nexus 6P, 43455c0 for Raspberry Pi 4, 4366c0 for ASUS RT-AC86U')
flags.DEFINE_string('chan_spec', None, 'Channel specification.')
flags.DEFINE_integer('core_mask', None, 'Bitmask for cores to use.', lower_bound=0, upper_bound=15)
flags.DEFINE_integer('stream_mask', None, 'Bitmask for streams to use.', lower_bound=0, upper_bound=15)
flags.DEFINE_multi_string('clients', None, 'List of client MAC addresses.')

flags.DEFINE_multi_float('yaw_range', [-np.pi/2,np.pi/2], 'Range of yaw values in radians.', lower_bound=-np.pi/2, upper_bound=np.pi/2)
flags.DEFINE_multi_float('joint1_range', [0,0], 'Range of joint1 values in radians.', lower_bound=0, upper_bound=0)
flags.DEFINE_multi_float('pitch_range', [-np.pi/2,np.pi/4], 'Range of pitch values in radians.', lower_bound=-np.pi/2, upper_bound=np.pi/2)
flags.DEFINE_multi_float('joint2_range', [-np.pi/2,np.pi/2], 'Range of joint2 values in radians.', lower_bound=-np.pi/2, upper_bound=np.pi/2)
flags.DEFINE_multi_float('roll_range', [-np.pi/2,np.pi/2], 'Range of roll values in radians.', lower_bound=-np.pi/2, upper_bound=np.pi/2)

flags.DEFINE_integer('n_experience', 1000, 'Number of experience samples to collect.', lower_bound=1)
flags.DEFINE_integer('n_frames', 100, 'Number of frames to capture per position.', lower_bound=1)
flags.DEFINE_integer('reset_every', 10, 'Set arm to home position every few steps.',lower_bound=1)
flags.DEFINE_float('action_stdev', np.pi/8, 'Determines how large each randomized action should be.', lower_bound=0)
flags.DEFINE_string('out_dir', None, 'Folder to store the results')

flags.mark_flag_as_required('locobot_ip')
flags.mark_flag_as_required('locobot_user')
flags.mark_flag_as_required('locobot_pwd')

flags.mark_flag_as_required('monitor_ip')
flags.mark_flag_as_required('monitor_user')
flags.mark_flag_as_required('monitor_pwd')
flags.mark_flag_as_required('chip')
flags.mark_flag_as_required('chan_spec')
flags.mark_flag_as_required('core_mask')
flags.mark_flag_as_required('stream_mask')
flags.mark_flag_as_required('clients')

flags.mark_flag_as_required('out_dir')

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
    # if not (joint1 + pitch + joint2) <= 1.5:
    #     return False

    return True

# Pick random action within a norm-ball
def sample_spherical():
    # Sample direction on unit sphere.
    vec = np.random.randn(4)
    vec /= np.linalg.norm(vec)

    # Scale by action_stdev
    vec *= np.random.normal(scale=FLAGS.action_stdev)
    return np.array([vec[0],0,vec[1],vec[2],vec[3]])

def main(_):
    # Make output directory. Throw error if already exists.
    out_dir = Path(FLAGS.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Dump metadata.
    with open(f'{out_dir}/chan_spec.pkl', 'wb') as f :
        pickle.dump(FLAGS.chan_spec, f)
    with open(f'{out_dir}/core_mask.pkl', 'wb') as f :
        pickle.dump(FLAGS.core_mask, f)
    with open(f'{out_dir}/stream_mask.pkl', 'wb') as f:
        pickle.dump(FLAGS.stream_mask, f)
    with open(f'{out_dir}/clients.pkl', 'wb') as f:
        pickle.dump(FLAGS.clients, f)

    # Store trajectory. 
    joint_positions = []
    actions = []

    # Initialize robot.
    roboap = gym.make('RoboAP-v1')
    roboap.reset()

    # Get experience tuples by performing n_experience random actions.
    for i in tqdm(range(FLAGS.n_experience)):

        # Get and save current joints and CSI
        current_joints, csi = roboap.render('csi', FLAGS.n_frames)
        print(f'joint_positions[{i}]: ', current_joints)
        # print(f'csi[{i}]: ', csi)

        joint_positions.append(current_joints)
        # Dump the CSI at the position to a file.
        with open(f'{out_dir}/{i}.npy', 'wb') as f:
            np.save(f, csi, allow_pickle=True)

        # Sample a random valid action within a valid range.
        if (i+1) % FLAGS.reset_every == 0:
            # Move arm to home position.
            action = -current_joints
        else:
            while True:
                action = sample_spherical()
                if valid_joints(current_joints + action):
                    break

        print (f'action[{i}]: ', action)
        actions.append(action)

        # Move arm to next joint.
        roboap.step_joints(current_joints + action)

    # Get and final joints and CSI
    current_joints, csi = roboap.render('csi', FLAGS.n_frames)
    print(f'joint_positions[{i}]: ', current_joints)
    # print(f'csi[{i}]: ', csi)

    joint_positions.append(current_joints)
    # Dump the CSI at the position to a file.
    with open(f'{out_dir}/{i}.npy', 'wb') as f:
        np.save(f, csi, allow_pickle=True)

    # Save joint positions.
    with open(f'{out_dir}/joint_positions.pkl', 'wb') as f:
        pickle.dump(joint_positions, f)

    # Save actions.
    with open(f'{out_dir}/actions.pkl', 'wb') as f:
        pickle.dump(actions, f)


if __name__ == '__main__':
    app.run(main)


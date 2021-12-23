import gym
from gym import error, spaces, utils
from gym.utils import seeding
import envs
import time
import io
import numpy as np
import pickle
from pathlib import Path
from tqdm import tqdm

from absl import app
from absl import flags

FLAGS = flags.FLAGS

flags.DEFINE_string('locobot_ip', None, 'IP address of LoCoBot.')
flags.DEFINE_string('locobot_user', 'locobot', 'Username for LoCoBot.')
flags.DEFINE_string('locobot_pwd', 'locobot', 'Password for LoCoBot.')
flags.DEFINE_string('monitor_ip', None, 'IP address of monitor.')
flags.DEFINE_string('monitor_user', 'root', 'Username for monitor.')
flags.DEFINE_string('monitor_pwd', 'toor', 'Password for monitor.')
flags.DEFINE_enum('chip', '43455c0', ['4358', '43455c0'], \
                  'Wifi card. Possible options are 4358 for Nexus 6P, 43455c0 for Raspberry Pi 4.')
flags.DEFINE_string('csi_params', \
                    'ZtgBEQAAAQDcpjKZ5CkAAAAAAAAAAAAAAAAAAAAAAAAAAA==',\
                    'CSI parameter string from makecsiparams.')
                    # -c 100/40 -C 1 -N 1 -m dc:a6:32:99:e4:29
                    # channel 100, bandwidth 40MHz, core 1, stream 1, pi1

flags.DEFINE_multi_float('yaw_range', [-np.pi/2,np.pi/2], 'Range of yaw values in radians.', lower_bound=-np.pi/2, upper_bound=np.pi/2)
flags.DEFINE_integer('yaw_samples', 4, 'Number of samples to take on yaw axis.', lower_bound=1)

flags.DEFINE_multi_float('joint1_range', [0,0], 'Range of joint1 values in radians.', lower_bound=0, upper_bound=0)
flags.DEFINE_integer('joint1_samples', 1, 'Number of samples to take on joint1 axis.', lower_bound=1)

flags.DEFINE_multi_float('pitch_range', [-np.pi/2,np.pi/6], 'Range of pitch values in radians.', lower_bound=-np.pi/2, upper_bound=np.pi/6)
flags.DEFINE_integer('pitch_samples', 4, 'Number of samples to take on pitch axis.', lower_bound=1)

flags.DEFINE_multi_float('joint2_range', [0,0], 'Range of joint2 values in radians.', lower_bound=0, upper_bound=0)
flags.DEFINE_integer('joint2_samples', 1, 'Number of samples to take on joint2 axis.', lower_bound=1)

flags.DEFINE_multi_float('roll_range', [-np.pi/2,np.pi/2], 'Range of roll values in radians.', lower_bound=-np.pi/2, upper_bound=np.pi/2)
flags.DEFINE_integer('roll_samples', 4, 'Number of samples to take on roll axis.', lower_bound=1)


flags.DEFINE_string('out_dir', None,'Folder to store the results')

flags.mark_flag_as_required('locobot_ip')
flags.mark_flag_as_required('monitor_ip')

def main(_):
    roboap = gym.make('RoboAP-v1')

    yaw_range = np.linspace(FLAGS.yaw_range[0], FLAGS.yaw_range[1], FLAGS.yaw_samples)
    joint1_range = np.linspace(FLAGS.joint1_range[0], FLAGS.joint1_range[1], FLAGS.joint1_samples)
    pitch_range = np.linspace(FLAGS.pitch_range[0], FLAGS.pitch_range[1], FLAGS.pitch_samples)
    joint2_range = np.linspace(FLAGS.joint2_range[0], FLAGS.joint2_range[1], FLAGS.joint2_samples)
    roll_range =  np.linspace(FLAGS.roll_range[0], FLAGS.roll_range[1], FLAGS.roll_samples)

    target_joints = [[yaw, joint1, pitch, joint2, roll] \
                     for yaw in yaw_range \
                     for joint1 in joint1_range \
                     for pitch in pitch_range \
                     for joint2 in joint2_range \
                     for roll in roll_range]

    # Move arm to home position.
    roboap.reset()

    if FLAGS.out_dir is not None:
        out_dir = Path(FLAGS.out_dir)
        out_dir.mkdir(parents=True, exist_ok=False)

        # Dump the list of target joints so we can recover this later.
        with open(f'{out_dir}/index.pkl', 'wb') as f:
            pickle.dump(target_joints, f)

    for i, joint in tqdm(enumerate(target_joints), total=len(target_joints)):
        #print(f'i={i}, target_joints={joint}')

        # Move RoboAP to joint position.
        # t = time.time()
        roboap.step_joints(joint)
        # print('Move Joint', time.time()-t)

        # Get the CSI from the monitor.
        # t = time.time()
        pcap_dump = roboap.render('pcap', 10)[1]
        # print('Sense CSI', time.time()-t)

        if FLAGS.out_dir is not None:
            # Dump the CSI at the position to a file.
            with open(f'{out_dir}/{i}.pcap', 'wb') as f:
                f.write(pcap_dump)


if __name__ == '__main__':
    app.run(main)

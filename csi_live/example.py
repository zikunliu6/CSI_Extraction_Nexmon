import gym
from gym import error, spaces, utils
from gym.utils import seeding
import envs
import time
import io
import numpy as np

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

flags.mark_flag_as_required('locobot_ip')
flags.mark_flag_as_required('monitor_ip')

def main(_):
    roboap = gym.make('RoboAP-v1')

    # Try two joint configurations.
    target_joints = [[0.408, 0.721, -0.471, -1.4, 0.920], [-0.675, 0, 0.23, 1, -0.70]]
    for i, joint in enumerate(target_joints):

        # Move RoboAP to joint position.
        roboap.step_joints(joint)

        # Dump the CSI at the position to a file.
        pcap_dump = roboap.render('pcap')
        with open('pos_' + str(i) + '.pcap', 'wb') as f:
            f.write(pcap_dump)

        # Show CSI as np array.
        csi = roboap.render('csi')
        print(csi)

        # Plot CSI.
        roboap.render('human')


if __name__ == '__main__':
    app.run(main)

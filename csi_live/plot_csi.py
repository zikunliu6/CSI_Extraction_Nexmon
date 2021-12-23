import os
import sys
import struct
import ctypes
import dpkt
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from envs.utils.csi_reader import *
from pathlib import Path
import pickle
import scipy.stats as stats

from absl import app
from absl import flags

FLAGS = flags.FLAGS
flags.DEFINE_multi_string('scan_dir', None, 'Directory where scan data is stored.')

flags.mark_flag_as_required('scan_dir')

matplotlib.rcParams.update({'font.size': 30})

def main(_):
    for dir in FLAGS.scan_dir:
        data_dir = Path(dir)
        with open(f'{data_dir}/chan_spec.pkl', 'rb') as f:
            chan_spec = pickle.load(f)
        with open(f'{data_dir}/core_mask.pkl', 'rb') as f:
            core_mask = pickle.load(f)
        with open(f'{data_dir}/stream_mask.pkl', 'rb') as f:
            stream_mask = pickle.load(f)
        with open(f'{data_dir}/clients.pkl', 'rb') as f:
            clients = pickle.load(f)

        n_subc = get_subc(chan_spec)
        cores = get_bitmask_positions(core_mask)
        streams = get_bitmask_positions(stream_mask)
        client = clients[0]

        x = subcarriers[n_subc][data_bins[n_subc]]

        fig, axes = plt.subplots(len(cores),len(streams), squeeze=False)
        fig.suptitle('CSI Variation vs Time')
        [axes[i][j].set_title(f"Core {core}, Stream {stream}") for i, core in enumerate(cores) for j, stream in enumerate(streams)]            
        [ax.set_xlabel('Frame Number') for row in axes for ax in row]
        [ax.set_ylabel('Subcarrier') for row in axes for ax in row]
        fig.show()

        numpy_files = data_dir.glob('*.npy')
        for numpy_file in numpy_files:
            csi = np.load(numpy_file)
            print(csi.shape)
            for i, core in enumerate(cores):
                for j, stream in enumerate(streams):
                    window = np.abs(csi[0,i,j].T)
                    axes[i][j].imshow(window,
                                      interpolation='bilinear',
                                      vmin=0, vmax=1.0,
                                      extent=[0,window.shape[1],min(x),max(x)])
            plt.pause(0.01)
            input()

if __name__ == '__main__':
    app.run(main)
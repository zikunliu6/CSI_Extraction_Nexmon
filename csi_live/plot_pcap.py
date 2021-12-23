import os
import sys
import struct
import ctypes
import dpkt
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from envs.utils.csi_reader import *
from envs.utils.csi_params import *
from pathlib import Path

from absl import app
from absl import flags
from tqdm import tqdm

FLAGS = flags.FLAGS

flags.DEFINE_string('pcap_file', None, '.pcap file to read packets from.')
flags.DEFINE_enum('chip', None, ['4358', '43455c0', '4366c0'], 'Wifi card. Possible options are 4358 for Nexus 6P, 43455c0 for Raspberry Pi 4, 4366c0 for ASUS RT-AC86U')
flags.DEFINE_integer('core_mask', None, 'Bitmask for cores to use.', lower_bound=0, upper_bound=15)
flags.DEFINE_integer('stream_mask', None, 'Bitmask for streams to use.', lower_bound=0, upper_bound=15)
flags.DEFINE_multi_string('clients', None, 'List of client MAC addresses.')

flags.mark_flag_as_required('pcap_file')
flags.mark_flag_as_required('chip')
flags.mark_flag_as_required('clients')
flags.mark_flag_as_required('core_mask')
flags.mark_flag_as_required('stream_mask')

matplotlib.rcParams.update({'font.size': 30})

def plot_csi_magnitude(fig, ax, subc, magnitude):
    """Plots the CSI magnitude on fig, ax

    Args:
        fig: Figure to plot on.
        ax: Axes to plot on.
        magnitude: Numpy array of magnitudes.
    """
    ax.set_title('Amplitudes')
    ax.set_xlabel('Subcarrier')
    ax.set_ylabel('Magnitude (a.u.)')
    ax.set_ylim([0,1])
    fig.suptitle('Channel State Information')

    ax.plot(subc,magnitude, '.-')

def main(_):
    cores = get_bitmask_positions(FLAGS.core_mask)
    streams = get_bitmask_positions(FLAGS.stream_mask)

    fig, axes = plt.subplots(len(cores), len(streams), sharex=True, sharey=True, squeeze=False)

    with open(FLAGS.pcap_file, 'rb') as pcap:
        pcap = pcap.read()
        csi = pcap_to_csi(pcap, FLAGS.chip, FLAGS.clients, cores, streams)[0]
        print(csi.shape)

        for t in range(csi.shape[2]):
            for c in range(csi.shape[0]):
                for s in range(csi.shape[1]):
                    axes[c,s].clear()
                    subc = subcarriers[csi.shape[3]][data_bins[csi.shape[3]]]
                    magnitude = np.abs(csi[c,s,t,:])[data_bins[csi.shape[3]]]
                    plot_csi_magnitude(fig, axes[c,s], subc, magnitude)

            plt.pause(0.001)
            input()

if __name__ == '__main__':
    app.run(main)

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
flags.DEFINE_enum('chip', None, ['4358', '43455c0', '4366c0'], 'Wifi card. Possible options are 4358 for Nexus 6P, 43455c0 for Raspberry Pi 4.')
flags.DEFINE_enum('format', None, ['numpy', 'pcap'], 'Format of CSI files.')

flags.mark_flag_as_required('scan_dir')
flags.mark_flag_as_required('chip')
flags.mark_flag_as_required('format')

matplotlib.rcParams.update({'font.size': 30})

def plot_histogram(fig, ax, data, name):
    ax.set_xlabel('Quality')
    ax.set_ylabel('Density')
    ax.set_title('Channel Quality')
    #n, x, _ = ax.hist(data, bins=100, range=(0,1.5*np.max(data)),
    #                  histtype=u'step', density=True)
    hist, x = np.histogram(data, bins=100, range=(0,1.5*np.max(data)), density=True)
    density = stats.gaussian_kde(data)
    ax.plot(x, density(x), label=name)
    ax.legend()
    fig.show()

def main(_):
    #csi_fig, csi_ax = plt.subplots(2,1)
    #csi_fig, csi_ax = plt.subplots(1,1)
    hist_fig, hist_ax = plt.subplots(1,1)

    if FLAGS.format == 'pcap':
        for data_dir in FLAGS.scan_dir:
            pcap_files = Path(data_dir).glob('*.pcap')

            data = []
            for pcap_file in pcap_files:
                with open(pcap_file, 'rb') as pcap:
                    pcap = pcap.read()
                    csi = pcap_to_csi(pcap,FLAGS.chip)

                    data.append(get_quality(csi))

            plot_histogram(hist_fig, hist_ax, data, data_dir)
            print(f"mean {data_dir}: {np.mean(data)}")
            print(f"stdev: {data_dir}: {np.std(data)}")

    else:
        for data_dir in FLAGS.scan_dir:
            numpy_files = Path(data_dir).glob('*.npy')

            data = []
            for numpy_file in numpy_files:
                csi = np.load(numpy_file)
                #data.append(get_quality(csi))
                data.append(get_quality_min(csi))

            plot_histogram(hist_fig, hist_ax, data, data_dir)
            print(f"mean {data_dir}: {np.mean(data)}")
            print(f"stdev: {data_dir}: {np.std(data)}")

    input()

if __name__ == '__main__':
    app.run(main)

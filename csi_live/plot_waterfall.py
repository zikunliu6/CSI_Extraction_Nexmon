import os
import sys
import io
import struct
import ctypes
import dpkt
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import paramiko
from envs.utils.csi_reader import *
from pathlib import Path
import time
from collections import deque
from multiprocessing import Process, Queue

from absl import app
from absl import flags

FLAGS = flags.FLAGS

flags.DEFINE_string('monitor_ip', None, 'IP address of monitor to read packets from.')
flags.DEFINE_string('monitor_user', None, 'Username for monitor.')
flags.DEFINE_string('monitor_pwd', None, 'Password for monitor.')
flags.DEFINE_enum('chip', None, ['4358', '43455c0', '4366c0'], 'Wifi card. Possible options are 4358 for Nexus 6P, 43455c0 for Raspberry Pi 4, 4366c0 for ASUS RT-AC86U')
flags.DEFINE_string('chan_spec', None, 'Channel specification.')
flags.DEFINE_integer('core_mask', None, 'Bitmask for cores to use.', lower_bound=0, upper_bound=15)
flags.DEFINE_integer('stream_mask', None, 'Bitmask for streams to use.', lower_bound=0, upper_bound=15)
flags.DEFINE_multi_string('clients', None, 'List of client MAC addresses.')

flags.DEFINE_integer('n_window', 1000, 'Number of frames to plot at a time.', lower_bound=1)
flags.DEFINE_integer('plot_interval', 100, 'Update plot after this number of frames.', lower_bound=1)
flags.DEFINE_integer('queue_size', 1000, 'Max number of frames to buffer', lower_bound=1)

flags.mark_flag_as_required('monitor_ip')
flags.mark_flag_as_required('monitor_user')
flags.mark_flag_as_required('monitor_pwd')
flags.mark_flag_as_required('chip')
flags.mark_flag_as_required('chan_spec')
flags.mark_flag_as_required('core_mask')
flags.mark_flag_as_required('stream_mask')
flags.mark_flag_as_required('clients')

matplotlib.rcParams.update({'font.size': 15})

def plot_csi_heatmap(queue):
    """Plots the CSI data bins matrix heatmap on fig, ax

    Args:
        queue: Where to render CSI from.
    """
    # Unpack flags.
    cores = get_bitmask_positions(FLAGS.core_mask)
    streams = get_bitmask_positions(FLAGS.stream_mask)
    n_subc = get_subc(FLAGS.chan_spec)

    # Display figure.
    fig, axes = plt.subplots(len(cores),len(streams), squeeze=False)
    fig.suptitle('CSI Variation vs Time')
    [axes[i][j].set_title(f"Core {core}, Stream {stream}") for i, core in enumerate(cores) for j, stream in enumerate(streams)]            
    [ax.set_xlabel('Frame Number') for row in axes for ax in row]
    [ax.set_ylabel('Subcarrier') for row in axes for ax in row]
    fig.show()
    plt.pause(0.1)

    # Initialize CSI window.
    x = subcarriers[n_subc][data_bins[n_subc]]
    csi_windows = [[deque(maxlen=FLAGS.n_window) for ax in row] for row in axes]
    for i,_ in enumerate(cores):
        for j,_ in enumerate(streams):
            for _ in range(FLAGS.n_window):
                csi_windows[i][j].append(np.zeros(len(x)))
    counter = 0

    while True:
        # Get new CSI frueue.
        new_csi = queue.get()
        print('queue pop: ', queue.qsize())

        # Check if CSI matches client.
        if new_csi["src_mac"] != FLAGS.clients[0]:
            return

        core_idx = cores.index(new_csi["core"])
        stream_idx = streams.index(new_csi["stream"])
        n_fft = len(new_csi["data"])

        # Append new CSI to appropriate window.
        y = np.abs(new_csi["data"][data_bins[n_fft]])
        csi_windows[core_idx][stream_idx].append(y)

        # Refresh plot every plot_interval steps.
        if counter % FLAGS.plot_interval == 0:
            counter = 0
            for i, _ in enumerate(cores):
                for j, _ in enumerate(streams):
                    window = np.vstack(csi_windows[i][j]).T
                    axes[i][j].imshow(window, 
                                    interpolation='bilinear', 
                                    vmin=0, vmax=1.0,
                                    extent=[0,window.shape[1],min(x),max(x)])
            # fig.canvas.draw()
            fig.show()
            plt.pause(0.01)

        counter = counter+1

def listen_csi(queue):
    csi_monitor = CSIMonitor(FLAGS.monitor_ip, FLAGS.monitor_user, FLAGS.monitor_pwd, FLAGS.chip,
                             FLAGS.chan_spec, FLAGS.core_mask, FLAGS.stream_mask, FLAGS.clients)
    csi_monitor.monitor_csi(queue)

def main(_):
    try:
        queue = Queue(FLAGS.queue_size)

        monitor = Process(target=listen_csi, 
                          args=(queue,))
        monitor.start()

        plot_csi_heatmap(queue)
    finally:
        monitor.join()

if __name__ == '__main__':
    app.run(main)

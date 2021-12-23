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

def main(_):
    with open(FLAGS.pcap_file, 'rb') as pcap:
        pcap_bytes = pcap.read()
        pcap_stream = io.BytesIO(pcap_bytes)
        packets = dpkt.pcap.Reader(pcap_stream)
        for ts, pkt in packets:
            eth = dpkt.ethernet.Ethernet(pkt)
            ip = eth.data
            udp = ip.data
            payload = udp.data

            unpacked_csi = unpack_csi(payload,FLAGS.chip)

            print(f'timestamp: {ts}')
            print(f'src_mac: {unpacked_csi["src_mac"]}')
            print(f'seq_num: {unpacked_csi["seq_num"]}')
            print(f'core: {unpacked_csi["core"]}')
            print(f'stream: {unpacked_csi["stream"]}')
            print(f'chip_ver: {unpacked_csi["chip_ver"]}')
            print(f'data: {unpacked_csi["data"]}')
            print(f'rssi: {unpacked_csi["rssi"]}')
            input()

        cores = get_bitmask_positions(FLAGS.core_mask)
        streams = get_bitmask_positions(FLAGS.stream_mask)
        csi = pcap_to_csi(pcap_bytes, FLAGS.chip, FLAGS.clients, cores, streams)

        for client_csi in csi:
            print(client_csi.shape)

if __name__ == '__main__':
    app.run(main)

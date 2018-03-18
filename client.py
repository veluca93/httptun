#!/usr/bin/env python3
from __future__ import print_function

from io import BytesIO
import sys
import os
import threading
import traceback
from queue import Queue
import requests
from pytun import TunTapDevice, IFF_TAP
from common import get_mac, BROADCAST, dequeue, parse_packets, serialize_packets

server_queue = Queue()


def read_data():
    try:
        while True:
            wdata = tap.read(2 * tap.mtu)
            server_queue.put(wdata)
    except:
        traceback.print_exc()
        os._exit(1)


def send_data():
    try:
        session = requests.Session()
        while True:
            wdata = dequeue(server_queue)
            wans = session.post(server + '/send',
                                my_mac + serialize_packets(wdata))
            if wans.status_code != 200:
                print("send: received status code " + str(wans.status_code) +
                      ": " + wans.text)
    except:
        traceback.print_exc()
        os._exit(1)


def main():
    global tap, my_mac, my_ip, server
    server = sys.argv[1]
    while server.endswith('/'):
        server = server[:-1]

    session = requests.Session()
    ans = session.post(server + '/connect', 'very_secret').content
    my_mac = ans[:6]
    my_ip = ans[6:10]
    tap = TunTapDevice(flags=IFF_TAP)
    tap.addr = ".".join(map(str, my_ip))
    print("My ip is:", tap.addr)
    tap.netmask = '255.255.0.0'
    tap.mtu = 1300
    tap.hwaddr = my_mac
    tap.up()
    tap_reader = threading.Thread(target=read_data, daemon=True)
    tap_reader.start()
    sender = threading.Thread(target=send_data, daemon=True)
    sender.start()

    while True:
        ans = session.post(server + '/recv', my_mac)
        if ans.status_code == 204:
            continue
        if ans.status_code != 200:
            print("recv: received status code " + str(ans.status_code) + ": " +
                  ans.text)
            sys.exit(1)

        def process_packet(data):
            packet_mac = get_mac(data)
            if packet_mac == my_mac or packet_mac == BROADCAST:
                tap.write(data)

        parse_packets(BytesIO(ans.content), process_packet)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
import sys
import threading
from queue import Queue
import requests
from pytun import TunTapDevice, IFF_TAP

IP_PREFIX = (10, 9)
BROADCAST = b'\xff\xff\xff\xff\xff\xff'

server_queue = Queue()


def read_data():
    while True:
        wdata = tap.read(2 * tap.mtu)
        server_queue.put(wdata)


def send_data():
    session = requests.Session()
    while True:
        wdata = server_queue.get()
        wans = session.post(server + '/send', my_mac + wdata)
        if wans.status_code != 200:
            print("send: received status code " + str(wans.status_code) +
                  ": " + wans.text)


if __name__ == '__main__':
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
        data = ans.content
        if data[4:10] == my_mac or data[4:10] == BROADCAST:
            tap.write(data)

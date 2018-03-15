#!/usr/bin/env python3
import logging
import os
import threading
import traceback
from queue import Queue, Empty
from wsgiserver import WSGIServer
from pytun import TunTapDevice, IFF_TAP

logger = logging.getLogger('httptun')
logger.setLevel(logging.INFO)

MYMAC = b'ter000'
IP_PREFIX = (10, 9)
BROADCAST = b'\xff\xff\xff\xff\xff\xff'

queue = dict()


def init_queue(dest_mac):
    queue[dest_mac] = Queue()


def put_in_queue(dest_mac, data):
    if dest_mac == BROADCAST:
        for k in queue:
            queue[k].put(data)
        return True
    if not dest_mac in queue:
        return False
    queue[dest_mac].put(data)
    return True


def get_from_queue(dest_mac):
    try:
        return queue[dest_mac].get(timeout=2)
    except Empty:
        return None


def read_data():
    while True:
        data = tap.read(2 * tap.mtu)
        # Bytes 0-1 are "flags", bytes 2-3 are a copy of the protocol.
        # From byte 4 on is the real ethernet frame.
        #data = data[4:]
        dest_mac = data[4:10]
        put_in_queue(dest_mac, data)


def application(env, start_response):
    logger.info(env['PATH_INFO'])
    try:
        if env['PATH_INFO'] == '/connect':
            if env['wsgi.input'].read() != b'very_secret':
                start_response('403 Forbidden', [])
                return [b""]
            while True:
                new_mac = b'terc' + os.urandom(2)
                if new_mac not in queue:
                    break
            ip = bytes(bytearray(IP_PREFIX)) + new_mac[4:6]
            init_queue(new_mac)
            start_response('200 OK', [])
            return [new_mac, ip]

        if env['PATH_INFO'] == '/send':
            client_mac = env['wsgi.input'].read(6)
            if client_mac not in queue:
                start_response('403 Forbidden', [])
                return [b""]
            data = env['wsgi.input'].read()
            dest_mac = data[4:10]
            if dest_mac == MYMAC or dest_mac == BROADCAST:
                tap.write(data)
            if dest_mac == MYMAC:
                start_response('200 OK', [])
                return []
            if not put_in_queue(dest_mac, data):
                start_response('404 Not Found', [])
                return [b'No such MAC address']
            start_response('200 OK', [])
            return []

        if env['PATH_INFO'] == '/recv':
            client_mac = env['wsgi.input'].read(6)
            if client_mac not in queue:
                start_response('403 Forbidden', [])
                return [b""]
            data = get_from_queue(client_mac)
            if data is None:
                start_response('204 No content', [])
                return [b'']
            start_response('200 OK', [])
            return [data]

        start_response('404 Not Found', [('Content-Type', 'text/html')])
        return [b'<h1>Not Found</h1>']
    except:
        traceback.print_exc()
        start_response('500', [])
        return [b'Internal server error']


if __name__ == '__main__':
    global tap
    tap = TunTapDevice(flags=IFF_TAP)
    tap.addr = ".".join(map(str, IP_PREFIX + (0, 1)))
    tap.netmask = '255.255.0.0'
    tap.mtu = 1300
    tap.hwaddr = MYMAC
    tap.up()
    tap_reader = threading.Thread(target=read_data, daemon=True)
    tap_reader.start()
    print('Serving on 8088...')
    WSGIServer(application, port=8088).start()

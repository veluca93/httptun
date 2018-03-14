#!/usr/bin/env python3
import os
import threading
from collections import deque
import traceback
from gevent.pywsgi import WSGIServer
from pytun import TunTapDevice, IFF_TAP

MYMAC = b'ter000'
IP_PREFIX = (10, 9)
BROADCAST = b'\xff\xff\xff\xff\xff\xff'

lck = threading.Lock()
queue = dict()


def read_data():
    while True:
        data = tap.read()
        # Bytes 0-1 are "flags", bytes 2-3 are a copy of the protocol.
        # From byte 4 on is the real ethernet frame.
        #data = data[4:]
        dest_mac = data[4:10]
        if dest_mac == BROADCAST:
            with lck:
                for k in queue:
                    queue[k].append(data)
        else:
            with lck:
                if dest_mac in queue:
                    queue[dest_mac].append(data)


def application(env, start_response):
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
            with lck:
                queue[new_mac] = deque()
            start_response('200 OK', [])
            return [new_mac, ip]

        if env['PATH_INFO'] == '/send':
            client_mac = env['wsgi.input'].read(6)
            if client_mac not in queue:
                start_response('403 Forbidden', [])
                return [b""]
            data = env['wsgi.input'].read()
            dest_mac = data[4:10]
            if dest_mac == MYMAC:
                tap.write(data)
                start_response('200 OK', [])
                return []
            if dest_mac == BROADCAST:
                tap.write(data)
                with lck:
                    for k in queue:
                        if k != client_mac:
                            queue[k].append(data)
                start_response('200 OK', [])
                return []
            if dest_mac not in queue:
                start_response('404 Not Found', [])
                return [b'No such MAC address']
            with lck:
                queue[dest_mac].append(data)
            start_response('200 OK', [])
            return []

        if env['PATH_INFO'] == '/recv':
            client_mac = env['wsgi.input'].read(6)
            if client_mac not in queue:
                start_response('403 Forbidden', [])
                return [b""]
            with lck:
                # TODO: wait for a packet?
                if not queue[client_mac]:
                    start_response('204 No content', [])
                    return [b'']
                data = queue[client_mac].popleft()
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
    WSGIServer(('', 8088), application).serve_forever()

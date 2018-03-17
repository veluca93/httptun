from queue import Empty
import struct

BROADCAST = b'\xff\xff\xff\xff\xff\xff'
HDR_FORMAT = '!i'


def get_mac(data):
    # Bytes 0-1 are "flags", bytes 2-3 are a copy of the protocol.
    # From byte 4 on is the real ethernet frame, which starts with
    # the destination MAC of the frame.
    return data[4:10]


def dequeue(queue, timeout=None):
    result = [queue.get(timeout=timeout)]
    try:
        while True:
            result.append(queue.get(False))
    except Empty:
        return result


def parse_packets(stream, callback):
    while True:
        hdr = stream.read(struct.calcsize(HDR_FORMAT))
        if not hdr:
            return
        data = stream.read(struct.unpack(HDR_FORMAT, hdr)[0])
        callback(data)


def serialize_packets(packets):
    return b"".join(
        struct.pack(HDR_FORMAT, len(packet)) + packet for packet in packets)

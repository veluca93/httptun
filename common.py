BROADCAST = b'\xff\xff\xff\xff\xff\xff'


def get_mac(data):
    # Bytes 0-1 are "flags", bytes 2-3 are a copy of the protocol.
    # From byte 4 on is the real ethernet frame, which starts with
    # the destination MAC of the frame.
    return data[4:10]


def dequeue(queue, timeout=None):
    return [queue.get(timeout=timeout)]


def parse_packets(stream, callback):
    callback(stream.read())


def serialize_packets(packets):
    return packets[0]

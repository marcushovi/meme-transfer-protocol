import selectors
import socket
import sys
import types

import pynetstring

sel = selectors.DefaultSelector()

decoder = pynetstring.Decoder()

messages_first_phase = [b"C MTP V:1.0", "C marcus"]
messages_first_phase = pynetstring.encode(messages_first_phase)

messages_second_phase = ["C marcus"]
messages_second_phase = pynetstring.encode(messages_second_phase)

messages_third_phase = [b"C marcus"]
messages_third_phase = pynetstring.encode(messages_third_phase)

received_data = []


def start_connections(host, port, num_conns, messages):
    server_addr = (host, port)
    print("starting connection", "to", server_addr)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(server_addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    data = types.SimpleNamespace(
        msg_total=sum(len(m) for m in messages),
        recv_total=0,
        messages=list(messages),
        outb=b'',
    )
    sel.register(sock, events, data=data)


def service_connection(key, mask):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Should be ready to read
        if recv_data:

            recv_data = decoder.feed(recv_data)

            for i in range(len(recv_data)):
                recv_data[i] = recv_data[i].decode("utf-8").replace("S ", "")
                # received_data.append(recv_data[i])

            print("received", recv_data, "from connection")
            data.recv_total += len(recv_data)
        if not recv_data or data.recv_total == data.msg_total:
            print("closing connection", data.connid)
            sel.unregister(sock)
            sock.close()
        else:
            print(received_data)
            if len(received_data) == 3:
                print(received_data[2])
                start_connections(host, int(received_data[2][0]), int(num_conns), messages_second_phase)

    if mask & selectors.EVENT_WRITE:
        if not data.outb and data.messages:
            data.outb = data.messages.pop(0)
        if data.outb:
            print("sending", repr(data.outb), "to connection")
            sent = sock.send(data.outb)  # Should be ready to write
            data.outb = data.outb[sent:]


if len(sys.argv) != 4:
    print("usage:", sys.argv[0], "<host> <port> <num_connections>")
    sys.exit(1)

host, port, num_conns = sys.argv[1:4]
start_connections(host, int(port), int(num_conns), messages_first_phase)

print("S")
# start_connections(host, received_data[1][1].replace("S ", ""), int(num_conns))

try:
    while True:
        events = sel.select(timeout=1)
        if events:
            for key, mask in events:
                service_connection(key, mask)
        # Check for a socket being monitored to continue.
        if not sel.get_map():
            break
except KeyboardInterrupt:
    print("caught keyboard interrupt, exiting")
finally:
    sel.close()

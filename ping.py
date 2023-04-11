from packets import *
import socket

def ping(port, packet):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Initialise UDP socket
    sock.settimeout(1)
    address, port = socket.getaddrinfo("127.0.0.1", port)[0][4]
    sock.connect((address, port)) # attempt to connect to server
    sock.sendall(packet) # send dt_request

ping(61110, generate_packet(2, 2, 1, [generate_entry(2, 1, 3), generate_entry(6, 3, 0), generate_entry(3, 5, 2), generate_entry(1, 2, 5)]))
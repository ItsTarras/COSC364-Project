import socket
import sys
from math import inf
from packets import *
from random import randint


class Router:
    
    def __init__(self, router_id, input_ports, outputs):
        forwarding_table = dict()
        for ports in outputs:
            forwarding_table[ports[1]] = ((ports[0], ports[2]))
       
        self.router_id = router_id
        self.input_ports = input_ports
        self.forwarding_table = forwarding_table
        self.outputs = outputs
        self.sockets = []
    
    def __str__(self):
        return(f"router-id = {self.router_id} \ninput-ports = {self.input_ports} \noutput-ports = {self.forwarding_table}")
    
    def open(self):
        """ Open sockets at each input_port"""
        for port in self.input_ports:
            server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Initialise UDP socket
            server.setblocking(0)
            try:
                server.bind(('', port))
            except OSError:
                raise Exception(f'Port {port} in use.')
            self.sockets.append(server)
    
    def close(self):
        """ Close all sockets"""
        for server in self.sockets:
            server.close()
    
    def route(self, input_port, output_port):
        """Reads from the forwarding table, and routes the message to the output port"""
        pass
    
    def ping(self, input_ports, outputs):
        """Use a timer to ping all ports periodically"""
        pass
    
    def check_distance_vectors(self, data):
        """ Compare incoming packet to existing forwarding tables"""
        pass
    
    def run(self):
        """ Server Loop"""
        while True:
            in_packets, _out_packets, _exceptions = select.select(servers, [], servers)
            for server in in_packets:
                for s in self.sockets:
                    if server is s: # Received packet
                        data, client_addr = server.recvfrom(BUF_SIZE)
                        # Check if data is a valid packet and do stuff
    
def main():
    filename = 'config.txt'
    try:
        router = Router(*check_config(parse_config(filename)))
        print(router)
        router.open()
        try:
            router.run()
        except KeyboardInterrupt:
            router.close()
            print("Keyboard Interrupt: Stopping Server")
    except Exception as e:
        print(f"Error: {e}")
        exit() 

if __name__ == "__main__":
    main()

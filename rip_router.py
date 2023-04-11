import socket
import select
import sys
from os import path
from math import inf
from packets import *
import random


class Router:
    
    def __init__(self, router_id, input_ports, outputs, timeout_default, timeout_delta):
        self.forwarding_table = dict()
        for i in outputs:
            self.forwarding_table[i.router_id] = i
       
        self.router_id = router_id
        self.input_ports = input_ports
        self.outputs = outputs
        self.timeout_default = timeout_default
        self.timeout_delta = timeout_delta
        
        self.sockets = []
    
    def __repr__(self):
        return(f"Router({self.router_id})")
    
    def pretty_print(self):
        print(f"Router Id: {self.router_id}")
        print(f"Listening for updates on {len(self.input_ports)} port(s)")
        print(f"Timeout: {self.timeout_default} seconds, +- {self.timeout_delta}")
        
        print("Neighboured router(s): (id, metric)")
        print(f"{', '.join([f'({i.router_id}, {i.metric})' for i in self.outputs])}")
        
    
    def random_timeout(self):
        """ Generate a uniformly distributed random timeout value"""
        return self.timeout_default + random.randint(-self.timeout_delta, self.timeout_delta)
    
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
    
    def send_table(self, destination_id):
        """ send contents of the routing table to another router with poisoned reverse"""
        if destination_id not in self.forwarding_table.keys():
            raise Exception("Unknown router ID")
        table_entries = []
        for key in self.forwarding_table.keys():
            data = self.forwarding_table[key]
            if data.id == self.id:
                metric = 16
            else:
                metric = data.metric
            table_entries.append(generate_entry(2, key, metric))
        packet = generate_packet(2, 2, self.id, table_entries)
        
        try:
            address, port = socket.getaddrinfo("127.0.0.1", self.forwarding_table[destination_id].port)[0][4] # verify ip and port
        except:
            raise Exception("Invalid port.")
        # Send Packet
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Initialise UDP socket
        sock.settimeout(1)
        try:
            sock.connect((address, port)) # attempt to connect to server
            sock.sendall(packet) # send packet
        except ConnectionRefusedError:
            raise Exception('Unable to connect to server - connection refused.')        
        sock.close()        
    
    def route(self, packet, destination):
        """Reads from the forwarding table, and routes the message to the output port"""
        
        try:
            port.sendto(packet, (destination[0], destination[1]))
            print('Sent packet to: ', destination[0], '\n')
        except:
            print("Error in sending request to client")
            
        
    def ping(self, input_ports, outputs):
        """Use a timer to ping all ports periodically"""
        pass
    
    def check_distance_vectors(self, data):
        """ Compare incoming packet to existing forwarding tables"""
        pass
    
    
    def update_forwarding_table(self, data):
        #We need to check if the route was updated, and if so, send out a response.
        debug_updated = False
        
        #Breaking down and decoding the packet - Tarras Weir 10/03/2023
        command, version, sender_id, entries = decode_packet(data)
        
        #Updated loop - Tarras Weir 14/03/2023
        for entry in entries:
            destination_id, metric = entry[1], entry[2]
        
            #Checking if the destination ID is already within the forwarding table:
            if destination_id in self.forwarding_table.keys():
                #Now, check if the sender is the next hop for the destination.
                if self.forwarding_table[destination_id][0] == sender_id:
                    #Compare the existing metrics
                    if metric + self.forwarding_table[sender_id][1] < self.forwarding_table[destination_id][1]:
                        self.forwarding_table[destination_id] = (
                            sender_id,
                            metric + self.forwarding_table[sender_id][1]
                        )
                        debug_updated = True
            
            else:
                #If it doesn't exist, put destination_id into the forwarding table.
                self.forwarding_table[destination_id] = (sender_id, metric + self.forwarding_table[sender_id][1])
                debug_updated = True
            
            #Print a debug messgae if there was a successful update.
            if debug_updated is True:
                print(f"Forwarding table was updated by {sender_id}")
            else:
                print(f"{self.forwarding_table[destination_id][0]} is not next hop - forwarding table unchanged")

    def run(self):
        """ Server Loop"""
        while True:
            in_packets, _out_packets, _exceptions = select.select(self.sockets, [], self.sockets, self.random_timeout())
            if in_packets == []: # Timeout, send packet to each neighbour (poisoned reverse)
                for neighbour in self.outputs:
                    entries_to_send = []
                    for destination, (next_hop, metric) in self.forwarding_table.items():
                        if next_hop == destination:
                            metric = 15
                        entries_to_send.append(generate_entry(2, destination, metric))
                        generate_packet(2, 2, self.router_id, entries_to_send)
                        address, port = socket.getaddrinfo("127.0.0.1", port)[0][4]
            else:
                for server in in_packets:
                    for s in self.sockets:
                        if server is s: # Received packet
                            data, client_addr = server.recvfrom(BUF_SIZE)
                            # Check if data is a valid packet and do stuff
                            
                            #Updates the forwarding table (hopefully)
                            self.update_forwarding_table(data)

                            #Checks what port we are receiving from, for debugging.
                            received_from_port = s.getsockname()[1]
                        
                            
                        else:
                            print("Server and Sockets not similar!")

def main():
    if len(sys.argv) == 1:
        filename = 'config_1.txt'
        print("DEBUG: Remove this condition before submission")
    elif len(sys.argv) == 2:
        filename = sys.argv[1]
    else:
        print(f"Error: Too many arguments. usage: python3 {path.basename(__file__)} <filename>")
    try:
        router = Router(*check_config(parse_config(filename)))
    except Exception as e:
        print(f"Error: {e}")
        exit()
    try:
        router.pretty_print()
        router.open()
        try:
            router.run()
        except KeyboardInterrupt:
            router.close()
            print("Keyboard Interrupt: Stopping Server")
    except Exception as e:
        print(f"Error: {e}")
        router.close()
        exit() 

if __name__ == "__main__":
    main()

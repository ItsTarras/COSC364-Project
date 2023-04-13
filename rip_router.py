import socket
import select
import sys
from os import path
from math import inf
from packets import *
import random
from time import time


class Router:
    def __init__(self, router_id, input_ports, outputs, timeout_default, timeout_delta):
        self.forwarding_table = dict()
        #for i in outputs:
        #    self.forwarding_table[i.router_id] = i
       
        self.router_id = router_id
        self.input_ports = input_ports
        self.outputs = outputs
        self.timeout_default = timeout_default
        self.timeout_delta = timeout_delta
        self.max_downtime = 3 * timeout_default
        
        self.last_packet = {out.router_id: None for out in self.outputs}
        
        self.sockets = []
    
    
    def __repr__(self):
        return(f"Router({self.router_id})")
    
    
    def pretty_print(self):
        print(f"Router Id: {self.router_id}")
        print(f"Listening for updates on {len(self.input_ports)} port(s)")
        print(f"Timeout: {self.timeout_default} seconds, +- {self.timeout_delta}")
        
        print("Neighboured router(s): (id, metric)")
        print(f"{', '.join([f'({i.router_id}, {i.metric})' for i in self.outputs])}")
        
        
    def get_neighbour_cost(self, neighbour_id):
        """Look through list of directly attached neighbours and find the cost of a given neighbour"""
        for neighbour in self.outputs:
            if neighbour.router_id == neighbour_id:
                return neighbour.metric
        raise Exception("Recieved packet from unconfigured router")
    
    
    def random_timeout(self):
        """ Generate a uniformly distributed random timeout value"""
        return self.timeout_default + round(random.uniform(-self.timeout_delta, self.timeout_delta), 2)
    
    
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
    
    
    def router_down(self, neighbour):
        """Mark a router in the forwarding table as 'down'"""
        print(f"Missing packets from router {neighbour}. Considering this router down.")
        for destination_id in self.forwarding_table:
            if self.forwarding_table[destination_id].router_id == neighbour: # next hop is the dead router
                self.forwarding_table[destination_id] = RoutingEntry(
                    self.forwarding_table[destination_id].router_id,
                    self.forwarding_table[destination_id].port,
                    INF_METRIC
                )
        
    
    def update_forwarding_table(self, sender_id, entries, port):
        """Update forwarding table using an incoming packet"""
        cost_to_sender = self.get_neighbour_cost(sender_id)
        
        for entry in entries:
            _, destination_id, metric = entry
            if destination_id != self.router_id:
                if destination_id not in self.forwarding_table or cost_to_sender + metric < self.forwarding_table[destination_id].metric:
                    self.forwarding_table[destination_id] = RoutingEntry(sender_id, port, cost_to_sender + min(metric, INF_METRIC))


    def send_forwarding_table(self):
        for neighbour in self.outputs:
            entries_to_send = [generate_entry(2, self.router_id, 0)]
            for destination, (next_hop, _, metric) in self.forwarding_table.items():
                if next_hop == neighbour.port:
                    metric = 15
                entries_to_send.append(generate_entry(2, destination, metric))
            
            rip_packet = generate_packet(2, 2, self.router_id, entries_to_send)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Initialise UDP socket
            sock.settimeout(1)
            sock.connect(("127.0.0.1", neighbour.port)) # attempt to connect to server
            sock.sendall(rip_packet) # send dt_request        


    def run(self):
        """ Server Loop"""
        while True:
            print(self.forwarding_table.items())
            in_packets, _out_packets, _exceptions = select.select(self.sockets, [], self.sockets, self.random_timeout())
            if in_packets == []: # Timeout, send packet to each neighbour (poisoned reverse)
                
                for neighbour in self.outputs:
                    if self.last_packet[neighbour.router_id] is not None and self.last_packet[neighbour.router_id] + self.max_downtime < time():
                        self.router_down(neighbour.router_id)
                
                self.send_forwarding_table()
            else:
                for server in in_packets:
                    for s in self.sockets:
                        if server is s: # Received packet
                            data, client_addr = server.recvfrom(BUF_SIZE)
                            # Check if data is a valid packet and do stuff
                            
                            #Checks what port we are receiving from, for debugging.
                            received_from_port = s.getsockname()[1]                            
                            
                            _, _, sender_id, entries = decode_packet(data)
                            #Updates the forwarding table
                            self.update_forwarding_table(sender_id, entries, received_from_port)
                            
                            #Update the time since this router was last heard from
                            self.last_packet[sender_id] = time()


def main():
    if len(sys.argv) == 1:
        filename = 'config.txt'
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
        print(f"Error: {type(e).__name__}, {e}")
        router.close()
        exit() 

if __name__ == "__main__":
    main()

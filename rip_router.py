import socket
import select
import sys
from os import path
from math import inf
from packets import *
import random
from time import time


class Router:
    def __init__(self, router_id, input_ports, outputs, timers):
        self.forwarding_table = dict()
        #for i in outputs:
        #    self.forwarding_table[i.router_id] = i
       
        self.router_id = router_id
        self.input_ports = input_ports
        self.outputs = outputs
        self.timeout_default = timers[0]
        self.timeout_delta = timers[1]
        self.max_downtime = timers[2]
        self.garbage_time = timers[3]
        self.sockets = []
        
        self.reset_timer()
    
    
    def __repr__(self):
        return(f"Router({self.router_id})")

    
    def pretty_print(self):
        print(f"Router Id: {self.router_id}")
        print(f"Listening for updates on {len(self.input_ports)} port(s)")
        print(f"Ping time: {self.timeout_default} seconds, +- {self.timeout_delta}")
        print(f"    Route Timeout: {self.max_downtime}, Garbage Timeout: {self.garbage_time}")
        print("Neighboured router(s): (id, metric)")
        print(f"    {', '.join([f'({i.router_id}, {i.metric})' for i in self.outputs])}")
        
        
    def get_neighbour_cost(self, neighbour_id):
        """ Look through list of directly attached neighbours and find the cost of a given neighbour"""
        for neighbour in self.outputs:
            if neighbour.router_id == neighbour_id:
                return neighbour.metric
        raise Exception("Recieved packet from unconfigured router")
    
    
    def get_update_time(self):
        """ Get the time in seconds until the router needs to update all neighbours"""
        return self.last_update - time() + self.current_timeout

    
    def reset_timer(self):
        """ Reset update timer with a uniformly distributed random timeout value"""
        self.current_timeout = self.timeout_default + round(random.uniform(-self.timeout_delta, self.timeout_delta), 2)
        self.last_update = time()
    
    
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
    
    
    def print_forwarding_table(self):
        if not self.forwarding_table:
            print("Forwarding Table is empty")
        else:
            print("Forwarding Table:")
            print("    destination, next_hop, metric, time-last-updated")
            for destination_id, entry in self.forwarding_table.items():
                print(f"    {destination_id:<11}  {entry.router_id:<8}  {entry.metric:<6}  {entry.timeout:.2f}")
                
                
    def check_router_down(self):
        """forwarding table to see if any routers should be marked as down"""
        has_updated = False
        routes_to_remove = []
        for destination_id, entry in self.forwarding_table.items():
            if entry.timeout + self.garbage_time < time(): # Remove entry from table entirely
                routes_to_remove.append(destination_id)
                print(f"{destination_id} is to be removed from the table")
                has_updated = True
            elif entry.timeout + self.max_downtime < time(): # Mark destination as unreachable
                self.forwarding_table[destination_id].metric = INF_METRIC
                has_updated = True
                print(f"{destination_id} is unreachable")
        
        for route in routes_to_remove:
            self.forwarding_table.pop(route)            
        
        if has_updated:
            self.print_forwarding_table()
    
    
    def update_forwarding_table(self, sender_id, entries):
        """Update forwarding table using an incoming packet"""
        cost_to_sender = self.get_neighbour_cost(sender_id)
        has_updated = False
        for entry in entries:
            _, destination_id, metric = entry
            if destination_id != self.router_id:
                if destination_id not in self.forwarding_table or cost_to_sender + metric < self.forwarding_table[destination_id].metric:
                    has_updated = True
                    self.forwarding_table[destination_id] = RoutingEntry(sender_id, None, min(cost_to_sender + metric, INF_METRIC), time())
                elif cost_to_sender + metric == self.forwarding_table[destination_id].metric:
                    self.forwarding_table[destination_id].timeout = time()
        if has_updated:
            self.print_forwarding_table()


    def send_forwarding_table(self):
        for neighbour in self.outputs:
            entries_to_send = [generate_entry(2, self.router_id, 0)]
            for destination, table_entry in self.forwarding_table.items():
                if table_entry.router_id == neighbour.router_id: # poisoned reverse
                    metric = INF_METRIC
                else:
                    metric = table_entry.metric
                if table_entry.timeout + self.max_downtime >= time(): # don't send information about timed out routes
                    entries_to_send.append(generate_entry(2, destination, metric))
            
            rip_packet = generate_packet(2, 2, self.router_id, entries_to_send)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Initialise UDP socket
            sock.setblocking(False)
            sock.connect(("127.0.0.1", neighbour.port)) # attempt to connect to server
            sock.sendall(rip_packet)
        
        self.reset_timer()

    def run(self):
        """ Server Loop"""
        while True:
            if self.get_update_time() < 0:
                print(f"timeout {self.current_timeout:.2f} {self.get_update_time():.2f}")
                self.check_router_down()
                self.send_forwarding_table()            
            in_packets, _out_packets, _exceptions = select.select(self.sockets, [], [], self.get_update_time())
            if in_packets != []:
                print(f"got packet {self.get_update_time():.2f}")
                for server in in_packets:
                    for s in self.sockets:
                        if server is s: # Received packet
                            data, client_addr = server.recvfrom(BUF_SIZE)
                            # Check if data is a valid packet and do stuff
                            
                            _, _, sender_id, entries = decode_packet(data)
                            #Updates the forwarding table
                            self.update_forwarding_table(sender_id, entries)


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
    #try:
    router.pretty_print()
    router.open()
    try:
        router.run()
    except KeyboardInterrupt:
        router.close()
        print("Keyboard Interrupt: Stopping Server")
    #except Exception as e:
        #print(f"Error: {type(e).__name__}, {e}")
        #router.close()
        #exit() 

if __name__ == "__main__":
    main()

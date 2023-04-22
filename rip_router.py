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
        self.periodic_timeout = timers[0]
        self.max_downtime = timers[1]
        self.garbage_time = timers[2]
        self.trigger_timer = timers[3]
        self.sockets = []
        
        self.reset_periodic_timer()
        self.reset_triggered_timer()
        self.schedule_update = False
    
    
    def __repr__(self):
        return(f"Router({self.router_id})")

    
    def pretty_print(self):
        print(f"Router Id: {self.router_id}")
        print(f"Listening for updates on {len(self.input_ports)} port(s)")
        print("Timers:")
        print(f"    Routing Update Time: {self.periodic_timeout[0]} seconds, +- {self.periodic_timeout[1]}")
        print(f"    Route Timeout: {self.max_downtime}")
        print(f"    Garbage Timeout: {self.garbage_time}")
        print(f"    Triggered Update Flooding Delay: {self.trigger_timer[0]}-{self.trigger_timer[1]} seconds")
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
        return max(self.last_update - time() + self.current_timeout, 0)

    
    def reset_periodic_timer(self):
        """ Reset update timer with a uniformly distributed random timeout value"""
        self.current_timeout = self.periodic_timeout[0] + round(random.uniform(-self.periodic_timeout[1], self.periodic_timeout[1]), 2)
        self.last_update = time()
    
    
    def get_trigger_time(self):
        """ Get the time in seconds until the router may send triggered messages"""
        return max(self.last_trigger - time() + self.trigger_timeout, 0)
    
    
    def reset_triggered_timer(self):
        """ Reset the timer that prevents flooding of lots of updated packets"""
        self.trigger_timeout = round(random.uniform(self.trigger_timer[0], self.trigger_timer[1]))
        self.last_trigger = time()
    
    
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
            print("    destination, next_hop, metric, last-updated, garbage-timer")
            for destination_id, entry in self.forwarding_table.items():
                timeout = '-' if entry.timeout is None else f"{entry.timeout:.1f}"
                garbage = '-' if entry.garbage is None else f"{entry.garbage:.1f}"
                print(f"    {destination_id:<11}  {entry.router_id:<8}  {entry.metric:<6}  {timeout:<12}  {garbage}")
            print()
                
                
    def check_router_down(self):
        """forwarding table to see if any routers should be marked as down"""
        has_updated = False
        routes_to_remove = []
        for destination_id, entry in self.forwarding_table.items():
            if entry.garbage is not None and entry.garbage + self.garbage_time < time(): # Remove entry from table entirely
                routes_to_remove.append(destination_id)
                print(f"{destination_id} is to be removed from the table")
                has_updated = True
            elif entry.timeout is not None and entry.timeout + self.max_downtime < time(): # Mark destination as unreachable
                self.forwarding_table[destination_id].metric = INF_METRIC
                self.forwarding_table[destination_id].garbage = time()
                self.forwarding_table[destination_id].timeout = None
                has_updated = True
                print(f"{destination_id} is unreachable")
            
        
        for route in routes_to_remove:
            self.forwarding_table.pop(route)            
        
        if has_updated:
            self.print_forwarding_table()
    
    
    def update_forwarding_table(self, sender_id, entries):
        """Update forwarding table using an incoming packet"""
        has_updated = False
        for entry in entries:
            _, destination_id, metric = entry
            if destination_id != self.router_id: #Ignore routes to self
                cost = min(self.get_neighbour_cost(sender_id) + metric, INF_METRIC)
                if destination_id not in self.forwarding_table or self.forwarding_table[destination_id].garbage is not None:
                    # Add an unknown or marked-for-garbage route
                    if cost < INF_METRIC:
                        #Don't bother adding a route with an infinite cost
                        self.forwarding_table[destination_id] = RoutingEntry(sender_id, None, cost, time(), None)
                        has_updated = True
                else:
                    route = self.forwarding_table[destination_id]
                    if route.router_id == sender_id:
                        # Reset timeout or re-enable a route if the route is confirmed alive by the next_hop
                        route.timeout = time()
                        if route.garbage is not None:
                            route.metric = cost
                            route.garbage = None
                    if (route.router_id == sender_id and route.metric != cost) or (route.router_id != sender_id and route.metric > cost):
                        # Update forwarding table if needed
                        route.metric = cost
                        route.router_id = sender_id
                        has_updated = True
                        if cost == INF_METRIC and route.timeout is not None:
                            route.timeout = None
                            route.garbage = time()
                        else:
                            route.timeout = time()
            
            if has_updated:
                #Print new table and schedule a triggered update
                print(f"Updated forwarding table with a packet from Router {sender_id}")
                self.print_forwarding_table()
                self.schedule_update = True
                    


    def send_forwarding_table(self):
        for neighbour in self.outputs:
            entries_to_send = [generate_entry(2, self.router_id, 0)]
            for destination, table_entry in self.forwarding_table.items():
                if table_entry.router_id == neighbour.router_id: # poisoned reverse
                    metric = INF_METRIC
                else:
                    metric = table_entry.metric
                if table_entry.timeout is not None: # don't send information about timed out routes
                    entries_to_send.append(generate_entry(2, destination, metric))
            
            rip_packet = generate_packet(2, 2, self.router_id, entries_to_send)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Initialise UDP socket
            sock.setblocking(False)
            sock.connect(("127.0.0.1", neighbour.port)) # attempt to connect to server
            sock.sendall(rip_packet)

    def run(self):
        """ Server Loop"""
        while True:
            if self.get_update_time() == 0:
                # Send periodic update
                self.check_router_down()
                self.send_forwarding_table()
                self.reset_periodic_timer()
                
            if self.schedule_update and self.get_trigger_time() == 0:
                # Send triggered update if timeout is valid
                self.check_router_down()
                self.send_forwarding_table()
                self.reset_triggered_timer()
                self.schedule_update = False
            
            # Get socket timeout such that it ends whenever its time to send a triggered or periodic update.
            if self.schedule_update:
                socket_timer = min(self.get_update_time(), self.get_trigger_time())
            else:
                socket_timer = self.get_update_time()
            
            in_packets, _out_packets, _exceptions = select.select(self.sockets, [], [], socket_timer)
            if in_packets != []:
                for server in in_packets:
                    for s in self.sockets:
                        if server is s: # read packet from correct port
                            data, client_addr = server.recvfrom(BUF_SIZE)
                            _, _, sender_id, entries = decode_packet(data)
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

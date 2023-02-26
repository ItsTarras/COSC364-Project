import socket
import select
import sys
from math import inf
from packets import *
from random import randint


class Router:
    
    def __init__(self, router_id, input_ports, outputs):
        self.forwarding_table = dict()
        for i in outputs:
            self.forwarding_table[i.router_id] = i
       
        self.router_id = router_id
        self.input_ports = input_ports
        self.outputs = outputs
        self.sockets = []
    
    def __str__(self):
        return(f"router-id = {self.router_id} \ninput-ports = {self.input_ports} \noutput-ports = {self.outputs} \ntable = {self.forwarding_table}")
    
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
        
        #We need to update the hop count first, but I've no idea which part
        #Of the bytearray stores that.
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
    
    def run(self):
        """ Server Loop"""
        while True:
            in_packets, _out_packets, _exceptions = select.select(self.sockets, [], self.sockets)
            for server in in_packets:
                for s in self.sockets:
                    if server is s: # Received packet
                        data, client_addr = server.recvfrom(BUF_SIZE)
                        # Check if data is a valid packet and do stuff
                        
                        #Checks what port we are receiving from, might need later.
                        received_from_port = s.getsockname()[1]
                        
                        #Checks the packet's hop count
                        decoded = decode_entry(data)
                        hop_count = decoded[2]
                        
                        #WE NEED TO CHECK THE FORWARDING TABLE FOR THE OUTPUT ADDRESS OF THE PORT!
                        if hop_count < 15:
                            #increase hop count
                            decoded[2] += 1
                            
                            #Re-encode the message into the packet -NEEDS WORK-.
                            
                            
                            #Send the message to the output from the forwarding table
                            route(data, "INSERT OUTPUT ADDR tuple HERE")
                    else:
                        print("Server and Sockets not similar!")

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
        router.close()
        exit() 

if __name__ == "__main__":
    main()

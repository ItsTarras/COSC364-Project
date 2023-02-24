import socket
import sys
from math import inf
from packets import *
from random import randint


class router:
    
    def __init__(self, router_id, input_ports, outputs):
        forwarding_table = {}
        for ports in outputs:
            forwarding_table[ports[1]] = ((ports[0], ports[2]))
       
        self.router_id = router_id
        self.input_ports = input_ports
        self.forwarding_table = forwarding_table
    
    def __str__(self):
        return(f"router-id = {self.router_id} \ninput-ports = {self.input_ports} \noutput-ports = {self.forwarding_table}")
    
    def route(self, input_port, output_port):
        """Reads from the forwarding table, and routes the message to the output port"""
        pass
    
    def ping(self, input_ports, outputs):
        """Use a timer to ping all ports periodically"""
        pass

def main():
    filename = 'config.txt'
    try:
        router_id, input_ports, outputs = check_config(parse_config(filename))      
    except Exception as e:
        print(f"Error: {e}")
        exit()
    print(f"Successfully loaded {filename}")
    print(f"router-id: {router_id}")
    print(f"input_ports: {input_ports}")
    print(f"outputs: {outputs}")  

if __name__ == "__main__":
    main()

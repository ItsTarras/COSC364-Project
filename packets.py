"""
Utility Functions for Implementing RIP version 2 in Python
Max Croucher - 23/2/23
"""

# TO-DO:
# Implement error capturing for these modules
# Test edge cases
# Read spec sheet and ensure correctness of these functions

from collections import namedtuple

COMMENT_CHAR = "#"
RIP_VERSION = 2
BUF_SIZE = 1024

RoutingEntry = namedtuple("RoutingEntry", "router_id port metric")

"""
RIP Packet Format:
    command (8b)
    version (8b)
    sender-router-id (16b)
    Entries (20b each), between 1 and 25

RIP Entry Format:
    addr family id: (16b)
    zero-arr: (16b)
    router-id: (32b)
    zero-arr: (64b)
    metric: (32b)

Fields:
    command:
        1 - request
        2 - response
    version:
        should always be 2
    sender-router-id:
        ID of the router that send the packet
    metric:
        number in 1-15, specifies metric for destination, or 16 if infinity
"""

def to_binary(value, size, endian):
    """ Convert an integer to a binary integer with a specified size"""
    if value >= 2 ** (size * 8):
        raise Exception("The number is too large for the speficied number of bytes.")
    else:
        return value.to_bytes(size, endian)

def generate_entry(family_id, router_id, metric):
    """ Takes and IP address and metric as integers and returns an RIP entry
        as a bytearray"""
    return to_binary(family_id, 2, 'big') + \
           bytearray(2) + \
           to_binary(router_id, 4, 'big') + \
           bytearray(8) + \
           to_binary(metric, 4, 'big')

def generate_packet(command, version, sender_id, entries):
    """ Takes the type and version of an RIP packet and up to 25 entries.
        returns a complete RIP packet as a bytearray"""
    if len(entries) == 0:
        raise Exception("At least one entry must be provided.")
    elif len(entries) > 25:
        raise Exception("Too many entries have been provided.")
    packet = to_binary(command, 1, 'big') + \
             to_binary(version, 1, 'big') + \
             to_binary(sender_id, 2, 'big')
    for entry in entries:
        packet += entry
    return packet

def decode_entry(entry):
    """ Takes an RIP entry and returns the stored fields"""
    family_id = int.from_bytes(entry[0:2], 'big')
    router_id = int.from_bytes(entry[4:8], 'big')
    metric = int.from_bytes(entry[16:20], 'big')
    return family_id, router_id, metric

def decode_packet(packet):
    """ Takes a recieved RIP packet returns the parameters and stored entries"""
    command = int.from_bytes(packet[0:1], 'big')
    version = int.from_bytes(packet[1:2], 'big')
    sender_id = int.from_bytes(packet[2:4], 'big')
    entries = []
    position = 4 # starting index for RIP entries
    while position < len(packet):
        entry = packet[position:position+20]
        entries.append(decode_entry(entry))
        position += 20
    return command, version, sender_id, entries

"""
Config File Specifications:
Parameters are specified in the <name><space><data> format, with data separated
with just a comma. Blank lines and comments beginning with a # are ignored.
The essential parameters for any config file are:
router-id: Unique Identifier for a router
input-ports: A list of ports the demon listens for packets from (1024 <= x <= 64000)
outputs: A list of port-metric-id groupings that the demon can communicate with
"""

def parse_config(filename):
    """ Takes the filename of a config file (with any file extension) and returns
        the saved parameters"""
    parameters = dict()
    try:
        with open(filename, 'r') as config:
            data = config.readlines()
    except Exception:
        raise Exception(f"{filename} could not be opened")
    for line in data:
        if line.startswith('\n') or line.startswith(COMMENT_CHAR):  
            pass
        else:
            line_contents = line.rstrip().split(' ')
            if len(line_contents) != 2:
                raise Exception(f"Incorrect syntax in {filename}.")
            field_name = line_contents[0]
            field_data = line_contents[1].split(',')
            if field_name in parameters.keys():
                raise Exception("Duplicate parameter name.")
            parameters[field_name] = field_data
    return parameters

def check_config(config):
    """ Take parameters taken from a config file and check for correctness """
    parameters = ['router-id', 'input-ports', 'outputs', 'timeout-default', 'timeout-delta']
    if not all (i in config.keys() for i in parameters):
        raise Exception(f"config file is missing required parameters.")
    
    # Ensure only one value for 'router-id' is present and that it is an integer
    if len(config["router-id"]) > 1:
        raise Exception("Parameter 'router-id' must only contain one value.")
    if not config["router-id"][0].isnumeric():
        raise Exception(f"Parameter 'router-id' contain an integer.")
    router_id = int(config["router-id"][0])
    
    # Ensure all values for 'input-ports' are integers 1024 <= x <= 64000
    try:
        input_ports = list(map(int, config["input-ports"]))
    except ValueError:
        raise Exception("All values for 'input-ports' must be integers.")
    for value in input_ports:
        if 1024 > value or 64000 < value:
            raise Exception("All values for 'input-ports' must be between 1024 and 64000.")
    if len(input_ports) != len(set(input_ports)):
        raise Exception("Parameter 'input-ports' may not contain any duplicate entries.")
    
    # Ensure all values for 'outputs' are 3-tuples and contain integers
    outputs = []
    for value in config["outputs"]:
        value = value.split('-')
        if len(value) != 3:
            raise Exception("All values for 'outputs' must be 3 integers, each separated by '-'.")
        try:
            port, metric, router_id = tuple(map(int, value))
        except ValueError:
            raise Exception("All components of a value for 'outputs' must be integers.")
        if 1024 > port or 64000 < port:
            raise Exception("The port field for an 'outputs' value must be between 1024 and 64000.")
        if port in input_ports:
            raise Exception("port numbers in 'outputs' must not also be in 'input-ports'.")
        if 0 > metric or 16 < metric:
            raise Exception("the metric field for an 'outputs' value must be between 0 and 16.")
        if 0 > router_id or 65536 < router_id:
            raise Exception("the router-id field for an 'outputs' value must be between 0 and 65536")
        outputs.append(RoutingEntry(router_id, port, metric))
    if len(config["timeout-default"]) > 1 or len(config["timeout-delta"]) > 1:
        raise Exception("A timeout parameter must be a single number")
    try:
        timeout_default = float(config["timeout-default"][0])
        timeout_delta = float(config["timeout-delta"][0])
    except ValueError:
        raise Exception("timeout parameters must be a number")
    if timeout_delta > timeout_default:
        raise Exception("timeout-delta must be less than timeout-default")
        
    return router_id, input_ports, outputs, timeout_default, timeout_delta

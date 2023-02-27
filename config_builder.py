import random
from datetime import datetime
import shutil
import os

NUM_ROUTERS = 10
COMPLETEDNESS = 0.5
METRIC_LOWER = 1
METRIC_UPPER = 8
PORT_LOWER = 1024
PORT_UPPER = 64000
ID_LOWER = 1
ID_UPPER = NUM_ROUTERS * 3
CONFIG_LOCATION = "generated_config"
DEFAULT_DELAY = 30
DELAY_DELTA = 5

def generate_adjacency_list(nodes):
    adj_list = {i: {j: (None, None) for j in nodes} for i in nodes}
    # build tree to ensure connectedness
    tree = [nodes[0]]
    used_ports = []
    for i in range(len(nodes) - 1):
        node_1 = random.choice(tree)
        node_2 = random.choice(nodes)
        while node_2 in tree:
            node_2 = random.choice(nodes)            
        
        metric = random.randint(METRIC_LOWER, METRIC_UPPER)
        port_1 = random.randint(PORT_LOWER, PORT_UPPER)
        while port_1 in used_ports:
            port_1 = random.randint(PORT_LOWER, PORT_UPPER)
        used_ports.append(port_1)
        port_2 = random.randint(PORT_LOWER, PORT_UPPER)
        while port_2 in used_ports:
            port_2 = random.randint(PORT_LOWER, PORT_UPPER)
        used_ports.append(port_2)
        adj_list[node_2][node_1] = (metric, port_1)
        adj_list[node_1][node_2] = (metric, port_2)
        tree.append(node_2)
    
    num_paths = len(nodes) - 1
    
    while num_paths < ((len(nodes) * (len(nodes)-1) / 2) * COMPLETEDNESS):
        node_1 = random.choice(nodes)
        node_2 = random.choice(nodes)
        if node_1 != node_2 and adj_list[node_1][node_2][0] is None:
            port_1 = random.randint(PORT_LOWER, PORT_UPPER)
            while port_1 in used_ports:
                port_1 = random.randint(PORT_LOWER, PORT_UPPER)
            used_ports.append(port_1)
            port_2 = random.randint(PORT_LOWER, PORT_UPPER)
            while port_2 in used_ports:
                port_2 = random.randint(PORT_LOWER, PORT_UPPER)
            used_ports.append(port_2)
            adj_list[node_2][node_1] = (metric, port_1)
            adj_list[node_1][node_2] = (metric, port_2)
            num_paths += 1
    
    return adj_list

def pretty_print(id_nums, adj_list):
    string = '# Adjacency Matrix:\n#       '
    for i in id_nums:
        string += f"{i: ^9}"
    for i in adj_list:
        string += "\n# "
        string += f"{i: <5}:"
        for j in adj_list[i]:
            if adj_list[i][j][0] == None:
                string += '   x:x   '
            else:
                string += f"{f'{adj_list[i][j][0]}:{adj_list[i][j][1]}': ^9}"
    return string
    
    
def main():
    id_nums = set()
    while len(id_nums) < NUM_ROUTERS:
        id_nums.add(random.randint(ID_LOWER, ID_UPPER))
    id_nums = list(id_nums)
    print(id_nums)
    adj_list = generate_adjacency_list(id_nums)
    print(adj_list)
    
    print(pretty_print(id_nums, adj_list))
    try:
        shutil.rmtree(CONFIG_LOCATION)
    except FileNotFoundError:
        pass
    os.mkdir(CONFIG_LOCATION)
    for i in id_nums:
        with open(f"{CONFIG_LOCATION}/config_{i}.txt", 'w+') as config_file:
            config_file.write(f"# This config file was generated on {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            config_file.write(pretty_print(id_nums, adj_list))
            config_file.write(f"\n\nrouter-id {i}")
            
            input_ports = []
            output_ports = []
            
            for neighbour_id in adj_list[i]:
                for neighbour_neighbour in adj_list[neighbour_id]:
                    metric, port = adj_list[neighbour_id][neighbour_neighbour]
                    if neighbour_neighbour == i and metric is not None:
                        input_ports.append(f"{port}")
            
            for neighbour_id in adj_list[i]:
                metric, port = adj_list[i][neighbour_id]
                if metric is not None:
                    output_ports.append(f"{port}-{metric}-{neighbour_id}")
            config_file.write(f"\n\ninput-ports {','.join(input_ports)}")
            config_file.write(f"\n\noutputs {','.join(output_ports)}")
            config_file.write("\n\n# Timeout params:")
            config_file.write(f"\ntimeout-default {DEFAULT_DELAY}")
            config_file.write(f"\ntimeout-delta {DELAY_DELTA}")
    
if __name__ == "__main__":
    main()
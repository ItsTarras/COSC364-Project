"""
Driver program for starting several instances of RIP version 2 on different threads.
    This program calls gnome-terminal for displaying each router, so will not work on Windows.
Max Croucher
12 Apr, 2023
"""

import multiprocessing
from os import listdir, path, system
import config_builder

ROUTER_FILENAME = "rip_router.py"
GENERATED_PATH = config_builder.CONFIG_LOCATION
TESTING_PREFIX = "demo_config"
SUBMISSION_PREFIX = "submission_config"
CONFIG_SUFFIX = ".txt"

def run_router(router_path):
    """ Launch a router"""
    command = f"python3 {ROUTER_FILENAME} {router_path}; bash"
    name = path.split(router_path)[1]
    system(f"gnome-terminal --title=\"Router {name}\" -- bash -c \"{command}\"")


def launch_network(prefix):
    """Iterate through a given directory and launch a router for each"""
    id_names = listdir(prefix)
    processes = []
    for router_id in id_names:
        if router_id.endswith(".txt"):
            processes.append(
                multiprocessing.Process(target=run_router, args=(path.join(prefix, router_id),))
            )
    for i in processes:
        i.start()


if __name__ == "__main__":
    launch_network(GENERATED_PATH)

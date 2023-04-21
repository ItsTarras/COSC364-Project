import config_builder
import os
import multiprocessing

config_builder.NUM_ROUTERS = 8

ROUTER_FILENAME = "rip_router.py"
CONFIG_PREFIX = f"{config_builder.CONFIG_LOCATION}/config_"
CONFIG_SUFFIX = ".txt"
TESTING_PREFIX = "demo_config/"
SUBMISSION_PREFIX = "submission_config/"

def run_router(router_id):
    os.system(f"gnome-terminal -- bash -c \"python3 {ROUTER_FILENAME} {CONFIG_PREFIX}{router_id}{CONFIG_SUFFIX}; bash\" ")

def main():
    id_nums = config_builder.generate_configs()
    processes = []
    for router_id in id_nums:
        processes.append(multiprocessing.Process(target=run_router, args=(router_id, )))
    
    for i in processes:
        i.start()

def run_test_router(router_id, prefix):
    os.system(f"gnome-terminal --title=\"Router {router_id}\" -- bash -c \"python3 {ROUTER_FILENAME} {prefix}{router_id}; bash\" ")


def run_test_configs(prefix):
    id_names = os.listdir(prefix)
    processes = []
    for router_id in id_names:
        if router_id.endswith(".txt"):
            processes.append(multiprocessing.Process(target=run_test_router, args=(router_id, prefix)))
    
    for i in processes:
        i.start()
if __name__ == "__main__":
    #main()
    #run_test_configs(SUBMISSION_PREFIX)
    run_test_configs(TESTING_PREFIX)
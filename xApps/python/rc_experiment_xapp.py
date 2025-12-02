#!/usr/bin/env python3

import time
import datetime
import argparse
import signal
from lib.xAppBase import xAppBase
import ricxappframe.xapp_rest as ricrest
import ricxappframe.xapp_sdl as ricsdl

class MyXapp(xAppBase):
    def __init__(self, config, http_server_port, rmr_port, sleep_interval, prb_lower_bound):
        super(MyXapp, self).__init__(config, http_server_port, rmr_port)
        self.sdl = ricsdl.SDLWrapper()
        self.sleep_interval = sleep_interval
        self.prb_lower_bound = prb_lower_bound

    def get_ml_decision(self, metrics):
        # Placeholder for ML model inference
        # In a real scenario, this function would load a trained ML model and use it to predict the optimal PRB allocation
        # based on the input metrics.
        print("Performing ML inference with metrics: {}".format(metrics))
        # For demonstration purposes, we will just return a fixed value
        return 50
    
    # Mark the function as xApp start function using xAppBase.start_function decorator.
    # It is required to start the internal msg receive loop.
    @xAppBase.start_function
    def start(self, e2_node_id, ue_id):
        while self.running:

            # Getting the KPMs of the UE from SDL
            metrics = self.sdl.get(ns="metrics", key=str(ue_id))
            print ("Retrieved KPM Metrics for UE ID {} from SDL: {}".format(ue_id, metrics))

            # Getting the target PRB allocation
            max_prb_ratio = self.get_ml_decision(metrics)
            if max_prb_ratio < self.prb_lower_bound:
                max_prb_ratio = self.prb_lower_bound

            # Setting the max_prb_ratio on the gNB and updating it on the SDL
            current_time = datetime.datetime.now()
            dedicated_prb_ratio = min_prb_ratio = 0
            print("{} Send RIC Control Request to E2 node ID: {} for UE ID: {}, PRB_dedicated_ratio: {}, PRB_min_ratio: {}, PRB_max_ratio: {}".format(current_time.strftime("%H:%M:%S"), e2_node_id, ue_id, dedicated_prb_ratio, min_prb_ratio, max_prb_ratio))
            self.e2sm_rc.control_slice_level_prb_quota(e2_node_id, ue_id, min_prb_ratio, max_prb_ratio, dedicated_prb_ratio, ack_request=1)
            self.sdl.set(ns="prb_alloc", key=str(ue_id), value=max_prb_ratio)
            time.sleep(self.sleep_interval)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='My example xApp')
    parser.add_argument("--config", type=str, default='', help="xApp config file path")
    parser.add_argument("--http_server_port", type=int, default=8090, help="HTTP server listen port")
    parser.add_argument("--rmr_port", type=int, default=4560, help="RMR port")
    parser.add_argument("--e2_node_id", type=str, default='gnbd_001_001_00019b_0', help="E2 Node ID")
    parser.add_argument("--ran_func_id", type=int, default=3, help="E2SM RC RAN function ID")
    parser.add_argument("--gnb_cu_ue_f1ap_id", type=int, default=0, help="UE ID")
    parser.add_argument("--sleep_interval", type=int, default=1, help="Sleep interval between control requests")
    parser.add_argument("--prb_lower_bound", type=int, default=4, help="Lower bound of PRB max ratio")

    args = parser.parse_args()
    config = args.config
    e2_node_id = args.e2_node_id # TODO: get available E2 nodes from SubMgr, now the id has to be given.
    ran_func_id = args.ran_func_id # TODO: get available E2 nodes from SubMgr, now the id has to be given.
    ue_id = args.gnb_cu_ue_f1ap_id
    sleep_interval = args.sleep_interval
    prb_lower_bound = args.prb_lower_bound

    # Create MyXapp.
    myXapp = MyXapp(config, args.http_server_port, args.rmr_port, sleep_interval, prb_lower_bound)
    myXapp.e2sm_rc.set_ran_func_id(ran_func_id)

    # Connect exit signals.
    signal.signal(signal.SIGQUIT, myXapp.signal_handler)
    signal.signal(signal.SIGTERM, myXapp.signal_handler)
    signal.signal(signal.SIGINT, myXapp.signal_handler)

    # Start xApp.
    myXapp.start(e2_node_id, ue_id)

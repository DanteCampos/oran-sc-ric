# A Framework for AI-Based Efficient Radio Resource Management on O-RAN

This repository is a fork from srsRAN's dockerized Near-RT RIC based on the OSC Near-RT RIC.

## Content

We modify the original repository to add the xApps from our experiment.
To do that, we:
- Add the Python code of our developed xApps on the `xApps/python` folder, namely: `rc_static_xapp`, `rc_experiment_xapp`, `rc_dataset_xapp`, `kpm_dataset_xapp`, and `kpm_experiment_xapp`
- Add a trained ML model for our data-driven RC xApp, located in `xApps/python/ml_model.pkl`
- Modify the Dockerfile for the container that runs xApps, located in `ric/images/ric-plt-xapp-frame-py/Dockerfile`, to install and update dependencies, and to define environmental variables enabling access to the SDL

The `project/` folder includes other important files from our project:
- `srsue_channel_configs/` is a folder containing the configurations we input on srsUE to generate different channel conditions, namely: `20_15.conf` and `50_40.conf`
- `training_datasets/` is a folder containing the `.csv` files for each dataset collected for training the ML algorithm (one for each channel condition)
- `dataset.ipynb` is a Jupyter Notebook to load the datasets collected for training, clean, balance, and combine them to create the `training_dataset.csv`; also, it plots the distribution of the training dataset
- `training_dataset.csv` is the clean dataset used to train the ML algorithm
- `training.ipynb` is a Jupyter Notebook that trains multiple ML algorithm using the training dataset, plots the scores and evaluations of the ML models, selects the model with the highest scores, and saves it as `ml_model.pkl`
- `result_datasets` is a folder containint the `.csv` files for our final evaluation, one for each combination of channel condition and RC xApp (4 in total)

## Setup the environment

From now on, we assume you are in a root folder for the experiment, containing our fork of `oran-sc-ric` inside.

Before we start, build our modified python_xapp_runner container for srsRAN's Near-RT RIC:

```bash
cd  oran-sc-ric
docker compose build python_xapp_runner
```

We follow [srsRAN RIC tutorial](https://docs.srsran.com/projects/project/en/latest/tutorials/source/near-rt-ric/source/index.html) to deploy our environment.
Based on their tutorial, and assuming you have already downloaded and built all required code, we execute the steps below to attach one UE with 5 Mbps uplink demand to the network.

(in a new terminal) Run the 5GC
```bash
cd srsRAN_Project/docker
docker compose up 5gc
```

(in a new terminal) Run the OSC Near RT RIC
```bash
cd oran-sc-ric
docker compose up
```

(in a new terminal) Run the gNB
```bash
cd ./srsRAN_Project/build/apps/gnb/
sudo ./gnb -c gnb_zmq.yaml e2 --addr="10.0.2.10" --bind_addr="10.0.2.1"
```

(in a new terminal) Run the srsUE using a .conf file from our `o-ran-sc/project/srsue_channel_configs/` folder
```bash
# Create routes for the UE
sudo ip netns add ue1
sudo ip ro add 10.45.0.0/16 via 10.53.1.2
cd srsRAN_4G/build/srsue/src/
sudo ./srsue <PATH_TO_CONFIG_FILE>
```

## Dataset collection and ML training

Having the environment setup done, we can collect the data.
We collect a single dataset for each channel condition in the `o-ran-sc/project/srsue_channel_configs/` folder.
To change the channel condition, you need to setup the entire environment again.

(in a new terminal) Run the Dataset KPM xApp
```bash
cd oran-sc-ric
docker compose exec python_xapp_runner ./kpm_dataset_xapp.py --metrics=DRB.UEThpUl --kpm_report_style=5 --http_server_port=8099 --target_thr=5000
```

(in a new terminal) Run the Dataset RC xApp (for setting a new RRM Policy Max Ratio  every 10 seconds, starting from 100, decreasing to 1, and going back to 100, endlessly)
```bash
cd oran-sc-ric
docker compose exec python_xapp_runner ./rc_dataset_xapp.py --sleep_interval=10 --prb_lower_bound=1
```

(in a new terminal) After enough time to run to cycles of decreasing the RRM Policy Max Ratio from 100 to 1 twice, download the dataset (it wil generate a `data.csv` file)
```bash
wget $(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $(docker ps -q --filter ancestor=python_xapp_runner:i-release)):8099/data -O data.csv
```

After collecting the dataset of each channel condition, run `o-ran-sc/project/dataset.ipynb`, changing the paths to the collected datasets, to generate the `training_dataset.csv` file for training the ML algorihtm.

Then, train the ML algorithm by executing `o-ran-sc/project/trainig.ipynb`, which will save the trained ML model as `ml_model.pkl`.

Finally, put the ML model on the `oran-sc-ric/xApps/python` folder so the Experiment RC xApp can access it. 

## Experiment

We evaluate the ML algorithm for defining RRM Policy Max Ratio values in an ML RC xApp against a static RC xApp that always allocates 100% resources.

To change the channel condition, you need to setup the entire environment again.

To change the RC xApp, you just need start this Experiment section from the beginning, after stopping both KPM and RC xApps.

(in a new terminal) Run the Experiment KPM xApp
```bash
cd oran-sc-ric
docker compose exec python_xapp_runner ./kpm_experiment_xapp.py --metrics=DRB.UEThpUl --kpm_report_style=5 --http_server_port=8093
```

(in a new terminal) Run the Experiment RC xApp
```bash
cd oran-sc-ric

# If you're running the ML RC xApp
docker compose exec python_xapp_runner ./rc_experiment_xapp.py --sleep_interval=1 --prb_lower_bound=10

# If you're running the static RC xApp
docker compose exec python_xapp_runner ./rc_static_xapp.py --policy=100
```

(in a new terminal) Download the results dataset after enough time (we set 10 minutes for each experiment)
```bash
wget $(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $(docker ps -q --filter ancestor=python_xapp_runner:i-release)):8093/data -O data.csv
```

This will download the results dataset as `data.csv`
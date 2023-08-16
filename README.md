# elastic-sim
This is a simulation code that models an HPC system's operation and allows for elastic jobs that can be re-sized at runtime.

# Running a Simulation
In order to run a simulation, a user must first create a .conf file that sets up the parameters for the simulation.  An example configure file with documentation can be found in the configs directory.  Once a configure file is created, the simulation can be run using the following command (replace with your own file name).

./simulator.py [config_file]

# Reproducing Paper Results

In order to reproduce the results from our SC23 paper submission, one must conduct the following steps:
* Run the simulation with each of the four inelastic configure files
  * ./simulator.py configs/perlmutter_gpu_inelastic.conf
  * ./simulator.py configs/perlmutter_cpu_inelastic.conf
  * ./simulator.py configs/cori_haswell_inelastic.conf
  * ./simulator.py configs/cori_knl_inelastic.conf
* Run the trials for the different elastic configurations
  * Be sure to put the results from each of these runs in their own directories
  * ./conservative_trials.py
  * ./aggressive_grow_trials.py
  * ./dynamic_trials.py
* Copy the inelastic _stats.txt file for each of the machines into the elastic tests directories
* Run the plot_trials.py utility on each of the output directories
  * For example, if you stored the conservative results in a directory called 'conservative', a plot might look like the following:
    * ./plot_trials.py conservative/output_trials_perlmutter_gpu/perlmutter_gpu_
* Run the multibar.py utility to get the bar plots we used in the paper
  * This utility assumes that you named your output directories for the trials: 'conservative', 'aggressive_grow', and 'dynamic'

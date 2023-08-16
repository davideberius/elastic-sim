#!/usr/bin/env python3

import os

input_dirs = ['perlmutter_gpu', 'perlmutter_cpu', 'cori_haswell', 'cori_knl']
prefixes = ['elastic_5', 'elastic_10', 'elastic_25', 'elastic_50', 'elastic_75', 'elastic_100']
elastic_ratios = ['0.05', '0.1', '0.25', '0.5', '0.75', '1.0']
elastic_policy = 'gsc'
total_nodes = ['1792', '3072', '2388', '9688']
random_seed = '1'
tick_rate = '1.0'
scaling_min = '0.5'
grow_steps = '3'

num_trials = 5
for i in range(0, len(input_dirs)):
    for j in range(0, len(prefixes)):
        for k in range(0, num_trials):
            prefix = input_dirs[i] + "_" + str(k) + "_" + prefixes[j]
            conf_fname = prefix + ".conf"
            ofile = open(conf_fname, "w+")

            ofile.write("input_file_dir %s\n" % input_dirs[i])
            ofile.write("output_prefix %s\n" % prefix)
            ofile.write("elastic_ratio %s\n" % elastic_ratios[j])
            ofile.write("elastic_policy %s\n" % elastic_policy)
            ofile.write("total_nodes %s\n" % total_nodes[i])
            ofile.write("random_seed %s\n" % str(k))
            ofile.write("tick_rate %s\n" % tick_rate)
            ofile.write("scaling_min %s\n" % scaling_min)
            ofile.write("grow_steps %s\n" % grow_steps)
            if 'gpu' in input_dirs[i]:
                ofile.write("node_memory 416.0\n")
                ofile.write("nic_bandwidth 80.0\n")
            elif 'cpu' in input_dirs[i]:
                ofile.write("node_memory 512.0\n")
                ofile.write("nic_bandwidth 20.0\n")
            elif 'haswell' in input_dirs[i]:
                ofile.write("node_memory 128.0\n")
                ofile.write("nic_bandwidth 10.0\n")
            elif 'knl' in input_dirs[i]:
                ofile.write("node_memory 112.0\n")
                ofile.write("nic_bandwidth 10.0\n")

            ofile.close()
            print("Running Simulator for %s..." % conf_fname)
            os.system("./simulator.py %s > /dev/null" % conf_fname)
    ofile_name = "output_trials_%s" % input_dirs[i]
    os.system("mkdir %s" % ofile_name)
    os.system("cp %s_* %s" % (input_dirs[i], ofile_name))


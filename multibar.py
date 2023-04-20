#!/usr/bin/env python3

import sys
import os

import numpy as np
import matplotlib.pyplot as plt

class Data:
    def __init__(self, err_min, err_max, lnames, yvals):
        self.err_min = err_min
        self.err_max = err_max
        self.lnames = lnames
        self.yvals = yvals

def parse_file(fname):
    f = open(fname, "r")
    err_min = []
    err_max = []
    lnames  = []
    yvals   = []

    for line in f:
        line = line.replace(",\n", "").split(",")
        temp = []
        for i in range(1, len(line)):
            if line[0] == "lnames":
                temp.append(line[i])
            else:
                temp.append(float(line[i]))
        if line[0] == "err_min":
            err_min = temp
        elif line[0] == "err_max":
            err_max = temp
        elif line[0] == "lnames":
            lnames = temp
        elif line[0] == "yvals":
            yvals = temp
    f.close()
    data = Data(err_min, err_max, lnames, yvals)
    return data

def plot_bars(data, ylabel, title, machine_label, test_labels, fname):
    plt.rcParams.update({'font.size': 12})
    plt.rcParams.update({'axes.labelsize' : 14})
    
    plt.figure()
    N = len(data[0].yvals) - 1
    ind = np.arange(N)
    width = 0.25

    #if "Turnaround" in title:
    #    for i in range(1, len(data[0].yvals)):
    #        data[0].yvals[i] += 0.1 * data[0].yvals[0]
    #        data[1].yvals[i] += 0.1 * data[1].yvals[0]
    #        data[2].yvals[i] += 0.1 * data[2].yvals[0]

    if "Utilization" in title:
        plt.ylim(0, 100)

    inelastic = data[0].yvals[0]

    data1 = []
    data2 = []
    data3 = []
    lnames = []
    for i in range(1, len(data[0].yvals)):
        data1.append(data[0].yvals[i])
        data2.append(data[1].yvals[i])
        data3.append(data[2].yvals[i])
        lnames.append(data[0].lnames[i])

    line = plt.axhline(y=inelastic, linewidth=1, color='k')
    bar1 = plt.bar(ind, data1, width, color = 'y')
    bar2 = plt.bar(ind+width, data2, width, color = 'm')
    bar3 = plt.bar(ind+width*2, data3, width, color = 'c')

    plt.xlabel("Elasticity Percentage")
    plt.ylabel(ylabel)

    plt.grid(axis = 'y')

    labels = []
    for i in range(0, len(lnames)):
        labels.append(lnames[i].split("_")[-1])

    plt.xticks(ind+width, labels)
    if "KNL" in machine_label and "Wait" in title:
        plt.legend( (line, bar1, bar2, bar3), test_labels, loc='upper right')
    else:
        plt.legend( (line, bar1, bar2, bar3), test_labels, loc='lower left')

    plt.savefig(fname, dpi=250, bbox_inches='tight')
    plt.clf()


test_dirs = ["uniform_scaling", "aggressive_shrink", "aggressive_priority"]
test_labels = ["Inelastic", "Uniform Scaling", "Aggressive Shrink", "Aggressive Priority"]
machine_names = ["perlmutter_gpu", "perlmutter_cpu", "cori_haswell", "cori_knl"]
machine_labels = ["Perlmutter GPU", "Perlmutter CPU", "Cori Haswell", "Cori KNL"]
machine_dirs = ["output_trials_perlmutter_gpu", "output_trials_perlmutter_cpu", "output_trials_cori_haswell", "output_trials_cori_knl"]
csv_names = ["_average_machine_utilization_by_elasticity.csv", "_average_runtime_by_elasticity.csv", "_average_turnaround_time_by_elasticity.csv", "_average_wait_time_by_elasticity.csv"]
plot_titles = ["Average Machine Utilization by Elasticity", "Average Runtime by Elasticity", "Average Turnaround Time by Elasticity", "Average Wait Time by Elasticity"]
plot_ylabels = ["Percent Utilization", "Time (s)", "Time (s)", "Time (s)"]

for j in range(0, len(machine_dirs)):
    for k in range(0, len(csv_names)):
        data = []
        for i in range(0, len(test_dirs)):
            fname = "%s/%s/%s" % (test_dirs[i], machine_dirs[j], machine_names[j] + csv_names[k])
            d = parse_file(fname)
            data.append(d)

        plot_fname = machine_names[j] + csv_names[k].replace(".csv", ".png")
        plot_bars(data, plot_ylabels[k], plot_titles[k], machine_labels[j], test_labels, plot_fname)

        baseline = data[0].yvals[0]
        min_val = baseline
        max_val = baseline
        for obj in data:
            print(obj.yvals)
            for val in obj.yvals:
                if val < min_val:
                    min_val = val
                if val > max_val:
                    max_val = val
        print(plot_fname)
        print("%f\t%f\t%f" % (baseline, min_val, max_val))
        if "util" in plot_fname:
            print("Best improvement: %f" % ((max_val/baseline)))
        else:
            print("Best improvement: %f" % (baseline/min_val))
        print("\n\n")

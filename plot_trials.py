#!/usr/bin/env python3

import sys

import matplotlib.pyplot as plt

basename = sys.argv[1]
lnames = ["inelastic", "elastic_5", "elastic_10", "elastic_25", "elastic_50", "elastic_75", "elastic_100"]
pname  = basename + "inelastic_vs_"
tnames = ["Total Runtime", "Average Runtime", "Total Wait Time", "Average Wait Time", "Average Turnaround Time", "System Utilization"]

def write_output(data, fname):
    outfile = open(fname, "w+")
    outfile.write("Elasticity,Trial 0,Trial 1,Trial 2,Trial 3,Trial 4,Average,Min,Max\n")

    for i in range(0, len(lnames)):
        outfile.write(lnames[i] + ",")
        min_val = data[i][0]
        max_val = data[i][0]
        total   = 0.0
        for j in range(0, len(data[i])):
            val = data[i][j]
            total += val
            if val < min_val:
                min_val = val
            elif val > max_val:
                max_val = val
            outfile.write("%f," % val)
        outfile.write("%f,%f,%f\n" % (total/len(data[i]), min_val, max_val))

def plot_bar(data, title, y_label):
    fig, ax = plt.subplots(1, 1, figsize=(16,9))

    yvals = []
    err_min = []
    err_max = []
    # Append inelastic data point
    yvals.append(data[0][0])
    err_min.append(0.0)
    err_max.append(0.0)
    for i in range(1, len(data)):
        min_val = data[i][0]
        min_idx = 0
        max_val = data[i][0]
        max_idx = 0
        total = 0.0

        for j in range(0, len(data[i])):
            val = data[i][j]
            if val < min_val:
                min_val = val
                min_idx = j
            elif val > max_val:
                max_val = val
                max_idx = j
            total += val

        total -= min_val + max_val
        yvals.append(total / float(len(data[i])-2))

        e_min = max_val
        e_max = min_val
        for j in range(0, len(data[i])):
            val = data[i][j]
            if j != min_idx and j != max_idx:
                if val < e_min:
                    e_min = val
                if val > e_max:
                    e_max = val
        
        tmp = yvals[-1] - e_min
        if abs(tmp) < 0.01:
            tmp = 0.0
        err_min.append(tmp)

        tmp = e_max - yvals[-1]
        if abs(tmp) < 0.01:
            tmp = 0.0
        err_max.append(tmp)
        
        if err_min[-1] < 0 or err_max[-1] < 0:
            print(data[i])
            print(yvals)
            print(e_min)
            print(err_min)
            print(e_max)
            print(err_max)
    
    y_error = [err_min, err_max]
    ax.grid(axis='y')
    ax.bar(lnames, yvals, color = 'b')
    ax.errorbar(lnames, yvals, yerr=y_error, fmt=".", color="r", markersize=0, capsize=5)

    plt.xlabel("Elasticity")
    plt.ylabel(y_label)
    plt.title(title)
    name = "%s%s.png" % (basename, title.replace(' ', '_').lower())
    plt.savefig(name, dpi=250)

    ofile = open("%s%s.csv" % (basename, title.replace(' ', '_').lower()), "w+")
    ofile.write("err_min,")
    for val in err_min:
        ofile.write(str(val) + ",")
    ofile.write("\n")

    ofile.write("err_max,")
    for val in err_max:
        ofile.write(str(val) + ",")
    ofile.write("\n")

    ofile.write("lnames,")
    for val in lnames:
        ofile.write(str(val) + ",")
    ofile.write("\n")

    ofile.write("yvals,")
    for val in yvals:
        ofile.write(str(val) + ",")
    ofile.write("\n")

tot_run_data  = []
avg_run_data  = []
tot_wait_data = []
avg_wait_data = []
util_data     = []
avg_tt_data   = []

for i in range(0, len(lnames)):
    tot_run  = []
    avg_run  = []
    tot_wait = []
    avg_wait = []
    util     = []
    avg_tt   = []

    j = 0
    while j < 5:
        if lnames[i] == "inelastic":
            fname = basename + "inelastic_stats.txt"
        else:
            fname = basename + str(j) + "_" + lnames[i] + "_stats.txt"
        with open(fname) as f:
            flag = ""
            for line in f:
                if "Run Time" in line:
                    flag = "Run"
                if "Wait Time" in line:
                    flag = "Wait"
                if "Elastic Time" in line:
                    flag = "Elastic"

                if flag == "Run" and "Total" in line:
                    line = line.split()
                    tot_run.append(float(line[1]))
                elif flag == "Run" and "Average" in line:
                    line = line.split()
                    avg_run.append(float(line[1]))
                elif flag == "Wait" and "Total" in line:
                    line = line.split()
                    tot_wait.append(float(line[1]))
                elif flag == "Wait" and "Average" in line:
                    line = line.split()
                    avg_wait.append(float(line[1]))
                elif flag == "Elastic" and "Average Utilization" in line:
                    line = line.split()
                    util.append(float(line[2].replace('%', '')))
        avg_tt.append(avg_wait[-1] + avg_run[-1])
        if lnames[i] == "inelastic":
            break
        j += 1
    tot_run_data.append(tot_run)
    avg_run_data.append(avg_run)
    tot_wait_data.append(tot_wait)
    avg_wait_data.append(avg_wait)
    util_data.append(util)
    avg_tt_data.append(avg_tt)    

plot_bar(avg_run_data, "Average Runtime by Elasticity", "Average Runtime (s)")
plot_bar(avg_wait_data, "Average Wait Time by Elasticity", "Average Wait Time (s)")
plot_bar(avg_tt_data, "Average Turnaround Time by Elasticity", "Average Turnaround Time (s)")
plot_bar(util_data, "Average Machine Utilization by Elasticity", "Average Machine Utilization Percentage")

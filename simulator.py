#!/usr/bin/env python3

import sys

if len(sys.argv) < 2:
    print("Usage: ./simulator.py [configure file]")
    print("*** See example.conf for how to create a configure file. ***")
    exit()

default_policy = "gsc"

import os
import random
import json

from sim_utilities import Job
from sim_utilities import JobQueue
from sim_utilities import PlotData

import time
from datetime import datetime

import cProfile

def get_file_list(directory):
    f_list = []
    for f in os.listdir(directory):
        if f.endswith(".csv"):
            f_list.append(directory + "/" + f)
    f_list.sort()
    return f_list

def get_jobs_from_files(file_list, percent_elastic, scaling_min, seed, node_mem, bw):
    sub_queue = JobQueue(-1, default_policy, '')

    node_breaks = [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]
    time_breaks = [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536]
    heatmap = []
    for i in range(0, len(time_breaks)):
        heatmap.append([])
        for j in range(0, len(node_breaks)):
            heatmap[-1].append(0)

    if seed < 0:
        seed = random.randrange(0, 1024)
    random.seed(seed)
    jid = 0

    for f in file_list:
        fptr = open(f, "r")

        line = fptr.readline()
        line = line.replace(',', '')
        line = line.replace('""', '"')
        line = line.split('"')

        t_idx = -1
        n_idx = -1
        for i in range(0, len(line)):
            if "Submit" in line[i]:
                s_idx = i
            if "Nodes Allocated" in line[i]:
                n_idx = i
            if "Elapsed Secs" in line[i]:
                t_idx = i
                
        line = fptr.readline()
        #jid = 0
        count = 0
        while line:
            line = line.replace(',', '')
            line = line.replace('""', '"')
            line = line.split('"')

            # Not enough information in this line to continue
            if len(line) < 3:
                break
            if line[n_idx] == '' or line[s_idx] == '' or line[t_idx] == '':
                break
            nodes  = float(line[n_idx])
            submit = line[s_idx]
            dur    = float(line[t_idx])
            
            time_offset = -1
            for i in range(0, len(time_breaks)):
                time_offset = i
                if dur <= time_breaks[i]:
                    break
            node_offset = -1
            for i in range(0, len(node_breaks)):
                node_offset = i
                if nodes <= node_breaks[i]:
                    break
            heatmap[time_offset][node_offset] += 1

            # Convert submit time string to timestamp
            submit = time.mktime(datetime.strptime(submit, "%Y-%m-%d %H:%M:%S").timetuple())
            if nodes > 0:
                if random.random() < percent_elastic:
                    job = Job(jid, nodes, 0, True)
                else:
                    job = Job(jid, nodes, 0, False)
                jid += 1
                job.timestamp = submit
                job.duration = dur
                job.init_duration = dur
                if job.is_elastic:
                    if scaling_min < 1.0:
                        job.scaling_factor = random.uniform(scaling_min, 1.0)
                    else:
                        job.scaling_factor = 1.0
                    # Determine overhead values
                    # 75% of jobs <25% of memory and 25% 25->50% (Assume 256GB mem and 20GB/s bandwidth)
                    #node_mem = 256.0 + 160.0
                    mem_midpoint = node_mem * 0.25
                    #bw = 20.0 * 4
                    num = random.uniform(0.0, 1.0)
                    gb = 0.0
                    if num < 0.75:
                        gb = random.uniform(0.01, 1.0) * mem_midpoint
                    else:
                        gb = (random.uniform(0.0, 1.0) * mem_midpoint) + mem_midpoint
                    t = gb / bw
                    job.grow_overhead = 0.5 * t
                    job.shrink_overhead = t
                    
                    sub_queue.elastic_push(job)
                else:
                    sub_queue.push(job)
                #jid += 1
            line = fptr.readline()
    ofile = open("job_heatmap.csv", "w+")
    for i in range(0, len(node_breaks)):
        ofile.write(",%d" % node_breaks[i])
    ofile.write("\n")
    for i in range(0, len(time_breaks)):
        ofile.write("%d" % time_breaks[i])
        for j in range(0, len(node_breaks)):
            ofile.write(",%d" % heatmap[i][j])
        ofile.write("\n")
        print(heatmap[i])

    # Sort the submitted jobs by their timestamps
    sub_queue.jobs = sorted(sub_queue.jobs, key=lambda x: x.timestamp)
    sub_queue.elastic_jobs = sorted(sub_queue.elastic_jobs, key=lambda x: x.timestamp)

    return sub_queue

def simulation(run_queue, sub_queue, tick, fname):
    complete_queue = JobQueue(run_queue.total_nodes, default_policy, '')
    wait_queue = JobQueue(-1, default_policy, '')

    if sub_queue.num_jobs <= 0:
        print("Didn't find any jobs in the submit queue.  Ending simulation...")
        return complete_queue
    # Determine initial timestamp
    init_timestamp = -1.0
    if sub_queue.num_normal_jobs > 0 and sub_queue.num_elastic_jobs > 0:
        init_timestamp = min(sub_queue.jobs[0].timestamp, sub_queue.elastic_jobs[0].timestamp)
    elif sub_queue.num_normal_jobs > 0:
        init_timestamp = sub_queue.jobs[0].timestamp
    else:
        init_timestamp = sub_queue.elastic_jobs[0].timestamp
    print("Initial Timestamp:")
    print(datetime.fromtimestamp(init_timestamp))

    wait_queue.timestamp_drain(sub_queue, init_timestamp, tick)
    
    # Initial Insertion
    run_queue.backfill(wait_queue, tick)
    print("Available Nodes: %.1f" % run_queue.available_nodes)
    print("Running Jobs:    %d" % run_queue.num_jobs)

    total_time = 0.0
    total_util = 0.0
    total_timesteps = 0
    timestamp = init_timestamp
    
    ofile = open(fname + "_output.csv", "w+")
    line = "Timestamp,Elapsed Seconds,Available Nodes,Running Nodes,Running Jobs,Waiting Jobs,Submission Queue Size\n"
    ofile.write(line)
    line = "%f,%f,%.1f,%d,%d,%d\n" % (timestamp, total_time, run_queue.available_nodes, run_queue.num_jobs, wait_queue.num_jobs, sub_queue.num_jobs)
    ofile.write(line)
    while run_queue.num_jobs > 0 or sub_queue.num_jobs > 0:
        wait_queue.increment_wait(tick)
        run_queue.progress_time(tick, complete_queue)
        
        total_time += tick
        timestamp  += tick

        to_print = False
        print_string = ""
        dt = datetime.fromtimestamp(timestamp)
        # Only print the first timestep of each hour
        if dt.minute == 0 and dt.second == 0:
            to_print = True
            
        print_string += "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n"
        print_string += "Submission Queue: %d\n" % sub_queue.num_jobs
        print_string += "Timestamp: %s (%s)\n" % (timestamp, dt)

        # Add any jobs that should now be submitted to the wait queue
        wait_queue.timestamp_drain(sub_queue, timestamp, tick)

        utilization = (float(run_queue.total_nodes-run_queue.available_nodes) / float(run_queue.total_nodes)) * 100.0
        total_util += utilization
        total_timesteps += 1
        
        print_string += "Total Nodes:     %.1f\n" % run_queue.total_nodes
        print_string += "Available Nodes: %.1f\n" % run_queue.available_nodes
        print_string += "Running Nodes:   %.1f\n" % (run_queue.total_nodes - run_queue.available_nodes)
        print_string += "Running Jobs:    %d\n" % run_queue.num_jobs
        print_string += "Waiting Jobs:    %d\n" % wait_queue.num_jobs
        print_string += "Utilization:     %.2f%%\n" % utilization
        if run_queue.num_jobs > (run_queue.total_nodes - run_queue.available_nodes):
            print("\n\n\n%d jobs and %.1f nodes... how?\n\n\n")
            for x in range(0, run_queue.num_elastic_jobs):
                run_queue.elastic_jobs[x].print_job()
            exit()

        line = "%f,%f,%.1f,%.1f,%d,%d,%d\n" % (timestamp, total_time, run_queue.available_nodes, run_queue.total_nodes - run_queue.available_nodes, run_queue.num_jobs, wait_queue.num_jobs, sub_queue.num_jobs)
        ofile.write(line)

        cutoff = 0.02
        if run_queue.dynamic:
            if run_queue.available_nodes / run_queue.total_nodes < cutoff and wait_queue.num_jobs > 0:
                run_queue.shrink_policy = "mp"
            else:
                run_queue.shrink_policy = "ip"
        n1 = run_queue.available_nodes
        run_queue.backfill(wait_queue, tick)

        cutoff = 0.10
        if run_queue.dynamic:
            if run_queue.available_nodes / run_queue.total_nodes > cutoff and wait_queue.num_jobs == 0:
                run_queue.elastic_policy = "a"
            else:
                run_queue.elastic_policy = "c"
        n2 = run_queue.available_nodes
        run_queue.elastic_grow()
        n3 = run_queue.available_nodes
        #if n1 < n2:
        #    print("%.1f -> %.1f -> %.1f" % (n1, n2, n3))
        
        # Ticks are in seconds
        days = int(total_time/86400)
        hours = (total_time - (days*86400)) / 3600.0
        # Only show two digits of hours
        print_string += "Elapsed Time:    %d Days, %.2f Hours\n" % (days, hours)
        print_string += "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n"
        
        # Print at only the desired frequency and for the last timestep
        if to_print or (run_queue.num_jobs == 0 and sub_queue.num_jobs == 0):
            print(print_string)
    ofile.close()
    avg_util = total_util / float(total_timesteps)
    return complete_queue, avg_util

def parse_conf(conf):
    infile_dir = "."
    outfile    = "simulator"
    ratio      = 0.0
    elastic_policy = "gsc"
    total_nodes = 1.0
    random_seed = 0
    tick_rate = 1
    scaling_min = 1.0
    grow_steps = 1
    node_mem = 256.0
    nic_bw = 20.0
    
    with open(conf, "r") as f:
        for line in f:
            line = line.split()
            if len(line) >= 2:
                if line[0] == '#':
                    continue
                elif line[0] == "input_file_dir":
                    infile_dir = line[1]
                elif line[0] == "output_prefix":
                    outfile = line[1]
                elif line[0] == "elastic_ratio":
                    ratio = float(line[1])
                elif line[0] == "elastic_policy":
                    elastic_policy = line[1]
                elif line[0] == "total_nodes":
                    total_nodes = float(line[1])
                elif line[0] == "random_seed":
                    random_seed = int(line[1])
                elif line[0] == "tick_rate":
                    tick_rate = float(line[1])
                elif line[0] == "scaling_min":
                    scaling_min = float(line[1])
                elif line[0] == "grow_steps":
                    grow_steps = int(line[1])
                elif line[0] == "node_memory":
                    node_mem = float(line[1])
                elif line[0] == "nic_bandwidth":
                    nic_bw = float(line[1])
                else:
                    continue
    return infile_dir, outfile, ratio, elastic_policy, total_nodes, random_seed, tick_rate, scaling_min, grow_steps, node_mem, nic_bw

infile_dir, fname, elastic_ratio, elastic_policy, num_nodes, seed, tick, scaling_min, grow_steps, node_mem, nic_bw = parse_conf(sys.argv[1])

file_list = get_file_list(infile_dir)
submit_queue = get_jobs_from_files(file_list, elastic_ratio, scaling_min, seed, node_mem, nic_bw)
run_queue  = JobQueue(num_nodes, elastic_policy, fname)
run_queue.grow_steps = grow_steps

# Profile the simulation to see where the time is spent
#cProfile.run('complete_queue, avg_util = simulation(run_queue, submit_queue, tick, fname)')
complete_queue, avg_util = simulation(run_queue, submit_queue, tick, fname)

# Plot the simulation
d = PlotData()
d.from_file(fname + "_output.csv")
d.plot([d], fname + ".png", ["simulation"])

###########################################
############ Gather Statistics ############
###########################################
total_wait = 0.0
total_run  = 0.0

num_modified  = 0
expected_time = 0.0
num_decrease  = 0
decrease_time = 0.0
num_increase  = 0
increase_time = 0.0
num_instant   = 0
instant_time  = 0.0

for i in range(0, complete_queue.num_normal_jobs):
    job = complete_queue.jobs[i]
    total_wait += job.wait_time
    total_run += job.run_time
    expected_time += job.init_duration

for i in range(0, complete_queue.num_elastic_jobs):
    job = complete_queue.elastic_jobs[i]
    
    total_wait += job.wait_time
    total_run += job.run_time

    expected_time += job.init_duration
    if job.run_time != job.init_duration:
        num_modified += 1
        if job.run_time < job.init_duration:
            num_decrease += 1
            decrease_time += job.init_duration - job.run_time
        else:
            num_increase += 1
            increase_time += job.run_time - job.init_duration

avg_wait = total_wait / float(complete_queue.num_jobs)
avg_run  = total_run / float(complete_queue.num_jobs)

percent_expected = (total_run/expected_time)*100.0

stats_string = ""
stats_string += ("##### Job Breakdown #####\n")
stats_string += "Total: %d\n" % (complete_queue.num_jobs)
stats_string += "Normal:  %d\n" % (complete_queue.num_normal_jobs)
stats_string += "Elastic: %d\n" % (complete_queue.num_elastic_jobs)
stats_string += ("##### Run Time #####\n")
stats_string += ("Total:   %.1f sec (%.2f%% expected)\n" % (total_run, percent_expected))
stats_string += ("Average: %.1f sec\n" % avg_run)
stats_string += ("##### Wait Time #####\n")
stats_string += ("Total:   %.1f sec\n" % total_wait)
stats_string += ("Average: %.1f sec\n" % avg_wait)
stats_string += ("##### Elastic Time #####\n")
stats_string += ("Num Modified: %d of %d\n" % (num_modified, complete_queue.num_elastic_jobs))
stats_string += ("Expected Time: %f sec\n" % expected_time)
stats_string += ("Increase Time: %f sec (%d jobs)\n" % (increase_time, num_increase))
stats_string += ("Decrease Time: %f sec (%d jobs)\n" % (decrease_time, num_decrease))
stats_string += ("Average Utilization: %.2f%%\n" % avg_util)
stats_string += ("##### Overhead Estimate #####\n")
stats_string += ("Num Resizes: %.2f\n" % (run_queue.resize_count))
stats_string += ("Num Grows:   %.2f\n" % (run_queue.grow_count))
stats_string += ("Num Shrinks: %.2f\n" % (run_queue.shrink_count))
stats_string += ("Average Resizes: %.2f\n" % (float(run_queue.resize_count) / float(complete_queue.num_elastic_jobs)))
stats_string += ("Nodes Resized: %.2f\n" % (run_queue.resize_nodes))
stats_string += ("Overhead Estimate: %.2f%%\n" % ( ((((run_queue.resize_count*0.5) + (run_queue.resize_nodes*0.1)) * 2.0) / (total_run+total_wait)) * 100.0 ))
stats_string += ("Ovherhead Added (actual): %.2f seconds\n" % run_queue.total_overhead)
stats_string += ("Overhead Percentage: %.2f%%\n" % ((run_queue.total_overhead / (total_run+total_wait))*100.0) )

print(stats_string)
ofile = open(fname + "_stats.txt", "w+")
ofile.write(stats_string)
ofile.close()














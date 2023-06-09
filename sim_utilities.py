import random
import json

class Job:
    def __init__(self, jid, nodes, hours, elastic):
        self.jid = jid
        self.nodes = nodes
        self.hours = hours
        self.wait_time = 0.0
        self.run_time = 0.0
        self.is_elastic = elastic
        self.cur_nodes = nodes
        self.timestamp = None
        self.duration = 0.0
        self.init_duration = 0.0
        self.scaling_factor = 1.0
    def print_job(self):
        # Assumption: Hours only have one decimal place
        print("[%d] Nodes: %d\tInit Duration: %.2f sec\tSubmit Timestamp: %s" % (self.jid, self.nodes, self.init_duration, self.timestamp))
        print("     Wait Time: %.2f sec\tRun Time: %.2f sec\tElastic: %s" % (self.wait_time, self.run_time, self.is_elastic))

# Assume that job ids are always increasing
class JobQueue:
    def __init__(self, total_nodes, policy):
        self.jobs = []
        self.elastic_jobs = []
        self.num_jobs = 0
        self.num_normal_jobs = 0
        self.num_elastic_jobs = 0
        self.total_nodes = total_nodes
        self.available_nodes = total_nodes
        self.max_jid = 0
        self.num_shrink = 0
        self.num_grow = 0
        self.grow_steps = 1
        self.wait_count = 0

        if "g" in policy:
            self.allow_grow = True
        else:
            self.allow_grow = False
        if "s" in policy:
            self.allow_shrink = True
        else:
            self.allow_shrink = False
        if "a" in policy:
            self.elastic_policy = "a"
        else:
            self.elastic_policy = "c"
        if "m" in policy:
            if "p" in policy:
                self.shrink_policy = "mp"
            else:
                self.shrink_policy = "m"
        else:
            if "p" in policy:
                self.shrink_policy = "ip"
            else:
                self.shrink_policy = "i"

    def push(self, job):
        self.jobs.append(job)
        self.num_jobs += 1
        self.num_normal_jobs += 1
        self.available_nodes -= job.nodes
        self.max_jid = job.jid
    def elastic_push(self, job):
        self.elastic_jobs.append(job)
        self.num_jobs += 1
        self.num_elastic_jobs += 1
        self.available_nodes -= job.cur_nodes
        self.max_jid = job.jid
        if job.cur_nodes < job.nodes:
            self.num_shrink += 1
        if job.cur_nodes > job.nodes:
            self.num_grow += 1
    def pop(self, index):
        job = self.jobs.pop(index)
        self.num_jobs -= 1
        self.num_normal_jobs -= 1
        self.available_nodes += job.nodes
        return job
    def elastic_pop(self, index):
        job = self.elastic_jobs.pop(index)
        self.num_jobs -= 1
        self.num_elastic_jobs -= 1
        self.available_nodes += job.cur_nodes
        if job.cur_nodes < job.nodes:
            self.num_shrink -= 1
        if job.cur_nodes > job.nodes:
            self.num_grow -= 1
        return job
    # Assumption: We only grow one job at a time
    def elastic_grow(self):
        grew = False
        if self.available_nodes == 0:
            return grew
        # We've already grown all of the jobs
        #if self.num_grow == self.num_elastic_jobs:
        #    return grew
        for i in range(0, self.num_elastic_jobs):
            job = self.elastic_jobs[i]
            # This job has either been shrunk or hasn't grown
            #if job.cur_nodes <= job.nodes and self.available_nodes >= job.cur_nodes * 2:
            if job.cur_nodes <= (job.nodes * (2**(self.grow_steps-1))) and self.available_nodes >= job.cur_nodes * 2:
                # The policy is to not grow larger than the original size
                if job.cur_nodes == job.nodes and not self.allow_grow:
                    continue
                temp = job
                # Remove from the queue and re-add it so we have a least-recently-updated
                # pattern for re-sizing jobs.
                self.elastic_pop(i)
                temp.cur_nodes *= 2
                self.elastic_push(temp)
                grew = True

                if self.elastic_policy == "c":
                    # This makes it so we grow exactly one job
                    return grew
                elif self.elastic_policy == "a":
                    # This makes it so we grow as many jobs as we can
                    continue
        return grew
    def individual_elastic_shrink(self):
        # We've already shrunk all of the elastic jobs
        if self.num_shrink == self.num_elastic_jobs:
            return False
        for i in range(0, self.num_elastic_jobs):
            job = self.elastic_jobs[i]
            # Take the first job with increased number of nodes because this is the
            # least-recently-updated job in the elastic job queue
            # Allow shrinking below the normal job size and take the first element
            # the queue that isn't already shrunk down.
            if job.cur_nodes >= job.nodes:
                # Check if the policy is to not shrink smaller than the original size
                if job.cur_nodes == job.nodes and not self.allow_shrink:
                    continue
                temp = job
                self.elastic_pop(i)
                temp.cur_nodes /= 2
                self.elastic_push(temp)
                # This makes it so we shrink exactly one job
                return True
        return False
    def individual_elastic_shrink_priority(self):
        # We've already shrunk all of the elastic jobs
        if self.num_shrink == self.num_elastic_jobs:
            return False
        for i in range(0, self.num_elastic_jobs):
            job = self.elastic_jobs[i]
            # Take the first job with increased number of nodes because this is the
            # least-recently-updated job in the elastic job queue
            # Allow shrinking below the normal job size and take the first element
            # the queue that isn't already shrunk down.
            if job.cur_nodes > job.nodes:
                # Check if the policy is to not shrink smaller than the original size
                if job.cur_nodes == job.nodes and not self.allow_shrink:
                    continue
                temp = job
                self.elastic_pop(i)
                temp.cur_nodes /= 2
                self.elastic_push(temp)
                # This makes it so we shrink exactly one job
                return True
        # Check if the policy is to not shrink smaller than the original size
        if not self.allow_shrink:
            return False
        for i in range(0, self.num_elastic_jobs):
            job = self.elastic_jobs[i]
            # Take the first job with increased number of nodes because this is the
            # least-recently-updated job in the elastic job queue
            # Allow shrinking below the normal job size and take the first element
            # the queue that isn't already shrunk down.
            if job.cur_nodes == job.nodes:
                temp = job
                self.elastic_pop(i)
                temp.cur_nodes /= 2
                self.elastic_push(temp)
                # This makes it so we shrink exactly one job
                return True
        return False
    def multiple_elastic_shrink(self, nodes_needed):
        # We've already shrunk all of the elastic jobs
        if self.num_shrink == self.num_elastic_jobs:
            return False
        marked = []
        nodes_freed = 0
        num_marked = 0
        for i in range(0, self.num_elastic_jobs):
            job = self.elastic_jobs[i]
            # Take the first job with increased number of nodes because this is the
            # least-recently-updated job in the elastic job queue
            # Allow shrinking below the normal job size and take the first element
            # the queue that isn't already shrunk down.
            if job.cur_nodes >= job.nodes:
                # Check if the policy is to not shrink smaller than the original size
                if job.cur_nodes == job.nodes and not self.allow_shrink:
                    continue
                marked.append(i)
                num_marked += 1
                nodes_freed += job.cur_nodes / 2
                # This makes it so we continue to shrink until we have the number
                # of nodes needed or we have completed one full pass through the
                # elastic 
                if self.available_nodes - nodes_freed >= nodes_needed:
                    break
        if nodes_freed > 0:
            i = 0
            j = marked[i]
            while True:
                temp = self.elastic_jobs[j]
                self.elastic_pop(j)
                temp.cur_nodes /= 2
                self.elastic_push(temp)

                i += 1
                if i == num_marked:
                    break
                # Since we popped an element from the queue, all of the marked
                # indices need to decrease by 1
                for k in range(i, num_marked):
                    marked[k] -= 1
                j = marked[i]
        return False
    def multiple_elastic_shrink_priority(self, nodes_needed):
        # We've already shrunk all of the elastic jobs
        if self.num_shrink == self.num_elastic_jobs:
            return False
        marked = []
        nodes_freed = 0
        num_marked = 0
        for i in range(0, self.num_elastic_jobs):
            job = self.elastic_jobs[i]
            # Take the first job with increased number of nodes because this is the
            # least-recently-updated job in the elastic job queue
            # Allow shrinking below the normal job size and take the first element
            # the queue that isn't already shrunk down.
            if job.cur_nodes > job.nodes:
                # Check if the policy is to not shrink smaller than the original size
                if job.cur_nodes == job.nodes and not self.allow_shrink:
                    continue
                marked.append(i)
                num_marked += 1
                nodes_freed += job.cur_nodes / 2
                # This makes it so we continue to shrink until we have the number
                # of nodes needed or we have completed one full pass through the
                # elastic 
                if self.available_nodes - nodes_freed >= nodes_needed:
                    break

        for i in range(0, self.num_elastic_jobs):
            # Check if the policy is to not shrink smaller than the original size
            if not self.allow_shrink:
                break
            job = self.elastic_jobs[i]
            # Take the first job with increased number of nodes because this is the
            # least-recently-updated job in the elastic job queue
            # Allow shrinking below the normal job size and take the first element
            # the queue that isn't already shrunk down.
            if job.cur_nodes == job.nodes:
                marked.append(i)
                num_marked += 1
                nodes_freed += job.cur_nodes / 2
                # This makes it so we continue to shrink until we have the number
                # of nodes needed or we have completed one full pass through the
                # elastic 
                if self.available_nodes - nodes_freed >= nodes_needed:
                    break
        if nodes_freed > 0:
            i = 0
            j = marked[i]
            while True:
                temp = self.elastic_jobs[j]
                self.elastic_pop(j)
                temp.cur_nodes /= 2
                self.elastic_push(temp)

                i += 1
                if i == num_marked:
                    break
                # Since we popped an element from the queue, all of the marked
                # indices need to decrease by 1
                for k in range(i, num_marked):
                    marked[k] -= 1
                j = marked[i]
        return False
    def next_jid(self):
        return self.max_jid + 1
    def backfill(self, queue, tick):
        inserted = False
        # No jobs to search for in the wait queue
        if queue.num_jobs == 0:
            return inserted
        
        if "i" in self.shrink_policy:
            # No available nodes to insert a job
            if self.available_nodes == 0:
                # Attempt to shrink one of our elastic jobs
                if "p" in self.shrink_policy:
                    self.individual_elastic_shrink_priority()
                else:
                    self.individual_elastic_shrink()
                if self.available_nodes == 0:
                    return inserted
        else:
            nodes_needed = 0
            if queue.num_normal_jobs > 0:
                nodes_needed += queue.jobs[0].cur_nodes
            if queue.num_elastic_jobs > 0:
                nodes_needed += queue.elastic_jobs[0].cur_nodes
            if nodes_needed > 0:
                if "p" in self.shrink_policy:
                    self.multiple_elastic_shrink_priority(nodes_needed)
                else:
                    self.multiple_elastic_shrink(nodes_needed)
        
        # Attempt to find a valid job in the wait queue(s) to insert
        i = 0 # Normal job queue index
        j = 0 # Elastic job queue index
        # Seek through normal jobs until there is a viable job
        for k in range(i, queue.num_normal_jobs):
            if queue.jobs[k].cur_nodes <= self.available_nodes:
                break
            i += 1
        # Seek through elastic jobs until there is a viable job
        for k in range(j, queue.num_elastic_jobs):
            if queue.elastic_jobs[k].cur_nodes <= self.available_nodes:
                break
            j += 1
        # Need to have at least some jobs left in either the normal
        # or elastic job queues to look through.
        while i < queue.num_normal_jobs or j < queue.num_elastic_jobs:
            # If we have jobs in both queues, we choose the next job
            # with the longest wait time between the two queues. This
            # ensures that we search through the two queues as if they
            # are one combined queue
            if self.available_nodes == 0:
                break
            job = None
            if i < queue.num_normal_jobs and j < queue.num_elastic_jobs:
                if queue.jobs[i].wait_time > queue.elastic_jobs[j].wait_time:
                    job = queue.jobs[i]
                elif queue.jobs[i].wait_time < queue.elastic_jobs[j].wait_time:
                    job = queue.elastic_jobs[j]
                else:
                    if queue.jobs[i].timestamp < queue.elastic_jobs[j].timestamp:
                        job = queue.jobs[i]
                    else:
                        job = queue.elastic_jobs[j]
            elif i < queue.num_normal_jobs:
                job = queue.jobs[i]
            else:
                job = queue.elastic_jobs[j]
            N = job.cur_nodes
            if N <= self.available_nodes:
                if job.is_elastic:
                    # We are about to remove a job from the wait queue, so
                    # we need to make sure the wait times are updated
                    if queue.wait_count != 0:
                        queue.progress_wait(tick)
                    self.elastic_push(queue.elastic_pop(j))
                    inserted = True
                else:
                    # We are about to remove a job from the wait queue, so
                    # we need to make sure the wait times are updated
                    if queue.wait_count != 0:
                        queue.progress_wait(tick)
                    self.push(queue.pop(i))
                    inserted = True
            if job.is_elastic:
                j += 1
            else:
                i += 1
        # Couldn't find valid job
        return inserted
    def timestamp_drain(self, queue, timestamp, tick):
        inserted = False
        # First drain normal jobs
        i = 0
        while i < queue.num_normal_jobs:
            if queue.jobs[i].timestamp <= timestamp:
                # We are about to add something to the wait queue,
                # so we need to make sure the wait times are updated
                if self.wait_count != 0:
                    self.progress_wait(tick)
                self.push(queue.pop(i))
                inserted = True
            else:
                break
        # Next drain elastic jobs
        while i < queue.num_elastic_jobs:
            if queue.elastic_jobs[i].timestamp <= timestamp:
                # We are about to add something to the wait queue,
                # so we need to make sure the wait times are updated
                if self.wait_count != 0:
                    self.progress_wait(tick)
                inserted = True
                self.elastic_push(queue.elastic_pop(i))
            else:
                break
        return inserted
    def progress_time(self, tick, complete_queue):
        i = 0
        while i < self.num_normal_jobs:
            self.jobs[i].duration -= tick
            self.jobs[i].run_time += tick

            if self.jobs[i].duration <= 0.0:
                complete_queue.push(self.pop(i))
                continue
            i += 1

        i = 0
        while i < self.num_elastic_jobs:
            # Assumption: There is perfect scaling for grown/shrunk jobs
            # Assumption: Jobs only grow by exactly double or half of their
            #             requested node count
            if self.elastic_jobs[i].cur_nodes < self.elastic_jobs[i].nodes:
                self.elastic_jobs[i].duration -= tick / (2.0 * self.elastic_jobs[i].scaling_factor)
            elif self.elastic_jobs[i].cur_nodes > self.elastic_jobs[i].nodes:
                multiplier = float(self.elastic_jobs[i].cur_nodes / self.elastic_jobs[i].nodes)
                self.elastic_jobs[i].duration -= tick * (multiplier * self.elastic_jobs[i].scaling_factor)
            else:
                self.elastic_jobs[i].duration -= tick
            #modifier = float(self.elastic_jobs[i].cur_nodes) / float(self.elastic_jobs[i].nodes)
            #self.elastic_jobs[i].duration -= tick * modifier
            self.elastic_jobs[i].run_time += tick

            if self.elastic_jobs[i].duration <= 0.0:
                complete_queue.elastic_push(self.elastic_pop(i))
                continue
            i += 1
    def increment_wait(self, tick):
        self.wait_count += tick
    def progress_wait(self, tick):
        for i in range(0, self.num_normal_jobs):
            self.jobs[i].wait_time += self.wait_count
        for i in range(0, self.num_elastic_jobs):
            self.elastic_jobs[i].wait_time += self.wait_count
        self.wait_count = 0
    def print_jobs(self):
        print("Normal Jobs:")
        if self.num_normal_jobs > 6:
            self.jobs[0].print_job()
            self.jobs[1].print_job()
            self.jobs[2].print_job()
            print("...")
            self.jobs[-3].print_job()
            self.jobs[-2].print_job()
            self.jobs[-1].print_job()
        else:
            for job in self.jobs:
                job.print_job()
        print("Elastic Jobs:")
        if self.num_elastic_jobs > 6:
            self.elastic_jobs[0].print_job()
            self.elastic_jobs[1].print_job()
            self.elastic_jobs[2].print_job()
            print("...")
            self.elastic_jobs[-3].print_job()
            self.elastic_jobs[-2].print_job()
            self.elastic_jobs[-1].print_job()
        else:
            for job in self.elastic_jobs:
                job.print_job()
    def append_from_json(self, json_file, jid_start):
        data = json.load(json_file)
        jobs_table = data['jobs']
        jid = jid_start
        local_jobs = []

        for entry in jobs_table:
            hours = entry[0]
            nodes = entry[1]
            if hours < 1:
                hours = 0.5
            for i in range(0, entry[-1]):
                job = Job(jid, nodes, hours)
                jid += 1
                local_jobs.append(job)
        random.shuffle(local_jobs)
        for job in local_jobs:
            self.push(job)
    
import matplotlib.pyplot as plt

class PlotData:
    def __init__(self):
        self.x_data = []
        self.y_data = []
        self.num_points = 0
        self.ceiling = -1
    def from_file(self, fname):
        f = open(fname, "r")

        headers = f.readline()
        headers = headers.split(",")

        a_idx = -1
        r_idx = -1
        for i in range(0, len(headers)):
            if headers[i] == "Available Nodes":
                a_idx = i
            if headers[i] == "Running Nodes":
                r_idx = i
            if a_idx >= 0 and r_idx >= 0:
                break

        if a_idx < 0 or r_idx < 0:
            print("Invalid input file.  Must contain columns \"Available Nodes\" and \"Running Nodes\".")
            return False

        xval = 0
        line = f.readline().split(",")
        if line:
            self.ceiling = int(line[a_idx]) + int(line[r_idx])
        else:
            print("Empty input file...")
            return False
        while len(line) > 1:
            yval = int(line[r_idx])
            
            self.x_data.append(xval)
            self.y_data.append(yval)
            self.num_points += 1

            xval += 1
            line = f.readline().split(",")
        return True
    def plot(self, data, filename, line_labels):
        plt.rcParams.update({'font.size': 22})
        plt.rcParams.update({'axes.labelsize' : 22})
        max_points = data[0].num_points
        for i in range(1, len(data)):
            if data[i].num_points > max_points:
                max_points = data[i].num_points
        fig = plt.figure(figsize=(16,9))
        ax  = plt.subplot(111)

        #plt.title('Simulated Running Nodes Over Time')
        plt.xlabel('Simulation Time (seconds)')
        plt.ylabel('Number of Nodes in Use')

        colors = ['b', 'r', 'g', 'c', 'm', 'y', 'darkviolet']
        for i in range(0, len(data)):
            ax.plot(data[i].y_data, linestyle='-', linewidth=0.5, marker='.', markersize=1, color=colors[i], label=line_labels[i])
        ax.plot([0,max_points], [data[0].ceiling, data[0].ceiling], linestyle='-', color='k', label='Max Nodes')

        box = ax.get_position()
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1),
                  fancybox=True, shadow=True, ncol=5)

        plt.savefig(filename, dpi=250, bbox_inches='tight')
        return True        

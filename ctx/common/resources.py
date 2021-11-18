import resource
import re
import time
import platform


def get_rlimit_nofile():
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    return {"soft": soft, "hard": hard}


def get_platform_info():
    try:
        uname = platform.uname()
        platform_info = {
            "system": uname.system,
            "version": uname.version,
            "release": uname.release,
            "machine": uname.machine,
            "processor": uname.processor
        }
    except:
        platform_info = {}
    try:
        with open('/proc/cpuinfo') as f:
            cpu_count = 0
            model = None
            for line in f:
                # Ignore the blank line separating the information between
                # details about two processing units
                if line.strip():
                    if line.rstrip('\n').startswith('model name'):
                        model_name = line.rstrip('\n').split(':')[1]
                        model = model_name
                        model = model.strip()
                        cpu_count += 1
            platform_info['model'] = model
            platform_info['cores'] = cpu_count
    except Exception as e:
        print(e)
    return platform_info


def get_cpu_load():
    with open('/proc/loadavg') as f:
        cpu_load = f.read()
        cpu_load_result = cpu_load.split(" ")
        return {
            "1min": cpu_load_result[0],
            "5min": cpu_load_result[1],
            "15min": cpu_load_result[2],
        }


def get_mem_info():
    with open('/proc/meminfo') as f:
        meminfo = f.read()
        matched = re.search(r'^MemTotal:\s+(\d+)', meminfo)
        if matched:
            mem_total_kb = int(matched.groups()[0])
            mem_total_mb = int(mem_total_kb / 1024)
            return mem_total_mb


def get_cpu_time():
    cpu_infos = {}
    with open('/proc/stat', 'r') as file_stat:
        cpu_lines = []
        for lines in file_stat.readlines():
            for line in lines.split('\n'):
                if line.startswith('cpu'):
                    cpu_lines.append(line.split(' '))
        for cpu_line in cpu_lines:
            if '' in cpu_line:
                cpu_line.remove('')  # First row(cpu) exist '' and Remove ''
            cpu_id = cpu_line[0]
            cpu_line = [float(item) for item in cpu_line[1:]]
            user, nice, system, idle, iowait, irq, softirq, steal, guest, guest_nice = cpu_line

            idle_time = idle + iowait
            non_idle_time = user + nice + system + irq + softirq + steal
            total = idle_time + non_idle_time

            cpu_infos.update({cpu_id: {'total': total, 'idle': idle_time}})
    return cpu_infos


def get_cpu_usage_percentage():
    start = get_cpu_time()
    time.sleep(1)
    end = get_cpu_time()

    cpu_usages = {}
    for cpu in start:
        diff_total = end[cpu]['total'] - start[cpu]['total']
        diff_idle = end[cpu]['idle'] - start[cpu]['idle']
        # diff_iowait = end[cpu]['iowait'] - start[cpu]['iowait']
        cpu_usage_percentage = (diff_total - diff_idle) / diff_total * 100
        cpu_usages.update({cpu: round(cpu_usage_percentage, 2)})
    return cpu_usages

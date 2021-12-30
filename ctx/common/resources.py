import resource
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


def get_mem_info(unit="GB"):
    """
    Read in the /proc/meminfo and return a dictionary of the memory and swap
    usage for all processes.
    """

    if unit == "MB":
        convert_unit = 1000
    elif unit == "GB":
        convert_unit = 1000 * 1000
    else:
        convert_unit = 1
        unit = "KB"

    data = {'mem_total': 0, 'mem_used': 0, 'mem_free': 0,
            'swap_total': 0, 'swap_used': 0, 'swap_free': 0,
            'buffers': 0, 'cached': 0}

    with open('/proc/meminfo', 'r') as fh:
        lines = fh.read()
        fh.close()

        for line in lines.split('\n'):
            fields = line.split(None, 2)
            if fields[0] == 'MemTotal:':
                data['mem_total'] = int(fields[1], 10)
            elif fields[0] == 'MemFree:':
                data['mem_free'] = int(fields[1], 10)
            elif fields[0] == 'Buffers:':
                data['buffers'] = int(fields[1], 10)
            elif fields[0] == 'Cached:':
                data['cached'] = int(fields[1], 10)
            elif fields[0] == 'SwapTotal:':
                data['swap_total'] = int(fields[1], 10)
            elif fields[0] == 'SwapFree:':
                data['swap_free'] = int(fields[1], 10)
                break
        data['mem_used'] = data['mem_total'] - data['mem_free']
        data['swap_used'] = data['swap_total'] - data['swap_free']

        for k, v in data.items():
            if isinstance(v, int):
                data[k] = round(v / convert_unit, 2)
        data['unit'] = unit

    return data


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

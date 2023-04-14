import psutil
from PerformanceMonitoring.process_data import ProcessData


def get_processes(vpn_exe_name, vpn_alt_exe_name=None):
    # Iterate over all running process
    for proc in psutil.process_iter():
        try:
            # Grab the cpu percent utilization and memory utilization of the current process
            cur_cpu_percent = round(proc.cpu_percent(interval=None) / psutil.cpu_count(), 8)
            cur_mem_percent = round(proc.memory_percent(), 8)
            if proc.name() == vpn_exe_name or proc.name() == vpn_alt_exe_name:
                # Get process name, pid, cpu percent, memory percent, and priority.
                process_name = proc.name()
                process_cpu = cur_cpu_percent
                process_memory = cur_mem_percent

                # Store into temp object to be added to dictionary of current iteration.
                temp = ProcessData(process_name, process_cpu, process_memory)
                return temp

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None

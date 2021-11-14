"""This was based on the following
https://www.thepythoncode.com/article/get-hardware-system-information-python
"""
import psutil
import platform
from datetime import datetime

def sysinfo():
    """ will use the uname to retirneve the system info
    
    Parameters
    ----------
    None

    Returns
    -------
    data: dict
    """
    uname = platform.uname()
    return {
        "system": uname.system,
        "node": uname.node,
        "release": uname.release,
        "version": uname.version,
        "machine": uname.machine,
        "processor": uname.processor
    }

def boottime():
    """ return the time the system was last boottime
    
    Parameters
    ----------
    None

    Returns
    -------
    data: dict
    """
    boot_time_timestamp = psutil.boot_time()
    
    return {
        "boottime": datetime.fromtimestamp(boot_time_timestamp).strftime("%Y/%m/%d %H:%M:%S")
    }

def cpuinfo():
    """ return the time the system was last boottime
    
    Parameters
    ----------
    None

    Returns
    -------
    data: dict
    """
    cpufreq = psutil.cpu_freq()

    cores = []
    for i, percentage in enumerate(psutil.cpu_percent(percpu=True, interval=1)):
        cores.append({
            "core": i,
            "percentage": percentage
        })

    return {
        "porcessors":{
            "physical": psutil.cpu_count(logical=False),
            "logical": psutil.cpu_count(logical=True)
        },
        "frequency": {
            "max": cpufreq.max,
            "min": cpufreq.min,
            "current": cpufreq.current,
            "cores": cores
        }
    }

def meminfo():
    """ return the time the system was last boottime
    
    Parameters
    ----------
    None

    Returns
    -------
    data: dict
    """
    virtmem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        "virtual":{
            "total": virtmem.total,
            "available": virtmem.available,
            "used": virtmem.used,
            "percent": virtmem.percent
        },
        "swap":{
            "total": swap.total,
            "free": swap.free,
            "used": swap.used,
            "percent": swap.percent
        }
    }

def diskinfo():
    """ return the time the system was last boottime
    
    Parameters
    ----------
    None

    Returns
    -------
    data: dict
    """
    data = dict

    return data

def networkinfo():
    """ return the time the system was last boottime
    
    Parameters
    ----------
    None

    Returns
    -------
    data: dict
    """
    data = dict

    return data

def gpuinfo():
    """ return the time the system was last boottime
    
    Parameters
    ----------
    None

    Returns
    -------
    data: dict
    """
    data = dict

    return data


if __name__ == "__main__":
    print(sysinfo())
    print(boottime())  
    print(cpuinfo())
    print(meminfo())
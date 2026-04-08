# sk_plugins_system.py
# =====================
# System Health Monitoring Plugin
# Requires: pip install psutil

import os
from typing import Annotated
from semantic_kernel.functions import kernel_function


# ============================================
# System Plugin - PC Health Monitoring
# ============================================

class SystemPlugin:
    """
    Monitor system health - CPU, RAM, Battery, Disk.
    Uses psutil for cross-platform metrics.
    """
    
    @kernel_function(
        name="system_status",
        description="Get PC health status - CPU, RAM, Battery. Use when user asks 'how is my PC?' or 'system status'"
    )
    def get_status(self) -> str:
        """Get full system status."""
        try:
            import psutil
            
            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.5)
            cpu_count = psutil.cpu_count()
            
            # RAM
            ram = psutil.virtual_memory()
            ram_used_gb = ram.used / (1024 ** 3)
            ram_total_gb = ram.total / (1024 ** 3)
            ram_percent = ram.percent
            
            # Battery
            battery = psutil.sensors_battery()
            if battery:
                bat_percent = battery.percent
                bat_plugged = "Charging" if battery.power_plugged else "On Battery"
            else:
                bat_percent = "N/A"
                bat_plugged = "No battery"
            
            # Disk
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free_gb = disk.free / (1024 ** 3)
            
            status = "System Status:\n"
            status += "- CPU: {:.1f}% ({} cores)\n".format(cpu_percent, cpu_count)
            status += "- RAM: {:.1f}/{:.1f} GB ({:.0f}%)\n".format(ram_used_gb, ram_total_gb, ram_percent)
            if battery:
                status += "- Battery: {}% ({})\n".format(int(bat_percent), bat_plugged)
            status += "- Disk: {:.0f}% used ({:.1f} GB free)".format(disk_percent, disk_free_gb)
            
            return status
            
        except ImportError:
            return "psutil not installed. Run: pip install psutil"
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="cpu_usage",
        description="Get CPU usage percentage"
    )
    def get_cpu(self) -> str:
        """Get CPU usage."""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.5)
            return "CPU usage: {:.1f}%".format(cpu)
        except ImportError:
            return "psutil not installed"
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="ram_usage",
        description="Get RAM/memory usage"
    )
    def get_ram(self) -> str:
        """Get RAM usage."""
        try:
            import psutil
            ram = psutil.virtual_memory()
            used = ram.used / (1024 ** 3)
            total = ram.total / (1024 ** 3)
            return "RAM: {:.1f}/{:.1f} GB ({:.0f}% used)".format(used, total, ram.percent)
        except ImportError:
            return "psutil not installed"
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="battery_status",
        description="Get battery level and charging status"
    )
    def get_battery(self) -> str:
        """Get battery status."""
        try:
            import psutil
            battery = psutil.sensors_battery()
            
            if battery is None:
                return "No battery detected (desktop PC?)"
            
            percent = battery.percent
            plugged = "Charging" if battery.power_plugged else "On Battery"
            
            if battery.secsleft > 0 and not battery.power_plugged:
                hours = battery.secsleft // 3600
                mins = (battery.secsleft % 3600) // 60
                time_left = " ({} hr {} min remaining)".format(hours, mins)
            else:
                time_left = ""
            
            return "Battery: {}% - {}{}".format(int(percent), plugged, time_left)
            
        except ImportError:
            return "psutil not installed"
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="disk_usage",
        description="Get disk space usage"
    )
    def get_disk(self) -> str:
        """Get disk usage."""
        try:
            import psutil
            disk = psutil.disk_usage('/')
            used = disk.used / (1024 ** 3)
            total = disk.total / (1024 ** 3)
            free = disk.free / (1024 ** 3)
            return "Disk: {:.0f}/{:.0f} GB used ({:.1f} GB free)".format(used, total, free)
        except ImportError:
            return "psutil not installed"
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="running_processes",
        description="List top 5 processes by memory usage"
    )
    def get_top_processes(self) -> str:
        """Get top memory-consuming processes."""
        try:
            import psutil
            
            processes = []
            for proc in psutil.process_iter(['name', 'memory_percent']):
                try:
                    processes.append({
                        'name': proc.info['name'],
                        'memory': proc.info['memory_percent']
                    })
                except:
                    pass
            
            # Sort by memory
            processes.sort(key=lambda x: x['memory'], reverse=True)
            top5 = processes[:5]
            
            result = "Top processes by RAM:\n"
            for p in top5:
                result += "- {}: {:.1f}%\n".format(p['name'], p['memory'])
            
            return result
            
        except ImportError:
            return "psutil not installed"
        except Exception as e:
            return "Error: " + str(e)


# ============================================
# Export
# ============================================

SYSTEM_PLUGINS = [
    SystemPlugin,
]

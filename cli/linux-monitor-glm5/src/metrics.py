"""
Core metrics collection module for Linux system resources.
Uses psutil to gather CPU, RAM, Swap, Load Average, and Network statistics.
"""

import psutil
import time
from dataclasses import dataclass
from typing import Tuple, Optional


@dataclass
class CPUMetrics:
    """CPU usage metrics."""
    percent: float
    per_core: list[float]
    freq_current: float  # MHz
    freq_max: float      # MHz


@dataclass
class MemoryMetrics:
    """Memory (RAM) metrics."""
    total_gb: float
    used_gb: float
    available_gb: float
    percent: float


@dataclass
class SwapMetrics:
    """Swap memory metrics."""
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float


@dataclass
class LoadAvgMetrics:
    """Load average metrics."""
    load_1: float
    load_5: float
    load_15: float
    process_count: int
    running_processes: int


@dataclass
class NetworkMetrics:
    """Network throughput metrics in Mbps."""
    download_mbps: float
    upload_mbps: float
    total_dl_gb: float
    total_up_gb: float


@dataclass
class SystemMetrics:
    """Complete system metrics container."""
    cpu: CPUMetrics
    memory: MemoryMetrics
    swap: SwapMetrics
    load_avg: LoadAvgMetrics
    network: NetworkMetrics
    uptime_seconds: int
    timestamp: float


class MetricsCollector:
    """
    Collects system metrics using psutil.
    Tracks network throughput by measuring delta between samples.
    """
    
    def __init__(self):
        self._last_net_io = None
        self._last_net_time = None
        self._interval = 1.0  # Default interval for Mbps calculation
    
    def _bytes_to_gb(self, bytes_val: int) -> float:
        """Convert bytes to gigabytes (power of 1024)."""
        return bytes_val / (1024 ** 3)
    
    def _bytes_to_mb(self, bytes_val: int) -> float:
        """Convert bytes to megabytes (power of 1024)."""
        return bytes_val / (1024 ** 2)
    
    def get_cpu_metrics(self, interval: float = 0.1) -> CPUMetrics:
        """
        Get CPU usage metrics.
        
        Args:
            interval: Time interval for CPU percent calculation
            
        Returns:
            CPUMetrics dataclass with CPU statistics
        """
        percent = psutil.cpu_percent(interval=interval)
        per_core = psutil.cpu_percent(interval=interval, percpu=True)
        
        freq = psutil.cpu_freq()
        freq_current = freq.current if freq else 0.0
        freq_max = freq.max if freq else 0.0
        
        return CPUMetrics(
            percent=percent,
            per_core=per_core,
            freq_current=freq_current,
            freq_max=freq_max
        )
    
    def get_memory_metrics(self) -> MemoryMetrics:
        """
        Get RAM usage metrics.
        
        Returns:
            MemoryMetrics dataclass with memory statistics
        """
        mem = psutil.virtual_memory()
        
        return MemoryMetrics(
            total_gb=self._bytes_to_gb(mem.total),
            used_gb=self._bytes_to_gb(mem.used),
            available_gb=self._bytes_to_gb(mem.available),
            percent=mem.percent
        )
    
    def get_swap_metrics(self) -> SwapMetrics:
        """
        Get swap memory metrics.
        
        Returns:
            SwapMetrics dataclass with swap statistics
        """
        swap = psutil.swap_memory()
        
        return SwapMetrics(
            total_gb=self._bytes_to_gb(swap.total),
            used_gb=self._bytes_to_gb(swap.used),
            free_gb=self._bytes_to_gb(swap.free),
            percent=swap.percent
        )
    
    def get_loadavg_metrics(self) -> LoadAvgMetrics:
        """
        Get system load average and process information.
        
        Returns:
            LoadAvgMetrics dataclass with load average statistics
        """
        load_1, load_5, load_15 = psutil.getloadavg()
        
        try:
            process_count = len(psutil.pids())
            # Count running processes
            running = 0
            for pid in psutil.process_iter(['status']):
                try:
                    if pid.info['status'] == psutil.STATUS_RUNNING:
                        running += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            process_count = 0
            running = 0
        
        return LoadAvgMetrics(
            load_1=load_1,
            load_5=load_5,
            load_15=load_15,
            process_count=process_count,
            running_processes=running
        )
    
    def get_network_metrics(self) -> NetworkMetrics:
        """
        Get network throughput metrics.
        Calculates Mbps based on delta from last measurement.
        
        Returns:
            NetworkMetrics dataclass with throughput in Mbps
        """
        current_io = psutil.net_io_counters()
        current_time = time.time()
        
        # Calculate throughput if we have previous measurements
        if self._last_net_io is not None and self._last_net_time is not None:
            time_delta = current_time - self._last_net_time
            
            if time_delta > 0:
                # Calculate deltas in bytes
                dl_bytes = current_io.bytes_recv - self._last_net_io.bytes_recv
                up_bytes = current_io.bytes_sent - self._last_net_io.bytes_sent
                
                # Convert to Mbps (Megabits per second)
                # 1 byte = 8 bits, 1 Mb = 1,000,000 bits
                dl_mbps = (dl_bytes * 8) / (time_delta * 1_000_000)
                up_mbps = (up_bytes * 8) / (time_delta * 1_000_000)
            else:
                dl_mbps = 0.0
                up_mbps = 0.0
        else:
            dl_mbps = 0.0
            up_mbps = 0.0
        
        # Store current values for next calculation
        self._last_net_io = current_io
        self._last_net_time = current_time
        
        return NetworkMetrics(
            download_mbps=dl_mbps,
            upload_mbps=up_mbps,
            total_dl_gb=self._bytes_to_gb(current_io.bytes_recv),
            total_up_gb=self._bytes_to_gb(current_io.bytes_sent)
        )
    
    def get_uptime(self) -> int:
        """
        Get system uptime in seconds.
        
        Returns:
            Uptime in seconds
        """
        return int(time.time() - psutil.boot_time())
    
    def collect_all(self, cpu_interval: float = 0.1) -> SystemMetrics:
        """
        Collect all system metrics at once.
        
        Args:
            cpu_interval: Interval for CPU measurement
            
        Returns:
            SystemMetrics containing all collected metrics
        """
        return SystemMetrics(
            cpu=self.get_cpu_metrics(cpu_interval),
            memory=self.get_memory_metrics(),
            swap=self.get_swap_metrics(),
            load_avg=self.get_loadavg_metrics(),
            network=self.get_network_metrics(),
            uptime_seconds=self.get_uptime(),
            timestamp=time.time()
        )

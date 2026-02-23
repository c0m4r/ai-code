import psutil
import time
import sys

class SystemMonitor:
    def __init__(self):
        self.last_io = psutil.net_io_counters(pernic=False)
        self.last_time = time.time()

    def get_cpu(self):
        """Returns CPU usage percentage."""
        return psutil.cpu_percent(interval=0.1)

    def get_ram(self):
        """Returns RAM usage in GB and percentage."""
        mem = psutil.virtual_memory()
        total_gb = mem.total / (1024**3)
        used_gb = mem.used / (1024**3)
        return used_gb, total_gb, mem.percent

    def get_load(self):
        """Returns 1, 5, and 15 minute load averages."""
        try:
            # Works on Linux/macOS. Windows usually returns None (will display 0.0)
            return psutil.getloadavg()
        except AttributeError:
            return (0.0, 0.0, 0.0)

    def get_net_speed(self):
        """
        Calculates current network speed in Mbps.
        Returns: (download_mbps, upload_mbps)
        """
        current_io = psutil.net_io_counters(pernic=False)
        current_time = time.time()

        if current_time == self.last_time:
            return 0.0, 0.0

        # Calculate delta time
        delta_time = current_time - self.last_time

        # Calculate bytes transferred
        bytes_down = current_io.bytes_recv - self.last_io.bytes_recv
        bytes_up = current_io.bytes_sent - self.last_io.bytes_sent

        # Convert to Mbps (Megabits per second)
        # Formula: (Bytes * 8) / 1,000,000 (bits) / Seconds
        down_mbps = (bytes_down * 8) / delta_time / 1_000_000
        up_mbps = (bytes_up * 8) / delta_time / 1_000_000

        self.last_io = current_io
        self.last_time = current_time

        return down_mbps, up_mbps

def main():
    monitor = SystemMonitor()
    print("System Monitor - Press Ctrl+C to exit")
    
    try:
        while True:
            # 1. CPU
            cpu_usage = monitor.get_cpu()
            
            # 2. RAM
            ram_used, ram_total, ram_percent = monitor.get_ram()
            
            # 3. Load Average
            lavg_1, lavg_5, lavg_15 = monitor.get_load()
            
            # 4. Network
            net_down, net_up = monitor.get_net_speed()

            # --- Display ---
            # Use carriage return (\r) to overwrite the previous line
            sys.stdout.write(
                f"\rCPU: {cpu_usage:.1f}% | "
                f"RAM: {ram_used:.1f}GB / {ram_total:.1f}GB ({ram_percent:.1f}%) | "
                f"Lavg: {lavg_1:.2f}, {lavg_5:.2f}, {lavg_15:.2f} | "
                f"NET: ↓ {net_down:.1f} Mbps / ↑ {net_up:.1f} Mbps    "
            )
            sys.stdout.flush() # Ensure the print happens immediately

            time.sleep(1) # Update every second

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")

if __name__ == "__main__":
    main()

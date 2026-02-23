import psutil
import time
import sys

# --- ANSI Color Codes ---
def color(text):
    """Returns ANSI color codes for the terminal."""
    return {
        'cyan': '\033[96m',    # CPU
        'blue': '\033[94m',    # RAM
        'magenta': '\033[95m', # SWAP
        'yellow': '\033[93m',  # Network
        'green': '\033[92m',   # OK/Good
        'red': '\033[91m',     # Critical
        'reset': '\033[0m'
    }.get(text, '')

def create_bar(percentage, width=15, color_name='white'):
    """
    Creates a graphical progress bar.
    Filled with █, empty with ░.
    """
    filled = int(percentage / 100 * width)
    bar = '█' * filled + '░' * (width - filled)
    return f"{color(color_name)}[{bar}]{color('reset')}"

class SystemMonitor:
    def __init__(self):
        # Initialize network counters for speed calculation
        self.last_io = psutil.net_io_counters(pernic=False)
        self.last_time = time.time()

    def get_metrics(self):
        # 1. CPU
        cpu_usage = psutil.cpu_percent(interval=0.1)

        # 2. RAM
        mem = psutil.virtual_memory()
        ram_used_gb = mem.used / (1024**3)
        ram_total_gb = mem.total / (1024**3)

        # 3. SWAP
        swap = psutil.swap_memory()
        swap_used_gb = swap.used / (1024**3)
        swap_total_gb = swap.total / (1024**3)

        # 4. Load Average
        try:
            load_avg = psutil.getloadavg()  # Linux/macOS
        except AttributeError:
            load_avg = (0.0, 0.0, 0.0)     # Fallback for Windows

        # 5. Network Speed
        current_io = psutil.net_io_counters(pernic=False)
        current_time = time.time()
        delta_time = current_time - self.last_time

        if delta_time > 0:
            bytes_down = current_io.bytes_recv - self.last_io.bytes_recv
            bytes_up = current_io.bytes_sent - self.last_io.bytes_sent
            
            # Convert Bytes/s to Megabits/s
            mbps_down = (bytes_down * 8) / delta_time / 1_000_000
            mbps_up = (bytes_up * 8) / delta_time / 1_000_000
        else:
            mbps_down, mbps_up = 0.0, 0.0

        # Update state
        self.last_io = current_io
        self.last_time = current_time

        return {
            'cpu': cpu_usage,
            'ram': (ram_used_gb, ram_total_gb),
            'swap': (swap_used_gb, swap_total_gb),
            'load': load_avg,
            'net': (mbps_down, mbps_up)
        }

def main():
    monitor = SystemMonitor()
    
    try:
        while True:
            data = monitor.get_metrics()
            
            # --- Construct UI ---
            
            # 1. Top Row: Bars
            cpu_bar = create_bar(data['cpu'], 20, 'cyan')
            ram_bar = create_bar(data['ram'][1], 20, 'blue')
            swap_bar = create_bar(data['swap'][1], 20, 'magenta')
            
            line1 = f" CPU {cpu_bar}  RAM {ram_bar}  SWAP {swap_bar}"

            # 2. Middle Row: Values
            # Calculate formatted strings for RAM/Swap
            ram_str = f"{color('blue')}{data['ram'][0]:.1f}GB / {data['ram'][1]:.1f}GB{color('reset')}"
            swap_str = f"{color('magenta')}{data['swap'][0]:.1f}GB / {data['swap'][1]:.1f}GB{color('reset')}"
            
            line2 = f" RAM: {ram_str:<40}  SWAP: {swap_str}"

            # 3. Bottom Row: Load & Network
            load_str = f"{data['load'][0]:.2f} | {data['load'][1]:.2f} | {data['load'][2]:.2f}"
            net_str = f"{color('yellow')}↓ {data['net'][0]:.1f} Mbps{color('reset')}  /  {color('yellow')}↑ {data['net'][1]:.1f} Mbps{color('reset')}"
            
            line3 = f" LOAD: {load_str:<45}  NET: {net_str}"

            # --- Render ---
            # Clear screen and move cursor to top
            sys.stdout.write("\033[2J")
            sys.stdout.write("\033[H")
            
            print(line1)
            print(line2)
            print(line3)
            print(color('reset')) # Reset colors at end
            
            # Optional: Add timestamp
            print(f" {time.strftime('%H:%M:%S')}   ")

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")

if __name__ == "__main__":
    main()

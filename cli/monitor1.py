import psutil
import time
import sys
import socket
import platform
import datetime
import shutil

# --- ANSI Color Codes ---
def color(text):
    return {
        'cyan': '\033[96m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'yellow': '\033[93m',
        'green': '\033[92m',
        'red': '\033[91m',
        'white': '\033[97m',
        'reset': '\033[0m'
    }.get(text, '')

def create_bar(percentage, width=10, color_name='white'):
    filled = int(percentage / 100 * width)
    bar = '█' * filled + '░' * (width - filled)
    return f"{color(color_name)}[{bar}]{color('reset')}"

class SystemMonitor:
    def __init__(self):
        self.last_io = psutil.net_io_counters(pernic=False)
        self.last_time = time.time()

    def get_metrics(self):
        # 1. System Info
        hostname = socket.gethostname()
        kernel = platform.uname().release
        uptime = time.time() - psutil.boot_time()
        
        # 2. CPU
        cpu_usage = psutil.cpu_percent(interval=0.1)

        # 3. RAM
        mem = psutil.virtual_memory()
        ram_used_gb = mem.used / (1024**3)
        ram_total_gb = mem.total / (1024**3)

        # 4. SWAP
        swap = psutil.swap_memory()
        swap_used_gb = swap.used / (1024**3)
        swap_total_gb = swap.total / (1024**3)

        # 5. Load Average
        try:
            load_avg = psutil.getloadavg()
        except:
            load_avg = (0.0, 0.0, 0.0)

        # 6. Network Speed
        current_io = psutil.net_io_counters(pernic=False)
        current_time = time.time()
        delta_time = current_time - self.last_time

        if delta_time > 0:
            bytes_down = current_io.bytes_recv - self.last_io.bytes_recv
            bytes_up = current_io.bytes_sent - self.last_io.bytes_sent
            mbps_down = (bytes_down * 8) / delta_time / 1_000_000
            mbps_up = (bytes_up * 8) / delta_time / 1_000_000
        else:
            mbps_down, mbps_up = 0.0, 0.0

        self.last_io = current_io
        self.last_time = current_time

        return {
            'hostname': hostname,
            'kernel': kernel,
            'uptime': uptime,
            'cpu': cpu_usage,
            'ram': (ram_used_gb, ram_total_gb),
            'swap': (swap_used_gb, swap_total_gb),
            'load': load_avg,
            'net': (mbps_down, mbps_up)
        }

def render_grid(metrics):
    # Get terminal dimensions
    cols, rows = shutil.get_terminal_size().columns, shutil.get_terminal_size().lines
    
    # --- 1. HEADER SECTION ---
    header_left = f" SYSTEM MONITOR  "
    header_right = f" KERNEL: {metrics['kernel']:8}  TIME: {datetime.datetime.now().strftime('%H:%M:%S')}"
    
    # Calculate spacing for header
    total_header_len = len(header_left) + len(header_right)
    if cols < total_header_len:
        header_right = f" KERNEL: {metrics['kernel']:8}"
    else:
        spacing = " " * (cols - total_header_len)
        header_right += spacing

    header_line = header_left + header_right

    # --- 2. STATS GRID (2 Columns) ---
    
    # Helper to format card
    def format_card(label, value, bar_width=10):
        label_str = f" {label}"
        bar_str = create_bar(value[1], bar_width, label.lower())
        val_str = f"{color('white')}{value[0]:.1f}{color('reset')}"
        # Fallback for load (which isn't a percentage bar)
        if label == 'LOAD':
            bar_str = ""
            val_str = f"{color('green')}{value[0]:.2f}{color('reset')}"
        
        return f"{label_str} {bar_str} {val_str}"

    # Left Column: CPU, RAM, LOAD
    col1_cpu = format_card('CPU', (metrics['cpu'], metrics['cpu']))
    col1_ram = format_card('RAM', (metrics['ram'][0], metrics['ram'][1]))
    col1_load = format_card('LOAD', (metrics['load'][0], 0))

    # Right Column: SWAP, NET
    col2_swap = format_card('SWAP', (metrics['swap'][0], metrics['swap'][1]))
    # Format Net nicely (arrows)
    net_d_str = f"{color('yellow')}↓{metrics['net'][0]:.1f} MB{color('reset')}"
    net_u_str = f"{color('yellow')}↑{metrics['net'][1]:.1f} MB{color('reset')}"
    col2_net = f" NET: {net_d_str} / {net_u_str}"

    # --- 3. DYNAMIC ALIGNMENT ---
    # Calculate max width for centering
    max_width = cols - 2
    
    def center_text(text):
        return text.center(max_width)
    
    # Format lines with padding
    # We want the two columns to line up horizontally
    line1 = center_text(f"{col1_cpu}  |  {col2_swap}")
    line2 = center_text(f"{col1_ram}  |  {col2_net}")
    line3 = center_text(f"{col1_load}  |  {(metrics['uptime'] / 3600):.1f}h UPTIME")

    return [header_line, line1, line2, line3]

def main():
    monitor = SystemMonitor()
    
    try:
        while True:
            data = monitor.get_metrics()
            lines = render_grid(data)
            
            # Render
            sys.stdout.write("\033[2J") # Clear screen
            sys.stdout.write("\033[H")  # Move to top
            
            print(color('white') + "\n")
            for line in lines:
                print(line)
            print(color('reset'))
            
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")

if __name__ == "__main__":
    main()

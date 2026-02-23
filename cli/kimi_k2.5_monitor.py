#!/usr/bin/env python3
"""
Simple Linux System Monitor
A beautiful, lightweight real-time system resource monitor for the terminal.

Requirements:
    pip install psutil rich

Usage:
    python3 sysmon.py
    # Or make executable: chmod +x sysmon.py && ./sysmon.py

Press Ctrl+C to exit.
"""

import os
import platform
import datetime
import time
import psutil
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich import box


class SystemMonitor:
    def __init__(self):
        self.cpu_cores = psutil.cpu_count()
        # Initialize CPU percent (first call returns 0)
        psutil.cpu_percent(interval=None)
        # Network tracking
        self.prev_net = psutil.net_io_counters()
        self.prev_time = time.time()
        
    def get_header_text(self):
        """Generate header with hostname, kernel, datetime and uptime."""
        hostname = platform.node()
        kernel = platform.release()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Calculate uptime
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        uptime = str(datetime.timedelta(seconds=int(uptime_seconds)))
        # Shorten uptime format: 2 days, 14:32:10 -> 2d 14h 32m
        parts = uptime.split(', ')
        if len(parts) > 1:
            days = parts[0].replace(' days', 'd').replace(' day', 'd')
            time_part = parts[1].split(':')
            uptime = f"{days} {time_part[0]}h {time_part[1]}m"
        else:
            time_part = uptime.split(':')
            uptime = f"{time_part[0]}h {time_part[1]}m {time_part[2]}s"
            
        return f"[bold cyan]{hostname}[/] | [green]Kernel {kernel}[/] | [yellow]{now}[/] | [blue]Up: {uptime}[/]"

    def make_bar(self, percent, width=25):
        """Create a colored progress bar using Unicode blocks."""
        filled = int(width * percent / 100)
        if percent < 50:
            color = "bright_green"
        elif percent < 80:
            color = "bright_yellow" 
        else:
            color = "bright_red"
        
        bar = "█" * filled + "░" * (width - filled)
        return f"[{color}]{bar}[/{color}] [white]{percent:>5.1f}%[/white]"

    def get_net_speed(self):
        """Calculate current download/upload speed in Mbps."""
        current_net = psutil.net_io_counters()
        current_time = time.time()
        interval = current_time - self.prev_time
        
        if interval <= 0:
            return 0.0, 0.0
            
        # Convert bytes to megabits (bytes * 8 / 1024 / 1024)
        dl_mbps = (current_net.bytes_recv - self.prev_net.bytes_recv) * 8 / 1024 / 1024 / interval
        up_mbps = (current_net.bytes_sent - self.prev_net.bytes_sent) * 8 / 1024 / 1024 / interval
        
        self.prev_net = current_net
        self.prev_time = current_time
        
        return dl_mbps, up_mbps

    def get_load_color(self, load_val):
        """Determine color for load average based on CPU cores."""
        if load_val < self.cpu_cores:
            return "bright_green"
        elif load_val < self.cpu_cores * 2:
            return "bright_yellow"
        else:
            return "bright_red"

    def generate_layout(self):
        """Generate the full dashboard layout."""
        # Create main table for metrics
        table = Table(show_header=False, box=None, padding=(0, 2), expand=True)
        table.add_column("Label", style="bold cyan", width=12, justify="right")
        table.add_column("Bar", style="white", ratio=2)
        table.add_column("Detail", style="dim", width=15)

        # CPU
        cpu_percent = psutil.cpu_percent(interval=None)
        cpu_freq = psutil.cpu_freq()
        freq_str = f"{cpu_freq.current:.0f}MHz" if cpu_freq else "N/A"
        table.add_row("CPU", self.make_bar(cpu_percent), f"[dim]{freq_str} | {self.cpu_cores} cores[/]")

        # RAM
        mem = psutil.virtual_memory()
        mem_used_gb = mem.used / 1024 / 1024 / 1024
        mem_total_gb = mem.total / 1024 / 1024 / 1024
        table.add_row("RAM", self.make_bar(mem.percent), f"[dim]{mem_used_gb:.1f}/{mem_total_gb:.1f} GB[/]")

        # Swap
        swap = psutil.swap_memory()
        if swap.total > 0:
            swap_used_gb = swap.used / 1024 / 1024 / 1024
            swap_total_gb = swap.total / 1024 / 1024 / 1024
            table.add_row("Swap", self.make_bar(swap.percent), f"[dim]{swap_used_gb:.1f}/{swap_total_gb:.1f} GB[/]")
        else:
            table.add_row("Swap", "[dim]No swap[/]", "")

        # Load Average
        load1, load5, load15 = os.getloadavg()
        load_color = self.get_load_color(load1)
        load_str = f"[{load_color}]{load1:.2f}[/{load_color}] [dim]{load5:.2f} {load15:.2f}[/]"
        table.add_row("Load Avg", load_str, f"[dim]{self.cpu_cores} cores[/]")

        # Network
        dl, ul = self.get_net_speed()
        dl_color = "bright_green" if dl < 10 else "bright_yellow" if dl < 50 else "bright_red"
        ul_color = "bright_blue" if ul < 5 else "bright_yellow" if ul < 20 else "bright_red"
        net_str = f"[{dl_color}]▼ {dl:>6.1f} Mbps[/{dl_color}]   [{ul_color}]▲ {ul:>6.1f} Mbps[/{ul_color}]"
        table.add_row("Network", net_str, "")

        # Create layout
        layout = Layout()
        
        # Header
        header = Panel(
            Text.from_markup(self.get_header_text(), justify="center"),
            box=box.ROUNDED,
            border_style="blue",
            padding=(1, 1)
        )
        
        # Main content
        content = Panel(
            table,
            title="[bold]System Resources[/bold]",
            title_align="left",
            box=box.ROUNDED,
            border_style="cyan",
            padding=(1, 2)
        )
        
        layout.split_column(
            Layout(header, size=3),
            Layout(content)
        )
        
        return layout

    def run(self):
        """Main loop with live display."""
        try:
            with Live(
                self.generate_layout(), 
                refresh_per_second=2, 
                screen=False,
                transient=False
            ) as live:
                while True:
                    time.sleep(0.5)
                    live.update(self.generate_layout())
        except KeyboardInterrupt:
            console.print("\n[dim]Monitor stopped.[/dim]")
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")


if __name__ == "__main__":
    console = Console()
    
    # Check if we're on Linux/Unix (for loadavg)
    if not hasattr(os, 'getloadavg'):
        console.print("[red]Error: This tool requires Linux/Unix (loadavg not available)[/red]")
        exit(1)
        
    monitor = SystemMonitor()
    monitor.run()

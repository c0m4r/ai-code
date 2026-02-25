#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ultimate Linux Monitoring Tool
A comprehensive CLI monitoring tool with beautiful UI, colors, and graphs
"""

import sys
import os
import time
import psutil
import argparse
import subprocess
from datetime import datetime
from collections import deque
import math

# Colors for terminal output
class Colors:
    RESET = '\033[0m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
    # Background colors
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

# Terminal size utility
def get_terminal_size():
    try:
        rows, columns = os.popen('stty size', 'r').read().split()
        return int(rows), int(columns)
    except:
        return 24, 80

# Graph drawing function
def draw_graph(data, max_val, width=50, char='█'):
    if not data:
        return " " * width
    
    # Normalize data to fit width
    normalized = [int((x / max_val) * width) if max_val > 0 else 0 for x in data]
    
    # Create graph string
    graph = ""
    for i, value in enumerate(normalized):
        if i == 0:
            graph += " "
        graph += char * value
        if i < len(normalized) - 1:
            graph += " "
    
    return graph

# CPU monitoring
def get_cpu_info():
    cpu_count = psutil.cpu_count()
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_freq = psutil.cpu_freq()
    
    # Get per-core usage
    cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)
    
    return {
        'count': cpu_count,
        'percent': cpu_percent,
        'freq': cpu_freq,
        'per_core': cpu_per_core
    }

# Memory monitoring
def get_memory_info():
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    return {
        'total': memory.total,
        'available': memory.available,
        'used': memory.used,
        'percent': memory.percent,
        'swap_total': swap.total,
        'swap_used': swap.used,
        'swap_percent': swap.percent
    }

# Load average
def get_load_average():
    try:
        load_avg = os.getloadavg()
        return {
            '1min': load_avg[0],
            '5min': load_avg[1],
            '15min': load_avg[2]
        }
    except:
        return {'1min': 0, '5min': 0, '15min': 0}

# Network monitoring
def get_network_info():
    net_io = psutil.net_io_counters()
    net_connections = len(psutil.net_connections())
    
    return {
        'bytes_sent': net_io.bytes_sent,
        'bytes_recv': net_io.bytes_recv,
        'packets_sent': net_io.packets_sent,
        'packets_recv': net_io.packets_recv,
        'connections': net_connections
    }

# Format bytes to human readable
def format_bytes(bytes_val):
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024**2:
        return f"{bytes_val/1024:.1f} KB"
    elif bytes_val < 1024**3:
        return f"{bytes_val/1024**2:.1f} MB"
    else:
        return f"{bytes_val/1024**3:.1f} GB"

# Format time
def format_time(seconds):
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.0f}m"
    else:
        return f"{seconds/3600:.0f}h"

# Draw a single bar with color
def draw_bar(value, max_val, width=30, color_func=None):
    if max_val == 0:
        percentage = 0
    else:
        percentage = min(100, (value / max_val) * 100)
    
    filled_width = int((percentage / 100) * width)
    bar = "█" * filled_width + "░" * (width - filled_width)
    
    if color_func:
        return color_func(bar)
    return bar

# Draw CPU usage graph
def draw_cpu_graph(cpu_data, width=50):
    if not cpu_data:
        return "No data"
    
    # Get max value for normalization
    max_val = max(cpu_data) if cpu_data else 1
    
    # Normalize and draw
    normalized = [int((x / max_val) * width) if max_val > 0 else 0 for x in cpu_data]
    
    graph = ""
    for i, value in enumerate(normalized):
        if i == 0:
            graph += " "
        graph += "█" * value
        if i < len(normalized) - 1:
            graph += " "
    
    return graph

# Main monitoring function
def monitor_system(interval=1, max_lines=20):
    # Initialize data storage for graphs
    cpu_history = deque(maxlen=max_lines)
    memory_history = deque(maxlen=max_lines)
    network_history = deque(maxlen=max_lines)
    
    # Clear screen
    os.system('clear')
    
    # Print header
    print(Colors.BOLD + Colors.BLUE + "="*80 + Colors.RESET)
    print(Colors.BOLD + Colors.CYAN + "           ULTIMATE LINUX MONITORING TOOL" + Colors.RESET)
    print(Colors.BOLD + Colors.BLUE + "="*80 + Colors.RESET)
    print()
    
    try:
        while True:
            # Clear screen
            os.system('clear')
            
            # Print header
            print(Colors.BOLD + Colors.BLUE + "="*80 + Colors.RESET)
            print(Colors.BOLD + Colors.CYAN + "           ULTIMATE LINUX MONITORING TOOL" + Colors.RESET)
            print(Colors.BOLD + Colors.BLUE + "="*80 + Colors.RESET)
            print()
            
            # Print timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(Colors.BOLD + Colors.YELLOW + f"System Time: {timestamp}" + Colors.RESET)
            print()
            
            # Get system information
            cpu_info = get_cpu_info()
            memory_info = get_memory_info()
            load_avg = get_load_average()
            network_info = get_network_info()
            
            # Store data for graphs
            cpu_history.append(cpu_info['percent'])
            memory_history.append(memory_info['percent'])
            
            # CPU Section
            print(Colors.BOLD + Colors.GREEN + "CPU USAGE" + Colors.RESET)
            print("-" * 80)
            
            # CPU usage bar
            cpu_bar = draw_bar(cpu_info['percent'], 100, 30)
            cpu_color = Colors.RED if cpu_info['percent'] > 80 else Colors.GREEN if cpu_info['percent'] < 40 else Colors.YELLOW
            print(f"Overall CPU Usage: {cpu_color}{cpu_info['percent']:.1f}%{Colors.RESET}")
            print(f"CPU Usage Bar:     {cpu_color}{cpu_bar}{Colors.RESET}")
            
            # Per-core usage
            print("Per-Core Usage:")
            cores = cpu_info['per_core']
            for i, usage in enumerate(cores):
                core_color = Colors.RED if usage > 80 else Colors.GREEN if usage < 40 else Colors.YELLOW
                print(f"  Core {i+1:2d}: {core_color}{usage:5.1f}%{Colors.RESET}")
            
            print()
            
            # Memory Section
            print(Colors.BOLD + Colors.GREEN + "MEMORY USAGE" + Colors.RESET)
            print("-" * 80)
            
            # Memory usage bar
            mem_bar = draw_bar(memory_info['percent'], 100, 30)
            mem_color = Colors.RED if memory_info['percent'] > 80 else Colors.GREEN if memory_info['percent'] < 40 else Colors.YELLOW
            print(f"Memory Usage:      {mem_color}{memory_info['percent']:.1f}%{Colors.RESET}")
            print(f"Memory Bar:        {mem_color}{mem_bar}{Colors.RESET}")
            
            # Memory details
            print(f"Total Memory:      {format_bytes(memory_info['total'])}")
            print(f"Used Memory:       {format_bytes(memory_info['used'])}")
            print(f"Available Memory:  {format_bytes(memory_info['available'])}")
            
            print()
            
            # Swap Section
            print(Colors.BOLD + Colors.GREEN + "SWAP USAGE" + Colors.RESET)
            print("-" * 80)
            
            # Swap usage bar
            swap_bar = draw_bar(memory_info['swap_percent'], 100, 30)
            swap_color = Colors.RED if memory_info['swap_percent'] > 80 else Colors.GREEN if memory_info['swap_percent'] < 40 else Colors.YELLOW
            print(f"Swap Usage:        {swap_color}{memory_info['swap_percent']:.1f}%{Colors.RESET}")
            print(f"Swap Bar:          {swap_color}{swap_bar}{Colors.RESET}")
            
            # Swap details
            print(f"Total Swap:        {format_bytes(memory_info['swap_total'])}")
            print(f"Used Swap:         {format_bytes(memory_info['swap_used'])}")
            
            print()
            
            # Load Average Section
            print(Colors.BOLD + Colors.GREEN + "LOAD AVERAGE" + Colors.RESET)
            print("-" * 80)
            
            # Load average with color coding
            la1 = load_avg['1min']
            la5 = load_avg['5min']
            la15 = load_avg['15min']
            
            la1_color = Colors.RED if la1 > 1.0 else Colors.GREEN if la1 < 0.5 else Colors.YELLOW
            la5_color = Colors.RED if la5 > 1.0 else Colors.GREEN if la5 < 0.5 else Colors.YELLOW
            la15_color = Colors.RED if la15 > 1.0 else Colors.GREEN if la15 < 0.5 else Colors.YELLOW
            
            print(f"1-minute:   {la1_color}{la1:.2f}{Colors.RESET}")
            print(f"5-minute:   {la5_color}{la5:.2f}{Colors.RESET}")
            print(f"15-minute:  {la15_color}{la15:.2f}{Colors.RESET}")
            
            print()
            
            # Network Section
            print(Colors.BOLD + Colors.GREEN + "NETWORK USAGE" + Colors.RESET)
            print("-" * 80)
            
            # Network details
            print(f"Bytes Sent:        {format_bytes(network_info['bytes_sent'])}")
            print(f"Bytes Received:    {format_bytes(network_info['bytes_recv'])}")
            print(f"Packets Sent:      {network_info['packets_sent']:,}")
            print(f"Packets Received:  {network_info['packets_recv']:,}")
            print(f"Active Connections: {network_info['connections']}")
            
            print()
            
            # System uptime
            try:
                with open('/proc/uptime', 'r') as f:
                    uptime_seconds = float(f.readline().split()[0])
                print(Colors.BOLD + Colors.MAGENTA + f"System Uptime: {format_time(uptime_seconds)}" + Colors.RESET)
            except:
                pass
            
            print()
            
            # Graphs section
            print(Colors.BOLD + Colors.GREEN + "HISTORICAL GRAPHS (last 20 samples)" + Colors.RESET)
            print("-" * 80)
            
            if len(cpu_history) > 1:
                print("CPU Usage:")
                cpu_graph = draw_graph(list(cpu_history), 100, 50, '█')
                print(f"  {cpu_graph}")
                
                print("Memory Usage:")
                mem_graph = draw_graph(list(memory_history), 100, 50, '█')
                print(f"  {mem_graph}")
            
            print()
            print(Colors.BOLD + Colors.CYAN + "Press Ctrl+C to exit" + Colors.RESET)
            print()
            
            # Wait for next update
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n" + Colors.BOLD + Colors.RED + "Monitoring stopped by user." + Colors.RESET)
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description='Ultimate Linux Monitoring Tool')
    parser.add_argument('-i', '--interval', type=int, default=1, help='Update interval in seconds (default: 1)')
    parser.add_argument('-l', '--lines', type=int, default=20, help='Number of historical lines for graphs (default: 20)')
    
    args = parser.parse_args()
    
    # Check if running on Linux
    if not sys.platform.startswith('linux'):
        print(Colors.BOLD + Colors.RED + "Error: This tool only works on Linux systems." + Colors.RESET)
        sys.exit(1)
    
    # Validate arguments
    if args.interval < 1:
        print(Colors.BOLD + Colors.RED + "Error: Interval must be at least 1 second." + Colors.RESET)
        sys.exit(1)
    
    if args.lines < 1:
        print(Colors.BOLD + Colors.RED + "Error: Lines must be at least 1." + Colors.RESET)
        sys.exit(1)
    
    # Start monitoring
    monitor_system(args.interval, args.lines)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3

import curses
import time
import os
import sys
from dataclasses import dataclass
from typing import Optional

@dataclass
class CPUStats:
    user: int; nice: int; system: int; idle: int; iowait: int; irq: int; softirq: int; steal: int
    @property
    def total(self) -> int: return self.user + self.nice + self.system + self.idle + self.iowait + self.irq + self.softirq + self.steal
    @property
    def active(self) -> int: return self.total - self.idle - self.iowait

@dataclass
class NetworkStats:
    rx_bytes: int; tx_bytes: int; timestamp: float

@dataclass
class SystemMetrics:
    cpu_percent: float; cpu_per_core: list[float]; memory_total: int; memory_used: int; memory_percent: float
    swap_total: int; swap_used: int; swap_percent: float; load_1: float; load_5: float; load_15: float
    net_download_speed: float; net_upload_speed: float; cpu_count: int

class HardwareMonitor:
    def __init__(self):
        self._prev_cpu_stats = None
        self._prev_cpu_per_core = []
        self._prev_net_stats = None

    def _read_cpu_stats(self):
        with open('/proc/stat', 'r') as f:
            lines = f.readlines()
        aggregate, per_core = None, []
        for line in lines:
            if line.startswith('cpu'):
                p = line.split()
                s = CPUStats(int(p[1]), int(p[2]), int(p[3]), int(p[4]), 
                             int(p[5]) if len(p)>5 else 0, int(p[6]) if len(p)>6 else 0,
                             int(p[7]) if len(p)>7 else 0, int(p[8]) if len(p)>8 else 0)
                if p[0] == 'cpu': aggregate = s
                else: per_core.append(s)
        return aggregate, per_core

    def _calculate_cpu_percent(self, prev, curr):
        diff = curr.total - prev.total
        return (curr.active - prev.active) / diff * 100 if diff > 0 else 0.0

    def get_metrics(self):
        curr_cpu, curr_per_core = self._read_cpu_stats()
        cpu_p = self._calculate_cpu_percent(self._prev_cpu_stats, curr_cpu) if self._prev_cpu_stats else 0.0
        core_p = [self._calculate_cpu_percent(p, c) for p, c in zip(self._prev_cpu_per_core, curr_per_core)] if self._prev_cpu_per_core else [0.0]*len(curr_per_core)
        
        self._prev_cpu_stats, self._prev_cpu_per_core = curr_cpu, curr_per_core

        m = {}
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                p = line.split(); m[p[0].rstrip(':')] = int(p[1]) * 1024
        
        mem_u = m['MemTotal'] - m['MemFree'] - m.get('Buffers',0) - m.get('Cached',0) - m.get('SReclaimable',0)
        swap_u = m['SwapTotal'] - m['SwapFree']
        
        with open('/proc/loadavg', 'r') as f:
            l = f.read().split()
        
        rx, tx = 0, 0
        with open('/proc/net/dev', 'r') as f:
            for line in f.readlines()[2:]:
                p = line.split()
                if p[0] != 'lo:': rx += int(p[1]); tx += int(p[9])
        curr_net = NetworkStats(rx, tx, time.time())
        
        dl, ul = 0.0, 0.0
        if self._prev_net_stats:
            dt = curr_net.timestamp - self._prev_net_stats.timestamp
            dl, ul = (curr_net.rx_bytes - self._prev_net_stats.rx_bytes)/dt, (curr_net.tx_bytes - self._prev_net_stats.tx_bytes)/dt
        self._prev_net_stats = curr_net

        return SystemMetrics(cpu_p, core_p, m['MemTotal'], mem_u, (mem_u/m['MemTotal']*100), 
                             m['SwapTotal'], swap_u, (swap_u/m['SwapTotal']*100 if m['SwapTotal']>0 else 0),
                             float(l[0]), float(l[1]), float(l[2]), dl, ul, len(curr_per_core))

class UI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.show_cores = True
        curses.start_color()
        curses.use_default_colors()
        for i, c in enumerate([curses.COLOR_WHITE, curses.COLOR_YELLOW, curses.COLOR_RED, curses.COLOR_CYAN, curses.COLOR_BLUE, curses.COLOR_GREEN, curses.COLOR_GREEN], 1):
            curses.init_pair(i, c, -1)
        self.stdscr.nodelay(True)

    def _format_mbps(self, bps):
        return f"{(bps * 8) / 1_000_000:6.2f} Mbps"

    def _format_mem(self, b):
        for u in ['B','K','M','G','T']:
            if abs(b) < 1024: return f"{b:.1f}{u}"
            b /= 1024
        return f"{b:.1f}P"

    def _draw_bar(self, y, x, w, p, label=""):
        if w < 5: return
        filled = int((w-2) * p / 100)
        c = 7 if p < 60 else (2 if p < 80 else 3)
        self.stdscr.addstr(y, x, "[" + "█"*filled + "░"*(w-2-filled) + "]", curses.color_pair(c))
        if label: self.stdscr.addstr(y, x + (w-len(label))//2, label, curses.A_BOLD)

    def draw(self, m: SystemMetrics):
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()
        if h < 10 or w < 40:
            self.stdscr.addstr(0,0, "Mini Mode: CPU " + f"{m.cpu_percent:.1f}%")
            self.stdscr.refresh(); return

        # Dynamic logic: hide cores if window too small
        needed_h = 18 + (m.cpu_count if self.show_cores else 0)
        effective_show_cores = self.show_cores and h > (15 + m.cpu_count // 2)

        self.stdscr.addstr(0, (w-20)//2, "══ HARDWARE MONITOR ══", curses.color_pair(4) | curses.A_BOLD)
        
        # CPU Box
        core_rows = (m.cpu_count + 1) // 2 if effective_show_cores else 0
        cpu_h = 4 + core_rows
        self._draw_box(2, 2, cpu_h, w-4, "CPU")
        self._draw_bar(3, 12, w-18, m.cpu_percent, f"{m.cpu_percent:.1f}%")
        
        if effective_show_cores:
            for i, p in enumerate(m.cpu_per_core):
                r, col = i // 2, i % 2
                self.stdscr.addstr(4+r, 4 + col*(w//2-2), f"C{i}:", curses.color_pair(1))
                self._draw_bar(4+r, 8 + col*(w//2-2), (w//2)-10, p)

        # Memory Box
        mem_y = 2 + cpu_h
        self._draw_box(mem_y, 2, 5, w-4, "MEMORY")
        self._draw_bar(mem_y+1, 10, w-16, m.memory_percent, f"RAM: {m.memory_percent:.1f}%")
        self.stdscr.addstr(mem_y+2, 10, f"{self._format_mem(m.memory_used)} / {self._format_mem(m.memory_total)}")
        self._draw_bar(mem_y+3, 10, w-16, m.swap_percent, f"SWAP: {m.swap_percent:.1f}%")

        # Load & Net
        stat_y = mem_y + 5
        self.stdscr.addstr(stat_y+1, 4, f"LOAD: {m.load_1:.2f} {m.load_5:.2f} {m.load_15:.2f}", curses.color_pair(4))
        self.stdscr.addstr(stat_y+2, 4, f"NET ↓: {self._format_mbps(m.net_download_speed)}", curses.color_pair(6))
        self.stdscr.addstr(stat_y+3, 4, f"NET ↑: {self._format_mbps(m.net_upload_speed)}", curses.color_pair(2))
        
        self.stdscr.addstr(h-1, 2, "Q:Quit | C:Toggle Cores", curses.color_pair(5))
        self.stdscr.refresh()

    def _draw_box(self, y, x, h, w, title):
        color = curses.color_pair(5)
        self.stdscr.attron(color)
        # Draw corners and horizontal lines
        self.stdscr.addstr(y, x, "╭" + "─" * (w - 2) + "╮")
        self.stdscr.addstr(y + h - 1, x, "╰" + "─" * (w - 2) + "╯")
        # Draw vertical lines
        for i in range(1, h - 1):
            self.stdscr.addstr(y + i, x, "│")
            self.stdscr.addstr(y + i, x + w - 1, "│")
        # Draw title
        if title:
            self.stdscr.addstr(y, x + (w - len(title) - 2) // 2, f" {title} ")
        self.stdscr.attroff(color)

def main(stdscr):
    monitor = HardwareMonitor()
    ui = UI(stdscr)
    while True:
        try:
            ui.draw(monitor.get_metrics())
            key = stdscr.getch()
            if key in [ord('q'), ord('Q')]: break
            if key in [ord('c'), ord('C')]: ui.show_cores = not ui.show_cores
            if key == curses.KEY_RESIZE: curses.update_lines_cols()
            time.sleep(0.8)
        except (KeyboardInterrupt, curses.error): break

if __name__ == "__main__":
    if os.name == 'posix' and os.path.exists('/proc'):
        curses.wrapper(main)
    else:
        print("Linux with /proc required.")

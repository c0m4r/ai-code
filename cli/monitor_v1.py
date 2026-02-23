#!/usr/bin/env python3

import curses
import time
import os
import sys
from dataclasses import dataclass
from typing import Optional


@dataclass
class CPUStats:
    user: int
    nice: int
    system: int
    idle: int
    iowait: int
    irq: int
    softirq: int
    steal: int

    @property
    def total(self) -> int:
        return self.user + self.nice + self.system + self.idle + self.iowait + self.irq + self.softirq + self.steal

    @property
    def active(self) -> int:
        return self.total - self.idle - self.iowait


@dataclass
class NetworkStats:
    rx_bytes: int
    tx_bytes: int
    timestamp: float


@dataclass
class SystemMetrics:
    cpu_percent: float
    cpu_per_core: list[float]
    memory_total: int
    memory_used: int
    memory_percent: float
    swap_total: int
    swap_used: int
    swap_percent: float
    load_1: float
    load_5: float
    load_15: float
    net_download_speed: float
    net_upload_speed: float
    cpu_count: int


class HardwareMonitor:
    def __init__(self):
        self._prev_cpu_stats: Optional[CPUStats] = None
        self._prev_cpu_per_core: list[Optional[CPUStats]] = []
        self._prev_net_stats: Optional[NetworkStats] = None

    def _read_cpu_stats(self) -> tuple[Optional[CPUStats], list[CPUStats]]:
        with open('/proc/stat', 'r') as f:
            lines = f.readlines()

        aggregate = None
        per_core = []

        for line in lines:
            if line.startswith('cpu'):
                parts = line.split()
                stats = CPUStats(
                    user=int(parts[1]),
                    nice=int(parts[2]),
                    system=int(parts[3]),
                    idle=int(parts[4]),
                    iowait=int(parts[5]) if len(parts) > 5 else 0,
                    irq=int(parts[6]) if len(parts) > 6 else 0,
                    softirq=int(parts[7]) if len(parts) > 7 else 0,
                    steal=int(parts[8]) if len(parts) > 8 else 0
                )
                if parts[0] == 'cpu':
                    aggregate = stats
                else:
                    per_core.append(stats)

        return aggregate, per_core

    def _calculate_cpu_percent(self, prev: CPUStats, curr: CPUStats) -> float:
        total_diff = curr.total - prev.total
        if total_diff == 0:
            return 0.0
        active_diff = curr.active - prev.active
        return (active_diff / total_diff) * 100

    def _read_memory_info(self) -> tuple[int, int, int, int]:
        mem_info = {}
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                parts = line.split()
                key = parts[0].rstrip(':')
                value = int(parts[1]) * 1024
                mem_info[key] = value

        mem_total = mem_info.get('MemTotal', 0)
        mem_free = mem_info.get('MemFree', 0)
        mem_buffers = mem_info.get('Buffers', 0)
        mem_cached = mem_info.get('Cached', 0)
        mem_sreclaimable = mem_info.get('SReclaimable', 0)

        mem_used = mem_total - mem_free - mem_buffers - mem_cached - mem_sreclaimable

        swap_total = mem_info.get('SwapTotal', 0)
        swap_free = mem_info.get('SwapFree', 0)
        swap_used = swap_total - swap_free

        return mem_total, mem_used, swap_total, swap_used

    def _read_load_average(self) -> tuple[float, float, float]:
        with open('/proc/loadavg', 'r') as f:
            parts = f.read().split()
        return float(parts[0]), float(parts[1]), float(parts[2])

    def _read_network_stats(self) -> NetworkStats:
        rx_bytes = 0
        tx_bytes = 0

        with open('/proc/net/dev', 'r') as f:
            lines = f.readlines()[2:]

        for line in lines:
            parts = line.split()
            interface = parts[0].rstrip(':')
            if interface == 'lo':
                continue
            rx_bytes += int(parts[1])
            tx_bytes += int(parts[9])

        return NetworkStats(rx_bytes=rx_bytes, tx_bytes=tx_bytes, timestamp=time.time())

    def get_metrics(self) -> SystemMetrics:
        curr_cpu, curr_per_core = self._read_cpu_stats()

        # Calculate CPU Percent
        if self._prev_cpu_stats is None or curr_cpu is None:
            cpu_percent = 0.0
        else:
            cpu_percent = self._calculate_cpu_percent(self._prev_cpu_stats, curr_cpu)

        # Calculate Per-Core Percent
        cpu_per_core = []
        if not self._prev_cpu_per_core:
            cpu_per_core = [0.0] * len(curr_per_core)
        else:
            for prev, curr in zip(self._prev_cpu_per_core, curr_per_core):
                if prev is None:
                    cpu_per_core.append(0.0)
                else:
                    cpu_per_core.append(self._calculate_cpu_percent(prev, curr))

        self._prev_cpu_stats = curr_cpu
        self._prev_cpu_per_core = curr_per_core

        # Memory
        mem_total, mem_used, swap_total, swap_used = self._read_memory_info()
        mem_percent = (mem_used / mem_total * 100) if mem_total > 0 else 0.0
        swap_percent = (swap_used / swap_total * 100) if swap_total > 0 else 0.0

        # Load
        load_1, load_5, load_15 = self._read_load_average()

        # Network
        curr_net = self._read_network_stats()
        if self._prev_net_stats is None:
            download_speed = 0.0
            upload_speed = 0.0
        else:
            time_diff = curr_net.timestamp - self._prev_net_stats.timestamp
            if time_diff > 0:
                download_speed = (curr_net.rx_bytes - self._prev_net_stats.rx_bytes) / time_diff
                upload_speed = (curr_net.tx_bytes - self._prev_net_stats.tx_bytes) / time_diff
            else:
                download_speed = 0.0
                upload_speed = 0.0

        self._prev_net_stats = curr_net

        return SystemMetrics(
            cpu_percent=cpu_percent,
            cpu_per_core=cpu_per_core,
            memory_total=mem_total,
            memory_used=mem_used,
            memory_percent=mem_percent,
            swap_total=swap_total,
            swap_used=swap_used,
            swap_percent=swap_percent,
            load_1=load_1,
            load_5=load_5,
            load_15=load_15,
            net_download_speed=download_speed,
            net_upload_speed=upload_speed,
            cpu_count=len(curr_per_core)
        )


class UI:
    COLORS = {
        'normal': 1,
        'warning': 2,
        'critical': 3,
        'header': 4,
        'border': 5,
        'highlight': 6,
        'good': 7,
    }

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self._setup_colors()
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.timeout(1000)

    def _setup_colors(self):
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_WHITE, -1)
        curses.init_pair(2, curses.COLOR_YELLOW, -1)
        curses.init_pair(3, curses.COLOR_RED, -1)
        curses.init_pair(4, curses.COLOR_CYAN, -1)
        curses.init_pair(5, curses.COLOR_BLUE, -1)
        curses.init_pair(6, curses.COLOR_GREEN, -1)
        curses.init_pair(7, curses.COLOR_GREEN, -1)

    def _get_color_for_percent(self, percent: float) -> int:
        if percent < 60:
            return curses.color_pair(self.COLORS['good'])
        elif percent < 80:
            return curses.color_pair(self.COLORS['warning'])
        else:
            return curses.color_pair(self.COLORS['critical'])

    def _format_bytes(self, bytes_val: float) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(bytes_val) < 1024.0:
                return f"{bytes_val:6.1f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:6.1f} PB"

    def _format_bytes_memory(self, bytes_val: int) -> str:
        val = float(bytes_val)
        for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
            if abs(val) < 1024.0:
                return f"{val:.1f} {unit}"
            val /= 1024.0
        return f"{val:.1f} PiB"

    def _draw_progress_bar(self, y: int, x: int, width: int, percent: float, label: str = ""):
        if width < 10:
            return

        bar_width = width - 2
        filled = int(bar_width * percent / 100)
        empty = bar_width - filled

        color = self._get_color_for_percent(percent)

        self.stdscr.addstr(y, x, "[", curses.color_pair(self.COLORS['border']))
        self.stdscr.addstr(y, x + 1, "█" * filled, color | curses.A_BOLD)
        self.stdscr.addstr(y, x + 1 + filled, "░" * empty, curses.color_pair(self.COLORS['normal']))
        self.stdscr.addstr(y, x + width - 1, "]", curses.color_pair(self.COLORS['border']))

        if label:
            label_pos = x + (width - len(label)) // 2
            if label_pos > x and label_pos + len(label) < x + width:
                self.stdscr.addstr(y, label_pos, label, curses.A_BOLD)

    def _draw_box(self, y: int, x: int, height: int, width: int, title: str = ""):
        border_color = curses.color_pair(self.COLORS['border'])
        header_color = curses.color_pair(self.COLORS['header']) | curses.A_BOLD

        self.stdscr.addstr(y, x, "╭" + "─" * (width - 2) + "╮", border_color)

        for i in range(1, height - 1):
            self.stdscr.addstr(y + i, x, "│", border_color)
            self.stdscr.addstr(y + i, x + width - 1, "│", border_color)

        self.stdscr.addstr(y + height - 1, x, "╰" + "─" * (width - 2) + "╯", border_color)

        if title:
            title_str = f" {title} "
            title_x = x + (width - len(title_str)) // 2
            self.stdscr.addstr(y, title_x, title_str, header_color)

    def draw(self, metrics: SystemMetrics):
        self.stdscr.clear()
        max_y, max_x = self.stdscr.getmaxyx()

        if max_y < 20 or max_x < 60:
            self.stdscr.addstr(0, 0, "Terminal too small. Please resize.", curses.color_pair(self.COLORS['critical']))
            self.stdscr.refresh()
            return

        header = "═══ HARDWARE MONITOR ═══"
        header_x = (max_x - len(header)) // 2
        self.stdscr.addstr(0, header_x, header, curses.color_pair(self.COLORS['header']) | curses.A_BOLD)

        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.stdscr.addstr(1, max_x - len(current_time) - 2, current_time, curses.color_pair(self.COLORS['normal']))

        box_width = max_x - 4
        cpu_box_height = 4 + (metrics.cpu_count + 1) // 2 if metrics.cpu_count > 4 else 4 + metrics.cpu_count

        self._draw_box(3, 2, cpu_box_height, box_width, "CPU")

        cpu_label = f"{metrics.cpu_percent:5.1f}%"
        self.stdscr.addstr(4, 4, "Total:", curses.color_pair(self.COLORS['normal']) | curses.A_BOLD)
        self._draw_progress_bar(4, 12, box_width - 14, metrics.cpu_percent, cpu_label)

        cores_per_row = 2 if metrics.cpu_count > 4 else 1
        core_width = (box_width - 8) // cores_per_row - 2

        for i, core_percent in enumerate(metrics.cpu_per_core):
            row = i // cores_per_row
            col = i % cores_per_row
            y_pos = 5 + row
            x_pos = 4 + col * (core_width + 4)

            self.stdscr.addstr(y_pos, x_pos, f"C{i}:", curses.color_pair(self.COLORS['normal']))
            self._draw_progress_bar(y_pos, x_pos + 4, core_width - 4, core_percent)

        mem_box_y = 3 + cpu_box_height + 1
        self._draw_box(mem_box_y, 2, 6, box_width, "MEMORY")

        mem_used_str = self._format_bytes_memory(metrics.memory_used)
        mem_total_str = self._format_bytes_memory(metrics.memory_total)
        mem_label = f"{metrics.memory_percent:5.1f}% ({mem_used_str} / {mem_total_str})"

        self.stdscr.addstr(mem_box_y + 1, 4, "RAM :", curses.color_pair(self.COLORS['normal']) | curses.A_BOLD)
        self._draw_progress_bar(mem_box_y + 1, 10, box_width - 12, metrics.memory_percent)
        self.stdscr.addstr(mem_box_y + 2, 10, mem_label, self._get_color_for_percent(metrics.memory_percent))

        swap_used_str = self._format_bytes_memory(metrics.swap_used)
        swap_total_str = self._format_bytes_memory(metrics.swap_total)
        swap_label = f"{metrics.swap_percent:5.1f}% ({swap_used_str} / {swap_total_str})"

        self.stdscr.addstr(mem_box_y + 4, 4, "SWAP:", curses.color_pair(self.COLORS['normal']) | curses.A_BOLD)
        self._draw_progress_bar(mem_box_y + 4, 10, box_width - 12, metrics.swap_percent)
        self.stdscr.addstr(mem_box_y + 5, 10, swap_label, self._get_color_for_percent(metrics.swap_percent))

        load_box_y = mem_box_y + 7
        self._draw_box(load_box_y, 2, 4, box_width, "LOAD AVERAGE")

        load_color_1 = self._get_color_for_percent(min(metrics.load_1 / metrics.cpu_count * 100, 100))
        load_color_5 = self._get_color_for_percent(min(metrics.load_5 / metrics.cpu_count * 100, 100))
        load_color_15 = self._get_color_for_percent(min(metrics.load_15 / metrics.cpu_count * 100, 100))

        self.stdscr.addstr(load_box_y + 1, 4, "1 min:", curses.color_pair(self.COLORS['normal']) | curses.A_BOLD)
        self.stdscr.addstr(load_box_y + 1, 12, f"{metrics.load_1:.2f}", load_color_1 | curses.A_BOLD)

        self.stdscr.addstr(load_box_y + 1, 22, "5 min:", curses.color_pair(self.COLORS['normal']) | curses.A_BOLD)
        self.stdscr.addstr(load_box_y + 1, 30, f"{metrics.load_5:.2f}", load_color_5 | curses.A_BOLD)

        self.stdscr.addstr(load_box_y + 1, 40, "15 min:", curses.color_pair(self.COLORS['normal']) | curses.A_BOLD)
        self.stdscr.addstr(load_box_y + 1, 49, f"{metrics.load_15:.2f}", load_color_15 | curses.A_BOLD)

        net_box_y = load_box_y + 5
        self._draw_box(net_box_y, 2, 4, box_width, "NETWORK")

        download_str = self._format_bytes(metrics.net_download_speed)
        upload_str = self._format_bytes(metrics.net_upload_speed)

        self.stdscr.addstr(net_box_y + 1, 4, "↓ Download:", curses.color_pair(self.COLORS['good']) | curses.A_BOLD)
        self.stdscr.addstr(net_box_y + 1, 17, f"{download_str}/s", curses.color_pair(self.COLORS['normal']))

        self.stdscr.addstr(net_box_y + 2, 4, "↑ Upload:  ", curses.color_pair(self.COLORS['warning']) | curses.A_BOLD)
        self.stdscr.addstr(net_box_y + 2, 17, f"{upload_str}/s", curses.color_pair(self.COLORS['normal']))

        footer = "Press 'q' to quit | Refresh: 1s"
        footer_x = (max_x - len(footer)) // 2
        self.stdscr.addstr(max_y - 1, footer_x, footer, curses.color_pair(self.COLORS['border']))

        self.stdscr.refresh()


def main(stdscr):
    monitor = HardwareMonitor()
    ui = UI(stdscr)

    # Initial call to populate stats
    monitor.get_metrics()
    time.sleep(0.1)

    while True:
        try:
            metrics = monitor.get_metrics()
            ui.draw(metrics)

            key = stdscr.getch()
            if key == ord('q') or key == ord('Q'):
                break

            time.sleep(0.9)

        except KeyboardInterrupt:
            break
        except curses.error:
            pass


def run():
    if os.name != 'posix' or not os.path.exists('/proc'):
        print("This program only runs on Linux systems.", file=sys.stderr)
        sys.exit(1)

    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()

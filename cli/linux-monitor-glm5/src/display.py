"""
Display module for rendering system metrics using Rich TUI.
Provides beautiful tables, progress bars, and live updating displays.
"""

from rich.console import Console
from rich.table import Table
from rich.progress import BarColumn, Progress, TextColumn
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.live import Live
from datetime import timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .metrics import SystemMetrics

console = Console()


class DisplayManager:
    """
    Manages the visual display of system metrics using Rich library.
    Creates formatted tables, progress bars, and panels for monitoring.
    """
    
    # Color thresholds for progress bars
    COLOR_THRESHOLDS = [
        (50, "green"),
        (75, "yellow"),
        (90, "orange1"),
        (100, "red")
    ]
    
    def __init__(self):
        self.console = Console()
    
    def _get_color_for_percent(self, percent: float) -> str:
        """
        Determine color based on percentage value.
        
        Args:
            percent: Usage percentage (0-100)
            
        Returns:
            Color name string
        """
        for threshold, color in self.COLOR_THRESHOLDS:
            if percent < threshold:
                return color
        return "red"
    
    def _format_bar(self, percent: float, width: int = 20) -> str:
        """
        Create a text-based progress bar.
        
        Args:
            percent: Usage percentage
            width: Bar width in characters
            
        Returns:
            Formatted progress bar string
        """
        filled = int((percent / 100) * width)
        empty = width - filled
        color = self._get_color_for_percent(percent)
        bar = f"[{color}]{'█' * filled}{'░' * empty}[/{color}]"
        return bar
    
    def _format_uptime(self, seconds: int) -> str:
        """
        Format uptime seconds to human readable string.
        
        Args:
            seconds: Uptime in seconds
            
        Returns:
            Formatted uptime string (e.g., "2d 5h 30m")
        """
        td = timedelta(seconds=seconds)
        days = td.days
        hours, remainder = divmod(td.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0 or days > 0:
            parts.append(f"{hours}h")
        parts.append(f"{minutes}m")
        
        return " ".join(parts)
    
    def create_metrics_table(self, metrics: 'SystemMetrics') -> Table:
        """
        Create main metrics display table.
        
        Args:
            metrics: SystemMetrics dataclass with current values
            
        Returns:
            Rich Table object
        """
        table = Table(
            title="[bold cyan]Linux Resource Monitor[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
            border_style="blue",
            expand=True
        )
        
        table.add_column("Resource", style="cyan", width=15)
        table.add_column("Usage", justify="right", width=10)
        table.add_column("Bar", width=22)
        table.add_column("Details", style="dim")
        
        # CPU Row
        cpu_color = self._get_color_for_percent(metrics.cpu.percent)
        table.add_row(
            "[bold]CPU[/bold]",
            f"[{cpu_color}]{metrics.cpu.percent:.1f}%[/{cpu_color}]",
            self._format_bar(metrics.cpu.percent),
            f"Freq: {metrics.cpu.freq_current:.0f}/{metrics.cpu.freq_max:.0f} MHz"
        )
        
        # Per-core CPU (show first 4 cores if available)
        if metrics.cpu.per_core:
            core_display = metrics.cpu.per_core[:4]
            core_str = " | ".join([f"C{i}: {v:.0f}%" for i, v in enumerate(core_display)])
            if len(metrics.cpu.per_core) > 4:
                core_str += f" (+{len(metrics.cpu.per_core) - 4} more)"
            table.add_row(
                "  Cores",
                "",
                "",
                core_str
            )
        
        # Memory Row
        mem_color = self._get_color_for_percent(metrics.memory.percent)
        table.add_row(
            "[bold]RAM[/bold]",
            f"[{mem_color}]{metrics.memory.percent:.1f}%[/{mem_color}]",
            self._format_bar(metrics.memory.percent),
            f"{metrics.memory.used_gb:.1f} / {metrics.memory.total_gb:.1f} GB"
        )
        
        # Swap Row
        if metrics.swap.total_gb > 0:
            swap_color = self._get_color_for_percent(metrics.swap.percent)
            table.add_row(
                "[bold]Swap[/bold]",
                f"[{swap_color}]{metrics.swap.percent:.1f}%[/{swap_color}]",
                self._format_bar(metrics.swap.percent),
                f"{metrics.swap.used_gb:.2f} / {metrics.swap.total_gb:.2f} GB"
            )
        else:
            table.add_row(
                "[bold]Swap[/bold]",
                "[dim]N/A[/dim]",
                "[dim]No swap configured[/dim]",
                ""
            )
        
        # Load Average Row
        n_cpus = len(metrics.cpu.per_core) if metrics.cpu.per_core else 1
        load_color = "green" if metrics.load_avg.load_1 < n_cpus else "red"
        table.add_row(
            "[bold]Load Avg[/bold]",
            f"[{load_color}]{metrics.load_avg.load_1:.2f}[/{load_color}]",
            f"5m: {metrics.load_avg.load_5:.2f} | 15m: {metrics.load_avg.load_15:.2f}",
            f"Procs: {metrics.load_avg.process_count} (Running: {metrics.load_avg.running_processes})"
        )
        
        # Network Row
        dl_color = "green" if metrics.network.download_mbps > 0 else "dim"
        up_color = "cyan" if metrics.network.upload_mbps > 0 else "dim"
        table.add_row(
            "[bold]Network[/bold]",
            "",
            "",
            ""
        )
        table.add_row(
            "  ↓ Download",
            f"[{dl_color}]{metrics.network.download_mbps:.2f} Mbps[/{dl_color}]",
            "",
            f"Total: {metrics.network.total_dl_gb:.2f} GB"
        )
        table.add_row(
            "  ↑ Upload",
            f"[{up_color}]{metrics.network.upload_mbps:.2f} Mbps[/{up_color}]",
            "",
            f"Total: {metrics.network.total_up_gb:.2f} GB"
        )
        
        # Uptime Row
        table.add_row(
            "[bold]Uptime[/bold]",
            "",
            "",
            self._format_uptime(metrics.uptime_seconds)
        )
        
        return table
    
    def create_compact_display(self, metrics: 'SystemMetrics') -> Panel:
        """
        Create a compact single-line display.
        
        Args:
            metrics: SystemMetrics dataclass
            
        Returns:
            Rich Panel with compact metrics
        """
        cpu_color = self._get_color_for_percent(metrics.cpu.percent)
        mem_color = self._get_color_for_percent(metrics.memory.percent)
        
        content = Text()
        content.append("CPU: ")
        content.append(f"{metrics.cpu.percent:.1f}%", style=cpu_color)
        content.append(" | RAM: ")
        content.append(f"{metrics.memory.percent:.1f}%", style=mem_color)
        content.append(f" | Load: {metrics.load_avg.load_1:.2f}")
        content.append(" | Net: ")
        content.append(f"↓{metrics.network.download_mbps:.1f}", style="green")
        content.append(" ")
        content.append(f"↑{metrics.network.upload_mbps:.1f}", style="cyan")
        content.append(" Mbps")
        
        return Panel(
            content,
            title="[bold]System Status[/bold]",
            border_style="blue"
        )
    
    def create_network_panel(self, metrics: 'SystemMetrics') -> Panel:
        """
        Create detailed network statistics panel.
        
        Args:
            metrics: SystemMetrics dataclass
            
        Returns:
            Rich Panel with network details
        """
        table = Table(show_header=False, expand=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")
        
        table.add_row("Current Download", f"[green]{metrics.network.download_mbps:.2f} Mbps[/green]")
        table.add_row("Current Upload", f"[cyan]{metrics.network.upload_mbps:.2f} Mbps[/cyan]")
        table.add_row("Total Downloaded", f"{metrics.network.total_dl_gb:.3f} GB")
        table.add_row("Total Uploaded", f"{metrics.network.total_up_gb:.3f} GB")
        
        # Calculate ratio
        if metrics.network.total_up_gb > 0:
            ratio = metrics.network.total_dl_gb / metrics.network.total_up_gb
            table.add_row("DL/UL Ratio", f"{ratio:.2f}")
        
        return Panel(
            table,
            title="[bold]Network Statistics[/bold]",
            border_style="green"
        )
    
    def create_cpu_panel(self, metrics: 'SystemMetrics') -> Panel:
        """
        Create detailed CPU statistics panel.
        
        Args:
            metrics: SystemMetrics dataclass
            
        Returns:
            Rich Panel with CPU details
        """
        table = Table(show_header=False, expand=True)
        table.add_column("Core", style="cyan")
        table.add_column("Usage", justify="right")
        table.add_column("Bar", width=15)
        
        # Overall
        table.add_row(
            "[bold]Overall[/bold]",
            f"[{self._get_color_for_percent(metrics.cpu.percent)}]{metrics.cpu.percent:.1f}%[/{self._get_color_for_percent(metrics.cpu.percent)}]",
            self._format_bar(metrics.cpu.percent, 15)
        )
        
        # Per core
        for i, core_percent in enumerate(metrics.cpu.per_core):
            color = self._get_color_for_percent(core_percent)
            table.add_row(
                f"Core {i}",
                f"[{color}]{core_percent:.1f}%[/{color}]",
                self._format_bar(core_percent, 15)
            )
        
        return Panel(
            table,
            title=f"[bold]CPU @ {metrics.cpu.freq_current:.0f} MHz[/bold]",
            border_style="yellow"
        )
    
    def print_static(self, metrics: 'SystemMetrics') -> None:
        """
        Print a static snapshot of metrics to console.
        
        Args:
            metrics: SystemMetrics dataclass
        """
        self.console.clear()
        self.console.print(self.create_metrics_table(metrics))
    
    def get_renderable(self, metrics: 'SystemMetrics') -> Layout:
        """
        Create a full layout for live display.
        
        Args:
            metrics: SystemMetrics dataclass
            
        Returns:
            Rich Layout object
        """
        layout = Layout()
        
        layout.split(
            Layout(name="main", ratio=2),
            Layout(name="bottom", ratio=1)
        )
        
        layout["main"].update(self.create_metrics_table(metrics))
        
        # Split bottom into CPU and Network panels
        layout["bottom"].split_row(
            Layout(name="cpu"),
            Layout(name="network")
        )
        
        layout["bottom"]["cpu"].update(self.create_cpu_panel(metrics))
        layout["bottom"]["network"].update(self.create_network_panel(metrics))
        
        return layout


def print_header(console: Console = None) -> None:
    """Print application header."""
    if console is None:
        console = Console()
    
    console.print(Panel(
        "[bold cyan]Linux Resource Monitor v1.0.0[/bold cyan]\n"
        "[dim]Real-time system monitoring tool[/dim]",
        border_style="blue"
    ))

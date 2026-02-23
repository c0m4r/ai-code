"""
Main monitoring loop orchestration module.
Coordinates metrics collection and display updates.
"""

import time
import signal
import sys
from typing import Optional, Callable

from .metrics import MetricsCollector, SystemMetrics
from .display import DisplayManager, print_header


class ResourceMonitor:
    """
    Main resource monitor class that orchestrates collection and display.
    Supports both live updating and one-shot monitoring modes.
    """
    
    def __init__(
        self,
        refresh_rate: float = 1.0,
        show_header: bool = True,
        compact: bool = False
    ):
        """
        Initialize the resource monitor.
        
        Args:
            refresh_rate: How often to update metrics (seconds)
            show_header: Whether to show application header
            compact: Use compact display mode
        """
        self.refresh_rate = refresh_rate
        self.show_header = show_header
        self.compact = compact
        
        self.collector = MetricsCollector()
        self.display = DisplayManager()
        self._running = False
        self._callbacks: list[Callable[[SystemMetrics], None]] = []
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle termination signals gracefully."""
        self._running = False
        self.display.console.print("\n[yellow]Shutting down monitor...[/yellow]")
        sys.exit(0)
    
    def add_callback(self, callback: Callable[[SystemMetrics], None]) -> None:
        """
        Add a callback to be called on each metrics update.
        
        Args:
            callback: Function that receives SystemMetrics
        """
        self._callbacks.append(callback)
    
    def _run_callbacks(self, metrics: SystemMetrics) -> None:
        """Run all registered callbacks with current metrics."""
        for callback in self._callbacks:
            try:
                callback(metrics)
            except Exception as e:
                self.display.console.print(
                    f"[red]Callback error: {e}[/red]"
                )
    
    def collect_metrics(self) -> SystemMetrics:
        """
        Collect current system metrics.
        
        Returns:
            SystemMetrics dataclass with all current values
        """
        return self.collector.collect_all(cpu_interval=self.refresh_rate * 0.1)
    
    def display_metrics(self, metrics: SystemMetrics) -> None:
        """
        Display metrics using configured display mode.
        
        Args:
            metrics: SystemMetrics to display
        """
        if self.compact:
            self.display.console.print(
                self.display.create_compact_display(metrics)
            )
        else:
            self.display.print_static(metrics)
    
    def run_once(self) -> SystemMetrics:
        """
        Collect and display metrics once.
        
        Returns:
            Collected SystemMetrics
        """
        if self.show_header:
            print_header(self.display.console)
        
        metrics = self.collect_metrics()
        self.display_metrics(metrics)
        
        return metrics
    
    def run_continuous(self) -> None:
        """
        Run continuous monitoring with live updates.
        Uses Rich Live for smooth terminal updates.
        """
        from rich.live import Live
        
        self._running = True
        
        if self.show_header:
            print_header(self.display.console)
            time.sleep(0.5)  # Brief pause to show header
        
        # Initial collection to establish network baseline
        self.collector.get_network_metrics()
        time.sleep(0.1)
        
        def get_display():
            metrics = self.collect_metrics()
            self._run_callbacks(metrics)
            
            if self.compact:
                return self.display.create_compact_display(metrics)
            else:
                return self.display.get_renderable(metrics)
        
        try:
            with Live(
                get_display(),
                refresh_per_second=1 / self.refresh_rate,
                console=self.display.console,
                screen=not self.compact
            ) as live:
                while self._running:
                    time.sleep(self.refresh_rate)
                    live.update(get_display())
        except KeyboardInterrupt:
            self._running = False
            self.display.console.print(
                "\n[green]Monitor stopped.[/green]"
            )
    
    def run(self, continuous: bool = True) -> Optional[SystemMetrics]:
        """
        Start the monitor.
        
        Args:
            continuous: If True, run continuously; if False, run once
            
        Returns:
            SystemMetrics if running once, None otherwise
        """
        if continuous:
            self.run_continuous()
            return None
        else:
            return self.run_once()
    
    def stop(self) -> None:
        """Stop continuous monitoring."""
        self._running = False


def create_monitor(
    refresh_rate: float = 1.0,
    compact: bool = False,
    show_header: bool = True
) -> ResourceMonitor:
    """
    Factory function to create a configured ResourceMonitor.
    
    Args:
        refresh_rate: Update interval in seconds
        compact: Use compact display mode
        show_header: Show application header
        
    Returns:
        Configured ResourceMonitor instance
    """
    return ResourceMonitor(
        refresh_rate=refresh_rate,
        compact=compact,
        show_header=show_header
    )

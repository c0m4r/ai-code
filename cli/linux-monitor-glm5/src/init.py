"""
Linux Resource Monitor - A real-time system monitoring tool.
"""

__version__ = "1.0.0"
__author__ = "Linux Monitor Team"

from .monitor import ResourceMonitor
from .metrics import MetricsCollector
from .display import DisplayManager

__all__ = ["ResourceMonitor", "MetricsCollector", "DisplayManager"]

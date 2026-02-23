# Linux Resource Monitor

A real-time system monitoring tool for Linux that displays CPU, RAM, Swap, Load Average, and Network throughput in a beautiful terminal interface.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- **CPU Monitoring**: Overall and per-core usage with frequency display
- **Memory (RAM)**: Usage percentage with GB values
- **Swap Memory**: Usage tracking with percentage bar
- **Load Average**: 1, 5, and 15-minute load averages with process counts
- **Network Throughput**: Real-time download/upload speeds in Mbps
- **System Uptime**: Human-readable uptime display

## Screenshots

```
╭───────────────── Linux Resource Monitor ─────────────────╮
│ Resource    Usage         Bar                  Details    │
├───────────────────────────────────────────────────────────┤
│ CPU         45.2%   ██████████░░░░░░░░░░    Freq: 2400 MHz│
│   Cores                                       C0: 42% | ...│
│ RAM         68.5%   ██████████████░░░░░░    5.5 / 8.0 GB  │
│ Swap        12.3%   ██░░░░░░░░░░░░░░░░░░░    0.25 / 2.0 GB│
│ Load Avg    1.25    5m: 1.10 | 15m: 0.95    Procs: 245    │
│ Network                                                  │
│   ↓ Download  25.50 Mbps                      Total: 15GB │
│   ↑ Upload     5.25 Mbps                      Total: 3GB  │
│ Uptime                                     2d 5h 30m      │
╰───────────────────────────────────────────────────────────╯
```

## Installation

### Prerequisites

- Python 3.8 or higher
- Linux operating system

### Install Dependencies

```bash
cd linux-monitor
pip install -r requirements.txt
```

## Usage

### Basic Usage (Continuous Monitoring)

```bash
python run.py
```

### Command-Line Options

```bash
# Show metrics once and exit
python run.py --once

# Custom refresh rate (0.5 seconds)
python run.py -r 0.5

# Compact single-line display
python run.py --compact

# Hide header
python run.py --no-header

# Show help
python run.py --help
```

### Options Reference

| Option | Short | Description |
|--------|-------|-------------|
| `--refresh-rate SECONDS` | `-r` | Update interval (default: 1.0) |
| `--once` | `-o` | Show metrics once and exit |
| `--compact` | `-c` | Use compact single-line display |
| `--no-header` | | Hide application header |
| `--version` | `-v` | Show version information |
| `--help` | `-h` | Show help message |

## Project Structure

```
linux-monitor/
├── src/
│   ├── __init__.py      # Package initialization
│   ├── metrics.py       # Core metrics collection (psutil)
│   ├── display.py       # Rich TUI display formatting
│   └── monitor.py       # Main monitoring orchestration
├── requirements.txt     # Python dependencies
├── README.md            # This file
└── run.py               # Entry point script
```

## API Usage

You can also use the monitor as a library:

```python
from src.monitor import create_monitor

# Create and run continuous monitor
monitor = create_monitor(refresh_rate=1.0, compact=False)
monitor.run()

# Or get metrics once
metrics = monitor.run(continuous=False)
print(f"CPU: {metrics.cpu.percent}%")
print(f"RAM: {metrics.memory.percent}%")
print(f"Net DL: {metrics.network.download_mbps} Mbps")
```

## Metrics Explained

### CPU
- **Percent**: Overall CPU usage across all cores
- **Per-core**: Individual core usage percentages
- **Frequency**: Current and maximum CPU frequency

### Memory (RAM)
- **Total**: Total installed RAM
- **Used**: Currently used RAM
- **Available**: RAM available for allocation
- **Percent**: Usage percentage

### Swap
- Virtual memory usage when RAM is full
- Shows total, used, and percentage

### Load Average
- Average number of processes waiting for CPU time
- Load < CPU count = system is handling load well
- Load > CPU count = system may be overloaded

### Network
- **Download/Upload Mbps**: Real-time throughput
- **Total**: Cumulative data transferred since boot

## Troubleshooting

### Permission Denied
Some metrics may require elevated permissions:
```bash
sudo python run.py
```

### Missing Metrics
If swap shows N/A, your system may not have swap configured.

## License

MIT License - Feel free to use and modify.

## Contributing

Contributions welcome! Please open an issue or pull request for any improvements.

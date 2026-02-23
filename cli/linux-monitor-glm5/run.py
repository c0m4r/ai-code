#!/usr/bin/env python3
"""
Entry point script for Linux Resource Monitor.
Provides command-line interface for running the monitor.
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.monitor import create_monitor


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Linux Resource Monitor - Real-time system monitoring tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Run continuous monitoring (default)
  %(prog)s --once             Show metrics once and exit
  %(prog)s -r 0.5             Update every 0.5 seconds
  %(prog)s --compact          Use compact single-line display
  %(prog)s --no-header        Hide application header
        """
    )
    
    parser.add_argument(
        "-r", "--refresh-rate",
        type=float,
        default=1.0,
        metavar="SECONDS",
        help="Refresh rate for continuous monitoring (default: 1.0)"
    )
    
    parser.add_argument(
        "-o", "--once",
        action="store_true",
        help="Show metrics once and exit (non-continuous mode)"
    )
    
    parser.add_argument(
        "-c", "--compact",
        action="store_true",
        help="Use compact single-line display mode"
    )
    
    parser.add_argument(
        "--no-header",
        action="store_true",
        help="Hide application header"
    )
    
    parser.add_argument(
        "-v", "--version",
        action="version",
        version="%(prog)s 1.0.0"
    )
    
    return parser.parse_args()


def main() -> int:
    """
    Main entry point function.
    
    Returns:
        Exit code (0 for success)
    """
    args = parse_arguments()
    
    # Validate refresh rate
    if args.refresh_rate <= 0:
        print("Error: Refresh rate must be positive", file=sys.stderr)
        return 1
    
    # Create monitor with parsed options
    monitor = create_monitor(
        refresh_rate=args.refresh_rate,
        compact=args.compact,
        show_header=not args.no_header
    )
    
    try:
        # Run monitor
        monitor.run(continuous=not args.once)
        return 0
    except KeyboardInterrupt:
        # Clean exit on Ctrl+C
        return 0
    except PermissionError as e:
        print(f"Permission error: {e}", file=sys.stderr)
        print("Try running with appropriate permissions.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

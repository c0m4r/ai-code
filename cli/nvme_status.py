#!/usr/bin/env python3
"""
Read an NVMe drive's health information and print:

  * Lifetime usage (% of rated writes)
  * Current temperature (Celsius)
  * Any error / warning bits reported by the drive

Requires:
    - Linux
    - nvme-cli (`nvme` command) installed and reachable in $PATH
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import json
from typing import Dict, List, Any


def call_nvme(args: List[str]) -> str:
    """Run `nvme <args>` and return stdout as text.

    Raises RuntimeError if the command returns a non‑zero exit code.
    """
    try:
        result = subprocess.run(
            ["nvme"] + args,
            capture_output=True,
            text=True,
            check=True,               # raises CalledProcessError on failure
        )
        return result.stdout
    except FileNotFoundError:
        sys.exit("❌  `nvme` executable not found. Install the `nvme-cli` package.")
    except subprocess.CalledProcessError as e:
        sys.exit(
            f"❌  nvme command failed (exit {e.returncode}):\n"
            f"{e.stderr.strip() or e.stdout}"
        )


def parse_json_smart_log(output: str) -> Dict[str, Any]:
    """Parse the JSON produced by `nvme smart-log -o json`. """
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        sys.exit(f"❌  Failed to decode JSON from nvme output:\n{exc}")


def extract_info(data: Dict[str, Any]) -> tuple[int, int, List[str]]:
    """Return (percentage_used, temperature_C, list_of_error_messages)."""
    # ------------------------------------------------------------------
    # 1️⃣ Lifetime – the NVMe spec exposes a "percentage_used" field under
    #    `health`. It may be missing on some firmware versions; in that case
    #    we fall back to `smart_log` → `percentage_used` (lower‑case) or simply
    #    report “unknown”.
    health = data.get("health", {})
    pct_used: int | None = None
    if "percentage_used" in health:
        pct_used = int(health["percentage_used"])
    else:  # older parsers may store it under a different key name capitalisation
        pct_used = int(health.get("Percentage_Used") or health.get("percentused"))

    # ------------------------------------------------------------------
    # 2️⃣ Temperature – the JSON contains a list of temperature sensors.
    # The first one is usually the chassis/ambient sensor; we just report its
    # current value in Celsius.
    temps = data.get("temperature", [])
    temp_C: int = -1
    if isinstance(temps, list) and len(temps) > 0:
        try:
            cur_val = temps[0]["current"]["value"]
            # Some firmware reports it already in Kelvin; convert if needed.
            if isinstance(cur_val, (float, int)):
                if cur_val > 500:           # looks like milli‑Kelvin
                    temp_C = round((cur_val / 1000.0), 2)
                else:
                    temp_C = round(cur_val, 2)
            else:
                temp_C = -9   # unknown representation
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 3️⃣ Errors – the JSON includes a field `critical_warning`. It is a bit‑mask.
    #     Each bit corresponds to a specific warning condition defined by
    #     the NVMe spec. We map the bits to human‑readable names and also
    #     show any non‑empty *error log* pages if requested (they are stored under
    #     `error_log` → `entries` but not all devices populate them directly).

    warning_bitfield: int = int(data.get("critical_warning", 0))

    WARN_NAMES: Dict[int, str] = {
        1: "Critical Temperature",
        2: "Media Error",
        4: "Sudden Power Loss",
        8: "Other Critical Vendor‑Specific Event",
        # The exact set can vary by vendor; feel free to extend.
    }

    warning_msgs: List[str] = []
    for bit, name in WARN_NAMES.items():
        if warning_bitfield & bit:
            warning_msgs.append(name)

    # Add a generic "no warnings" message if the flag is zero
    if not warning_msgs:
        warning_msgs.append("No critical warnings")

    return pct_used or -1, temp_C or -1, warning_msgs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print health information (lifetime, temperature, errors) for an NVMe drive."
    )
    parser.add_argument(
        "device",
        help="Block device path of the NVMe SSD, e.g. /dev/nvme0 or nvme0n1",
    )
    args = parser.parse_args()

    dev: str = args.device

    # ------------------------------------------------------------------
    # 1️⃣ Run `nvme smart-log -o json <device>`
    raw_json = call_nvme(["smart-log", "-o", "json", dev])

    # ------------------------------------------------------------------
    # 2️⃣ Parse the JSON structure
    parsed = parse_json_smart_log(raw_json)

    pct_used, temp_C, warnings = extract_info(parsed)

    # ------------------------------------------------------------------
    # 3️⃣ Pretty‑print the result
    print(f"🔧 Device: {dev}")
    print()
    if isinstance(pct_used, int) and pct_used >= 0:
        print(f"📈 Lifetime usage      : {pct_used}% of rated writes")
    else:
        print("⚠️  Lifetime usage      : unknown (field 'percentage_used' not present)")
    if temp_C >= 0:
        print(f"🌡️  Temperature          : {temp_C} °C")
    else:
        print("⚠️  Temperature          : unknown / sensor missing")
    print()
    # Show each warning on its own line – might be multiple
    for w in warnings:
        if "No critical warnings" == w:
            print(f"✅  Status               : {w}")
        else:
            print(f"🚨  Warning              : {w}")

    # If you want to dump the whole JSON for debugging, uncomment:
    # print("\n--- Full nvme smart‑log JSON ---")
    # print(json.dumps(parsed, indent=2))


if __name__ == "__main__":
    main()

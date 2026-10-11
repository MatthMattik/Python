#!/usr/bin/env python3
"""
ip_monitor.py - Check the public IP every 20 minutes and log any change.

Usage:
    python ip_monitor.py            # run forever, checking every 20 minutes
    python ip_monitor.py --once     # check once and exit (for Task Scheduler / cron)
    python ip_monitor.py --interval 5   # custom interval in minutes

Log file: ip_changes.log (next to this script)
    2026-10-10 20:40:12  98.24.113.7  (first recorded)
    2026-10-12 03:20:45  98.24.119.201  (changed from 98.24.113.7)

Standard library only - no pip installs needed.
"""

import argparse
import ipaddress
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_FILE = SCRIPT_DIR / "ip_changes.log"

# Several services, tried in order, so one being down doesn't break the check.
IP_SERVICES = [
    "https://api.ipify.org",
    "https://ifconfig.me/ip",
    "https://icanhazip.com",
    "https://checkip.amazonaws.com",
]


def get_public_ip(timeout: int = 10) -> str | None:
    """Return the current public IP, or None if every service fails."""
    for url in IP_SERVICES:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ip-monitor/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                ip = resp.read().decode().strip()
            ipaddress.ip_address(ip)  # make sure it's a real IP, not an error page
            return ip
        except Exception as exc:  # network error, timeout, bad response
            print(f"[warn] {url} failed: {exc}", file=sys.stderr)
    return None


def last_logged_ip() -> str | None:
    """Read the most recent IP from the log file (the second column)."""
    if not LOG_FILE.exists():
        return None
    lines = [ln for ln in LOG_FILE.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        return None
    parts = lines[-1].split()
    return parts[2] if len(parts) >= 3 else None


def check_once() -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ip = get_public_ip()
    if ip is None:
        print(f"{now}  could not determine public IP (all services failed)", file=sys.stderr)
        return

    previous = last_logged_ip()
    if ip == previous:
        print(f"{now}  no change ({ip})")
        return

    note = "first recorded" if previous is None else f"changed from {previous}"
    entry = f"{now}  {ip}  ({note})"
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(entry + "\n")
    print(entry)


def main() -> None:
    parser = argparse.ArgumentParser(description="Log public IP changes.")
    parser.add_argument("--once", action="store_true", help="check once and exit")
    parser.add_argument("--interval", type=float, default=20, help="minutes between checks (default 20)")
    args = parser.parse_args()

    if args.once:
        check_once()
        return

    print(f"Checking public IP every {args.interval:g} minutes. Logging changes to {LOG_FILE}")
    print("Press Ctrl+C to stop.")
    try:
        while True:
            check_once()
            time.sleep(args.interval * 60)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()

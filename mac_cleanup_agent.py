#!/usr/bin/env python3
"""
Mac Cleanup Agent
-----------------
Frees disk space and improves performance on macOS.
Runs in DRY RUN mode by default — nothing is deleted until you confirm.

Usage:
  python3 mac_cleanup_agent.py           # dry run (safe preview)
  python3 mac_cleanup_agent.py --clean   # actually delete
  python3 mac_cleanup_agent.py --report  # disk + process report only
"""

import os
import sys
import shutil
import subprocess
import argparse
import platform
from pathlib import Path
from datetime import datetime

# ── ANSI colors ──────────────────────────────────────────────────────────────
R = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
DIM = "\033[2m"

def c(color, text): return f"{color}{text}{R}"
def header(text): print(f"\n{BOLD}{CYAN}{'─'*60}{R}\n{BOLD}{CYAN}  {text}{R}\n{CYAN}{'─'*60}{R}")
def ok(text): print(f"  {GREEN}✔{R}  {text}")
def warn(text): print(f"  {YELLOW}⚠{R}  {text}")
def info(text): print(f"  {BLUE}ℹ{R}  {text}")
def dry(text): print(f"  {DIM}~  {text}{R}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def human_size(num_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num_bytes) < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} PB"

def dir_size(path: Path) -> int:
    total = 0
    try:
        for entry in path.rglob("*"):
            try:
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat().st_size
            except (PermissionError, OSError):
                pass
    except (PermissionError, OSError):
        pass
    return total

def safe_remove(path: Path, dry_run: bool) -> int:
    """Delete a file or directory tree. Returns bytes freed (0 in dry run)."""
    try:
        size = dir_size(path) if path.is_dir() else path.stat().st_size
    except (PermissionError, OSError):
        size = 0
    if dry_run:
        dry(f"  would remove  {path}  ({human_size(size)})")
        return 0
    try:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
        return size
    except (PermissionError, OSError) as e:
        warn(f"  Could not remove {path}: {e}")
        return 0

def run(cmd: list, capture=True) -> str:
    try:
        result = subprocess.run(
            cmd, capture_output=capture, text=True, timeout=30
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


# ── 1. DISK REPORT ────────────────────────────────────────────────────────────

def disk_report():
    header("Disk usage report")
    df = run(["df", "-h", "/"])
    for line in df.splitlines():
        info(line)

    home = Path.home()
    big_dirs = [
        ("Downloads",        home / "Downloads"),
        ("Desktop",          home / "Desktop"),
        ("Documents",        home / "Documents"),
        ("Movies",           home / "Movies"),
        ("Library/Caches",   home / "Library" / "Caches"),
    ]
    print()
    for label, path in big_dirs:
        if path.exists():
            size = dir_size(path)
            info(f"{label:<25} {human_size(size)}")


# ── 2. PROCESS REPORT ─────────────────────────────────────────────────────────

def process_report():
    header("Top CPU consumers")
    out = run(["ps", "-Arco", "pid,%cpu,comm"])
    lines = out.splitlines()[1:11]
    for line in lines:
        parts = line.split(None, 2)
        if len(parts) == 3:
            pid, cpu, name = parts
            try:
                cpu_f = float(cpu)
            except ValueError:
                cpu_f = 0.0
            bar = "▓" * int(cpu_f)
            color = RED if cpu_f > 20 else (YELLOW if cpu_f > 5 else GREEN)
            print(f"  {DIM}{pid:>6}{R}  {color}{cpu:>6}%{R}  {bar}  {name}")

    header("Top memory consumers")
    out = run(["ps", "-Arco", "pid,%mem,rss,comm"])
    lines = out.splitlines()[1:11]
    for line in lines:
        parts = line.split(None, 3)
        if len(parts) == 4:
            pid, mem, rss, name = parts
            try:
                rss_mb = int(rss) // 1024
                mem_f  = float(mem)
            except ValueError:
                rss_mb, mem_f = 0, 0.0
            color = RED if mem_f > 10 else (YELLOW if mem_f > 3 else GREEN)
            print(f"  {DIM}{pid:>6}{R}  {color}{mem:>6}%{R}  {rss_mb:>5} MB  {name}")


# ── 3. CLEANUP TARGETS ────────────────────────────────────────────────────────

class CleanupTarget:
    def __init__(self, name: str, paths: list, description: str):
        self.name = name
        self.paths = paths
        self.description = description

    def preview_size(self) -> int:
        return sum(dir_size(p) for p in self.paths if p.exists())

    def clean(self, dry_run: bool) -> int:
        freed = 0
        for path in self.paths:
            if not path.exists():
                continue
            if path.is_dir():
                for child in path.iterdir():
                    freed += safe_remove(child, dry_run)
            else:
                freed += safe_remove(path, dry_run)
        return freed


def build_targets(home: Path) -> list:
    lib = home / "Library"

    # Firefox profile caches — resolve dynamically
    ff_profiles = []
    ff_base = lib / "Caches" / "Firefox" / "Profiles"
    if ff_base.exists():
        ff_profiles = list(ff_base.glob("*"))

    return [
        CleanupTarget(
            "User caches",
            [lib / "Caches"],
            "App caches in ~/Library/Caches"
        ),
        CleanupTarget(
            "User logs",
            [lib / "Logs"],
            "App logs in ~/Library/Logs"
        ),
        CleanupTarget(
            "Safari cache",
            [lib / "Caches" / "com.apple.Safari"],
            "Safari browser cache"
        ),
        CleanupTarget(
            "Chrome cache",
            [
                lib / "Caches" / "Google" / "Chrome" / "Default" / "Cache",
                lib / "Application Support" / "Google" / "Chrome" / "Default" / "Code Cache",
            ],
            "Chrome browser cache and code cache"
        ),
        CleanupTarget(
            "Firefox cache",
            ff_profiles,
            "Firefox profile caches"
        ),
        CleanupTarget(
            "Xcode derived data",
            [lib / "Developer" / "Xcode" / "DerivedData"],
            "Xcode build artifacts (safe to delete — Xcode rebuilds them)"
        ),
        CleanupTarget(
            "iOS device support",
            [lib / "Developer" / "Xcode" / "iOS DeviceSupport"],
            "Old iOS device debug symbols (safe to delete old versions)"
        ),
        CleanupTarget(
            "Xcode simulator cache",
            [lib / "Developer" / "CoreSimulator" / "Caches"],
            "Simulator cache (old runtime data)"
        ),
        CleanupTarget(
            "Homebrew cache",
            [lib / "Caches" / "Homebrew"],
            "Homebrew download cache"
        ),
        CleanupTarget(
            "pip cache",
            [lib / "Caches" / "pip"],
            "Python pip download cache"
        ),
        CleanupTarget(
            "npm cache",
            [home / ".npm" / "_cacache"],
            "npm package download cache"
        ),
        CleanupTarget(
            "Trash",
            [home / ".Trash"],
            "Files in your Trash"
        ),
        CleanupTarget(
            ".DS_Store files",
            list(home.rglob(".DS_Store"))[:500],
            "Hidden metadata files created by Finder"
        ),
    ]


# ── 4. LARGE FILES FINDER ─────────────────────────────────────────────────────

def find_large_files(home: Path, min_mb: int = 500, limit: int = 20):
    header(f"Large files (>= {min_mb} MB) in your home folder")
    info("Scanning... this may take a moment.")
    min_bytes = min_mb * 1024 * 1024
    results = []
    skip_dirs = {".Trash", "Library/Application Support/MobileSync"}

    def should_skip(path: Path) -> bool:
        for skip in skip_dirs:
            if skip in str(path):
                return True
        return False

    try:
        for entry in home.rglob("*"):
            try:
                if entry.is_file(follow_symlinks=False) and not should_skip(entry):
                    size = entry.stat().st_size
                    if size >= min_bytes:
                        results.append((size, entry))
            except (PermissionError, OSError):
                pass
    except (PermissionError, OSError):
        pass

    results.sort(reverse=True)
    if not results:
        ok(f"No files >= {min_mb} MB found.")
        return

    for size, path in results[:limit]:
        rel = path.relative_to(home) if path.is_relative_to(home) else path
        color = RED if size > 2 * 1024**3 else (YELLOW if size > 500 * 1024**2 else R)
        print(f"  {color}{human_size(size):>10}{R}  {DIM}{rel}{R}")

    if len(results) > limit:
        info(f"  ... and {len(results) - limit} more.")


# ── 5. NODE_MODULES FINDER ────────────────────────────────────────────────────

def find_node_modules(home: Path):
    header("node_modules directories (npm/yarn project dependencies)")
    info("These are safe to delete — run 'npm install' to restore.")
    results = []
    try:
        for nm in home.rglob("node_modules"):
            if nm.is_dir() and "node_modules/node_modules" not in str(nm):
                size = dir_size(nm)
                results.append((size, nm))
    except (PermissionError, OSError):
        pass

    results.sort(reverse=True)
    if not results:
        ok("No node_modules directories found.")
        return

    total = sum(s for s, _ in results)
    for size, path in results[:15]:
        rel = path.relative_to(home) if path.is_relative_to(home) else path
        print(f"  {human_size(size):>10}  {DIM}{rel}{R}")
    if len(results) > 15:
        info(f"  ... and {len(results) - 15} more.")
    info(f"Total across all node_modules: {human_size(total)}")


# ── 6. PERFORMANCE TIPS ───────────────────────────────────────────────────────

def performance_tips():
    header("Performance tips")

    launch_agents = Path.home() / "Library" / "LaunchAgents"
    if launch_agents.exists():
        agents = list(launch_agents.glob("*.plist"))
        if agents:
            warn(f"You have {len(agents)} Launch Agents (startup services):")
            for a in agents[:10]:
                print(f"  {DIM}  {a.name}{R}")
            if len(agents) > 10:
                info(f"  ... and {len(agents) - 10} more in ~/Library/LaunchAgents")
            info("  Review with: launchctl list | grep -v com.apple")
        else:
            ok("No custom Launch Agents found.")

    print()
    info("See which apps use the most energy:")
    print(f"  {DIM}  pmset -g stats{R}")
    info("Purge memory page cache (after heavy work sessions):")
    print(f"  {DIM}  sudo purge{R}")
    info("Check for software updates:")
    print(f"  {DIM}  softwareupdate -l{R}")
    info("Reset Spotlight index if search feels slow:")
    print(f"  {DIM}  sudo mdutil -E /{R}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    if platform.system() != "Darwin":
        print(f"{RED}This script is for macOS only.{R}")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Mac Cleanup Agent — free space and improve performance"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Actually delete files (default: dry run preview only)"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Show disk and process report only, no cleanup"
    )
    parser.add_argument(
        "--large-files",
        action="store_true",
        help="Scan for large files (>= 500 MB)"
    )
    parser.add_argument(
        "--node-modules",
        action="store_true",
        help="Find node_modules directories"
    )
    args = parser.parse_args()

    dry_run = not args.clean

    print(f"\n{BOLD}{'='*60}")
    print(f"  Mac Cleanup Agent")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}{R}")

    if dry_run and not args.report:
        print(f"\n{YELLOW}{BOLD}  DRY RUN MODE - nothing will be deleted.")
        print(f"  Run with --clean to actually free space.{R}\n")

    home = Path.home()

    disk_report()
    process_report()

    if args.report:
        performance_tips()
        sys.exit(0)

    if args.large_files:
        find_large_files(home)

    if args.node_modules:
        find_node_modules(home)

    # ── Cleanup pass ──────────────────────────────────────────────────────────
    header("Cleanup targets")
    targets = build_targets(home)

    total_preview = 0
    total_freed   = 0

    for target in targets:
        size = target.preview_size()
        total_preview += size
        if size == 0:
            continue
        color = GREEN if not dry_run else YELLOW
        print(f"\n  {color}{BOLD}{target.name}{R}  {DIM}({human_size(size)}){R}")
        print(f"  {DIM}{target.description}{R}")
        freed = target.clean(dry_run)
        total_freed += freed
        if not dry_run and freed > 0:
            ok(f"  Freed {human_size(freed)}")

    # ── Summary ───────────────────────────────────────────────────────────────
    header("Summary")
    if dry_run:
        print(f"\n  {YELLOW}{BOLD}Space you could free: {human_size(total_preview)}{R}")
        print(f"\n  Run the following to actually clean up:")
        print(f"  {DIM}  python3 mac_cleanup_agent.py --clean{R}\n")
    else:
        print(f"\n  {GREEN}{BOLD}Total space freed: {human_size(total_freed)}{R}\n")

    performance_tips()

    if not args.large_files:
        print(f"\n  {DIM}Tip: run with --large-files to scan for files >= 500 MB{R}")
    if not args.node_modules:
        print(f"  {DIM}Tip: run with --node-modules to find stale node_modules dirs{R}")
    print()


if __name__ == "__main__":
    main()
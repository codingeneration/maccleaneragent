# 🧹 MacCleaner Agent

**A lightweight, zero-dependency Python script that intelligently cleans your macOS machine** — safe dry-run first, full transparency, no bloat.

---

## Why This Tool?

Over time, macOS accumulates gigabytes of hidden junk: caches, logs, Xcode build artifacts, browser data, package manager downloads, and more. Most cleanup tools are either overkill, paid, or risky.

**MacCleaner Agent** shows you **exactly** what it plans to remove before touching anything.

---

## Features

- **Safe by default** — dry-run mode previews everything before deleting a single byte
- Disk usage report + top CPU/memory processes
- Smart cleanup targets (caches, logs, browsers, Xcode, Homebrew, pip, npm, Trash, etc.)
- Large file scanner (≥ 500 MB)
- `node_modules` hunter
- Helpful performance tips
- Pure Python — **zero dependencies**

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/codingeneration/maccleaneragent.git
cd maccleaneragent

# 2. Preview what can be cleaned (100% safe — nothing is deleted)
python3 mac_cleanup_agent.py

# 3. Perform the actual cleanup
python3 mac_cleanup_agent.py --clean
```

---

## Usage

```bash
python3 mac_cleanup_agent.py [OPTIONS]
```

| Option | Description |
|---|---|
| *(no flags)* | Dry run — shows what would be cleaned, no deletions |
| `--clean` | Execute cleanup and report space freed |
| `--report` | Disk + CPU/memory report only, no cleanup |
| `--large-files` | Scan home folder for files ≥ 500 MB |
| `--node-modules` | Find all `node_modules` directories and their sizes |

Combine flags freely:

```bash
# Full audit — report, large files, and node_modules in one pass
python3 mac_cleanup_agent.py --report --large-files --node-modules

# Clean and surface any large files at the same time
python3 mac_cleanup_agent.py --clean --large-files
```

---

## What Gets Cleaned

| Target | Path | Notes |
|---|---|---|
| User caches | `~/Library/Caches` | Largest single win on most Macs |
| User logs | `~/Library/Logs` | App-generated log files |
| Safari cache | `~/Library/Caches/com.apple.Safari` | Browser cache |
| Chrome cache | `~/Library/Caches/Google/Chrome/...` | Cache + code cache |
| Firefox cache | `~/Library/Caches/Firefox/Profiles/...` | Profile caches |
| Xcode derived data | `~/Library/Developer/Xcode/DerivedData` | Safe — Xcode rebuilds on demand |
| iOS device support | `~/Library/Developer/Xcode/iOS DeviceSupport` | Old debug symbols |
| Xcode simulator cache | `~/Library/Developer/CoreSimulator/Caches` | Stale runtime data |
| Homebrew cache | `~/Library/Caches/Homebrew` | Downloaded formula archives |
| pip cache | `~/Library/Caches/pip` | Python package downloads |
| npm cache | `~/.npm/_cacache` | Node package downloads |
| Trash | `~/.Trash` | Emptied as part of cleanup |
| `.DS_Store` files | Throughout `~` | Hidden Finder metadata files |

> **Note:** The agent never touches `~/Documents`, `~/Downloads`, `~/Desktop`, or application data. Cleanup is scoped to caches, logs, build artifacts, and temp files that are safe to regenerate.

---

## Example Output

```
============================================================
  🧹  Mac Cleanup Agent
  2026-05-27 09:14
============================================================

  DRY RUN MODE — nothing will be deleted.
  Run with --clean to actually free space.

────────────────────────────────────────────────────────────
  Disk usage report
────────────────────────────────────────────────────────────
  Filesystem      Size    Used   Avail  Use%
  /dev/disk3s5   926Gi   512Gi  414Gi   55%

  Downloads                  8.2 GB
  Library/Caches            14.7 GB
  Documents                  3.1 GB

────────────────────────────────────────────────────────────
  Cleanup targets
────────────────────────────────────────────────────────────

  User caches  (14.7 GB)
  ~  would remove  ~/Library/Caches/com.apple.dt.Xcode  (6.1 GB)
  ~  would remove  ~/Library/Caches/com.google.Chrome   (1.8 GB)

────────────────────────────────────────────────────────────
  Summary
────────────────────────────────────────────────────────────

  Space you could free: 18.4 GB

  Run the following to actually clean up:
    python3 mac_cleanup_agent.py --clean
```

---

## Requirements

- macOS (tested on Ventura, Sonoma, Sequoia)
- Python 3.9+ (pre-installed on all modern Macs)
- No `pip install` needed — zero third-party dependencies

---

## Extending the Agent

The codebase is intentionally modular. Each cleanup target is a `CleanupTarget` object — add new ones in `build_targets()` with a name, list of paths, and description. The dry-run safety model applies automatically to everything you add.

Ideas for extending it:

- Wrap in a cron job for weekly automated cleanups
- Add a `--min-mb` flag to tune the large file threshold
- Pipe output to a log file for cleanup history over time
- Integrate with the Claude API to generate a plain-English summary of findings

---

## License

MIT — free to use, modify, and distribute.

---

## Author

Built by [Steve Moynihan](https://www.linkedin.com/in/stevenmoynihan/) — Solutions Engineer, Google Workspace specialist, and tool builder.

---

*If this saved you some gigs, a ⭐ on the repo goes a long way.*

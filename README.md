# Chrome Hopping

> Instant switching between Chrome profiles from your menu bar.

If you run multiple Google accounts — work, freelance, personal — Chrome gives you isolated browser instances with no way to move between them from the menu bar. Chrome Hopping lives outside Chrome entirely. It reads your profiles directly from disk, tracks which windows belong to which profile, and gets you there in one click or one keystroke.

![Chrome Hopping menu bar screenshot](docs/screenshot.png)

---

## Features

- **Auto-detects all profiles** — reads `~/Library/Application Support/Google/Chrome/Local State` directly, no manual setup
- **One-click focus** — brings all windows for a profile to the front and moves them to your current screen
- **⌘§ hotkey** — cycle through open profiles without touching the mouse
- **Opens closed profiles** — clicking a profile with no open windows launches Chrome directly into it
- **Smart sorting** — most-used profiles float to the top automatically
- **Color icons** — each profile gets a unique shape/color combo for fast visual scanning
- **Auto-refresh** — re-detects every 15 seconds, recovers gracefully after Chrome restarts
- **Custom names** — rename any profile to whatever makes sense to you

---

## Install

### One-liner (Homebrew tap)

```bash
brew install tito-sec/chrome-hopping/chrome-hopping
```

Then grant two permissions (macOS will prompt you automatically on first use):
- **Accessibility** — to raise and move Chrome windows
- **Full Disk Access** — to read Chrome's profile data

### Manual install

```bash
git clone https://github.com/tito-sec/chrome_hopping.git
cd chrome_hopping
chmod +x install.sh
./install.sh
```

Requirements: macOS 12+, Google Chrome, Python 3.10+ (install via `brew install python@3.12` if needed).

---

## Permissions

Chrome Hopping needs two macOS permissions:

| Permission | Why |
|---|---|
| Accessibility | Raise Chrome windows, move them via AppleScript |
| Full Disk Access | Read `~/Library/Application Support/Google/Chrome/Local State` |

Go to **System Settings → Privacy & Security** and add Terminal (or the Python process) to each.

---

## Usage

| Action | How |
|---|---|
| Switch to a profile | Click **⇄** in the menu bar → click the profile |
| Cycle profiles | Press **⌘§** |
| Open a closed profile | Click it — Chrome launches automatically |
| Rename a profile | **⇄** → Rename profile… |
| Force refresh | **⇄** → Refresh now |
| Toggle screen-move | **⇄** → Move to this screen |

---

## How it works

Chrome names each window `<page title> - <profile short name>`. Chrome Hopping parses that suffix via System Events and matches it against the profile names and email domains in `Local State`. When you click a profile, it raises each matching window via `AXRaise` and optionally repositions it to your current screen using Quartz cursor-position detection.

---

## File locations

| Path | What |
|---|---|
| `~/.chrome-hopping/switcher.py` | App source |
| `~/.chrome-hopping/venv/` | Python virtual environment |
| `~/.chrome-hopping/error.log` | Runtime log |
| `~/.chrome-hopping-custom-names.json` | Your renamed profiles |
| `~/.chrome-hopping-usage.json` | Usage counts for sorting |
| `~/Library/LaunchAgents/com.chrome-hopping.plist` | Login item |

---

## Uninstall

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.chrome-hopping.plist 2>/dev/null; true
rm -rf ~/.chrome-hopping ~/.chrome-hopping-custom-names.json ~/.chrome-hopping-usage.json
rm ~/Library/LaunchAgents/com.chrome-hopping.plist
```

---

## Troubleshooting

**⇄ icon doesn't appear**
```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.chrome-hopping.plist 2>/dev/null; true 2>/dev/null
launchctl load ~/Library/LaunchAgents/com.chrome-hopping.plist
```

**Clicking a profile does nothing** — run the app directly to see live logs:
```bash
~/.chrome-hopping/venv/bin/python ~/.chrome-hopping/switcher.py
```

**Profiles not detected** — Terminal needs Full Disk Access (System Settings → Privacy & Security → Full Disk Access).

**⌘§ hotkey doesn't work** — the Python process needs Accessibility permission.

**Windows don't come to front** — same: Accessibility permission required.

---

## Contributing

Issues and PRs welcome. The app is a single Python file ([switcher.py](switcher.py)) — easy to read and modify.

---

## License

[PolyForm Noncommercial 1.0.0](LICENSE) — free for personal use, all commercial rights reserved.

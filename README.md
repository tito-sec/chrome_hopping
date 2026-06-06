# Chrome Hopping

> Switch between Chrome profiles instantly from your macOS menu bar, Dock, or Spotlight.

If you use multiple Google accounts — work, freelance, personal — Chrome creates a completely separate browser instance for each one. Chrome Hopping lets you jump between them in one click or one keystroke, from wherever you are.

Most switchers only handle a single window per profile. Chrome Hopping raises **all open windows** for the selected profile at once. It always places them at **80% of the screen, centered**, so you're never hunting for a window buried behind something else. If you have multiple monitors, it moves the windows to **whichever screen your mouse is on** — no dragging required. You can also **minimize all other profiles** with Option+click to cut the noise, and the **⌘§ hotkey cycles through every profile** — including ones with minimized windows, not just the visible ones.

In v1.1 you can also generate a dedicated **native macOS app** for each profile — drag them to your Dock or launch any profile directly from **⌘Space Spotlight**.

![Chrome Hopping menu bar screenshot](docs/screenshot.png)

---

## Install

### Option A — Homebrew (recommended)

```bash
brew install tito-sec/chrome-hopping/chrome-hopping
```

Then launch it:

```bash
chrome-hopping &
```

The **⇄** icon appears in your menu bar. It will start automatically every time you log in.

### Option B — Manual

```bash
git clone https://github.com/tito-sec/chrome_hopping.git
cd chrome_hopping
chmod +x install.sh
./install.sh
```

Requirements: macOS 12+, Google Chrome, Python 3.10+

---

## First-time permissions

macOS will ask for two permissions the first time you use it:

| Permission | Why |
|---|---|
| **Accessibility** | To bring Chrome windows to the front |
| **Full Disk Access** | To read your Chrome profile list |

Go to **System Settings → Privacy & Security** and add Terminal to both lists.

---

## How to use

| What you want to do | How |
|---|---|
| Switch to a profile | Click **⇄** in the menu bar → click the profile name |
| Cycle profiles with keyboard | Press **⌘§** — cycles all profiles, even minimized ones |
| Minimize all other profiles | **Option+click** a profile name |
| Open a profile that's not running | Click it — Chrome launches automatically |
| Switch from the Dock | See setup below — drag a profile app to your Dock |
| Switch from Spotlight | Press **⌘Space**, type a profile name, press Enter |
| Rename a profile | **⇄** → Rename profile… |
| Refresh the profile list | **⇄** → Refresh now |
| Move windows to your current screen | **⇄** → ✓ Move to this screen (on by default) |

### Dock & Spotlight setup

Chrome Hopping can generate a native macOS `.app` for each of your profiles, complete with a colored icon. These apps live in `~/Applications/Chrome Profiles` and let you switch profiles without touching the menu bar.

**Step 1 — Generate the apps**
Click **⇄** in the menu bar → **⚙ Settings** → **Update Dock & Spotlight apps**.
A colored `.app` is created for every profile. Stale apps are removed automatically.

**Step 2 — Add to Dock**
Open `~/Applications/Chrome Profiles` in Finder and drag any profile app to your Dock.

**Step 3 — Use Spotlight**
Press **⌘Space**, type a profile name (e.g. "Work"), and press Enter.
Chrome Hopping switches you straight to that profile.

### What makes it different

- **All windows, not just one** — if a profile has three open windows, all three come to the front.
- **Always centered at 80%** — windows are placed at 80% of the screen size, centered, so they're never buried or off-screen.
- **Follows your mouse across monitors** — on multi-screen setups, windows move to whichever screen your cursor is on when you click.
- **Keyboard cycling includes minimized profiles** — ⌘§ rotates through every profile, not just ones with visible windows.
- **Option+click to silence other profiles** — minimizes all other profiles' windows instantly so you can focus on one context.
- **Dock & Spotlight apps** — one-click profile switching from the Dock or ⌘Space, with colored per-profile icons.

---

## Uninstall

**If installed via Homebrew:**
```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.chrome-hopping.plist 2>/dev/null; true
brew uninstall chrome-hopping
rm -rf ~/.chrome-hopping ~/.chrome-hopping-custom-names.json \
       ~/.chrome-hopping-usage.json \
       ~/Library/LaunchAgents/com.chrome-hopping.plist
```

**If installed manually:**
```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.chrome-hopping.plist 2>/dev/null; true
rm -rf ~/.chrome-hopping ~/.chrome-hopping-custom-names.json ~/.chrome-hopping-usage.json
rm ~/Library/LaunchAgents/com.chrome-hopping.plist
```

---

## Troubleshooting

**⇄ icon doesn't appear after install**
```bash
chrome-hopping &
```

**Profiles not detected** — Terminal needs Full Disk Access:
System Settings → Privacy & Security → Full Disk Access → add Terminal

**⌘§ hotkey doesn't work** — Terminal needs Accessibility:
System Settings → Privacy & Security → Accessibility → add Terminal

**Windows don't come to front** — same as above, Accessibility permission needed

---

## How it works

Chrome labels each window with the profile name in the title bar. Chrome Hopping reads that label via System Events and matches it to your profile list in `~/Library/Application Support/Google/Chrome/Local State`. When you click a profile, it raises each matching window and moves it to your current screen.

---

## Contributing

Issues and PRs welcome. The entire app is a single Python file — [switcher.py](switcher.py).

---

## License

[PolyForm Noncommercial 1.0.0](LICENSE) — free for personal use, all commercial rights reserved.

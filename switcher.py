#!/usr/bin/env python3
"""
Chrome Hopping - macOS menu bar app
Auto-detects Chrome profiles and their open windows.
"""

import rumps
import subprocess
import json
import os
import re
import shutil
import threading
import datetime
import time
import tempfile
import plistlib

CHROME_DIR = os.path.expanduser("~/Library/Application Support/Google/Chrome")
LOCAL_STATE = os.path.join(CHROME_DIR, "Local State")
CUSTOM_NAMES_PATH = os.path.expanduser("~/.chrome-hopping-custom-names.json")
USAGE_PATH = os.path.expanduser("~/.chrome-hopping-usage.json")
LOG_PATH = os.path.expanduser("~/.chrome-hopping/error.log")
PROFILE_APPS_DIR = os.path.expanduser("~/Applications/Chrome Profiles")
SWITCH_CMD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pending_switch.json")

# Chrome's profile color indices map to these colors
CHROME_COLORS = {
    0:  "#4d84e2",  # blue
    1:  "#e25d42",  # red
    2:  "#65bb4e",  # green
    3:  "#f5a623",  # orange
    4:  "#9b59b6",  # purple
    5:  "#1abc9c",  # teal
    6:  "#e91e8c",  # pink
    7:  "#795548",  # brown
    8:  "#607d8b",  # blue grey
    9:  "#f06292",  # light pink
    10: "#aed581",  # light green
    11: "#4fc3f7",  # light blue
    12: "#ffb74d",  # amber
}
FALLBACK_COLORS = [
    "#f4a7a3",  # soft coral/red
    "#f9c99a",  # soft peach/orange
    "#fde89a",  # soft yellow
    "#c5e8a0",  # soft yellow-green
    "#a8e6c1",  # soft mint/teal
    "#a8daf5",  # soft sky blue
    "#b3bff5",  # soft periwinkle
    "#d4a8f5",  # soft purple
    "#f5a8d4",  # soft pink
    "#f5a8b0",  # soft rose
    "#b5e8b0",  # soft green
    "#f7d4a0",  # soft amber
]

# Each profile index gets a unique shape+color combo
PROFILE_ICONS = [
    "🟡",  # yellow square
    "🟢",  # green square
    "🔵",  # blue square
    "🟣",  # purple square
    "🔶",  # orange diamond
    "🔷",  # blue diamond
    "♥️",  # red heart
    "♦️",  # red diamond
    "♠️",  # black spade
    "♣️",  # black club
    "🩷",  # pink heart
    "🟠",  # orange circle
]

def log(msg):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(f"[{datetime.datetime.now()}] {msg}\n")
    print(msg, flush=True)

def run_applescript(script):
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode != 0:
        log(f"AppleScript error: {result.stderr.strip()}")
    return result.stdout.strip(), result.returncode

def load_custom_names():
    if os.path.exists(CUSTOM_NAMES_PATH):
        try:
            with open(CUSTOM_NAMES_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_custom_names(names):
    with open(CUSTOM_NAMES_PATH, "w") as f:
        json.dump(names, f, indent=2)

def load_usage():
    if os.path.exists(USAGE_PATH):
        try:
            with open(USAGE_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_usage(usage):
    with open(USAGE_PATH, "w") as f:
        json.dump(usage, f, indent=2)

def get_display_name(profile, custom_names):
    if profile["folder"] in custom_names:
        return custom_names[profile["folder"]]
    name = profile["name"]
    cleaned = re.sub(r'\.[a-z]{2,10}$', '', name, flags=re.IGNORECASE)
    if cleaned == cleaned.lower():
        cleaned = cleaned.upper()
    return cleaned

def read_chrome_profiles():
    """Read all profiles from Chrome's Local State file, including color info."""
    try:
        with open(LOCAL_STATE) as f:
            state = json.load(f)
        info_cache = state.get("profile", {}).get("info_cache", {})
        profiles = []
        for i, (folder, info) in enumerate(info_cache.items()):
            # Chrome stores avatar_icon like "chrome://theme/IDR_PROFILE_AVATAR_26"
            # and profile_highlight_color as ARGB int - we use a simple index-based fallback
            color_idx = i % len(FALLBACK_COLORS)
            # Try to get a meaningful color from the avatar index
            avatar = info.get("last_downloaded_gaia_picture_url_with_size", "")
            color = FALLBACK_COLORS[color_idx]
            profiles.append({
                "folder": folder,
                "name": info.get("name", folder),
                "email": info.get("user_name", ""),
                "color": color,
                "color_idx": color_idx,
            })
        return profiles
    except Exception as e:
        log(f"read_chrome_profiles error: {e}")
        return []

def get_open_windows():
    """Get all open Chrome windows from System Events with profile name extracted."""
    script = '''
tell application "System Events"
    tell process "Google Chrome"
        set winNames to {}
        repeat with w in windows
            set end of winNames to name of w
        end repeat
        return winNames
    end tell
end tell
'''
    out, code = run_applescript(script)
    if code != 0 or not out:
        return []
    windows = []
    for title in out.split(", "):
        title = title.strip()
        match = re.search(r'\(([^)]+)\)\s*$', title)
        profile_shortname = match.group(1) if match else None
        windows.append({"title": title, "profile_shortname": profile_shortname})
    return windows

def match_windows_to_profiles(profiles, windows):
    result = {p["folder"]: [] for p in profiles}
    for win in windows:
        shortname = win.get("profile_shortname")
        if not shortname:
            continue
        shortname_lower = shortname.lower()
        for p in profiles:
            pname_lower = p["name"].lower()
            email_lower = p["email"].lower()
            email_domain = email_lower.split("@")[-1] if "@" in email_lower else ""
            if (pname_lower == shortname_lower or
                email_domain == shortname_lower or
                email_lower == shortname_lower):
                result[p["folder"]].append(win["title"])
                break
    return result

def minimize_windows_by_titles(titles):
    for title in titles:
        safe = title[:40].replace('"', '\\"').replace('\\', '\\\\')
        script = (
            'tell application "System Events"\n'
            '    tell process "Google Chrome"\n'
            '        repeat with win in windows\n'
            '            if name of win contains "' + safe + '" then\n'
            '                set value of attribute "AXMinimized" of win to true\n'
            '                exit repeat\n'
            '            end if\n'
            '        end repeat\n'
            '    end tell\n'
            'end tell\n'
        )
        run_applescript(script)

def focus_windows_by_titles(titles):
    if not titles:
        return
    for title in titles:
        safe = title[:40].replace('"', '\\"').replace('\\', '\\\\')
        script = f'''
tell application "System Events"
    tell process "Google Chrome"
        set frontmost to true
        repeat with win in windows
            if name of win contains "{safe}" then
                perform action "AXRaise" of win
                exit repeat
            end if
        end repeat
    end tell
end tell
tell application "Google Chrome" to activate
'''
        run_applescript(script)

def launch_chrome_profile(folder):
    """Launch Chrome with a specific profile, restoring the previous session."""
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    subprocess.Popen([chrome_path, f"--profile-directory={folder}", "--restore-last-session"])

def is_chrome_running():
    out, _ = run_applescript('tell application "System Events" to (name of processes) contains "Google Chrome"')
    return out.strip().lower() == "true"


def get_cursor_screen():
    """Returns the frame of the screen where the mouse cursor currently is."""
    try:
        from AppKit import NSScreen, NSEvent
        pos = NSEvent.mouseLocation()
        cx, cy = pos.x, pos.y
        for screen in NSScreen.screens():
            f = screen.frame()
            if (f.origin.x <= cx <= f.origin.x + f.size.width and
                    f.origin.y <= cy <= f.origin.y + f.size.height):
                return f
        return NSScreen.mainScreen().frame()
    except Exception as e:
        log(f"get_cursor_screen error: {e}")
        return None

def move_window_to_screen(window_title, screen_frame):
    """Move a Chrome window to the target screen, using 80% of its area."""
    if not screen_frame:
        return
    from AppKit import NSScreen
    # NSScreen uses AppKit coords (y=0 at bottom of primary, increases upward).
    # AppleScript set position uses Quartz coords (y=0 at top of primary, increases downward).
    primary_height = NSScreen.screens()[0].frame().size.height
    quartz_y = primary_height - (screen_frame.origin.y + screen_frame.size.height)
    tx = int(screen_frame.origin.x + screen_frame.size.width * 0.1)
    ty = int(quartz_y + screen_frame.size.height * 0.1)
    tw = int(screen_frame.size.width * 0.8)
    th = int(screen_frame.size.height * 0.8)
    safe = window_title[:40].replace('"', '\\"')
    script = (
        'tell application "System Events"\n'
        '    tell process "Google Chrome"\n'
        '        repeat with win in windows\n'
        '            if name of win contains "' + safe + '" then\n'
        '                set position of win to {' + str(tx) + ', ' + str(ty) + '}\n'
        '                set size of win to {' + str(tw) + ', ' + str(th) + '}\n'
        '                exit repeat\n'
        '            end if\n'
        '        end repeat\n'
        '    end tell\n'
        'end tell\n'
    )
    run_applescript(script)

def _make_icon_png(color_hex, letter, size, out_path):
    from AppKit import (NSImage, NSBitmapImageRep, NSColor, NSBezierPath,
                        NSString, NSFont, NSMutableParagraphStyle,
                        NSFontAttributeName, NSForegroundColorAttributeName,
                        NSParagraphStyleAttributeName)
    from Foundation import NSMakeRect
    try:
        from AppKit import NSTextAlignmentCenter as _CENTER
    except ImportError:
        _CENTER = 2

    r = int(color_hex[1:3], 16) / 255.0
    g = int(color_hex[3:5], 16) / 255.0
    b = int(color_hex[5:7], 16) / 255.0

    img = NSImage.alloc().initWithSize_((size, size))
    img.lockFocus()
    NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, 1.0).setFill()
    NSBezierPath.bezierPathWithOvalInRect_(NSMakeRect(0, 0, size, size)).fill()

    para = NSMutableParagraphStyle.alloc().init()
    para.setAlignment_(_CENTER)
    font = NSFont.boldSystemFontOfSize_(size * 0.45)
    attrs = {
        NSFontAttributeName: font,
        NSForegroundColorAttributeName: NSColor.whiteColor(),
        NSParagraphStyleAttributeName: para,
    }
    ns_str = NSString.stringWithString_(letter)
    text_h = ns_str.sizeWithAttributes_(attrs).height
    y = (size - text_h) / 2.0
    ns_str.drawInRect_withAttributes_(NSMakeRect(0, y, size, text_h), attrs)
    img.unlockFocus()

    tiff = img.TIFFRepresentation()
    rep = NSBitmapImageRep.imageRepWithData_(tiff)
    try:
        from AppKit import NSBitmapImageFileTypePNG as _PNG
    except ImportError:
        _PNG = 4
    png_data = rep.representationUsingType_properties_(_PNG, None)
    with open(out_path, 'wb') as f:
        f.write(bytes(png_data))


def make_profile_icns(display_name_str, color_hex, icns_path):
    letter = (display_name_str[0] if display_name_str else "?").upper()
    with tempfile.TemporaryDirectory(suffix='.iconset') as iconset_dir:
        base_png = os.path.join(iconset_dir, '_base.png')
        _make_icon_png(color_hex, letter, 512, base_png)
        for fname, sz in [
            ('icon_16x16.png', 16), ('icon_16x16@2x.png', 32),
            ('icon_32x32.png', 32), ('icon_32x32@2x.png', 64),
            ('icon_128x128.png', 128), ('icon_128x128@2x.png', 256),
            ('icon_256x256.png', 256), ('icon_256x256@2x.png', 512),
            ('icon_512x512.png', 512),
        ]:
            subprocess.run(
                ['sips', '-z', str(sz), str(sz), base_png,
                 '--out', os.path.join(iconset_dir, fname)],
                capture_output=True
            )
        os.remove(base_png)
        subprocess.run(
            ['iconutil', '-c', 'icns', iconset_dir, '-o', icns_path],
            capture_output=True, check=True
        )


def generate_profile_apps(profiles, custom_names):
    os.makedirs(PROFILE_APPS_DIR, exist_ok=True)
    generated = set()

    install_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(install_dir, 'venv', 'bin', 'python')
    switch_script = os.path.join(install_dir, 'switch_profile.py')

    for profile in profiles:
        name = get_display_name(profile, custom_names)
        folder = profile["folder"]
        color = profile.get("color", FALLBACK_COLORS[0])

        safe_name = re.sub(r'[/:\\*?"<>|]', '-', name)
        app_name = f"{safe_name}.app"
        app_path = os.path.join(PROFILE_APPS_DIR, app_name)
        generated.add(app_name)

        scpt = (
            f'set pyPath to "{venv_python}"\n'
            f'set scPath to "{switch_script}"\n'
            f'set profFolder to "{folder}"\n'
            'do shell script (quoted form of pyPath) & " " & '
            '(quoted form of scPath) & " " & '
            '(quoted form of profFolder) & " >/dev/null 2>&1"'
        )
        result = subprocess.run(
            ['osacompile', '-o', app_path, '-e', scpt],
            capture_output=True
        )
        if result.returncode != 0:
            log(f"osacompile failed for {name}: {result.stderr.decode()}")
            continue

        plist_path = os.path.join(app_path, "Contents", "Info.plist")
        with open(plist_path, 'rb') as f:
            plist_data = plistlib.load(f)
        plist_data['CFBundleName'] = name
        plist_data['CFBundleDisplayName'] = name
        plist_data['LSUIElement'] = True
        with open(plist_path, 'wb') as f:
            plistlib.dump(plist_data, f)

        resources_dir = os.path.join(app_path, "Contents", "Resources")
        icon_name = plist_data.get('CFBundleIconFile', 'applet')
        if not icon_name.endswith('.icns'):
            icon_name += '.icns'
        icns_path = os.path.join(resources_dir, icon_name)
        try:
            make_profile_icns(name, color, icns_path)
        except Exception as e:
            log(f"Icon generation failed for {name}: {e}")

    for item in os.listdir(PROFILE_APPS_DIR):
        if item.endswith(".app") and item not in generated:
            shutil.rmtree(os.path.join(PROFILE_APPS_DIR, item), ignore_errors=True)

    subprocess.run(['mdimport', PROFILE_APPS_DIR], capture_output=True)
    log(f"Generated {len(profiles)} profile apps in {PROFILE_APPS_DIR}")
    return len(profiles)


def ask_text(prompt, default=""):
    script = f'display dialog "{prompt}" default answer "{default}" with title "Chrome Hopping"'
    result, _ = run_applescript(script)
    match = re.search(r'text returned:(.*)', result)
    return match.group(1).strip() if match else None

def ask_choice(prompt, choices):
    items = ", ".join(f'"{c}"' for c in choices)
    script = f'choose from list {{{items}}} with title "Chrome Hopping" with prompt "{prompt}" OK button name "Select" cancel button name "Cancel"'
    result, _ = run_applescript(script)
    if result == "false" or not result:
        return None
    return result.strip()

def show_alert(msg):
    run_applescript(f'display alert "Chrome Hopping" message "{msg}"')


class ChromeHoppingApp(rumps.App):
    def __init__(self):
        super().__init__("⇄", quit_button=None)
        self.custom_names = load_custom_names()
        self.usage = load_usage()         # folder -> count
        self.profiles = []
        self.window_map = {}
        self.profile_map = {}
        self._chrome_was_running = False
        self._current_profile_idx = 0    # for keyboard cycling

        self.move_to_cursor_screen = True
        self.refresh_data()
        self.update_menu()

        # Auto-refresh every 15 seconds + Chrome restart detection
        self.timer = rumps.Timer(self.auto_refresh, 15)
        self.timer.start()

        # Generate Dock/Spotlight .app bundles shortly after startup
        rumps.Timer(self._init_generate_apps, 3).start()

        # Poll for switch commands from .app bundle launchers (they lack Accessibility)
        self.cmd_timer = rumps.Timer(self._check_switch_command, 0.5)
        self.cmd_timer.start()

        # Register global keyboard shortcut ⌘§
        self._setup_hotkey()

    def _setup_hotkey(self):
        """
        Register ⌘§ via a background thread using CGEventTap.
        Falls back silently if accessibility isn't granted.
        """
        def hotkey_thread():
            try:
                from Cocoa import NSApplication, NSEvent, NSKeyDown
                from Quartz import (CGEventTapCreate, kCGSessionEventTap,
                                    kCGHeadInsertEventTap, kCGEventFlagMaskCommand,
                                    kCGEventFlagMaskShift, kCGEventKeyDown,
                                    CGEventGetIntegerValueField, kCGKeyboardEventKeycode,
                                    CGEventGetFlags, CFMachPortCreateRunLoopSource,
                                    CFRunLoopAddSource, CFRunLoopGetCurrent,
                                    CFRunLoopRun, kCFRunLoopCommonModes,
                                    CGEventTapEnable)

                # § key = keycode 10 on most keyboards (the key left of 1)
                SECTION_KEYCODE = 10

                def callback(proxy, event_type, event, refcon):
                    try:
                        keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
                        flags = CGEventGetFlags(event)
                        cmd = bool(flags & kCGEventFlagMaskCommand)
                        if keycode == SECTION_KEYCODE and cmd:
                            self.cycle_next_profile()
                    except Exception:
                        pass
                    return event

                tap = CGEventTapCreate(
                    kCGSessionEventTap,
                    kCGHeadInsertEventTap,
                    0,
                    1 << kCGEventKeyDown,
                    callback,
                    None
                )
                if tap:
                    src = CFMachPortCreateRunLoopSource(None, tap, 0)
                    CFRunLoopAddSource(CFRunLoopGetCurrent(), src, kCFRunLoopCommonModes)
                    CGEventTapEnable(tap, True)
                    CFRunLoopRun()
            except Exception as e:
                log(f"Hotkey setup failed (accessibility permission needed): {e}")

        t = threading.Thread(target=hotkey_thread, daemon=True)
        t.start()

    def cycle_next_profile(self):
        """Cycle to the next open profile on ⌘§."""
        open_profiles = [p for p in self.sorted_profiles() if self.window_map.get(p["folder"])]
        if not open_profiles:
            return
        self._current_profile_idx = (self._current_profile_idx + 1) % len(open_profiles)
        profile = open_profiles[self._current_profile_idx]
        titles = self.window_map.get(profile["folder"], [])
        self._record_usage(profile["folder"])
        threading.Thread(target=focus_windows_by_titles, args=(titles,), daemon=True).start()

    def _init_generate_apps(self, timer):
        timer.stop()
        self._do_generate_apps()

    def _do_generate_apps(self):
        try:
            generate_profile_apps(self.profiles, self.custom_names)
        except Exception as e:
            log(f"generate_profile_apps error: {e}")

    def generate_dock_apps(self, _=None):
        try:
            count = generate_profile_apps(self.profiles, self.custom_names)
        except Exception as e:
            log(f"generate_profile_apps error: {e}")
            show_alert(f"Failed to generate apps:\n{e}")
            return
        try:
            rumps.notification(
                "Chrome Hopping",
                f"{count} profile apps updated",
                "Find them in ~/Applications/Chrome Profiles — drag any to the Dock or search by name in Spotlight."
            )
        except Exception:
            pass

    def _check_switch_command(self, _=None):
        if not os.path.exists(SWITCH_CMD_PATH):
            return
        try:
            with open(SWITCH_CMD_PATH) as f:
                cmd = json.load(f)
            os.remove(SWITCH_CMD_PATH)
            folder = cmd.get("folder")
            if folder:
                self.refresh_data()
                self._switch_to_folder(folder)
        except Exception as e:
            log(f"switch command error: {e}")

    def _switch_to_folder(self, folder):
        self._record_usage(folder)
        screen_frame = get_cursor_screen() if self.move_to_cursor_screen else None
        titles = self.window_map.get(folder, [])
        if titles:
            def focus_and_move(t=titles, sf=screen_frame):
                focus_windows_by_titles(t)
                if sf and t:
                    time.sleep(0.3)
                    move_window_to_screen(t[0], sf)
            threading.Thread(target=focus_and_move, daemon=True).start()
        else:
            def launch_and_refresh():
                launch_chrome_profile(folder)
                time.sleep(3)
                self.refresh_data()
                rumps.Timer(self._do_menu_update, 0.1).start()
            threading.Thread(target=launch_and_refresh, daemon=True).start()

    def auto_refresh(self, _=None):
        # This is called from rumps.Timer which runs on the main thread - safe to update menu
        chrome_running = is_chrome_running()
        if self._chrome_was_running and not chrome_running:
            log("Chrome quit - will re-detect on next launch")
        if not self._chrome_was_running and chrome_running:
            log("Chrome launched - refreshing window map")
        self._chrome_was_running = chrome_running
        old_folders = {p["folder"] for p in self.profiles}
        self.refresh_data()
        if {p["folder"] for p in self.profiles} != old_folders:
            self._do_generate_apps()
        self.update_menu()

    def refresh_data(self):
        self.profiles = read_chrome_profiles()
        windows = get_open_windows()
        self.window_map = match_windows_to_profiles(self.profiles, windows)

    def _record_usage(self, folder):
        self.usage[folder] = self.usage.get(folder, 0) + 1
        save_usage(self.usage)

    def display_name(self, profile):
        return get_display_name(profile, self.custom_names)

    def sorted_profiles(self):
        """Sort by usage count descending, then alphabetically."""
        return sorted(
            self.profiles,
            key=lambda p: (-self.usage.get(p["folder"], 0), self.display_name(p).lower())
        )

    def color_dot(self, profile):
        idx = profile.get("color_idx", 0)
        return PROFILE_ICONS[idx % len(PROFILE_ICONS)]

    def update_menu(self):
        self.menu.clear()
        self.profile_map = {}

        profiles = self.sorted_profiles()
        open_profiles = [p for p in profiles if self.window_map.get(p["folder"])]
        closed_profiles = [p for p in profiles if not self.window_map.get(p["folder"])]

        if not profiles:
            self.menu.add(rumps.MenuItem("No Chrome profiles found"))
            self.menu.add(rumps.separator)
        else:
            for p in open_profiles:
                win_count = len(self.window_map.get(p["folder"], []))
                dot = self.color_dot(p)
                name = self.display_name(p)
                label = f"{dot} {name}  · {win_count}"
                self.profile_map[label] = p["folder"]
                self.menu.add(rumps.MenuItem(label, callback=self.on_profile_click))

            if open_profiles and closed_profiles:
                self.menu.add(rumps.separator)

            for p in closed_profiles:
                dot = self.color_dot(p)
                name = self.display_name(p)
                label = f"{dot} {name}  (closed)"
                self.profile_map[label] = p["folder"]
                self.menu.add(rumps.MenuItem(label, callback=self.on_profile_click))

            self.menu.add(rumps.separator)

        screen_label = "✓ Move to this screen" if self.move_to_cursor_screen else "  Move to this screen"
        settings = rumps.MenuItem("⚙ Settings")
        settings.add(rumps.MenuItem("Rename profile…", callback=self.rename_profile))
        settings.add(rumps.MenuItem("Update Dock & Spotlight apps…", callback=self.generate_dock_apps))
        settings.add(rumps.separator)
        settings.add(rumps.MenuItem(screen_label, callback=self.toggle_screen_move))
        settings.add(rumps.MenuItem("Refresh now", callback=self.manual_refresh))
        self.menu.add(settings)
        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("About Chrome Hopping…", callback=self.show_about))
        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("Quit", callback=rumps.quit_application))

    def _is_option_click(self):
        """Return True if the Option (⌥) key is held during the current event."""
        try:
            from AppKit import NSApp, NSEventModifierFlagOption
            event = NSApp.currentEvent()
            if event:
                return bool(event.modifierFlags() & NSEventModifierFlagOption)
        except Exception:
            pass
        return False

    def _minimize_other_profiles(self, active_folder):
        """Minimize all Chrome windows belonging to profiles other than active_folder."""
        titles_to_minimize = []
        for folder, titles in self.window_map.items():
            if folder != active_folder:
                titles_to_minimize.extend(titles)
        if titles_to_minimize:
            threading.Thread(target=minimize_windows_by_titles, args=(titles_to_minimize,), daemon=True).start()

    def on_profile_click(self, sender):
        folder = self.profile_map.get(sender.title)
        if not folder:
            return
        option_held = self._is_option_click()
        self._record_usage(folder)
        screen_frame = get_cursor_screen() if self.move_to_cursor_screen else None
        titles = self.window_map.get(folder, [])
        if titles:
            def focus_and_move(t=titles, sf=screen_frame, opt=option_held, f=folder):
                if opt:
                    self._minimize_other_profiles(f)
                    time.sleep(0.2)
                focus_windows_by_titles(t)
                if sf and t:
                    time.sleep(0.3)
                    move_window_to_screen(t[0], sf)
            threading.Thread(target=focus_and_move, daemon=True).start()
        else:
            # No open windows - launch Chrome with this profile
            log(f"Launching Chrome for profile: {folder}")
            def launch_and_refresh():
                launch_chrome_profile(folder)
                time.sleep(3)
                self.refresh_data()
                # Schedule UI update back on the main thread via rumps timer
                rumps.Timer(self._do_menu_update, 0.1).start()
            threading.Thread(target=launch_and_refresh, daemon=True).start()

    def _do_menu_update(self, timer):
        timer.stop()
        self.update_menu()

    def rename_profile(self, _=None):
        if not self.profiles:
            show_alert("No profiles found.")
            return
        names = [self.display_name(p) for p in self.sorted_profiles()] + ["(cancel)"]
        choice = ask_choice("Select profile to rename:", names)
        if not choice or choice == "(cancel)":
            return
        idx = names.index(choice)
        profile = self.sorted_profiles()[idx]
        new_name = ask_text("New display name:", self.display_name(profile))
        if new_name:
            self.custom_names[profile["folder"]] = new_name
            save_custom_names(self.custom_names)
            self.update_menu()

    def show_about(self, _=None):
        install_dir = os.path.dirname(os.path.abspath(__file__))
        home = os.path.expanduser("~")
        install_short = install_dir.replace(home, "~")
        log_short = LOG_PATH.replace(home, "~")
        lines = [
            "Chrome Hopping  v1.0.0",
            "",
            "Switch between Chrome profiles instantly from your menu bar, Dock, or Spotlight. Auto-detects all profiles, tracks open windows, and brings any profile to front in one click.",
            "",
            f"Profiles found: {len(self.profiles)}",
            f"Install path: {install_short}",
            f"Log file: {log_short}",
            "",
            "By Amir Tito",
            "Website: amirtito.com/chrome_hopping",
            "License: PolyForm Noncommercial 1.0.0",
        ]
        msg_parts = " & return & ".join(f'"{ln}"' for ln in lines)
        script = (
            f"set msg to {msg_parts}\n"
            'set choice to button returned of '
            '(display dialog msg with title "Chrome Hopping" '
            'buttons {"Website", "License", "Close"} '
            'default button "Close" with icon note)\n'
            'if choice is "Website" then\n'
            '    do shell script "open https://amirtito.com/chrome_hopping/"\n'
            'else if choice is "License" then\n'
            '    do shell script "open https://polyformproject.org/licenses/noncommercial/1.0.0/"\n'
            'end if'
        )
        run_applescript(script)

    def toggle_screen_move(self, _=None):
        self.move_to_cursor_screen = not self.move_to_cursor_screen
        self.update_menu()

    def manual_refresh(self, _=None):
        self.refresh_data()
        self.update_menu()


if __name__ == "__main__":
    log("App starting")
    ChromeHoppingApp().run()

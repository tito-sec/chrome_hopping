#!/usr/bin/env python3
"""
Called by Dock/Spotlight .app bundle launchers.
Delegates to the running menu bar app via a command file — it already has
the Accessibility permission needed to focus Chrome windows.
"""
import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from switcher import SWITCH_CMD_PATH, launch_chrome_profile

def main():
    if len(sys.argv) < 2:
        sys.exit(1)
    folder = sys.argv[1]

    with open(SWITCH_CMD_PATH, 'w') as f:
        json.dump({"folder": folder}, f)

    # Wait up to 2 seconds for the menu bar app to consume the command
    for _ in range(20):
        time.sleep(0.1)
        if not os.path.exists(SWITCH_CMD_PATH):
            return  # Menu bar app handled it

    # Fallback: menu bar app not running — launch Chrome directly
    try:
        os.remove(SWITCH_CMD_PATH)
    except FileNotFoundError:
        pass
    launch_chrome_profile(folder)

if __name__ == "__main__":
    main()

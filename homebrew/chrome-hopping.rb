class ChromeHopping < Formula
  desc "macOS menu bar app for instant Chrome profile switching"
  homepage "https://amirtito.com/chrome_hopping/"
  url "https://github.com/tito-sec/chrome_hopping/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "337bc3c2de8314758c70686c3aab2dceb0e280248101affc3ed8239418255a5e"
  license "PolyForm-Noncommercial-1.0.0"

  depends_on "python@3.12"
  depends_on :macos

  def install
    venv = libexec/"venv"
    system "python3.12", "-m", "venv", venv
    system "#{venv}/bin/pip", "install", "rumps", "--quiet"

    (libexec/"app").mkpath
    cp "switcher.py", libexec/"app/switcher.py"

    (bin/"chrome-hopping").write <<~SH
      #!/bin/bash
      PLIST="$HOME/Library/LaunchAgents/com.chrome-hopping.plist"
      INSTALL_DIR="$HOME/.chrome-hopping"

      # First-run: register as login item
      if [ ! -f "$PLIST" ]; then
        mkdir -p "$INSTALL_DIR" "$HOME/Library/LaunchAgents"
        cat > "$PLIST" << EOF
      <?xml version="1.0" encoding="UTF-8"?>
      <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
        "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
      <plist version="1.0">
      <dict>
        <key>Label</key>
        <string>com.chrome-hopping</string>
        <key>ProgramArguments</key>
        <array>
          <string>#{bin}/chrome-hopping</string>
        </array>
        <key>RunAtLoad</key>
        <true/>
        <key>KeepAlive</key>
        <false/>
        <key>StandardErrorPath</key>
        <string>$INSTALL_DIR/error.log</string>
        <key>StandardOutPath</key>
        <string>$INSTALL_DIR/output.log</string>
      </dict>
      </plist>
      EOF
        launchctl load "$PLIST" 2>/dev/null
      fi

      exec "#{venv}/bin/python" "#{libexec}/app/switcher.py" "$@"
    SH
  end

  def caveats
    <<~EOS
      Run once to start Chrome Hopping and register it as a login item:

        chrome-hopping &

      The ⇄ icon will appear in your menu bar. It will start automatically on login.

      Two macOS permissions are required on first launch:
        • Accessibility    — System Settings → Privacy & Security → Accessibility
        • Full Disk Access — System Settings → Privacy & Security → Full Disk Access

      Hotkey: ⌘§ cycles through open Chrome profiles.

      To uninstall completely:
        launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.chrome-hopping.plist 2>/dev/null; true
        brew uninstall chrome-hopping
        rm -rf ~/.chrome-hopping ~/.chrome-hopping-custom-names.json \\
               ~/.chrome-hopping-usage.json \\
               ~/Library/LaunchAgents/com.chrome-hopping.plist
    EOS
  end

  test do
    assert_predicate bin/"chrome-hopping", :exist?
  end
end

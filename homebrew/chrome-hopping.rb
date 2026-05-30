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
    system "#{venv}/bin/pip", "install", "rumps", "pyobjc", "--quiet"

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
      ✅ Installed! One more step — run this to start Chrome Hopping:

        chrome-hopping &

      The ⇄ icon will appear in your menu bar.
      It will launch automatically every time you log in.

      On first use, macOS will ask for two permissions:
        • Accessibility    — to bring Chrome windows to the front
        • Full Disk Access — to read your Chrome profile list
      Grant both in System Settings → Privacy & Security.

      To uninstall:
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

class ChromeHopping < Formula
  desc "macOS menu bar app for instant Chrome profile switching"
  homepage "https://github.com/tito-sec/Chrome_Hopping"
  url "https://github.com/tito-sec/Chrome_Hopping/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "REPLACE_WITH_ACTUAL_SHA256_AFTER_TAGGING"
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
      exec "#{venv}/bin/python" "#{libexec}/app/switcher.py" "$@"
    SH
  end

  def post_install
    install_dir = File.expand_path("~/.chrome-hopping")
    FileUtils.mkdir_p(install_dir)

    plist_path = File.expand_path("~/Library/LaunchAgents/com.chrome-hopping.plist")
    plist_content = <<~PLIST
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
        <string>#{install_dir}/error.log</string>
        <key>StandardOutPath</key>
        <string>#{install_dir}/output.log</string>
      </dict>
      </plist>
    PLIST
    File.write(plist_path, plist_content)
    system "launchctl", "unload", plist_path, err: File::NULL
    system "launchctl", "load", plist_path
  end

  def caveats
    <<~EOS
      Chrome Hopping has been installed and registered as a login item.
      The ⇄ icon should appear in your menu bar shortly.

      Two macOS permissions are required:
        • Accessibility   — System Settings → Privacy & Security → Accessibility
        • Full Disk Access — System Settings → Privacy & Security → Full Disk Access
      Add Terminal (or the Python process) to both lists.

      Hotkey: ⌘§ cycles through open Chrome profiles.

      To uninstall completely:
        brew uninstall chrome-hopping
        launchctl unload ~/Library/LaunchAgents/com.chrome-hopping.plist
        rm -rf ~/.chrome-hopping ~/.chrome-hopping-custom-names.json \\
               ~/.chrome-hopping-usage.json \\
               ~/Library/LaunchAgents/com.chrome-hopping.plist
    EOS
  end

  test do
    assert_predicate bin/"chrome-hopping", :exist?
  end
end

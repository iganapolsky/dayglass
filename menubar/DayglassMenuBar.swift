import Cocoa

class AppDelegate: NSObject, NSApplicationDelegate {
    var statusItem: NSStatusItem!
    var timer: Timer?

    func applicationDidFinishLaunching(_ aNotification: Notification) {
        // Create Status Item in macOS Menu Bar
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        
        if let button = statusItem.button {
            // Using SF Symbol or clean lens/glass icon
            if #available(macOS 11.0, *) {
                let config = NSImage.SymbolConfiguration(pointSize: 14, weight: .regular)
                let image = NSImage(systemSymbolName: "eyeglasses", accessibilityDescription: "Dayglass")?.withSymbolConfiguration(config)
                button.image = image
            } else {
                button.title = "👓"
            }
            button.toolTip = "Dayglass — Local Screen Memory ($0.00 / Local)"
        }

        buildMenu()

        // Refresh status every 30 seconds
        timer = Timer.scheduledTimer(withTimeInterval: 30.0, repeats: true) { [weak self] _ in
            self?.updateStatus()
        }
    }

    func buildMenu() {
        let menu = NSMenu()

        // Header / Status
        let titleItem = NSMenuItem(title: "Dayglass • 100% Local & Free", action: nil, keyEquivalent: "")
        titleItem.isEnabled = false
        menu.addItem(titleItem)

        let statusLine = NSMenuItem(title: "● Capturing Active (45s)", action: nil, keyEquivalent: "")
        statusLine.tag = 101
        statusLine.isEnabled = false
        menu.addItem(statusLine)

        menu.addItem(NSMenuItem.separator())

        // Primary Actions
        let captureItem = NSMenuItem(title: "Capture Now", action: #selector(captureNow), keyEquivalent: "C")
        captureItem.keyEquivalentModifierMask = [.command, .shift]
        captureItem.target = self
        menu.addItem(captureItem)

        let desktopItem = NSMenuItem(title: "Open Dayglass Desktop...", action: #selector(openDesktop), keyEquivalent: "D")
        desktopItem.keyEquivalentModifierMask = [.command, .shift]
        desktopItem.target = self
        menu.addItem(desktopItem)

        menu.addItem(NSMenuItem.separator())

        // Automations Submenu
        let autoItem = NSMenuItem(title: "Run Automation", action: nil, keyEquivalent: "")
        let autoSubmenu = NSMenu()

        let autos = [
            ("Daily Standup Prep", "standup-prep"),
            ("Day Recap", "day-recap"),
            ("Missed To-Dos", "missed-todos"),
            ("Detect Blockers", "blockers"),
            ("Time Breakdown", "time-breakdown"),
            ("Automate My Work", "automate-my-work")
        ]

        for (label, key) in autos {
            let item = NSMenuItem(title: label, action: #selector(runAutomationAction(_:)), keyEquivalent: "")
            item.representedObject = key
            item.target = self
            autoSubmenu.addItem(item)
        }

        autoItem.submenu = autoSubmenu
        menu.addItem(autoItem)

        menu.addItem(NSMenuItem.separator())

        // Pause / Resume
        let pauseItem = NSMenuItem(title: "Pause Capture", action: #selector(togglePause(_:)), keyEquivalent: "P")
        pauseItem.keyEquivalentModifierMask = [.command, .shift]
        pauseItem.target = self
        menu.addItem(pauseItem)

        menu.addItem(NSMenuItem.separator())

        // Quit
        let quitItem = NSMenuItem(title: "Quit Dayglass", action: #selector(quitApp), keyEquivalent: "q")
        quitItem.target = self
        menu.addItem(quitItem)

        statusItem.menu = menu
    }

    @objc func captureNow() {
        runShell(cmd: "python3 -m dayglass capture") { success in
            self.notify(title: "Dayglass", message: success ? "Captured screen frame" : "Capture failed")
        }
    }

    @objc func openDesktop() {
        runShell(cmd: "open -a Dayglass") { _ in }
    }

    @objc func runAutomationAction(_ sender: NSMenuItem) {
        guard let autoName = sender.representedObject as? String else { return }
        self.notify(title: "Dayglass Automation", message: "Running \(autoName)...")
        runShell(cmd: "python3 -m dayglass automate \(autoName)") { success in
            self.notify(title: "Dayglass Automation Complete", message: "\(autoName) finished. View in Desktop.")
        }
    }

    @objc func togglePause(_ sender: NSMenuItem) {
        if sender.title == "Pause Capture" {
            sender.title = "Resume Capture"
            statusItem.menu?.item(withTag: 101)?.title = "○ Paused"
            self.notify(title: "Dayglass", message: "Screen capture paused.")
        } else {
            sender.title = "Pause Capture"
            statusItem.menu?.item(withTag: 101)?.title = "● Capturing Active"
            self.notify(title: "Dayglass", message: "Screen capture resumed.")
        }
    }

    @objc func quitApp() {
        NSApplication.shared.terminate(self)
    }

    func updateStatus() {
        // Query local API if running
        guard let url = URL(string: "http://127.0.0.1:3333/api/status") else { return }
        let task = URLSession.shared.dataTask(with: url) { [weak self] data, _, _ in
            guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let count = json["frames_count"] as? Int else { return }
            DispatchQueue.main.async {
                self?.statusItem.menu?.item(withTag: 101)?.title = "● Capturing Active (\(count) frames)"
            }
        }
        task.resume()
    }

    func notify(title: String, message: String) {
        let script = "display notification \"\(message)\" with title \"\(title)\""
        if let appleScript = NSAppleScript(source: script) {
            var error: NSDictionary?
            appleScript.executeAndReturnError(&error)
        }
    }

    func runShell(cmd: String, completion: @escaping (Bool) -> Void) {
        DispatchQueue.global(qos: .userInitiated).async {
            let task = Process()
            task.launchPath = "/bin/bash"
            task.arguments = ["-c", "cd /Users/iganapolsky/workspace/projects/dayglass && " + cmd]
            task.launch()
            task.waitUntilExit()
            DispatchQueue.main.async {
                completion(task.terminationStatus == 0)
            }
        }
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory) // Prevents dock icon from showing; pure menu bar!
app.run()

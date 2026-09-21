import Cocoa
import WebKit

class DayglassAppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate {
    var window: NSWindow!
    var webView: WKWebView!
    var statusItem: NSStatusItem!
    var serverProcess: Process?

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Ensure Dayglass background server is running
        ensureServerRunning()

        // Setup Application Menu Bar
        setupMainMenu()

        // Setup Menu Bar Status Item
        setupStatusItem()

        // Create Main App Window
        setupMainWindow()

        // Activate Application
        NSApp.activate(ignoringOtherApps: true)
    }

    func ensureServerRunning() {
        // Check if port 3333 is reachable
        let url = URL(string: "http://127.0.0.1:3333/api/status")!
        var reachable = false
        let sema = DispatchSemaphore(value: 0)

        let task = URLSession.shared.dataTask(with: url) { _, resp, _ in
            if let http = resp as? HTTPURLResponse, http.statusCode == 200 {
                reachable = true
            }
            sema.signal()
        }
        task.resume()
        _ = sema.wait(timeout: .now() + 0.4)

        if !reachable {
            let proc = Process()
            proc.launchPath = "/bin/bash"
            proc.arguments = ["-c", "cd /Users/iganapolsky/workspace/projects/dayglass && python3 -m dayglass serve --port 3333"]
            do {
                try proc.run()
                self.serverProcess = proc
                Thread.sleep(forTimeInterval: 0.5)
            } catch {
                print("Failed to start server: \(error)")
            }
        }
    }

    func setupMainMenu() {
        let mainMenu = NSMenu()

        // Dayglass App Menu
        let appMenuItem = NSMenuItem()
        let appMenu = NSMenu(title: "Dayglass")
        appMenu.addItem(NSMenuItem(title: "About Dayglass", action: #selector(showAbout), keyEquivalent: ""))
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(NSMenuItem(title: "Preferences…", action: nil, keyEquivalent: ","))
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(NSMenuItem(title: "Hide Dayglass", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h"))
        let hideOthers = NSMenuItem(title: "Hide Others", action: #selector(NSApplication.hideOtherApplications(_:)), keyEquivalent: "h")
        hideOthers.keyEquivalentModifierMask = [.command, .option]
        appMenu.addItem(hideOthers)
        appMenu.addItem(NSMenuItem(title: "Show All", action: #selector(NSApplication.unhideAllApplications(_:)), keyEquivalent: ""))
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(NSMenuItem(title: "Quit Dayglass", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
        appMenuItem.submenu = appMenu
        mainMenu.addItem(appMenuItem)

        // Edit Menu (Essential for Cut/Copy/Paste/Undo in webview!)
        let editMenuItem = NSMenuItem()
        let editMenu = NSMenu(title: "Edit")
        editMenu.addItem(NSMenuItem(title: "Undo", action: #selector(UndoManager.undo), keyEquivalent: "z"))
        let redoItem = NSMenuItem(title: "Redo", action: #selector(UndoManager.redo), keyEquivalent: "Z")
        redoItem.keyEquivalentModifierMask = [.command, .shift]
        editMenu.addItem(redoItem)
        editMenu.addItem(NSMenuItem.separator())
        editMenu.addItem(NSMenuItem(title: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x"))
        editMenu.addItem(NSMenuItem(title: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c"))
        editMenu.addItem(NSMenuItem(title: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v"))
        editMenu.addItem(NSMenuItem(title: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a"))
        editMenuItem.submenu = editMenu
        mainMenu.addItem(editMenuItem)

        // Window Menu
        let windowMenuItem = NSMenuItem()
        let windowMenu = NSMenu(title: "Window")
        windowMenu.addItem(NSMenuItem(title: "Minimize", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m"))
        windowMenu.addItem(NSMenuItem(title: "Zoom", action: #selector(NSWindow.performZoom(_:)), keyEquivalent: ""))
        windowMenu.addItem(NSMenuItem.separator())
        windowMenu.addItem(NSMenuItem(title: "Bring All to Front", action: #selector(NSApplication.arrangeInFront(_:)), keyEquivalent: ""))
        windowMenuItem.submenu = windowMenu
        mainMenu.addItem(windowMenuItem)

        NSApp.mainMenu = mainMenu
    }

    func setupMainWindow() {
        let rect = NSRect(x: 0, y: 0, width: 1200, height: 820)
        window = NSWindow(
            contentRect: rect,
            styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
            backing: .buffered,
            defer: false
        )
        window.center()
        window.title = "Dayglass"
        window.titlebarAppearsTransparent = true
        window.titleVisibility = .hidden
        window.isReleasedWhenClosed = false
        window.delegate = self
        window.backgroundColor = NSColor(red: 0.07, green: 0.08, blue: 0.09, alpha: 1.0)

        // Configure WKWebView
        let config = WKWebViewConfiguration()
        config.preferences.setValue(true, forKey: "developerExtrasEnabled")
        webView = WKWebView(frame: window.contentView!.bounds, configuration: config)
        webView.autoresizingMask = [.width, .height]
        webView.setValue(false, forKey: "drawsBackground")

        window.contentView?.addSubview(webView)

        // Load Dayglass local UI
        if let url = URL(string: "http://127.0.0.1:3333") {
            webView.load(URLRequest(url: url))
        }

        window.makeKeyAndOrderFront(nil)
    }

    func setupStatusItem() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let button = statusItem.button {
            if #available(macOS 11.0, *) {
                let config = NSImage.SymbolConfiguration(pointSize: 13, weight: .regular)
                button.image = NSImage(systemSymbolName: "eyeglasses", accessibilityDescription: "Dayglass")?.withSymbolConfiguration(config)
            } else {
                button.title = "👓"
            }
            button.toolTip = "Dayglass — Local Screen Memory"
        }

        let menu = NSMenu()
        menu.addItem(NSMenuItem(title: "Dayglass", action: nil, keyEquivalent: ""))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Open Window", action: #selector(showWindow), keyEquivalent: "o"))
        menu.addItem(NSMenuItem(title: "Capture Now", action: #selector(captureNow), keyEquivalent: "C"))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Quit Dayglass", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
        statusItem.menu = menu
    }

    @objc func showWindow() {
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    @objc func captureNow() {
        let task = Process()
        task.launchPath = "/bin/bash"
        task.arguments = ["-c", "cd /Users/iganapolsky/workspace/projects/dayglass && python3 -m dayglass capture"]
        try? task.run()
    }

    @objc func showAbout() {
        let alert = NSAlert()
        alert.messageText = "Dayglass"
        alert.informativeText = "Local Screen Memory & Intelligence\n100% On-Device • $0.00 / Local"
        alert.alertStyle = .informational
        alert.addButton(withTitle: "OK")
        alert.runModal()
    }

    func windowShouldClose(_ sender: NSWindow) -> Bool {
        // Hide window instead of quitting when close button is clicked
        window.orderOut(nil)
        return false
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if !flag {
            window.makeKeyAndOrderFront(nil)
        }
        return true
    }

    func applicationWillTerminate(_ notification: Notification) {
        serverProcess?.terminate()
    }
}

// Entrypoint
let app = NSApplication.shared
let delegate = DayglassAppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular) // Makes it a first-class macOS App in the Dock!
app.run()

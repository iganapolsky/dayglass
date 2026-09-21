import AppKit
import Darwin
import WebKit

private let bundleID = "com.iganapolsky.dayglass"
private let defaultPort = 3333

@main
struct DayglassMain {
    static func main() {
        let app = NSApplication.shared
        let delegate = AppDelegate()
        DayglassMain.keepAlive = delegate
        app.delegate = delegate
        app.setActivationPolicy(.regular)
        app.run()
    }

    private static var keepAlive: AppDelegate?
}

final class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate {
    private var window: NSWindow?
    private var webView: WKWebView?
    private var ownedServer: Process?
    private let port = defaultPort

    func applicationDidFinishLaunching(_ notification: Notification) {
        if focusExistingInstance() {
            NSApp.terminate(nil)
            return
        }
        buildMenu()
        NSApp.applicationIconImage = Self.dockIcon()
        let frame = NSRect(x: 0, y: 0, width: 1200, height: 820)
        let window = NSWindow(
            contentRect: frame,
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Dayglass"
        window.minSize = NSSize(width: 880, height: 640)
        window.setFrameAutosaveName("DayglassMain")
        window.backgroundColor = NSColor(calibratedRed: 0.07, green: 0.08, blue: 0.10, alpha: 1)
        window.center()

        let web = WKWebView(frame: frame)
        web.navigationDelegate = self
        web.setValue(false, forKey: "drawsBackground")
        window.contentView = web
        window.makeKeyAndOrderFront(nil)
        self.window = window
        self.webView = web
        NSApp.activate(ignoringOtherApps: true)

        if !portOpen(port) {
            startServer()
        }
        waitThenLoad()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }

    func applicationWillTerminate(_ notification: Notification) {
        guard let ownedServer, ownedServer.isRunning else { return }
        ownedServer.terminate()
    }

    private func focusExistingInstance() -> Bool {
        let me = ProcessInfo.processInfo.processIdentifier
        let others = NSWorkspace.shared.runningApplications.filter {
            $0.bundleIdentifier == bundleID && $0.processIdentifier != me
        }
        guard let other = others.first else { return false }
        other.activate(options: [.activateAllWindows])
        return true
    }

    private func buildMenu() {
        let main = NSMenu()
        let appItem = NSMenuItem()
        main.addItem(appItem)
        let appMenu = NSMenu(title: "Dayglass")
        appItem.submenu = appMenu
        appMenu.addItem(
            withTitle: "Quit Dayglass",
            action: #selector(NSApplication.terminate(_:)),
            keyEquivalent: "q"
        )
        NSApp.mainMenu = main
    }

    private func startServer() {
        guard let located = locateInstall() else {
            window?.title = "Dayglass — local install not found"
            return
        }
        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: located.python)
        proc.arguments = ["-m", "dayglass", "serve", "--port", String(port)]
        proc.currentDirectoryURL = URL(fileURLWithPath: located.root)
        proc.standardOutput = FileHandle(forWritingAtPath: "/dev/null")
        proc.standardError = FileHandle(forWritingAtPath: "/dev/null")
        do {
            try proc.run()
            ownedServer = proc
        } catch {
            window?.title = "Dayglass — server failed to start"
        }
    }

    private func waitThenLoad() {
        DispatchQueue.global(qos: .userInitiated).async {
            let deadline = Date().addingTimeInterval(8)
            while Date() < deadline {
                if self.portOpen(self.port) { break }
                Thread.sleep(forTimeInterval: 0.15)
            }
            DispatchQueue.main.async {
                guard self.portOpen(self.port) else {
                    self.window?.title = "Dayglass — server not running"
                    return
                }
                self.webView?.load(URLRequest(url: URL(string: "http://127.0.0.1:\(self.port)/")!))
            }
        }
    }

    private func portOpen(_ port: Int) -> Bool {
        let sock = socket(AF_INET, SOCK_STREAM, 0)
        if sock < 0 { return false }
        defer { close(sock) }
        var addr = sockaddr_in()
        addr.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
        addr.sin_family = sa_family_t(AF_INET)
        addr.sin_port = in_port_t(UInt16(port)).bigEndian
        addr.sin_addr = in_addr(s_addr: inet_addr("127.0.0.1"))
        let result = withUnsafePointer(to: &addr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                connect(sock, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }
        return result == 0
    }

    private func locateInstall() -> (root: String, python: String)? {
        let fm = FileManager.default
        var roots: [String] = []
        if let env = ProcessInfo.processInfo.environment["DAYGLASS_HOME"], !env.isEmpty {
            roots.append(env)
        }
        roots.append(fm.homeDirectoryForCurrentUser.appendingPathComponent("workspace/projects/dayglass").path)
        for root in roots {
            let python = (root as NSString).appendingPathComponent(".venv/bin/python")
            if fm.isExecutableFile(atPath: python) {
                return (root, python)
            }
        }
        return nil
    }

    private static func dockIcon() -> NSImage {
        let side: CGFloat = 1024
        let image = NSImage(size: NSSize(width: side, height: side))
        image.lockFocus()
        let bg = NSBezierPath(roundedRect: NSRect(x: 0, y: 0, width: side, height: side), xRadius: 224, yRadius: 224)
        NSColor(calibratedRed: 0.09, green: 0.16, blue: 0.38, alpha: 1).setFill()
        bg.fill()
        NSColor.white.setStroke()
        let ring = NSBezierPath(ovalIn: NSRect(x: 230, y: 230, width: 564, height: 564))
        ring.lineWidth = 46
        ring.stroke()
        let bar = NSBezierPath()
        bar.move(to: NSPoint(x: 360, y: 690))
        bar.line(to: NSPoint(x: 664, y: 512))
        bar.line(to: NSPoint(x: 360, y: 334))
        bar.lineWidth = 42
        bar.lineCapStyle = .round
        bar.lineJoinStyle = .round
        bar.stroke()
        image.unlockFocus()
        return image
    }
}

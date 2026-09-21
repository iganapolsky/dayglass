import Cocoa

let size = NSSize(width: 512, height: 512)
let image = NSImage(size: size)

image.lockFocus()

let ctx = NSGraphicsContext.current!.cgContext

// Background: rounded dark charcoal rounded rect
let rect = NSRect(x: 32, y: 32, width: 448, height: 448)
let path = NSBezierPath(roundedRect: rect, xRadius: 96, yRadius: 96)

// Dark gradient
let gradient = NSGradient(starting: NSColor(red: 0.15, green: 0.18, blue: 0.22, alpha: 1.0),
                          ending: NSColor(red: 0.08, green: 0.09, blue: 0.11, alpha: 1.0))!
gradient.draw(in: path, angle: -45)

// Outer border
NSColor(red: 0.25, green: 0.30, blue: 0.36, alpha: 0.6).setStroke()
path.lineWidth = 4
path.stroke()

// Glass Lenses / Eyeglasses symbol in center
let config = NSImage.SymbolConfiguration(pointSize: 180, weight: .semibold)
if let symbol = NSImage(systemSymbolName: "eyeglasses", accessibilityDescription: nil)?.withSymbolConfiguration(config) {
    let symRect = NSRect(x: 106, y: 156, width: 300, height: 200)
    NSColor(red: 0.23, green: 0.51, blue: 0.96, alpha: 1.0).set() // Electric blue
    symbol.draw(in: symRect, from: .zero, operation: .sourceOver, fraction: 1.0)
}

image.unlockFocus()

// Save to PNG
let tiff = image.tiffRepresentation!
let rep = NSBitmapImageRep(data: tiff)!
let png = rep.representation(using: .png, properties: [:])!

let outputDir = URL(fileURLWithPath: "/tmp/DayglassIcon.iconset")
try? FileManager.default.createDirectory(at: outputDir, withIntermediateDirectories: true)

let sizes = [16, 32, 64, 128, 256, 512]
for s in sizes {
    let resized = NSImage(size: NSSize(width: s, height: s))
    resized.lockFocus()
    image.draw(in: NSRect(x: 0, y: 0, width: s, height: s))
    resized.unlockFocus()
    let rRep = NSBitmapImageRep(data: resized.tiffRepresentation!)!
    let rPng = rRep.representation(using: .png, properties: [:])!
    try! rPng.write(to: outputDir.appendingPathComponent("icon_\(s)x\(s).png"))
    if s <= 256 {
        let s2 = s * 2
        let resized2 = NSImage(size: NSSize(width: s2, height: s2))
        resized2.lockFocus()
        image.draw(in: NSRect(x: 0, y: 0, width: s2, height: s2))
        resized2.unlockFocus()
        let rRep2 = NSBitmapImageRep(data: resized2.tiffRepresentation!)!
        let rPng2 = rRep2.representation(using: .png, properties: [:])!
        try! rPng2.write(to: outputDir.appendingPathComponent("icon_\(s)x\(s)@2x.png"))
    }
}

print("Iconset created at /tmp/DayglassIcon.iconset")

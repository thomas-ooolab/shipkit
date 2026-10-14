// popup-tools.swift — macOS helpers for capture-native-popup.js (run: `swift popup-tools.swift <cmd> ...`).
//   list                                           JSON of Chromium / Chrome-for-Testing windows
//                                                  {id, layer, onscreen, x, y, w, h} (points)
//   compose <main.png> <popup.png> <out.png> <mainX> <mainY> <popupX> <popupY> <mainW>
//                                                  paste the popup onto the main-window image; the
//                                                  pixel/point scale is main image width / <mainW>
import Foundation
import CoreGraphics
import ImageIO

let a = CommandLine.arguments
if a.count < 2 { exit(64) }

if a[1] == "list" {
  let list = CGWindowListCopyWindowInfo([.optionAll], kCGNullWindowID) as! [[String: Any]]
  var out: [[String: Any]] = []
  for w in list {
    let owner = w[kCGWindowOwnerName as String] as? String ?? ""
    guard owner.contains("Chromium") || owner.contains("Chrome for Testing") else { continue }
    let b = w[kCGWindowBounds as String] as! [String: CGFloat]
    out.append(["id": w[kCGWindowNumber as String] ?? 0, "layer": w[kCGWindowLayer as String] ?? 0,
                "onscreen": w[kCGWindowIsOnscreen as String] ?? false,
                "x": b["X"] ?? 0, "y": b["Y"] ?? 0, "w": b["Width"] ?? 0, "h": b["Height"] ?? 0])
  }
  print(String(data: try! JSONSerialization.data(withJSONObject: out), encoding: .utf8)!)
} else if a[1] == "compose", a.count == 10 {
  func load(_ p: String) -> CGImage { CGImageSourceCreateImageAtIndex(CGImageSourceCreateWithURL(URL(fileURLWithPath: p) as CFURL, nil)!, 0, nil)! }
  let main = load(a[2]), pop = load(a[3])
  let mx = Double(a[5])!, my = Double(a[6])!, px = Double(a[7])!, py = Double(a[8])!
  let scale = Double(main.width) / Double(a[9])!
  let ctx = CGContext(data: nil, width: main.width, height: main.height, bitsPerComponent: 8, bytesPerRow: 0,
                      space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
  ctx.draw(main, in: CGRect(x: 0, y: 0, width: main.width, height: main.height))
  // CoreGraphics' origin is bottom-left; window coordinates are top-left
  let dy = Double(main.height) - (py - my) * scale - Double(pop.height)
  let popRect = CGRect(x: (px - mx) * scale, y: dy, width: Double(pop.width), height: Double(pop.height))
  ctx.draw(pop, in: popRect)
  // ring the popup so it is the first thing the eye finds in the window-sized image
  ctx.setStrokeColor(CGColor(red: 0.88, green: 0.11, blue: 0.28, alpha: 1)); ctx.setLineWidth(4)
  ctx.stroke(popRect.insetBy(dx: -4, dy: -4))
  let dest = CGImageDestinationCreateWithURL(URL(fileURLWithPath: a[4]) as CFURL, "public.png" as CFString, 1, nil)!
  CGImageDestinationAddImage(dest, ctx.makeImage()!, nil)
  CGImageDestinationFinalize(dest)
  print("composed")
} else { exit(64) }

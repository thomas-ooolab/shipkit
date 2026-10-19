# Screenshot scale — shared by every skill that saves or attaches a screenshot

An image that is saved as evidence, written into a spec or contract, or attached to Jira is captured at **scale 1**, the full
size the tool gives. A picture a reader cannot read proves nothing: a full-page capture at scale 0.6 came out 874 px wide, the
text was unreadable, and the PO saw nothing.

- **Claude in Chrome** (`mcp__claude-in-chrome__computer`): `action: "screenshot"` or `"zoom"` with `scale: 1` written out (it is
  also the default), and `save_to_disk: true` when the image is kept or attached. **Never** a `scale` below 1 for an image that
  is saved or attached. A `scale` below 1 is only for a throwaway look that is neither saved nor shown to anyone.
  ```
  computer  action: "screenshot"  scale: 1  save_to_disk: true
  computer  action: "zoom"  region: [x0, y0, x1, y1]  scale: 1  save_to_disk: true      (a closer look at one area)
  ```
- **Playwright MCP** (`browser_take_screenshot`) has no scale option: take it at its own size and never shrink the saved file
  afterwards (no resize, no downscaled copy).
- **Check the saved image** (open it, as each skill already says): the text you rely on is readable at the size it was saved, and
  the image is as wide as the viewport you captured. A narrower image was scaled down: retake it at scale 1.

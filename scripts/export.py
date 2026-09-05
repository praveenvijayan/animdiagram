#!/usr/bin/env python3
"""animdiagram export — render a finished looping SVG to an MP4 (H.264) video.

    python3 export.py --doctor                          # check playwright / chromium / ffmpeg
    python3 export.py diagram.svg                       # diagram-desktop.mp4 (1920x1080)
    python3 export.py diagram.svg --layout mobile       # diagram-mobile.mp4  (1080x1920, vertical)
    python3 export.py diagram.svg --layout both
    python3 export.py diagram.svg --loops 2 --fps 30 --out clips/

The SVG stays the primary deliverable. This is an opt-in extra for platforms
that strip SVG animation (Substack, LinkedIn, X/Twitter, Slack previews).

How it works: the SVG is inlined into a page sized to the target canvas,
every CSS animation is paused and seeked to an exact time with the Web
Animations API (same trick as preview.py), one screenshot per frame is piped
into ffmpeg. Deterministic timing, no dropped frames, no real-time capture.

Requirements (opt-in, checked by --doctor, never auto-installed):
    pip install playwright && python3 -m playwright install chromium
    ffmpeg with libx264 on PATH (brew install ffmpeg / apt install ffmpeg)
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

LAYOUTS = {
    # name: (width, height, margin)  — margin is the minimum gap around the SVG on each side
    "desktop": (1920, 1080, 120),
    "mobile": (1080, 1920, 72),
}
PAPER = {"dark": "#0D0D0E", "light": "#F5F5F5"}

PAGE = """<!doctype html>
<meta charset="utf-8">
<style>
  html, body { margin: 0; width: __W__px; height: __H__px; overflow: hidden; background: __BG__; }
  body { display: grid; place-items: center; }
  #wrap { width: __SW__px; height: __SH__px; }
  #wrap svg { display: block; width: 100%; height: 100%; }
</style>
<div id="wrap">__SVG__</div>
"""

SEEK_JS = """
(ms) => {
  const anims = document.getAnimations({ subtree: true });
  for (const a of anims) { a.pause(); a.currentTime = ms; }
  return anims.length;
}
"""

LOOP_JS = """
() => {
  let loop = 0;
  for (const a of document.getAnimations({ subtree: true })) {
    const d = a.effect.getComputedTiming().duration;
    if (typeof d === 'number' && d > loop) loop = d;
  }
  return loop;
}
"""


# ---------------------------------------------------------------- doctor ------

def doctor() -> int:
    """Report each requirement; exit 0 if MP4 export can run, 2 otherwise."""
    rows: list[tuple[bool, str, str]] = []

    ok_py = sys.version_info >= (3, 10)
    rows.append((ok_py, f"python {sys.version.split()[0]}", "" if ok_py else "need Python 3.10+"))

    try:
        import playwright  # noqa: F401
        from playwright.sync_api import sync_playwright
        rows.append((True, "playwright module", ""))
        try:
            with sync_playwright() as p:
                b = p.chromium.launch()
                ver = b.version
                b.close()
            rows.append((True, f"chromium {ver}", ""))
        except Exception as e:  # noqa: BLE001
            msg = str(e).splitlines()[0][:80]
            rows.append((False, "chromium browser", f"python3 -m playwright install chromium   ({msg})"))
    except ModuleNotFoundError:
        rows.append((False, "playwright module", "pip install playwright && python3 -m playwright install chromium"))
        rows.append((False, "chromium browser", "install playwright first"))

    ff = shutil.which("ffmpeg")
    if ff:
        try:
            enc = subprocess.run([ff, "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=20).stdout
            has_x264 = "libx264" in enc
            ver = subprocess.run([ff, "-version"], capture_output=True, text=True, timeout=20).stdout.split("\n")[0]
            ver = re.sub(r"\s+Copyright.*", "", ver)
            rows.append((True, ver, ""))
            rows.append((has_x264, "ffmpeg libx264 encoder", "" if has_x264 else "rebuild/reinstall ffmpeg with libx264 (brew install ffmpeg)"))
        except Exception as e:  # noqa: BLE001
            rows.append((False, "ffmpeg", f"found at {ff} but failed to run: {e}"))
    else:
        rows.append((False, "ffmpeg on PATH", "brew install ffmpeg   |   apt install ffmpeg   |   winget install ffmpeg"))

    width = max(len(r[1]) for r in rows)
    for ok, what, fix in rows:
        print(f"  {'ok     ' if ok else 'MISSING'}  {what.ljust(width)}  {fix}")
    good = all(r[0] for r in rows)
    print()
    print("MP4 export ready." if good else "MP4 export not available on this machine. Install the MISSING items above, or ship the .svg (it needs nothing).")
    return 0 if good else 2


# ---------------------------------------------------------------- render ------

def read_svg(path: Path) -> tuple[str, int, int, str]:
    text = path.read_text(encoding="utf-8")
    if text.lstrip().startswith("<?xml"):
        text = text.split("?>", 1)[1]
    m = re.search(r'viewBox="\s*[\d.]+\s+[\d.]+\s+([\d.]+)\s+([\d.]+)\s*"', text)
    if not m:
        sys.exit(f"error: {path}: no viewBox on <svg>; export needs it to size the canvas")
    w, h = float(m.group(1)), float(m.group(2))
    skin = "light" if re.search(r"\(light skin\)", text) or PAPER["light"].lower() in text.lower()[:2000] else "dark"
    return text, int(w), int(h), skin


def fit(svg_w: int, svg_h: int, layout: str) -> tuple[int, int]:
    W, H, m = LAYOUTS[layout]
    scale = min((W - 2 * m) / svg_w, (H - 2 * m) / svg_h)
    return round(svg_w * scale), round(svg_h * scale)


def render(svg_path: Path, layout: str, out: Path, fps: int, loops: int, bg: str | None,
           frames_dir: Path | None) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        sys.exit("error: playwright not installed. Run:  python3 scripts/export.py --doctor")

    svg, sw, sh, skin = read_svg(svg_path)
    W, H, _ = LAYOUTS[layout]
    fw, fh = fit(sw, sh, layout)
    page_bg = bg or PAPER[skin]
    html = (PAGE.replace("__W__", str(W)).replace("__H__", str(H))
            .replace("__SW__", str(fw)).replace("__SH__", str(fh))
            .replace("__BG__", page_bg).replace("__SVG__", svg))

    ff = None if frames_dir else shutil.which("ffmpeg")
    if not frames_dir and not ff:
        sys.exit("error: ffmpeg not on PATH. Install it, or pass --frames-dir DIR to get a PNG sequence instead.")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as e:  # noqa: BLE001
            sys.exit(f"error: chromium not available ({str(e).splitlines()[0]}). Run:  python3 -m playwright install chromium")
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        page.emulate_media(reduced_motion="no-preference")
        page.set_content(html, wait_until="load")
        loop_ms = page.evaluate(LOOP_JS)
        if not loop_ms:
            browser.close()
            sys.exit(f"error: {svg_path}: no CSS animations found (did you run timeline.py --inject?)")
        n_anims = page.evaluate(SEEK_JS, 0)
        loop_s = loop_ms / 1000.0
        total = round(loop_s * loops * fps)

        print(f"{svg_path.name}: {sw}x{sh} svg, skin {skin}, loop {loop_s:.2f}s, {n_anims} animations")
        print(f"  {layout}: {W}x{H} canvas, svg drawn at {fw}x{fh} on {page_bg}, {fps} fps x {loops} loop(s) = {total} frames")

        proc = None
        if ff:
            out.parent.mkdir(parents=True, exist_ok=True)
            cmd = [ff, "-hide_banner", "-loglevel", "error", "-y",
                   "-f", "image2pipe", "-framerate", str(fps), "-c:v", "png", "-i", "-",
                   "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow",
                   "-movflags", "+faststart", "-r", str(fps), str(out)]
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        else:
            frames_dir.mkdir(parents=True, exist_ok=True)

        for i in range(total):
            t_ms = (i / fps * 1000.0) % loop_ms          # [0, loop): no duplicate frame at the seam
            page.evaluate(SEEK_JS, t_ms)
            png = page.screenshot(type="png", clip={"x": 0, "y": 0, "width": W, "height": H})
            if proc:
                proc.stdin.write(png)
            else:
                (frames_dir / f"{layout}-{i:05d}.png").write_bytes(png)
            if i % fps == 0 or i == total - 1:
                print(f"\r  frame {i + 1}/{total}", end="", flush=True)
        print()
        browser.close()

    if proc:
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            sys.exit(f"error: ffmpeg exited {rc}")
        size = out.stat().st_size
        print(f"  wrote {out}  ({size / 1024:.0f} KB, {total / fps:.1f}s)")
    else:
        print(f"  wrote {total} PNG frames to {frames_dir}/  (encode: ffmpeg -framerate {fps} -i {frames_dir}/{layout}-%05d.png -c:v libx264 -pix_fmt yuv420p out.mp4)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("svg", nargs="?", type=Path, help="finished, injected diagram .svg")
    ap.add_argument("--doctor", action="store_true", help="check requirements and exit")
    ap.add_argument("--layout", choices=["desktop", "mobile", "both"], default="desktop",
                    help="desktop = 1920x1080 landscape, mobile = 1080x1920 vertical (default: desktop)")
    ap.add_argument("--fps", type=int, default=30, help="frames per second (default 30)")
    ap.add_argument("--loops", type=int, default=1, help="how many times the loop plays in the clip (default 1; use 2-3 for players that do not loop)")
    ap.add_argument("--out", type=Path, help="output .mp4 (single layout) or directory (default: next to the svg)")
    ap.add_argument("--bg", help="canvas colour around the diagram (default: the skin's paper colour)")
    ap.add_argument("--frames-dir", type=Path, help="write a PNG sequence here instead of encoding (no ffmpeg needed)")
    args = ap.parse_args()

    if args.doctor:
        return doctor()
    if not args.svg:
        ap.error("svg path required (or --doctor)")
    if not args.svg.exists():
        ap.error(f"{args.svg} not found")
    if args.fps < 1 or args.fps > 60:
        ap.error("--fps must be 1..60")
    if args.loops < 1:
        ap.error("--loops must be >= 1")

    layouts = ["desktop", "mobile"] if args.layout == "both" else [args.layout]
    stem = args.svg.stem
    for lay in layouts:
        if args.out and args.out.suffix.lower() == ".mp4":
            if len(layouts) > 1:
                ap.error("--out must be a directory when --layout both")
            out = args.out
        else:
            out_dir = args.out or args.svg.parent
            out = out_dir / f"{stem}-{lay}.mp4"
        render(args.svg, lay, out, args.fps, args.loops, args.bg, args.frames_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())

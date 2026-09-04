#!/usr/bin/env python3
"""animdiagram preview — wraps an SVG in an HTML page with a timeline scrubber.

    python3 preview.py diagram.svg            # writes diagram.preview.html next to it
    python3 preview.py diagram.svg --out p.html
    python3 preview.py diagram.svg --open     # also open in the default browser

The page inlines the SVG, so the Web Animations API can pause every CSS
animation and seek it to an exact second. Use it to tune event offsets by eye,
check the static frame (t = loop end, or "static" button), and compare the
diagram on a dark and a light page background.
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

PAGE = """<!doctype html>
<meta charset="utf-8">
<title>preview · __NAME__</title>
<style>
  :root { color-scheme: dark; }
  body { margin: 0; font: 13px/1.4 Inter, -apple-system, 'Segoe UI', sans-serif; background: #0a0a0b; color: #b6c0cf; }
  body.light { background: #f5f5f5; color: #2d3142; }
  header { display: flex; gap: 12px; align-items: center; padding: 12px 16px; border-bottom: 1px solid rgba(128,128,128,.25); flex-wrap: wrap; }
  header b { font-family: ui-monospace, Menlo, monospace; letter-spacing: 1px; }
  button { font: inherit; padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(128,128,128,.4); background: transparent; color: inherit; cursor: pointer; }
  button[aria-pressed="true"] { background: rgba(76,244,144,.15); border-color: #4CF490; }
  input[type=range] { width: 320px; }
  #t { font-family: ui-monospace, Menlo, monospace; min-width: 90px; }
  main { display: grid; place-items: center; padding: 32px 16px; }
  #wrap { transform-origin: top center; }
  #wrap svg { display: block; }
  .hint { opacity: .6; font-size: 12px; }
</style>
<header>
  <b>__NAME__</b>
  <button id="play" aria-pressed="true">pause</button>
  <button id="static">static frame</button>
  <input id="scrub" type="range" min="0" max="1" step="0.01" value="0">
  <span id="t">0.00 s</span>
  <button id="bg">light bg</button>
  <button id="zoom">2×</button>
  <span class="hint">space = play/pause · ←/→ = ±0.1 s · shift = ±1 s</span>
</header>
<main><div id="wrap">__SVG__</div></main>
<script>
(() => {
  const wrap = document.getElementById('wrap');
  const play = document.getElementById('play');
  const stat = document.getElementById('static');
  const scrub = document.getElementById('scrub');
  const tOut = document.getElementById('t');
  const anims = () => wrap.getAnimations({ subtree: true });
  // loop length = longest finite iteration duration among animations (ms)
  let loop = 0;
  for (const a of anims()) {
    const d = a.effect.getComputedTiming().duration;
    if (typeof d === 'number' && d > loop) loop = d;
  }
  if (!loop) loop = 9000;
  scrub.max = (loop / 1000).toFixed(2);
  let playing = true, raf;
  function seek(ms) {
    for (const a of anims()) { a.pause(); a.currentTime = ms; }
    scrub.value = (ms / 1000).toFixed(2);
    tOut.textContent = (ms / 1000).toFixed(2) + ' s';
  }
  function setPlaying(p) {
    playing = p;
    play.setAttribute('aria-pressed', String(p));
    play.textContent = p ? 'pause' : 'play';
    if (p) { for (const a of anims()) a.play(); tick(); } else { cancelAnimationFrame(raf); }
  }
  function tick() {
    if (!playing) return;
    const a = anims()[0];
    if (a) { const ms = (a.currentTime || 0) % loop; scrub.value = (ms / 1000).toFixed(2); tOut.textContent = (ms / 1000).toFixed(2) + ' s'; }
    raf = requestAnimationFrame(tick);
  }
  play.onclick = () => setPlaying(!playing);
  scrub.oninput = () => { setPlaying(false); seek(parseFloat(scrub.value) * 1000); };
  stat.onclick = () => { setPlaying(false); seek(loop - 1); };
  document.getElementById('bg').onclick = (e) => { document.body.classList.toggle('light'); e.target.textContent = document.body.classList.contains('light') ? 'dark bg' : 'light bg'; };
  document.getElementById('zoom').onclick = (e) => { const z = wrap.style.transform === 'scale(2)' ? '' : 'scale(2)'; wrap.style.transform = z; e.target.textContent = z ? '1×' : '2×'; };
  document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT') return;
    if (e.code === 'Space') { e.preventDefault(); setPlaying(!playing); }
    if (e.code === 'ArrowRight' || e.code === 'ArrowLeft') {
      e.preventDefault(); setPlaying(false);
      const step = (e.shiftKey ? 1000 : 100) * (e.code === 'ArrowRight' ? 1 : -1);
      seek((parseFloat(scrub.value) * 1000 + step + loop) % loop);
    }
  });
  tick();
})();
</script>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("svg", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--open", action="store_true")
    args = ap.parse_args()
    svg = args.svg.read_text(encoding="utf-8")
    if svg.lstrip().startswith("<?xml"):
        svg = svg.split("?>", 1)[1]
    out = args.out or args.svg.with_suffix(".preview.html")
    out.write_text(PAGE.replace("__NAME__", args.svg.name).replace("__SVG__", svg), encoding="utf-8")
    print(out)
    if args.open:
        webbrowser.open(out.resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())

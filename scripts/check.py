#!/usr/bin/env python3
"""animdiagram verifier — checks a looping animated SVG against the skill contract.

    python3 check.py diagram.svg [--strict]

Errors (exit 1): malformed XML, missing root attributes, scripts / SMIL /
external references, animation-name without @keyframes (or vice versa),
non-monotonic keyframe stops, missing reduced-motion block, viewBox off grid.
Warnings (exit 0 unless --strict): budget overruns, off-grid coordinates,
odd font sizes, too many colours on animated elements.

No third-party dependencies.
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

SVG_NS = "http://www.w3.org/2000/svg"
NS = {"svg": SVG_NS}

BUDGET = {
    "story_keyframes": 14,   # story-clock keyframes (packets + rings + glows + phases)
    "story_packets": 8,      # packets on the shared clock
    "streams": 4,            # ambient stream keyframes
    "phases": 6,             # phase / show labels
    "nodes": 9,              # rects wider than 40px that are not the frame / zones
    "colors": 3,             # distinct hex colours on animated elements
    "loop_min": 4.0,
    "loop_max": 14.0,
}
FONT_SIZES_OK = {7, 7.5, 8, 8.5, 9, 9.5, 10, 10.5, 12, 13, 14, 16, 17}
NEUTRALS = {"#0D0D0E", "#141416", "#202126", "#363840", "#6F7987", "#B6C0CF", "#F4F6FC",
            "#F5F5F5", "#ECECEC", "#2D3142", "#4F5D75", "#7A8399", "#BFC0C0", "#FFFFFF", "NONE"}

KEYFRAMES_RE = re.compile(r"@keyframes\s+([A-Za-z_][\w-]*)\s*\{", re.S)
ANIM_NAME_RE = re.compile(r"animation-name\s*:\s*([A-Za-z_][\w-]*)")
ANIM_SHORT_RE = re.compile(r"animation\s*:\s*([A-Za-z_][\w-]*)\s")
STOP_RE = re.compile(r"([0-9.]+)%")
DURATION_RE = re.compile(r"animation-duration\s*:\s*([0-9.]+)s")


def tag(el) -> str:
    return el.tag.split("}")[-1]


def extract_keyframe_blocks(css: str) -> dict[str, str]:
    """name -> body text, using brace matching."""
    blocks = {}
    for m in KEYFRAMES_RE.finditer(css):
        name = m.group(1)
        depth, i = 1, m.end()
        while i < len(css) and depth:
            if css[i] == "{":
                depth += 1
            elif css[i] == "}":
                depth -= 1
            i += 1
        blocks[name] = css[m.end(): i - 1]
    return blocks


def check(path: Path):
    errors, warns = [], []
    text = path.read_text(encoding="utf-8")

    # --- XML
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        return [f"XML parse error: {exc}"], []
    if root.tag != f"{{{SVG_NS}}}svg":
        errors.append("root element is not <svg xmlns=\"http://www.w3.org/2000/svg\">")
        return errors, warns

    # --- root attributes
    w, h, vb = root.get("width"), root.get("height"), root.get("viewBox")
    if not (w and h and vb):
        errors.append("root needs width, height and viewBox")
    else:
        try:
            wi, hi = int(w), int(h)
            parts = [int(float(p)) for p in vb.split()]
            if parts != [0, 0, wi, hi]:
                errors.append(f"viewBox {vb!r} must equal '0 0 {wi} {hi}'")
            if wi % 4 or hi % 4:
                errors.append(f"width/height {wi}x{hi} must be multiples of 4")
        except ValueError:
            errors.append("width/height must be integers")
    if root.get("role") != "img":
        errors.append('root needs role="img"')
    label = root.get("aria-label", "")
    if not label.strip():
        errors.append("root needs a non-empty aria-label describing the whole story")
    elif len(label) > 400:
        warns.append(f"aria-label is {len(label)} chars; keep it to one or two sentences")

    # --- forbidden content
    for el in root.iter():
        t = tag(el)
        if t == "script":
            errors.append("<script> is not allowed; motion is CSS only")
        if t in ("animate", "animateTransform", "animateMotion", "set"):
            errors.append(f"SMIL <{t}> is not allowed; use CSS @keyframes")
        if t == "foreignObject":
            errors.append("<foreignObject> is not allowed")
        for attr in ("href", f"{{http://www.w3.org/1999/xlink}}href"):
            v = el.get(attr)
            if v and not v.startswith("#"):
                errors.append(f"<{t}> references external resource {v!r}")
        for k in el.attrib:
            if k.startswith("on"):
                errors.append(f"<{t}> has event attribute {k}")

    styles = root.findall(".//svg:style", NS)
    if len(styles) != 1:
        errors.append(f"expected exactly one <style>, found {len(styles)}")
    css = "".join(s.text or "" for s in styles)
    if "@import" in css or "url(" in css:
        errors.append("<style> must not @import or url() anything")

    # --- keyframes vs references
    blocks = extract_keyframe_blocks(css)
    used = Counter()
    for el in root.iter():
        st = el.get("style", "")
        for m in ANIM_NAME_RE.finditer(st):
            used[m.group(1)] += 1
        for m in ANIM_SHORT_RE.finditer(st):
            used[m.group(1)] += 1
    for m in ANIM_NAME_RE.finditer(css):
        used[m.group(1)] += 1
    for m in ANIM_SHORT_RE.finditer(css):
        used[m.group(1)] += 1
    for name in used:
        if name not in blocks and name != "none":
            errors.append(f"animation-name '{name}' has no @keyframes")
    for name in blocks:
        if name not in used:
            warns.append(f"@keyframes '{name}' is defined but never used")

    # --- keyframe stop order
    for name, body in blocks.items():
        stops = [float(s) for s in STOP_RE.findall(body)]
        if any(s < 0 or s > 100 for s in stops):
            errors.append(f"@keyframes '{name}' has a stop outside 0–100%")
        # selectors like "8%, 100%" may repeat; require non-decreasing sequence of selector groups
        # Selector groups like "8%, 100% {…}" pin the end state; a group is out of order only
        # when its lowest stop falls before the lowest stop of the previous group.
        groups = re.findall(r"([0-9.%,\s]+)\{", body)
        last = -1.0
        for g in groups:
            vals = [float(v) for v in STOP_RE.findall(g)]
            if not vals:
                continue
            if min(vals) < last - 1e-9:
                errors.append(f"@keyframes '{name}': stop {min(vals)}% appears after {last}% — stops must be in order")
            last = min(vals)

    # --- reduced motion
    if "prefers-reduced-motion" not in css:
        errors.append("missing @media (prefers-reduced-motion: reduce) block that hides .pkt/.ring/.story")
    elif ".pkt" not in css.split("prefers-reduced-motion", 1)[1]:
        errors.append("reduced-motion block must switch off .pkt (and .ring/.story/.glow)")

    # --- loop length
    durs = [float(d) for d in DURATION_RE.findall(css)]
    story = [d for d in durs if d >= BUDGET["loop_min"]]
    if story:
        loop = max(story)
        if loop > BUDGET["loop_max"]:
            warns.append(f"loop is {loop}s; keep story loops ≤ {BUDGET['loop_max']}s")
        if len(set(story)) > 1:
            warns.append(f"several story durations {sorted(set(story))}; one shared clock reads better")

    # --- budgets
    story_kf = [n for n in blocks if not n.startswith("s") or n.endswith("-ring") or n.endswith("-glow")]
    packets = [el for el in root.iter() if "pkt" in (el.get("class") or "").split()
               and "animation-duration" not in (el.get("style") or "")]
    streams = [el for el in root.iter() if "pkt" in (el.get("class") or "").split()
               and "animation-duration" in (el.get("style") or "")]
    stream_names = {ANIM_NAME_RE.search(el.get("style", "")).group(1) for el in streams
                    if ANIM_NAME_RE.search(el.get("style", ""))}
    phases = [el for el in root.iter() if tag(el) == "text" and "story" in (el.get("class") or "").split()]
    if len(packets) > BUDGET["story_packets"]:
        warns.append(f"{len(packets)} story packets; budget is {BUDGET['story_packets']} — split the story or merge messages")
    if len(stream_names) > BUDGET["streams"]:
        warns.append(f"{len(stream_names)} ambient streams; budget is {BUDGET['streams']}")
    if len(phases) > BUDGET["phases"]:
        warns.append(f"{len(phases)} phase/show labels; budget is {BUDGET['phases']}")

    # nodes: rects between 40 and 400 px wide that are not glow overlays
    nodes = []
    for el in root.iter():
        if tag(el) != "rect":
            continue
        cls = (el.get("class") or "").split()
        if "glow" in cls or "bar" in cls:
            continue
        try:
            rw, rh = float(el.get("width", 0)), float(el.get("height", 0))
        except ValueError:
            continue
        if 40 <= rw <= 400 and 24 <= rh <= 160 and el.get("stroke-dasharray") is None:
            nodes.append(el)
    if len(nodes) > BUDGET["nodes"] * 2:
        warns.append(f"{len(nodes)} boxes drawn; if more than {BUDGET['nodes']} are distinct nodes, split into two diagrams")

    # colours on animated elements
    colors = set()
    for el in root.iter():
        cls = set((el.get("class") or "").split())
        if cls & {"pkt", "ring", "story", "glow", "bar"}:
            for k in ("fill", "stroke"):
                v = (el.get(k) or "").upper()
                if v.startswith("#") and v not in NEUTRALS:
                    colors.add(v)
            for child in el.iter():
                for k in ("fill", "stroke"):
                    v = (child.get(k) or "").upper()
                    if v.startswith("#") and v not in NEUTRALS:
                        colors.add(v)
    if len(colors) > BUDGET["colors"]:
        warns.append(f"{len(colors)} accent colours on animated elements {sorted(colors)}; budget is {BUDGET['colors']} (signal + ≤2 lanes)")

    # --- typography
    has_text_rule = re.search(r"(^|[}\s,])text\s*\{[^}]*font-family", css) is not None
    off_sizes = Counter()
    for el in root.iter():
        if tag(el) != "text":
            continue
        if not has_text_rule and not el.get("font-family") and not el.get("class"):
            warns.append(f"<text> '{(el.text or '').strip()[:24]}' has no font-family and no class")
        fs = el.get("font-size")
        if fs:
            try:
                if float(fs) not in FONT_SIZES_OK:
                    off_sizes[fs] += 1
            except ValueError:
                pass
    if off_sizes:
        warns.append(f"font sizes off the ramp: {dict(off_sizes)}")

    # --- grid (warning only): rect x/y/width/height on the 4px grid, ignoring the 0.5 frame rect
    off_grid = 0
    for el in nodes:
        for k in ("x", "y", "width", "height"):
            try:
                v = float(el.get(k, 0))
            except ValueError:
                continue
            if abs(v - round(v / 4) * 4) > 1e-6:
                off_grid += 1
    if off_grid:
        warns.append(f"{off_grid} node rect values are off the 4px grid")

    # --- legend / title presence
    texts = [(el.text or "").strip() for el in root.iter() if tag(el) == "text"]
    if not any(t.isupper() and len(t) > 3 for t in texts[:3]):
        warns.append("no uppercase title text found near the top of the file")

    return errors, warns


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("svg", type=Path, nargs="+")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = ap.parse_args()
    rc = 0
    for p in args.svg:
        errors, warns = check(p)
        print(f"== {p}")
        for e in errors:
            print(f"  ERROR  {e}")
        for w in warns:
            print(f"  warn   {w}")
        if not errors and not warns:
            print("  ok")
        if errors or (args.strict and warns):
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())

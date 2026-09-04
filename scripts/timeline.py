#!/usr/bin/env python3
"""animdiagram timeline compiler.

Turns a small JSON motion spec into the CSS `@keyframes` block and the
decorative packet / ring / glow / phase elements that the looping-SVG style
needs, then injects them into an SVG between marker comments:

    <style>
      ...base rules...
      <!-- @motion:css -->        (inside <style>, use CSS comment form: /* @motion:css */)
      /* @/motion:css */
    </style>
    ...
    <!-- @motion:elements -->
    <!-- @/motion:elements -->

Usage:
    python3 timeline.py spec.json --inject diagram.svg     # rewrite between markers
    python3 timeline.py spec.json --print                  # print css + elements
    python3 timeline.py spec.json --table                  # print the schedule only

Spec format is documented in references/storyboard.md. All times in seconds.
No third-party dependencies.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

CSS_OPEN = "/* @motion:css */"
CSS_CLOSE = "/* @/motion:css */"
EL_OPEN = "<!-- @motion:elements -->"
EL_CLOSE = "<!-- @/motion:elements -->"

DEFAULTS = {
    "loop": 9.0,          # seconds, one shared story clock
    "accent": "#4CF490",  # signal colour for story packets
    "r": 4,               # packet radius
    "ring_r": 10,         # arrival ring radius
    "appear": 0.06,       # seconds from spawn to fully visible
    "fade": 0.12,         # seconds after arrival before packet hides
    "ring_dur": 0.5,      # seconds the arrival ring lives
    "glow_dur": 0.4,      # seconds the destination glow lives
    "gap": 0.3,           # seconds between chained events ("after")
    "hold": 0.1,          # edge width for phase/show windows
    "label_dy": -12,      # label offset above a packet
    "stroke_width": 1.5,  # ring stroke
}

NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


# ----------------------------------------------------------------------------
# helpers


def pct(t: float, loop: float) -> str:
    """Seconds -> keyframe percentage string with at most 2 decimals."""
    v = max(0.0, min(100.0, t / loop * 100.0))
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s or "0"


def fmt(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s or "0"


def tr(dx: float, dy: float) -> str:
    return f"transform: translate({fmt(dx)}px, {fmt(dy)}px);"


def esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


class SpecError(Exception):
    pass


def need(ev: dict, key: str):
    if key not in ev:
        raise SpecError(f"event '{ev.get('id', '?')}' needs '{key}'")
    return ev[key]


def point(v, ev, key) -> tuple[float, float]:
    if not (isinstance(v, (list, tuple)) and len(v) == 2):
        raise SpecError(f"event '{ev.get('id', '?')}': '{key}' must be [x, y]")
    return float(v[0]), float(v[1])


# ----------------------------------------------------------------------------
# path timing


def path_times(points: list[tuple[float, float]], start: float, travel: float):
    """Constant-speed timing across an orthogonal polyline."""
    segs = []
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        segs.append(math.hypot(x1 - x0, y1 - y0))
    total = sum(segs) or 1.0
    out, acc = [], 0.0
    for i, seg in enumerate(segs):
        acc += seg
        out.append(start + travel * acc / total)
    return out  # arrival time at points[1:]


# ----------------------------------------------------------------------------
# compilers: each returns (css_list, element_list, end_time)


def compile_packet(ev, cfg, loop):
    eid = ev["id"]
    at = float(ev["at"])
    travel = float(ev.get("travel", 0.6))
    src = point(need(ev, "from"), ev, "from")
    dst = point(need(ev, "to"), ev, "to")
    via = [point(p, ev, "via") for p in ev.get("via", [])]
    pts = [src] + via + [dst]
    color = ev.get("color", cfg["accent"])
    r = ev.get("r", cfg["r"])
    appear = cfg["appear"]
    fade = cfg["fade"]

    times = path_times(pts, at, travel)
    arrive = times[-1]
    hide = arrive + fade
    if hide > loop:
        raise SpecError(f"event '{eid}' ends at {hide:.2f}s, after the {loop}s loop")

    # keyframes
    lines = []
    if at > 0:
        lines.append(f"  0%, {pct(at, loop)}% {{ transform: translate(0, 0); opacity: 0; }}")
    else:
        lines.append("  0% { transform: translate(0, 0); opacity: 0; }")
    first_stop = times[0]
    ap = min(at + appear, first_stop - 0.001)
    if ap > at:
        lines.append(f"  {pct(ap, loop)}% {{ opacity: 1; }}")
    for (x, y), t in zip(pts[1:-1], times[:-1]):
        lines.append(f"  {pct(t, loop)}% {{ {tr(x - src[0], y - src[1])} }}")
    dx, dy = dst[0] - src[0], dst[1] - src[1]
    lines.append(f"  {pct(arrive, loop)}% {{ {tr(dx, dy)} opacity: 1; }}")
    lines.append(f"  {pct(hide, loop)}%, 100% {{ {tr(dx, dy)} opacity: 0; }}")
    css = [f"@keyframes {eid} {{\n" + "\n".join(lines) + "\n}"]

    # element
    els = []
    label = ev.get("label")
    circle = (
        f'<circle cx="{fmt(src[0])}" cy="{fmt(src[1])}" r="{r}" fill="{color}"'
    )
    if label:
        ly = src[1] + ev.get("label_dy", cfg["label_dy"])
        els.append(
            f'<g class="pkt" style="animation-name:{eid}">\n'
            f"    {circle}/>\n"
            f'    <text class="t-tag" x="{fmt(src[0])}" y="{fmt(ly)}" text-anchor="middle" '
            f'fill="{color}">{esc(label)}</text>\n'
            f"  </g>"
        )
    else:
        els.append(f'{circle} class="pkt" style="animation-name:{eid}"/>')

    # ring
    if ev.get("ring", True):
        rid = f"{eid}-ring"
        rr = ev.get("ring_r", cfg["ring_r"])
        r_end = min(arrive + cfg["ring_dur"], loop)
        r_peak = arrive + cfg["ring_dur"] * 0.08
        css.append(
            f"@keyframes {rid} {{ 0%, {pct(arrive, loop)}% {{ transform: scale(0.4); opacity: 0; }} "
            f"{pct(r_peak, loop)}% {{ transform: scale(0.5); opacity: 0.8; }} "
            f"{pct(r_end, loop)}%, 100% {{ transform: scale(1.4); opacity: 0; }} }}"
        )
        els.append(
            f'<circle cx="{fmt(dst[0])}" cy="{fmt(dst[1])}" r="{rr}" fill="none" '
            f'stroke="{color}" stroke-width="{cfg["stroke_width"]}" class="ring" '
            f'style="animation-name:{rid}"/>'
        )

    # glow
    glow = ev.get("glow")
    if glow:
        gid = f"{eid}-glow"
        g_end = min(arrive + cfg["glow_dur"], loop)
        g_peak = arrive + cfg["glow_dur"] * 0.2
        css.append(
            f"@keyframes {gid} {{ 0%, {pct(arrive, loop)}% {{ opacity: 0; }} "
            f"{pct(g_peak, loop)}% {{ opacity: 0.3; }} "
            f"{pct(g_end, loop)}%, 100% {{ opacity: 0; }} }}"
        )
        x, y, w, h = (float(glow[k]) for k in ("x", "y", "w", "h"))
        rx = glow.get("rx", 6)
        els.append(
            f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" rx="{rx}" '
            f'fill="{color}" class="glow" style="animation-name:{gid}"/>'
        )
    return css, els, arrive


def compile_stream(ev, cfg, loop):
    """Ambient constant stream on its own short clock (period), independent of the story."""
    eid = ev["id"]
    src = point(need(ev, "from"), ev, "from")
    dst = point(need(ev, "to"), ev, "to")
    via = [point(p, ev, "via") for p in ev.get("via", [])]
    pts = [src] + via + [dst]
    period = float(ev.get("period", 1.2))
    count = int(ev.get("count", 3))
    color = ev.get("color", cfg["accent"])
    r = ev.get("r", 3)
    phase = float(ev.get("phase", 0.0))  # extra delay offset in seconds

    times = path_times(pts, 0.0, period)  # over one period
    lines = ["  0% { transform: translate(0, 0); opacity: 0; }", "  12% { opacity: 1; }"]
    for (x, y), t in zip(pts[1:-1], times[:-1]):
        lines.append(f"  {pct(t, period)}% {{ {tr(x - src[0], y - src[1])} }}")
    dx, dy = dst[0] - src[0], dst[1] - src[1]
    lines.append(f"  88% {{ {tr(dx, dy)} opacity: 1; }}")
    lines.append(f"  100% {{ {tr(dx, dy)} opacity: 0; }}")
    css = [f"@keyframes {eid} {{\n" + "\n".join(lines) + "\n}"]

    els = []
    for k in range(count):
        delay = -(k * period / count) - phase
        els.append(
            f'<circle cx="{fmt(src[0])}" cy="{fmt(src[1])}" r="{r}" fill="{color}" class="pkt" '
            f'style="animation-name:{eid};animation-duration:{fmt(period)}s;animation-delay:{fmt(delay)}s"/>'
        )
    if ev.get("ring", False):
        rid = f"{eid}-ring"
        css.append(
            f"@keyframes {rid} {{ 0%, 88% {{ transform: scale(0.5); opacity: 0; }} "
            f"90% {{ transform: scale(0.6); opacity: 0.8; }} 100% {{ transform: scale(1.4); opacity: 0; }} }}"
        )
        for k in range(count):
            delay = -(k * period / count) - phase
            els.append(
                f'<circle cx="{fmt(dst[0])}" cy="{fmt(dst[1])}" r="{cfg["ring_r"]}" fill="none" '
                f'stroke="{color}" stroke-width="{cfg["stroke_width"]}" class="ring" '
                f'style="animation-name:{rid};animation-duration:{fmt(period)}s;animation-delay:{fmt(delay)}s"/>'
            )
    return css, els, None


def compile_window(ev, cfg, loop, kind):
    """phase / show: an opacity window [at, until]. Emits a text element when text+x+y given."""
    eid = ev["id"]
    at = float(ev["at"])
    until = float(need(ev, "until"))
    edge = float(ev.get("edge", cfg["hold"]))
    if until <= at:
        raise SpecError(f"event '{eid}': 'until' must be after 'at'")
    if until > loop:
        raise SpecError(f"event '{eid}' ends at {until:.2f}s, after the {loop}s loop")
    on_lo = ev.get("opacity", 1)
    parts = []
    if at > 0:
        parts.append(f"0%, {pct(max(0, at - edge), loop)}% {{ opacity: 0; }}")
        parts.append(f"{pct(at, loop)}%, {pct(until, loop)}% {{ opacity: {on_lo}; }}")
    else:
        parts.append(f"0%, {pct(until, loop)}% {{ opacity: {on_lo}; }}")
    if until + edge < loop:
        parts.append(f"{pct(until + edge, loop)}%, 100% {{ opacity: 0; }}")
    else:
        parts.append("100% { opacity: 0; }")
    css = [f"@keyframes {eid} {{ " + " ".join(parts) + " }"]

    els = []
    if "text" in ev and "x" in ev and "y" in ev:
        anchor = ev.get("anchor", "end" if kind == "phase" else "middle")
        color = ev.get("color", cfg["accent"])
        cls = ev.get("class", "t-tag")
        els.append(
            f'<text class="{cls} story" x="{fmt(float(ev["x"]))}" y="{fmt(float(ev["y"]))}" '
            f'text-anchor="{anchor}" fill="{color}" style="animation-name:{eid};opacity:0">{esc(ev["text"])}</text>'
        )
    return css, els, until


def compile_pulse(ev, cfg, loop):
    """A ring that fires at a point at time `at` with no packet."""
    eid = ev["id"]
    at = float(ev["at"])
    x, y = float(need(ev, "x")), float(need(ev, "y"))
    color = ev.get("color", cfg["accent"])
    dur = float(ev.get("dur", cfg["ring_dur"]))
    end = min(at + dur, loop)
    peak = at + dur * 0.08
    css = [
        f"@keyframes {eid} {{ 0%, {pct(at, loop)}% {{ transform: scale(0.4); opacity: 0; }} "
        f"{pct(peak, loop)}% {{ transform: scale(0.5); opacity: 0.8; }} "
        f"{pct(end, loop)}%, 100% {{ transform: scale(1.4); opacity: 0; }} }}"
    ]
    els = [
        f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{ev.get("ring_r", cfg["ring_r"])}" fill="none" '
        f'stroke="{color}" stroke-width="{cfg["stroke_width"]}" class="ring" style="animation-name:{eid}"/>'
    ]
    return css, els, end


def compile_bar(ev, cfg, loop):
    """A horizontal fill bar that steps its scaleX at given times: steps = [[t, fraction], ...]."""
    eid = ev["id"]
    steps = need(ev, "steps")
    edge = float(ev.get("edge", cfg["hold"]))
    if not steps or steps[0][0] != 0:
        raise SpecError(f"event '{eid}': steps must start with [0, fraction]")
    parts = []
    for i, (t, v) in enumerate(steps):
        nxt = steps[i + 1][0] if i + 1 < len(steps) else loop
        lo = pct(float(t), loop)
        hi = pct(max(float(t), float(nxt) - edge), loop)
        if i + 1 == len(steps):
            hi = pct(max(float(t), loop * 0.96), loop)
        parts.append(f"{lo}%, {hi}% {{ transform: scaleX({fmt(float(v))}); }}")
    parts.append(f"100% {{ transform: scaleX({fmt(float(steps[0][1]))}); }}")
    css = [f"@keyframes {eid} {{ " + " ".join(parts) + " }"]
    els = []
    if all(k in ev for k in ("x", "y", "w", "h")):
        color = ev.get("color", cfg["accent"])
        els.append(
            f'<rect x="{fmt(float(ev["x"]))}" y="{fmt(float(ev["y"]))}" width="{fmt(float(ev["w"]))}" '
            f'height="{fmt(float(ev["h"]))}" rx="{ev.get("rx", 2)}" fill="{color}" fill-opacity="0.6" '
            f'class="bar" style="animation-name:{eid}"/>'
        )
    return css, els, float(steps[-1][0])


def compile_move(ev, cfg, loop):
    """Translate a group (authored by hand with class="story") and hold it, then snap back."""
    eid = ev["id"]
    at = float(ev["at"])
    dur = float(ev.get("dur", 1.0))
    hold = float(ev.get("until", loop * 0.96))
    dx, dy = float(ev.get("dx", 0)), float(ev.get("dy", 0))
    if at + dur > hold:
        raise SpecError(f"event '{eid}': 'until' must be after at+dur")
    css = [
        f"@keyframes {eid} {{ 0%, {pct(at, loop)}% {{ transform: translate(0, 0); }} "
        f"{pct(at + dur, loop)}%, {pct(hold, loop)}% {{ {tr(dx, dy)} }} 100% {{ transform: translate(0, 0); }} }}"
    ]
    return css, [], hold


COMPILERS = {
    "packet": compile_packet,
    "stream": compile_stream,
    "pulse": compile_pulse,
    "bar": compile_bar,
    "move": compile_move,
}


# ----------------------------------------------------------------------------
# driver


def resolve_time(ev, ends, cfg):
    """Fill ev['at'] from 'after' / 'with' chaining if absent."""
    if "at" in ev:
        return
    if "after" in ev:
        ref = ev["after"]
        if ref not in ends or ends[ref] is None:
            raise SpecError(f"event '{ev['id']}': 'after' refers to unknown or unbounded event '{ref}'")
        ev["at"] = ends[ref] + float(ev.get("gap", cfg["gap"]))
        return
    if "with" in ev:
        ref = ev["with"]
        if ref not in ends:
            raise SpecError(f"event '{ev['id']}': 'with' refers to unknown event '{ref}'")
        ev["at"] = STARTS[ref]
        return
    if ev.get("kind") == "stream":
        return
    raise SpecError(f"event '{ev['id']}' needs 'at', 'after' or 'with'")


STARTS: dict[str, float] = {}


def compile_spec(spec: dict):
    cfg = {**DEFAULTS, **{k: v for k, v in spec.items() if k in DEFAULTS}}
    loop = float(cfg["loop"])
    events = spec.get("events", [])
    if not events:
        raise SpecError("spec has no events")

    css: list[str] = [
        f"/* generated by timeline.py — loop {fmt(loop)}s — edit the spec, not this block */",
        f".story, .pkt, .ring, .glow, .bar {{ animation-duration: {fmt(loop)}s; }}",
    ]
    els: list[str] = []
    table: list[tuple] = []
    ends: dict[str, float | None] = {}
    seen: set[str] = set()

    for ev in events:
        eid = ev.get("id")
        if not eid or not NAME_RE.match(eid):
            raise SpecError(f"every event needs an id matching {NAME_RE.pattern}; got {eid!r}")
        if eid in seen:
            raise SpecError(f"duplicate event id '{eid}'")
        seen.add(eid)
        kind = ev.get("kind", "packet")
        resolve_time(ev, ends, cfg)
        if "at" in ev:
            STARTS[eid] = float(ev["at"])
        if kind in ("phase", "show"):
            c, e, end = compile_window(ev, cfg, loop, kind)
        elif kind in COMPILERS:
            c, e, end = COMPILERS[kind](ev, cfg, loop)
        else:
            raise SpecError(f"event '{eid}': unknown kind '{kind}'")
        ends[eid] = end
        css.append(f"/* {eid}: {ev.get('note', kind)} */")
        css.extend(c)
        els.extend(e)
        table.append((eid, kind, ev.get("at"), end, ev.get("label") or ev.get("text") or ""))

    return css, els, table, loop


def render_table(table, loop):
    out = [f"loop {fmt(loop)}s", f"{'id':<10}{'kind':<8}{'start':>7}{'end':>7}  label"]
    for eid, kind, at, end, label in table:
        a = fmt(float(at)) if at is not None else "-"
        e = fmt(float(end)) if end is not None else "-"
        out.append(f"{eid:<10}{kind:<8}{a:>7}{e:>7}  {label}")
    return "\n".join(out)


def inject(svg_text: str, css: list[str], els: list[str]) -> str:
    def replace_between(text, open_m, close_m, body, indent):
        i = text.find(open_m)
        j = text.find(close_m)
        if i < 0 or j < 0 or j < i:
            raise SpecError(f"SVG is missing markers {open_m!r} … {close_m!r} (copy assets/template.svg)")
        return text[: i + len(open_m)] + "\n" + body + "\n" + indent + text[j:]

    css_body = "\n".join("    " + line.replace("\n", "\n    ") for line in css)
    el_body = "\n".join("  " + line for line in els)
    out = replace_between(svg_text, CSS_OPEN, CSS_CLOSE, css_body, "    ")
    out = replace_between(out, EL_OPEN, EL_CLOSE, el_body, "  ")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", type=Path, help="motion spec JSON")
    ap.add_argument("--inject", type=Path, metavar="SVG", help="rewrite the SVG between motion markers")
    ap.add_argument("--print", action="store_true", help="print generated css and elements")
    ap.add_argument("--table", action="store_true", help="print the schedule table")
    args = ap.parse_args()

    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
        css, els, table, loop = compile_spec(spec)
        if args.inject:
            svg = args.inject.read_text(encoding="utf-8")
            args.inject.write_text(inject(svg, css, els), encoding="utf-8")
            print(f"injected {len(css)} css lines, {len(els)} elements into {args.inject}")
        if args.print or not (args.inject or args.table):
            print("\n".join(css))
            print()
            print("\n".join(els))
        if args.table or args.inject:
            print(render_table(table, loop))
    except (SpecError, json.JSONDecodeError, OSError) as exc:
        print(f"timeline.py: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

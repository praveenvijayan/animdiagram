#!/usr/bin/env python3
"""animdiagram skin — convert a finished diagram between the dark and light skins.

    python3 skin.py diagram.svg --to light            # writes diagram-light.svg
    python3 skin.py diagram-light.svg --to dark       # writes diagram-dark.svg
    python3 skin.py diagram.svg --to light --out x.svg

Swaps every token hex (see references/style-guide.md), the badge rgba pair, the
skin comment in <style>, and lowers glow peak opacity on light paper so the
accent wash does not shout. Author once in dark, derive light — never maintain
two hand-edited copies.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DARK_TO_LIGHT = {
    "#0D0D0E": "#F5F5F5",   # paper
    "#141416": "#FFFFFF",   # panel
    "#202126": "#D9DADB",   # frame-rule / trunk links
    "#363840": "#BFC0C0",   # rule
    "#F4F6FC": "#2D3142",   # ink
    "#B6C0CF": "#3B4054",   # label (distinct from ink so the swap is reversible)
    "#6F7987": "#4F5D75",   # muted
    "#4CF490": "#EB6C36",   # signal
    "#02BEFA": "#2E5AA8",   # lane-cyan
    "#FBDC8E": "#B8915A",   # lane-amber
    "#FF9E9E": "#9C6B50",   # lane-rose
    "#A880FF": "#6E6479",   # lane-violet
    "#00CCB4": "#5E7A9B",   # lane-teal
    "#FF4C4C": "#C0392B",   # alarm
    "rgba(168,128,255,0.1)": "rgba(110,100,121,0.08)",
    "rgba(168,128,255,0.5)": "rgba(110,100,121,0.5)",
    "rgba(76,244,144,0.3)": "rgba(235,108,54,0.45)",
    "(dark skin)": "(light skin)",
}
GLOW_PEAK = {"light": "0.18", "dark": "0.3"}


def convert(text: str, to: str) -> str:
    table = DARK_TO_LIGHT if to == "light" else {v: k for k, v in DARK_TO_LIGHT.items()}
    # longest keys first so rgba() strings win over bare hexes they contain
    for src in sorted(table, key=len, reverse=True):
        text = re.sub(re.escape(src), table[src], text, flags=re.IGNORECASE)
    # glow peak opacity lives inside *-glow keyframes: "… { opacity: 0.3; }" between the 0% and end stops
    src_peak, dst_peak = GLOW_PEAK["dark" if to == "light" else "light"], GLOW_PEAK[to]
    text = re.sub(
        r"(@keyframes [\w-]+-glow \{[^}]*\}\s*[0-9.]+% \{ opacity: )" + re.escape(src_peak) + r"(;)",
        r"\g<1>" + dst_peak + r"\2",
        text,
    )
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("svg", type=Path)
    ap.add_argument("--to", choices=("light", "dark"), required=True)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    src = args.svg.read_text(encoding="utf-8")
    out = args.out
    if out is None:
        stem = re.sub(r"-(light|dark)$", "", args.svg.stem)
        out = args.svg.with_name(f"{stem}-{args.to}.svg")
    out.write_text(convert(src, args.to), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

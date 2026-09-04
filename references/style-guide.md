# Style guide — tokens, type, node treatments

Single source of truth for the skin. Reference roles by name; the hex lives here.

## Dark skin (default)

| Role | Hex | Use |
|---|---|---|
| `paper` | `#0D0D0E` | Frame fill, inner tile fill |
| `panel` | `#141416` | Node fill, panel fill |
| `frame-rule` | `#202126` | Frame stroke, faint trunk lines |
| `rule` | `#363840` | Node stroke, connectors, chevrons, dashed cluster boundary |
| `ink` | `#F4F6FC` | Title |
| `label` | `#B6C0CF` | Node names |
| `muted` | `#6F7987` | Sublabels, prose, legend, zone labels, idle client dots |
| `signal` | `#4CF490` | **The accent.** Story packets, arrival rings, glows, tick dots, legend dot |
| `lane-cyan` | `#02BEFA` | Second lane: replication, WAL, streams |
| `lane-amber` | `#FBDC8E` | Third lane: locks held, waiting, RFO, "partial" stickers |
| `lane-rose` | `#FF9E9E` | Failure / stall / "does not scale" sticker |
| `lane-violet` | `#A880FF` | Date / status badge only (`PLANNED`, `OCT 2026`) |
| `lane-teal` | `#00CCB4` | Reads, persist round (only if cyan is already taken) |
| `alarm` | `#FF4C4C` | Invalidation ring, X mark — rare |

Rule: `signal` + at most two lanes on moving elements, each lane with a legend entry. Stickers and badges don't count as lanes but keep to one per diagram.

## Light skin (opt-in)

Maps to the diagram-design default palette so animated and static figures in one post share a family. Don't author in light: finish the dark file, then `python3 scripts/skin.py diagram.svg --to light`. The script swaps every token below, the badge rgba pair, and drops glow peak opacity to 0.18. `assets/template-light.svg` and `assets/example-async-jobs-light.svg` are both derived this way.

| Role | Hex |
|---|---|
| `paper` | `#F5F5F5` |
| `panel` | `#FFFFFF` |
| `frame-rule` | `rgba(45,49,66,0.12)` |
| `rule` | `#BFC0C0` |
| `ink` | `#2D3142` |
| `label` | `#2D3142` |
| `muted` | `#4F5D75` |
| `signal` | `#EB6C36` (atomic tangerine) |
| `lane-cyan` | `#2E5AA8` |
| `lane-amber` | `#B8915A` |
| `lane-rose` | `#9C6B50` |
| `lane-violet` | `#6E6479` |

Extra rows the script also maps: `frame-rule` → `#D9DADB`, `lane-teal` → `#5E7A9B`, `alarm` → `#C0392B`. Glow opacity on light paper: 0.18 instead of 0.3.

## Type ramp

Standalone SVGs cannot load web fonts, so stacks are system-safe. Mono for everything structural (title, names, tags, legend); sans only for prose (subtitle, sublabel descriptions, captions).

| Class | Family | Size | Weight / tracking | Fill | Use |
|---|---|---|---|---|---|
| `.t-title` | mono | 17 | 700 · 2px | `ink` | Title, CAPS, ≤ 24 chars |
| `.t-sub` | sans | 13 | 400 | `muted` | One-sentence claim under the title |
| `.t-zone` | mono | 9 | 400 · 1.5px | `muted` | Cluster / zone label, CAPS |
| `.t-name` | mono | 9 | 400 · 1px | `label` | Node name, CAPS; legend text |
| `.t-small` | mono | 8 | 400 · 1px | `muted` | Tile labels, connector labels, client labels, CAPS |
| `.t-desc` | sans | 8.5 | 400 | `muted` | Node sublabel: `compute + storage · one writer` |
| `.t-tag` | mono | 7.5 | 600 · 1px | per element | Packet labels, phase captions, stall counters |
| `.t-prose` | sans | 10 | 400 | `muted` | Caption line(s) under the diagram |
| `.t-badge` | mono | 8.5 | 600 · 1px | `lane-violet` | Pill badge text |

Stacks: mono `'Source Code Pro', ui-monospace, Menlo, Consolas, monospace`; sans `Inter, -apple-system, 'Segoe UI', sans-serif`. Both are declared once in `<style>`; never inline `font-family` per element.

Sizes off this ramp (11, 15…) trigger a `check.py` warning. Coordinates still obey the 4px grid; font sizes are exempt because 9px mono caps is the register this style is built on.

## Node treatments

| Kind | Fill | Stroke | Extra |
|---|---|---|---|
| Service / node | `panel` | `rule` | tick dot + name + sublabel |
| Inner tile (DB inside a node, cache line, page slot) | `paper` | `rule` | `.t-small` label, tick dot |
| Passive sink (metrics, object storage) | `paper` | `rule` | no tick |
| Cluster boundary | none | `rule` dashed `4 4` | `.t-zone` label top-left |
| Panel (side-by-side comparison) | `panel` | `rule` | `rx=10`, `.t-name` 600 label |
| Client / reader / writer | circle r=4 `muted` | — | `.t-small` label below |
| Waiting slot | none | `rule` dashed `2 2` | packet parks inside |
| Highlighted-border node | `paper` | `signal @ 0.3` | "owns the line" |

Radius: nodes `rx=7`, tiles `rx=6`, panels `rx=10`, frame `rx=12`, badge pill `rx=9`, bar segments `rx=3`.

## Chrome

- **Frame**: `<rect x="0.5" y="0.5" width="W-1" height="H-1" rx="12" fill=paper stroke=frame-rule/>`. The 0.5 offset keeps the 1px stroke crisp; it's the only off-grid coordinate allowed.
- **Title** at `(28, 42)`, **subtitle** at `(28, 66)`. Content starts at `y ≥ 88`.
- **Badge** (optional, one): pill at `x=568 y=30 w=68 h=18`, fill `rgba(168,128,255,0.1)`, stroke `rgba(168,128,255,0.5)`, text centred at `(602, 42)`.
- **Sticker** (optional, one): rotated `-8°…-10°` group, amber `rgba(251,220,142,0.92)` or rose `rgba(255,158,158,0.92)` fill, `.t-tag`-style 10.5–14px 700 text in `paper` colour. Use for verdicts like `DOES NOT SCALE`, `TIMING TO SCALE!`.
- **Caption**: `.t-prose` centred at `x=330`, 24–28 px above the legend.
- **Legend**: bottom strip, `y = H-24` for the dots, text `+4`. One entry per moving colour, ≤ 3 entries, 160–220 px apart.

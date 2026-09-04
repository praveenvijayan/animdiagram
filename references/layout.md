# Layout grammar — grid, connectors, nodes, zones

## Canvas

- Width **660** (Substack / blog body). Height 280–500, multiple of 4. Wide variant 960 only when the user asks; scale gaps, not type.
- Outer margin 28 px (frame to first node). Title block occupies `y < 88`.
- Vertical rhythm: node rows 56 px tall (tiles 30 px), row gap 48 px (`120 → 176`, `224 → 280`).
- **4px grid**: every `x y width height` on nodes, tiles, connectors and text anchors is a multiple of 4. Exceptions: the 0.5 frame offset, tick-dot centres (`x+14, y+17`), chevron points, packet radii.

## Nodes

```svg
<rect x="X" y="Y" width="112" height="56" rx="7" fill="#141416" stroke="#363840"/>
<circle cx="X+14" cy="Y+17" r="2.5" fill="#4CF490" class="tick" style="animation-delay:-0.7s"/>
<text class="t-name" x="X+24" y="Y+20">NAME</text>
<text class="t-desc" x="X+12" y="Y+40">two words · detail</text>
```

- Widths from `{80, 96, 112, 128, 140, 170, 184}`; same width for peers in a row.
- Tick dots: stagger `animation-delay` by `-0.35 s` steps so the cluster breathes rather than blinks in unison. Passive sinks get no tick.
- **Tile grid** inside a node (many DBs on one node, page slots): tiles `76×30` or `72×56`, 8 px apart, `.t-small` labels. Tiles are not nodes for the budget, but ≤ 4 per node unless the point *is* "many".
- **Client rows**: `circle r=4 fill=muted` + `.t-small` label; stack 20–26 px apart with a `.t-small` header (`WRITERS`, `READERS`).

## Connectors

Same six rules as diagram-design §6, restated for motion:

1. **Orthogonal only.** `<line>` when endpoints share x or y; otherwise an elbow path with `r=8` quarter-arcs:
   `M x1,y1 H mid-8 Q mid,y1 mid,y1+8 V y2-8 Q mid,y2 mid+8,y2 H x2`. Packets travel corner to corner via `via` waypoints at the bend centres; the 8 px arc is invisible at packet speed.
2. **Label off the stroke**: 6–10 px clear, `.t-small` CAPS, on the open side of the segment. No mask rect is needed on `paper`-coloured ground because connectors are drawn first — place the label beside the line, never across it.
3. **No overlapping connectors.** Request and reply get separate lines 24–40 px apart, or one line with packets in both directions only when they never coincide in time.
4. **Fan attach points** ≥ 12 px apart on a shared edge: for N connectors on an edge of length L, attach at `L·k/(N+1)`, rounded to the grid.
5. **No transit behind a non-endpoint node.** Route around; if geometrically forced, dash the segment `4 3`.
6. **Direction is visible in the static frame.** Put a 6×6 chevron polygon at the destination end of every story connector: `points="x-6,y-3 x,y x-6,y+3"` (pointing right; rotate coordinates for other directions). Ambient stream links may skip chevrons; dash them `3 3` instead.

Trunk / mesh links between many nodes (as in SpacetimeDB's async-IDC figure) use `frame-rule` colour so the story packets read against them.

## Zones and panels

- **Cluster boundary**: `rect rx=12 fill=none stroke=rule stroke-dasharray="4 4"`, `.t-zone` label at `(x+16, y+22)`, first node ≥ 32 px below the label baseline.
- **Comparison panels**: two `288`-wide panels at `x=32` and `x=340`, `rx=10`, `.t-name`-weight-600 titles at `y+24`. Each panel runs its own local story; keep both loops the same length or make the right one an ambient stream (fast, repeating) against the left one's slow story — that contrast *is* the argument.
- **Storage hierarchy / pyramid**: stacked full-width bars 40–48 px tall, latency annotations right-aligned `.t-small` at `x=540`.

## Phase caption slot

One text slot for act labels, right-aligned at `(632, 96)`, `.t-tag`, `story` class, one element per act stacked at the same coordinates with opacity windows. Numbering `1 · VERB PHRASE`. Colour follows the act's mood: `signal` for healthy, `lane-amber` for waiting, `lane-rose` for failure.

## Legend

Bottom strip, dots at `y = H-24`, texts at `y = H-20`. Match dot radius to the packet radius it explains (4 for story, 3 for streams, 2.5 for ticks). Never inside the diagram area.

## Anti-patterns (automatic fail)

| Anti-pattern | Why |
|---|---|
| Diagonal connectors | Packets slide off-axis; reads as a doodle |
| Coloured node fills | Nodes are neutral; colour belongs to motion and legend |
| Two packets sharing a stroke at the same time | Reader can't tell which is which |
| Packet label duplicating a static connector label | Double text at arrival (`WRITE` on top of `WRITE`) |
| Title longer than 24 chars or sentence-case | The mono caps title is the format's signature |
| Sans for node names | Mono caps names are the register; sans is for prose only |
| Legend inside the frame body | Collides with nodes |
| More than one badge or sticker | Chrome competes with the story |
| Missing chevrons | Static frame loses direction |
| Loop with no rest | Reader can't find the start |

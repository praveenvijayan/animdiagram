---
name: animdiagram
description: Create looping, self-contained animated SVG explainer diagrams (SpacetimeDB "how does it scale" style) — dark frame, monospace labels, packets travelling along orthogonal connectors with arrival rings and glows, phase labels, ambient streams, growing bars — for blog posts, Substack, READMEs and docs. Use when the user asks for an animated / looping / moving diagram, a "packets flowing" explainer, a message-sequence animation, or an SVG that plays in an <img> tag with no JavaScript. Pairs the diagram-design editorial discipline (density budget, one accent, 4px grid, orthogonal connectors) with a CSS-keyframe motion grammar and three scripts: timeline.py (spec → keyframes), check.py (verifier), preview.py (scrubber).
license: MIT
metadata:
  version: "1.0"
---

# animdiagram

Looping animated SVG explainers. One file, one `<style>` block, all motion as CSS `@keyframes`. Works in `<img>`, Markdown, Substack, GitHub. No script, no SMIL, no fonts to load, no build step.

The design discipline comes from **diagram-design** (deletion first, one accent, complexity budget, 4px grid, orthogonal connectors, static frame must read on its own). The motion grammar is distilled from the animated figures in SpacetimeDB's ["How does Spacetime scale"](https://spacetimedb.com/blog) series: packets on a shared story clock, arrival rings, destination glows, idle ticks, ambient streams, phase captions, growing bars, state swaps.

References load on demand:

| Need | File |
|---|---|
| Tokens, type ramp, node treatments, badges, light skin | [references/style-guide.md](references/style-guide.md) |
| Grid, connectors, nodes, zones, tiles, legend, anti-patterns | [references/layout.md](references/layout.md) |
| Motion primitives, timing math, budgets, reduced motion | [references/motion-grammar.md](references/motion-grammar.md) |
| Brief + event list → `spec.json` format for `timeline.py` | [references/storyboard.md](references/storyboard.md) |
| Pre-ship taste gate | [references/checklist.md](references/checklist.md) |

Assets: `assets/template.svg` (dark), `assets/template-light.svg`, worked example `assets/example-async-jobs.svg` + `.spec.json`.

---

## 1. When to use — and when not

Use when motion carries the meaning: **order** (A before B), **propagation** (one write fans out), **waiting** (a packet parks until an ack), **contention** (two things want one slot), **accumulation** (a log grows), **failure and recovery** (a node dims, a role moves).

Don't use for: a static architecture map (use diagram-design), a list of components, a chart, anything where the reader would learn the same from a paragraph. If the story has no "then", it doesn't loop.

**Explicit request only.** Never animate unprompted. Never route here from a generic "draw a diagram" ask.

---

## 2. Philosophy

- **The static frame is the diagram.** Hide every packet and the picture must still be complete: boxes, connectors with direction chevrons, labels, legend. Motion explains; it never supplies missing meaning. Reduced-motion readers and screenshot readers get exactly this frame.
- **One story per loop.** A loop tells one sequence of ≤8 events, then rests, then repeats. If you need two stories, make two diagrams (or two side-by-side comparison panels, as in the SpacetimeDB data-placement figure).
- **One signal colour.** Story packets are the accent (`signal` green by default). Up to two more hues are allowed only as *lanes* with a legend entry (ack vs request, replication vs client traffic). Never colour nodes.
- **Deletion first.** Every node, connector, packet and caption earns its place. Target density 4/10. Above 9 nodes it's two diagrams.
- **Time is honest.** Events on the shared clock sit in story order with visible gaps. Do not overlap two story packets unless simultaneity *is* the point.

---

## 3. Workflow

1. **Brief** (three lines, confirm with the user unless already pinned):
   - Title in caps (≤ 24 chars) and one-sentence subtitle = the claim.
   - Cast: nodes, ≤ 9, each with a 1–2 word name and optional 2-word sublabel.
   - Story: ordered event list `id · kind · from → to · what it means`, ≤ 8 story events, plus any ambient streams / phases / bars. Say the loop length (6–12 s).
   State the plan in one message; if the user is reachable, let them redirect. Skip only when the request already pins layout and events.
2. **Load references**: `layout.md` + `motion-grammar.md` always; `storyboard.md` for the spec; `style-guide.md` if the skin, badge, or light variant matters.
3. **Static SVG first.** Copy `assets/template.svg`, set `width`/`height`/`viewBox` (660 wide; height a multiple of 4), write the frame, title, subtitle, connectors, chevrons, nodes, static labels, caption, legend. Keep the two motion markers. Open it in a browser: it must read complete with no packets.
4. **Spec the motion.** Write `<slug>.spec.json` next to the SVG using coordinates from step 3 (packet `from`/`to`/`via` are connector endpoints; `glow` is the destination rect). Chain with `after` so timing stays relative.
5. **Compile**: `python3 scripts/timeline.py <slug>.spec.json --inject <slug>.svg`. The schedule table prints; sanity-check start/end times.
6. **Verify**: `python3 scripts/check.py <slug>.svg` — fix every ERROR, justify every warn.
7. **Tune by eye**: `python3 scripts/preview.py <slug>.svg --open`; scrub to each arrival, check rings land on box edges, labels don't collide, the rest gap reads as "idle", light-bg toggle if the post may be light. Adjust the spec, re-inject (idempotent), re-check.
8. **Ship** the `.svg` (optionally the `.spec.json` beside it for edits). Report the schedule table and any budget cuts.

Output path: `diagrams/<kebab-slug>.svg` in the current project, or the scratchpad when there is no project.

---

## 4. File contract (what every output looks like)

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="660" height="H" viewBox="0 0 660 H" fill="none"
     role="img" aria-label="One or two sentences: what happens over one loop, in story order">
  <style>
    text { font-family: 'Source Code Pro', ui-monospace, Menlo, Consolas, monospace; }
    .t-title … .t-badge          /* type ramp, see style-guide.md */
    .pkt .story .ring .glow .bar .tick   /* motion base classes */
    /* @motion:css */  …generated…  /* @/motion:css */
    @media (prefers-reduced-motion: reduce) { …hide decorative, show static… }
  </style>
  <rect frame/>  <text title/>  <text subtitle/>  [badge]
  <g stroke="#363840"> connectors </g>   <g fill="#363840"> chevrons </g>
  nodes (rect + tick dot + name + sublabel)
  static labels, captions, hand-authored .story groups
  <!-- @motion:elements -->  …generated packets / rings / glows / phase texts…  <!-- @/motion:elements -->
  legend strip
</svg>
```

Hard rules: exactly one `<style>`; no `<script>`, SMIL, `<foreignObject>`, `<image>`, `@import`, `url()`; no `<defs>` / id soup (markers are inline polygons); everything inside the loop budget in `motion-grammar.md`; `check.py` passes with zero errors.

---

## 5. Budgets (per diagram)

| Limit | Value |
|---|---|
| Nodes | ≤ 9 (tile grids inside a node don't count) |
| Connectors | ≤ 12, all orthogonal |
| Story events on the shared clock | ≤ 8 packets (+ their rings/glows) |
| Ambient streams | ≤ 3 |
| Phase / state captions | ≤ 6 visible texts, ≤ 1 caption slot |
| Accent colours on moving things | signal + ≤ 2 lanes |
| Loop | 6–12 s (28 s only for to-scale timing demos, say so in the subtitle) |
| Rest gap at loop end | ≥ 10 % of the loop |
| Canvas | 660 wide; height 280–500, multiple of 4 |

Over budget → split into two diagrams or two panels. Never shrink the type to fit.

---

## 6. Relationship to diagram-design

Same taste, different contract. diagram-design's `animation.md` forbids indefinite loops, glow, and dark-glow palettes because its outputs are static editorial figures with optional one-shot reveals. This skill *is* the looping explainer, so those rules are replaced by `motion-grammar.md`. Everything else carries over: §1 philosophy, §6 connector rules (orthogonal, fanned attach points ≥ 12 px, no overlaps, labels 6–10 px off the stroke), §7 grid, §9 taste gate. When a request needs a static figure, hand it to diagram-design.

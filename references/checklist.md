# Pre-ship checklist (taste gate)

Run before handing over any `.svg`.

**Story**
- [ ] The animation demonstrates one claim, stated in the subtitle, and the loop shows it once then rests.
- [ ] ≤ 8 story packets, in DOM order = story order, each with a one-line `note`.
- [ ] Every ring has an arrival; every glow has a packet; no motion is decorative.
- [ ] Phase captions (if any) name acts, ≤ 5, numbered, in one slot.
- [ ] Rest gap ≥ 10 % of the loop; loop 6–12 s.

**Static frame**
- [ ] With `.pkt/.ring/.glow` hidden the diagram is complete: nodes, connectors, chevrons, labels, legend, caption.
- [ ] `aria-label` narrates the loop in one or two sentences of prose.
- [ ] Title CAPS ≤ 24 chars; subtitle one sentence; ≤ 1 badge, ≤ 1 sticker.

**Deletion**
- [ ] Can any node go? Any connector? Any packet? Any caption? (If yes, remove it.)
- [ ] ≤ 9 nodes, ≤ 12 connectors; tile grids ≤ 4 tiles unless "many" is the point.

**Colour**
- [ ] `signal` on story packets only; ≤ 2 lanes; every moving colour in the legend; nodes neutral.

**Geometry**
- [ ] All connectors orthogonal; elbows `r=8`; attach points fanned ≥ 12 px; no overlaps; no transit behind a non-endpoint node.
- [ ] Labels 6–10 px clear of strokes; no packet label duplicating a static label.
- [ ] Node coordinates on the 4px grid; canvas 660 × (multiple of 4).

**Technical**
- [ ] `python3 scripts/check.py file.svg` → zero errors; each warning justified in the handover note.
- [ ] One `<style>`, no script/SMIL/defs/external refs; reduced-motion block present.
- [ ] Opened in `preview.py`: scrubbed to every arrival; rings sit on ports; glows on the right node; light-bg check if the post might be light.
- [ ] Renders in an `<img>` tag (drag the file into a browser tab — not the preview page).

**Handover**
- [ ] Path, schedule table, and CUTS list reported. Spec file saved beside the SVG.

# Motion grammar — primitives, timing, budgets

All motion is CSS `@keyframes` on a **shared story clock**: one duration `L` (6–12 s), `linear`, `infinite`. Every story event is pinned to percentages of that clock. Elements hold their end state to `100%` so nothing reappears before the loop restarts. `timeline.py` generates all of this from a spec; this file explains what it generates so you can author, read, and hand-tune it.

## Base classes (in every file)

```css
.pkt   { animation-timing-function: linear; animation-iteration-count: infinite; }
.story { animation-timing-function: linear; animation-iteration-count: infinite; }
.ring  { transform-box: fill-box; transform-origin: center; opacity: 0; …same… }
.glow  { opacity: 0; …same… }
.bar   { transform-box: fill-box; transform-origin: left; …same… }
.tick  { animation: tick 2.6s ease-in-out infinite; }
@keyframes tick { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
/* generated: */ .story, .pkt, .ring, .glow, .bar { animation-duration: Ls; }
```

`transform-box: fill-box` makes `scale()` work on SVG shapes around their own centre. Streams override `animation-duration` inline with their own short period.

## Primitives

| Primitive | Spec `kind` | What the reader sees | Keyframe shape |
|---|---|---|---|
| **Packet** | `packet` | Dot spawns at source, travels along the connector at constant speed, fades just after arrival | `0%,s%{t(0) o0} s+ε%{o1} …waypoints… a%{t(end) o1} a+f%,100%{t(end) o0}` |
| **Arrival ring** | on packet (`ring: true`, default) | Thin circle bursts outward at the destination the instant the packet lands | `0%,a%{scale(.4) o0} a+.04s%{scale(.5) o.8} a+.5s%,100%{scale(1.4) o0}` |
| **Destination glow** | on packet (`glow: {x,y,w,h}`) | Node fills with 30 % accent for ~0.4 s | `0%,a%{o0} a+.08s%{o.3} a+.4s%,100%{o0}` |
| **Labelled packet** | `packet` + `label` | Dot with a `.t-tag` word riding 12 px above it (`CALL`, `PREPARED`, `202`) | same as packet, on a `<g>` |
| **Ambient stream** | `stream` | 2–4 dots evenly spaced on a short independent loop (0.7–1.5 s) — "this never stops" | own duration; `0%{o0} 12%{o1} 88%{t(end) o1} 100%{o0}`; tokens use negative `animation-delay` `-k·period/count` |
| **Pulse** | `pulse` | Ring with no packet: an event happened here at time t | ring shape at `t` |
| **Phase caption** | `phase` | Act label `1 · VERB` visible during its window at the caption slot | `0%,s-δ%{o0} s%,e%{o1} e+δ%,100%{o0}` |
| **State swap** | `show` (×2) | A text/mark appears (`I` for Invalid, `?` → `@3`), another disappears | same window shape; pair one `show` per state |
| **Growing bar** | `bar` | Log / dataset grows in steps and resets at loop end | `scaleX` holds: `t1%,t2-δ%{scaleX(v1)} …` |
| **Move / rebalance** | `move` | Whole group slides to a new home and holds, snaps back at loop end | `0%,s%{t(0)} s+d%,h%{t(dx,dy)} 100%{t(0)}` |
| **Idle tick** | `.tick` class | Status dot breathes 1 → 0.3 → 1 every 2.6 s | global |
| **Lock / colour state** | hand-authored | Lock glyph turns amber while held | `@keyframes lockA { 0%,8%{fill:rule} 9%,37%{fill:amber} 38%,100%{fill:rule} }` |
| **Failure** | hand-authored `show` + dim | Node drops to 0.65 opacity with an X mark; role label swaps `PRIMARY`↔`BACKUP` | window shapes |
| **Bounce** | hand-authored | 0.2 s vertical bounce = one unit of work, gated by a `show` window on the parent `<g>` | `0%{t(0)} 50%{t(0,24px)} 100%{t(0)}` |

Waiting is a packet whose `via` list ends where it parks, with a long hold before the next event: give it `travel` for the trip and let the next event's `after` gap express the wait. For a parked packet that later resumes, author two packets (arrive-and-park, depart) or hand-edit the keyframes with a hold stop.

## Timing math

Given loop `L`, event start `s`, travel `d`, waypoints `P0…Pn`:

- Percent of a time `t` is `100·t/L`, written to 2 decimals.
- Arrival at `Pi` is `s + d · (path length to Pi) / (total path length)` — constant speed, so a long corridor takes proportionally longer than a short hop.
- Spawn fade-in `ε = 0.06 s`; post-arrival fade `f = 0.12 s`; ring life 0.5 s; glow life 0.4 s.
- Ring fires **at** arrival, glow peaks 0.08 s after: the eye reads ring-then-fill as "landed".
- Chaining: `after: X` starts 0.3 s (`gap`) after X arrives. Reply packets chain off the request; acks chain off the write.
- Two things must never share the same `%` stop inside one keyframe block; `timeline.py` guarantees this per event, you guarantee it across hand-authored blocks.

## Composition rules

1. **Story order = DOM order.** Emit packets in narrative order so a reader of the source can follow the plot.
2. **Rest gap.** Leave ≥ 10 % of the loop with nothing but ticks and streams at the end. The reader needs to see "quiet" to recognise the restart.
3. **One thing at a time** on the story clock unless simultaneity is the message (quorum fan-out, both replicas acked). Simultaneous packets get the same `at` via `with`.
4. **Streams contrast the story.** Fast ambient streams beside a slow choreographed story make the slow one feel expensive (SpacetimeDB's data-placement figure: local commits hum while the cross-node transaction crawls).
5. **Speed is semantic.** Travel 0.4–0.6 s for LAN hops, 0.8–1.2 s for cross-node / WAN, 1.5 s+ only when latency is the point. Don't vary speed for decoration.
6. **Glow the destination, ring the port.** Ring at the exact point the packet reaches (box edge or tile centre); glow the whole node or tile.
7. **Captions narrate acts, not packets.** ≤ 5 phase captions; each spans several events.
8. **No easing on travel.** Linear. Eased packets look like UI, not data.

## Reduced motion / static contract

```css
@media (prefers-reduced-motion: reduce) {
  .pkt, .ring, .glow { animation: none !important; visibility: hidden; }
  .story { animation: none !important; }
  text.story { visibility: hidden; }      /* stacked captions would overprint */
  .bar   { animation: none !important; transform: scaleX(1); }
  .tick  { animation: none !important; }
}
```

- Decorative packets, rings, glows vanish. Static labels, connectors, chevrons, legend remain: the complete diagram.
- Phase captions share one slot, so the reduced frame hides them and the subtitle carries the claim. Hand-authored `<g class="story">` groups (movers, gated bounces) freeze at their initial inline state — give them the *resting* state inline (`opacity:0` for things that appear later, no transform for movers).
- Bars show full; role swaps show the initial role (`.rolein { opacity: 0 !important }`).
- The `aria-label` narrates the whole loop in prose so non-visual readers get the story, not the geometry.
- The "static frame" button in `preview.py` seeks to the last millisecond of the loop, which is the same picture.

## Budgets

| Limit | Value | Why |
|---|---|---|
| Story packets per loop | ≤ 8 | Beyond that the eye can't hold the order |
| Simultaneous story packets | ≤ 2 (3 for quorum) | |
| Ambient streams | ≤ 3, ≤ 4 tokens each | |
| Rings + glows | one each per arrival | Never ring without an arrival |
| Phase captions | ≤ 5 | |
| Moving colours | signal + ≤ 2 lanes | |
| Loop length | 6–12 s | 28 s only for to-scale timing, declared in the subtitle |
| Rest gap | ≥ 10 % | |
| Flash rate | nothing changes luminance > 3×/s | ticks at 2.6 s, streams ≥ 0.7 s |

## Hand-tuning after generation

The generated block is regenerated on every `--inject`; put permanent tweaks in the spec (`travel`, `gap`, `at`, `edge`, `label_dy`). Hand-authored keyframes (locks, bounces, role swaps) live **outside** the markers, above the reduced-motion block, and reference the same clock by using `class="story"`.

# Storyboard — from brief to `spec.json`

## 1. Brief (write this before any SVG)

```
TITLE:     ASYNC JOB PIPELINE                    (caps, ≤ 24 chars)
CLAIM:     Accept fast, process later; the client never waits on the database
LOOP:      8 s
CAST:      client · API · QUEUE · WORKER · DATABASE · METRICS   (6 ≤ 9)
STORY:
  m1  packet  client → API        job submitted
  m2  packet  API → QUEUE         enqueued (glow queue)
  m3  packet  API → client        202 accepted, via top corridor, label "202"
  m4  packet  QUEUE → WORKER      worker pulls
  m5  packet  WORKER → DATABASE   write (glow db)
  m6  packet  DATABASE → WORKER   ack
ACTS:      1 · ACCEPT (0–2.9) · 2 · PROCESS (3–5.9) · 3 · DURABLE (6–7.8)
AMBIENT:   s1 stream WORKER → METRICS, cyan, period 1.2 s
LEGEND:    green = job messages · cyan = metrics stream
CUTS:      retry path, dead-letter queue (would be a second diagram)
```

Show this to the user unless everything is already pinned. It is also the fidelity ledger: what you left out goes under CUTS.

## 2. Coordinates come from the static SVG

Draw the static file first (see `layout.md`). Then read connector endpoints off it: a packet's `from` is where the connector leaves the source, `to` is where the chevron sits on the destination edge, `via` lists the elbow corners in order. A glow is the destination node's rect.

## 3. Spec format

```json
{
  "loop": 8,                 // seconds; one shared clock
  "accent": "#4CF490",       // default packet colour (signal)
  "r": 4, "ring_r": 10,      // optional global overrides (see DEFAULTS in timeline.py)
  "events": [ … ]            // in story order
}
```

Common event fields: `id` (CSS identifier, unique), `kind`, `note` (goes into a CSS comment), timing via exactly one of `at` (seconds), `after: "<id>"` (+ optional `gap`), or `with: "<id>"`.

### `packet`
```json
{ "id": "m3", "kind": "packet", "after": "m2", "gap": 0.1, "travel": 1.2,
  "from": [152,120], "via": [[152,96],[40,96]], "to": [40,140],
  "label": "202", "label_dy": -12,
  "color": "#4CF490", "r": 4,
  "ring": true, "ring_r": 10,
  "glow": { "x": 96, "y": 120, "w": 112, "h": 56, "rx": 7 } }
```
`ring` defaults to true; set false for trivial hops. `glow` is optional. Omit `label` when the connector already has a static label.

### `stream`
```json
{ "id": "s1", "kind": "stream", "from": [512,148], "to": [552,148], "via": [],
  "period": 1.2, "count": 3, "color": "#02BEFA", "r": 2.5, "ring": false, "phase": 0 }
```
Independent of the story clock. `phase` shifts all tokens by seconds (negative delay).

### `phase` and `show`
```json
{ "id": "ph1", "kind": "phase", "at": 0, "until": 2.9,
  "text": "1 · ACCEPT", "x": 632, "y": 96, "anchor": "end", "color": "#4CF490", "class": "t-tag" }
{ "id": "inv", "kind": "show", "at": 4.1, "until": 6.5 }     // keyframes only; author the element by hand:
```
Hand element for a keyframes-only window: `<text class="t-tag story" style="animation-name:inv;opacity:0" …>I</text>` or a `<g class="story" style="animation-name:inv;opacity:0">`.

### `pulse`
```json
{ "id": "p1", "kind": "pulse", "at": 2.0, "x": 300, "y": 176, "color": "#00CCB4", "dur": 0.5 }
```

### `bar`
```json
{ "id": "b1", "kind": "bar", "steps": [[0,0.15],[1.0,0.4],[3.5,0.65],[6.0,0.9]],
  "x": 60, "y": 300, "w": 200, "h": 6, "color": "#4CF490" }
```
Steps are `[seconds, fraction 0–1]`; the first must be at 0. Omit `x/y/w/h` to author the `<rect class="bar">` yourself.

### `move`
```json
{ "id": "mvP3", "kind": "move", "at": 6.0, "dur": 1.5, "until": 11.5, "dx": 312, "dy": -60 }
```
Keyframes only; wrap the moving group: `<g class="story" style="animation-name:mvP3">…</g>`.

## 4. Compile, inject, check, tune

```bash
python3 scripts/timeline.py diagrams/slug.spec.json --table            # read the schedule
python3 scripts/timeline.py diagrams/slug.spec.json --inject diagrams/slug.svg
python3 scripts/check.py diagrams/slug.svg
python3 scripts/preview.py diagrams/slug.svg --open
```

`--inject` replaces everything between `/* @motion:css */ … /* @/motion:css */` and `<!-- @motion:elements --> … <!-- @/motion:elements -->`; it is safe to run repeatedly. Hand-authored motion (locks, role swaps, bounces) lives outside the markers and survives.

## 5. Reading the schedule table

```
loop 8s
id        kind      start    end  label
m1        packet      0.2    0.7
m2        packet        1    1.4
m3        packet      1.5    2.7  202
ph1       phase         0    2.9  1 · ACCEPT
…
```

Check: events ascend, no two story packets overlap unless intended, last `end` ≤ 0.9 × loop, each act's caption spans its events.

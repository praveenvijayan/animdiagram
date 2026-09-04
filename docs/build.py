#!/usr/bin/env python3
"""Build docs/index.html from gallery.json + diagrams/*.spec.json. No dependencies."""
from __future__ import annotations
import html, json, sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "scripts"))
from timeline import compile_spec  # noqa: E402

def esc(s): return html.escape(str(s), quote=True)

def schedule(spec: dict):
    """Return [(id, kind, start, end, label)] using the compiler's own resolution."""
    _, _, table, _ = compile_spec(json.loads(json.dumps(spec)))
    notes = {e["id"]: e.get("note", "") for e in spec["events"]}
    rows = []
    for eid, kind, start, end, label in table:
        f = lambda v: "" if v is None else f"{float(v):g}"
        rows.append({"id": eid, "kind": kind, "start": f(start), "end": f(end),
                     "label": label, "note": notes.get(eid, "")})
    return rows

def build():
    g = json.loads((HERE / "gallery.json").read_text())
    site = g["site"]
    entries = g["entries"]
    chips, sections = [], []
    for i, e in enumerate(entries, 1):
        spec = json.loads((HERE / "diagrams" / f"{e['slug']}.spec.json").read_text())
        rows = schedule(spec)
        trs = "".join(
            f"<tr><td>{esc(r['id'])}</td><td>{esc(r['kind'])}</td>"
            f"<td class=num>{esc(r['start'])}</td>"
            f"<td class=num>{esc(r['end'])}</td>"
            f"<td>{esc(r.get('label') or r.get('note') or '')}</td></tr>"
            for r in rows)
        prim = "".join(f"<li>{esc(p)}</li>" for p in e["primitives"])
        n = f"{i:02d}"
        chips.append(f'<a class="chip" href="#{e["slug"]}"><span class="n">{n}</span>{esc(e["title"])}</a>')
        sections.append(f'''
<section class="entry" id="{e["slug"]}"{"" if i == 1 else " hidden"}>
  <div class="entry-head">
    <div class="eyebrow"><span class="n">{n}</span>{esc(e["category"])}<span class="sep">·</span><span class="src">{esc(e["source"])}</span></div>
    <h2>{esc(e["title"])}</h2>
    <p class="claim">{esc(e["claim"])}</p>
  </div>
  <div class="entry-body">
    <figure class="fig">
      <img src="diagrams/{e["slug"]}.svg" data-dark="diagrams/{e["slug"]}.svg" data-light="diagrams/{e["slug"]}-light.svg" alt="{esc(e["title"])} animated diagram" width="660" loading="lazy">
      <figcaption>
        <a href="diagrams/{e["slug"]}.svg" target="_blank" rel="noopener">open .svg ↗</a>
        <a href="diagrams/{e["slug"]}.spec.json" target="_blank" rel="noopener">spec.json ↗</a>
        <span class="loop">loop {esc(spec.get("loop", 9))} s</span>
      </figcaption>
    </figure>
    <aside class="ledger">
      <div class="col">
        <h3>Schedule <span class="hint">from spec.json</span></h3>
        <div class="tablewrap"><table>
          <thead><tr><th>id</th><th>kind</th><th class=num>start</th><th class=num>end</th><th>label / note</th></tr></thead>
          <tbody>{trs}</tbody>
        </table></div>
      </div>
      <div class="col">
        <h3>Motion used</h3>
        <ul class="prims">{prim}</ul>
        <h3>Cut from the source</h3>
        <p class="cuts">{esc(e["cuts"])}</p>
      </div>
    </aside>
  </div>
</section>''')

    page = TEMPLATE.replace("{{CHIPS}}", "\n".join(chips)).replace("{{SECTIONS}}", "\n".join(sections))
    for k, v in site.items():
        page = page.replace("{{" + k.upper() + "}}", esc(v))
    page = page.replace("{{COUNT}}", f"{len(entries):02d}")
    (HERE / "index.html").write_text(page)
    print(f"wrote docs/index.html with {len(entries)} entries")

TEMPLATE = (HERE / "template.html").read_text()

if __name__ == "__main__":
    build()

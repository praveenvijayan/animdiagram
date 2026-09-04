#!/usr/bin/env python3
"""Smoke tests for timeline.py and check.py. Run: python3 scripts/test_timeline.py"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import timeline  # noqa: E402
import check  # noqa: E402
import skin  # noqa: E402


def run(*args):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True)


def test_example_round_trip():
    """Injecting the shipped spec into the shipped example changes nothing and passes check."""
    svg = ROOT / "assets" / "example-async-jobs.svg"
    spec = ROOT / "assets" / "example-async-jobs.spec.json"
    before = svg.read_text()
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d) / "x.svg"
        tmp.write_text(before)
        r = run(HERE / "timeline.py", spec, "--inject", tmp)
        assert r.returncode == 0, r.stderr
        assert tmp.read_text() == before, "inject is not idempotent"
        errors, warns = check.check(tmp)
        assert not errors, errors
        assert not warns, warns


def test_packet_timing_constant_speed():
    spec = {"loop": 10, "events": [
        {"id": "p", "kind": "packet", "at": 1, "travel": 2, "from": [0, 0], "via": [[100, 0]], "to": [100, 300]}]}
    css, els, table, loop = timeline.compile_spec(spec)
    block = "\n".join(css)
    # 100px of 400px total path -> 25% of travel -> 1 + 0.5 s = 15%
    assert re.search(r"15% \{ transform: translate\(100px, 0px\); \}", block), block
    assert "30% { transform: translate(100px, 300px); opacity: 1; }" in block, block
    assert any('class="pkt"' in e for e in els)
    assert any('class="ring"' in e for e in els)


def test_after_chaining_and_gap():
    spec = {"loop": 8, "gap": 0.5, "events": [
        {"id": "a", "kind": "packet", "at": 0, "travel": 1, "from": [0, 0], "to": [10, 0]},
        {"id": "b", "kind": "packet", "after": "a", "from": [0, 0], "to": [10, 0]},
        {"id": "c", "kind": "packet", "with": "b", "from": [0, 0], "to": [10, 0]}]}
    _, _, table, _ = timeline.compile_spec(spec)
    starts = {row[0]: row[2] for row in table}
    assert abs(starts["b"] - 1.5) < 1e-9
    assert starts["c"] == starts["b"]


def test_overrun_is_an_error():
    spec = {"loop": 2, "events": [{"id": "p", "kind": "packet", "at": 1.9, "travel": 1, "from": [0, 0], "to": [1, 0]}]}
    try:
        timeline.compile_spec(spec)
    except timeline.SpecError:
        return
    raise AssertionError("expected SpecError for an event past the loop end")


def test_stream_tokens_and_phase_text():
    spec = {"loop": 6, "events": [
        {"id": "s", "kind": "stream", "from": [0, 0], "to": [50, 0], "period": 1.5, "count": 4},
        {"id": "ph", "kind": "phase", "at": 0, "until": 3, "text": "1 · GO", "x": 10, "y": 10}]}
    css, els, _, _ = timeline.compile_spec(spec)
    assert sum('animation-duration:1.5s' in e for e in els) == 4
    assert any("1 · GO" in e and 'class="t-tag story"' in e for e in els)
    assert "@keyframes ph { 0%, 50% { opacity: 1; }" in "\n".join(css)


def test_check_rejects_script_and_orphan_keyframes():
    with tempfile.TemporaryDirectory() as d:
        bad = Path(d) / "bad.svg"
        bad.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100" role="img" aria-label="x">'
            '<style>.pkt{} @keyframes zz { 0% { opacity: 0 } 100% { opacity: 1 } }</style>'
            '<script>alert(1)</script><circle class="pkt" style="animation-name:nope" r="1"/></svg>')
        errors, _ = check.check(bad)
        joined = " | ".join(errors)
        assert "<script>" in joined and "no @keyframes" in joined and "reduced-motion" in joined, errors


def test_templates_pass_check():
    for name in ("template.svg", "template-light.svg"):
        errors, warns = check.check(ROOT / "assets" / name)
        assert not errors and not warns, (name, errors, warns)


def test_skin_round_trip():
    dark = (ROOT / "assets" / "example-async-jobs.svg").read_text()
    light = skin.convert(dark, "light")
    assert "#4CF490" not in light.upper() and "#EB6C36" in light.upper()
    glows = [l for l in light.splitlines() if "-glow {" in l]
    assert glows and all("opacity: 0.18;" in l and "opacity: 0.3;" not in l for l in glows)
    back = skin.convert(light, "dark")
    assert back == dark, "light -> dark does not restore the original"
    shipped = (ROOT / "assets" / "example-async-jobs-light.svg").read_text()
    assert shipped == light, "shipped light example is stale; rerun skin.py"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"ok    {t.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL  {t.__name__}: {exc}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)

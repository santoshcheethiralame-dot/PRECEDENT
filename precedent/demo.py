"""The split screen. Two copies of the same app, two agents, one clock.

Left has no memory. Right has the ledger. You watch one of them go down.
Nothing here is mocked: the same gate, the same ledger, the same oracle.
"""
from __future__ import annotations

import json
import shutil
import socketserver
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from .change import Change
from .db import Ledger
from .harness import register_failure, run
from . import gate

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "seeds" / "clinic"
WORK = ROOT / ".demo"
PORTS = {"A": 8901, "C": 8902, "ui": 8900}

TASK = "Add a phone_verified field to the Patient model"
MODEL_SRC = ('FIELDS = ["id", "name", "phone", "phone_verified"]\n\n'
             'LABELS = {"id": "#", "name": "Patient", "phone": "Phone", '
             '"phone_verified": "Verified"}\n')
MIGRATION = "ALTER TABLE patients ADD COLUMN phone_verified INTEGER DEFAULT 0;\n"

STEPS = [
    {"label": "read the model",
     "A": {"tool": "read_file", "path": "models/patient.py"},
     "C": {"tool": "read_file", "path": "models/patient.py"}},
    {"label": "add the field",
     "A": {"tool": "write_file", "path": "models/patient.py", "content": MODEL_SRC},
     "C": {"tool": "write_file", "path": "models/patient.py", "content": MODEL_SRC}},
    {"label": "carry on",
     "A": {"tool": "done"},
     "C": {"tool": "write_file", "path": "migrations/003_phone_verified.sql", "content": MIGRATION}},
    {"label": "finish",
     "A": {"tool": "done"},
     "C": {"tool": "done"}},
]


SKIP = {"__pycache__", ".precedent"}


def _files(root: Path) -> set[str]:
    return {str(p.relative_to(root)).replace("\\", "/") for p in root.rglob("*")
            if p.is_file() and not SKIP & set(p.parts)}


def _copy(dst: Path) -> None:
    """Restore the tree in place. The app servers hold this directory open on
    Windows, so it is never deleted - only brought back to the seed state."""
    dst.mkdir(parents=True, exist_ok=True)
    want = _files(SEED)
    for rel in _files(dst) - want:
        (dst / rel).unlink(missing_ok=True)
    for rel in want:
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SEED / rel, target)


def teach(led: Ledger, repo: Path) -> dict:
    """Give the ledger the history it would have had: one good run, one bad one."""
    good = ('FIELDS = ["id", "name", "phone", "notes"]\n\n'
            'LABELS = {"id": "#", "name": "Patient", "phone": "Phone"}\n')
    run(repo, "add a notes field", led, arm="A", scripted=[
        {"tool": "write_file", "path": "models/patient.py", "content": good},
        {"tool": "write_file", "path": "migrations/002_notes.sql",
         "content": "ALTER TABLE patients ADD COLUMN notes TEXT;\n"},
        {"tool": "done"}])
    bad = run(repo, "add an email field", led, arm="A", scripted=[
        {"tool": "write_file", "path": "models/patient.py",
         "content": 'FIELDS = ["id", "name", "phone", "email"]\n\nLABELS = {"id": "#"}\n'},
        {"tool": "done"}])
    return register_failure(repo, led, bad, use_model=False)


class State:
    def __init__(self) -> None:
        self.led: Ledger | None = None
        self.reset()

    def reset(self) -> dict:
        self.step = 0
        self.edits = {"A": {}, "C": {}}
        self.trace = {"A": [], "C": []}
        self.blocked = None
        self.verdict = None
        self.t0 = time.time()
        for arm in ("A", "C"):
            _copy(WORK / arm)
        if self.led is None:
            self.led = Ledger(WORK / "ledger.db")
        self.led.wipe()
        self.holding = teach(self.led, WORK / "C")
        _copy(WORK / "C")          # a pristine tree; the ledger keeps what it learned
        return self.snapshot()

    def advance(self) -> dict:
        if self.step >= len(STEPS):
            return self.snapshot()
        s = STEPS[self.step]
        self.blocked = None
        for arm in ("A", "C"):
            a = s[arm]
            line = a["tool"] + (" " + a.get("path", "") if a.get("path") else "")
            if a["tool"] == "write_file":
                p = WORK / arm / a["path"]
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(a["content"], encoding="utf-8")
                self.edits[arm][a["path"]] = a["content"]
                if arm == "C":
                    v = gate.evaluate(self.led, str((WORK / "C").resolve()),
                                      Change.from_edits(WORK / "C", self.edits["C"]))
                    if v:
                        self.blocked = {
                            "n": v[0].holding_id, "says": v[0].says, "rule": v[0].rule,
                            "reason": v[0].reason, "cited": v[0].cited,
                            "empanel": v[0].empanel,
                            "when": time.strftime("%d %b", time.localtime(v[0].established)),
                        }
                        line += "   HALTED"
            self.trace[arm].append(line)
        self.step += 1
        return self.snapshot()

    def _verdicts(self) -> dict:
        """The oracle decides, not the browser. Same script the benchmark runs."""
        if self.verdict is None and self.step >= len(STEPS):
            self.verdict = {
                arm: subprocess.run("python oracle.py", cwd=WORK / arm, shell=True,
                                    capture_output=True, text=True).returncode == 0
                for arm in ("A", "C")}
        return self.verdict or {}

    def snapshot(self) -> dict:
        return {"step": self.step, "total": len(STEPS), "blocked": self.blocked,
                "verdict": self._verdicts(),
                "trace": self.trace, "task": TASK,
                "label": STEPS[self.step]["label"] if self.step < len(STEPS) else "finished",
                "counts": self.led.counts(str((WORK / "C").resolve())) if self.led else {}}


STATE = State()


class UI(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path.startswith("/state"):
            return self._json(STATE.snapshot())
        if self.path.startswith("/step"):
            return self._json(STATE.advance())
        if self.path.startswith("/reset"):
            return self._json(STATE.reset())
        page = (ROOT / "web" / "demo.html").read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)


def serve_app(arm: str) -> subprocess.Popen:
    return subprocess.Popen([sys.executable, "app.py", str(PORTS[arm])],
                            cwd=WORK / arm, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> int:
    STATE.reset()
    procs = [serve_app("A"), serve_app("C")]
    print(f"  arm A  http://127.0.0.1:{PORTS['A']}")
    print(f"  arm C  http://127.0.0.1:{PORTS['C']}")
    print(f"  demo   http://127.0.0.1:{PORTS['ui']}\n")
    try:
        HTTPServer(("127.0.0.1", PORTS["ui"]), UI).serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            p.terminate()
    return 0

"""A local HTTP face for the ledger, so a real agent runtime can reach it.

Standard library only, one process, no container. The agent-side plugin is
deliberately thin: every decision is made here, where it is testable.

Endpoints:
  POST /v1/gate       {repo, pending[]}  -> binding precedents that would fire
  POST /v1/advise     {repo, task}       -> persuasive authority, as prose
  POST /v1/reject     {repo, reason}     -> file a rejection against the tree
  POST /v1/postflight {repo, cmd}        -> run a check, file the failure
  GET  /v1/health
"""
from __future__ import annotations

import json
import subprocess
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from .change import Change
from .db import Ledger, ledger_path
from .harvest import Signal, human_reject
from . import gate, nextstep, recall, record, shell, templates, transfer

PORT = 4000
_ledgers: dict[str, Ledger] = {}


def _led(repo: str) -> Ledger:
    key = str(Path(repo).resolve())
    if key not in _ledgers:
        _ledgers[key] = Ledger(ledger_path(Path(key)))
    return _ledgers[key]


def _relative(repo: Path, path: str) -> str:
    """Agent runtimes hand out absolute paths; every rule in the ledger is
    repo-relative. Getting this wrong makes the gate both under- and
    over-block: the triggering write slips through, and then the fix the
    halt card asked for is itself refused."""
    q = str(path).replace("\\", "/").strip()
    if not q:
        return ""
    try:
        return Path(q).resolve().relative_to(Path(repo).resolve()).as_posix()
    except (ValueError, OSError):
        return q.lstrip("./")


def _tree(repo: str, pending: list[str] | None = None) -> Change:
    """The tree as it stands, plus what the agent is about to touch.

    Judging a write before it lands is the difference between a gate and a
    post-mortem. Autopsy could only ever report; this refuses.
    """
    ch = Change.from_git(Path(repo))
    for raw in pending or []:
        rel = _relative(Path(repo), raw)
        if rel and rel not in ch.touched:
            ch.touched.append(rel)
    ch.touched.sort()
    return ch


def gate_check(repo: str, pending: list[str] | None = None) -> dict:
    led = _led(repo)
    root = str(Path(repo).resolve())
    verdicts = gate.evaluate(led, root, _tree(repo, pending),
                             borrowed=transfer.borrowed(root))
    ch = _tree(repo, pending)
    return {"block": bool(verdicts), "verdicts": [
        {"n": v.holding_id, "says": v.says, "rule": v.rule, "reason": v.reason,
         "next": nextstep.suggest(v, Path(repo), ch.touched),
         "cited": v.cited, "empanel": v.empanel,
         "when": time.strftime("%d %b %Y", time.localtime(v.established))}
        for v in verdicts]}


def advise(repo: str, task: str, everything: bool = False) -> dict:
    """Persuasive authority as prose.

    With `everything`, binding rules are rendered as warnings too. That is arm B:
    the same knowledge the gate holds, delivered the way Autopsy delivers it -
    a paragraph in the prompt that the model is free to ignore.
    """
    led, root = _led(repo), str(Path(repo).resolve())
    if not everything:
        return {"text": recall.briefing(led, root, task or "")}
    rows = recall.similar(led, root, task or "", k=6, statuses=("binding", "persuasive"))
    if not rows:
        return {"text": ""}
    lines = ["Past failures on tasks like this one, from this repository's own history:"]
    for r in rows:
        lines.append(f"- {r['says']}")
        if r["template"] in templates.TEMPLATES:
            lines.append(f"  ({templates.render(r['template'], r['params'])})")
    return {"text": chr(10).join(lines)}


def reject(repo: str, reason: str) -> dict:
    led = _led(repo)
    root = str(Path(repo).resolve())
    run_id = led.open_run(root, reason, arm="live")
    led.close_run(run_id, "fail")
    out = record.file_case(led, run_id, root, human_reject(reason), _tree(repo),
                           use_model=False, share=True)
    return {k: out[k] for k in ("case_id", "holding_id", "status", "says", "shared")}


def postflight(repo: str, cmd: str) -> dict:
    r = shell.run(cmd, repo)
    output = (r.stdout + r.stderr)[-1500:]
    if r.returncode == 0:
        return {"passed": True, "output": output}
    led = _led(repo)
    root = str(Path(repo).resolve())
    run_id = led.open_run(root, f"check: {cmd}", arm="live")
    led.close_run(run_id, "fail")
    sig = Signal("command_fail", "high", "the working tree failed its check",
                 json.dumps({"output": output[:400]}))
    out = record.file_case(led, run_id, root, sig, _tree(repo), use_model=False, share=True)
    return {"passed": False, "output": output,
            "filed": {k: out[k] for k in ("case_id", "holding_id", "status", "says", "shared")}}


ROUTES = {
    "/v1/gate": lambda b: gate_check(b["repo"], b.get("pending")),
    "/v1/advise": lambda b: advise(b["repo"], b.get("task", ""), b.get("everything", False)),
    "/v1/reject": lambda b: reject(b["repo"], b.get("reason", "")),
    "/v1/postflight": lambda b: postflight(b["repo"], b.get("cmd", "python oracle.py")),
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code: int, obj) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/v1/health"):
            return self._send(200, {"ok": True, "ledgers": list(_ledgers)})
        self._send(404, {"error": "no such route"})

    def do_POST(self):
        fn = ROUTES.get(self.path.split("?")[0])
        if not fn:
            return self._send(404, {"error": "no such route"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
            self._send(200, fn(body))
        except Exception as e:                       # the agent must never stall on us
            self._send(200, {"error": str(e), "block": False, "verdicts": []})


def main(port: int = PORT) -> int:
    print(f"  precedent listening on http://127.0.0.1:{port}")
    try:
        HTTPServer(("127.0.0.1", port), Handler).serve_forever()
    except KeyboardInterrupt:
        pass
    return 0

"""Filing a case and, if it survives empanelment, establishing precedent."""
from __future__ import annotations

from pathlib import Path

from .change import Change
from .db import Ledger
from .harvest import Signal
from . import artifacts, compiler, empanel, templates  # noqa: F401


def file_case(led: Ledger, run_id: int, repo: str, sig: Signal, ch: Change,
              use_model: bool = True) -> dict:
    """Record the failure, compile a holding, and test it against history."""
    case_id = led.file_case(run_id, repo, sig.source, sig.confidence,
                            sig.summary, ch.touched, sig.detail)
    artifacts.save(Path(repo), run_id, ch)   # the case's own tree, for re-empanelment
    case = led.case(case_id)

    past = [c for c in (artifacts.load(Path(repo), r["id"])
                        for r in led.successful_runs(repo, limit=40)) if c]
    template, params, says = compiler.compile_case(case, ch, use_model=use_model, past=past)
    if not template:
        hid = led.establish(case_id, repo, "prose", {"text": says}, says, status="persuasive")
        return {"case_id": case_id, "holding_id": hid, "status": "persuasive",
                "template": None, "says": says, "receipt": {"error": "no template fit"}}

    status, receipt = empanel.empanel(led, repo, template, params, ch)
    if sig.confidence != "high" and status == "binding":
        status, receipt = "persuasive", {**receipt, "note": "low-confidence signal"}

    hid = led.establish(case_id, repo, template, params, says, status=status, empanel=receipt)
    return {"case_id": case_id, "holding_id": hid, "status": status,
            "template": template, "params": params, "says": says, "receipt": receipt}


def record_success(led: Ledger, run_id: int, repo: str, ch: Change) -> None:
    """A passing run is evidence too: it is what future holdings get tested against."""
    led.close_run(run_id, "pass")
    artifacts.save(Path(repo), run_id, ch)
    empanel.reconsider(led, repo)

# PRECEDENT

**Your coding agent forgot the migration again. It was told not to, on Tuesday.**

Precedent turns a failure into a **binding check** — deterministic, executable,
and cited to the run that established it. Not a paragraph in the system prompt,
which a model is free to ignore, but a rule that fires and stops the run.

```
Autopsy tells the agent about the crash. Precedent takes the keys.
```

## See it

```bash
python -m precedent demo
```

Two copies of the same app, two agents, one clock, one task: *add a
phone_verified field to the Patient model*. The left agent has no memory. The
right one has the ledger.

Left edits the model, skips the migration, and **the app goes down on screen**.
Right is halted mid-edit by a card citing precedent No 1, writes the migration,
and stays up. You do not have to read code to see which one is still standing.

## Run it on a repo

```bash
python -m precedent gate .        # does any binding precedent fire on this tree?
python -m precedent reject "you changed models/ without touching migrations/"
python -m precedent docket        # the cases, and what each one established
python -m precedent sweep         # re-decide every binding holding from its citations
```

`gate` exits 1 when a precedent fires, so it drops into a pre-commit hook or CI
without ceremony.

## How a lesson becomes law

**Case** → a failed run: a human rejection, a failing check, or a free signal
(a file rewritten inside one run, a revert, tests that flipped from green to red).

**Holding** → the case compiled into one of six typed checks. The model's only
job is choosing a template and filling its blanks; it never writes a checker,
because a small free model fills a schema reliably and writes novel code badly.
Nothing fits → a prose warning, labelled as the weaker tier.

| Template | Fires when |
|---|---|
| `co_change(trigger, required)` | trigger glob touched, required glob not |
| `required_command(glob, cmd)` | glob touched and `cmd` exits non-zero |
| `forbidden_edit(glob)` | glob touched at all |
| `must_not_appear(regex, glob)` | banned pattern in added lines |
| `must_appear(regex, glob)` | required pattern missing |
| `regression_test(path)` | a test generated from the case fails |

**Empanelment** → the part that makes *binding* mean something. A holding is
replayed against history before it gets any authority: it must fire on the case
that produced it, and stay silent across the stored working trees of past
**successful** runs. With no history to test against it stays advisory, and a
later passing run can promote it. Every card shows the receipt: `1/1 fire ·
0/40 false`.

**Citation** → every firing is recorded with what happened next.

**Overruling** → a precedent whose overrides keep passing anyway loses its
authority and is published as overruled. Being wrong in public is the point.

## The pairing is learned, not authored

The fallback compiler needs no model at all. It reads the repo's own successful
runs and finds the directories that were **never changed alone** — then, when a
failing run changes one without the other, it proposes exactly that rule. In the
seeded app it learns `models/*.py -> migrations/**` from one run that went right,
and enforces it on the one that goes wrong.

## What it costs

Nothing. Python 3.12 and the standard library. One SQLite file, `sqlite3`.
Retrieval is a bag-of-words cosine over a few hundred rows — no pgvector, no ANN
index, no Postgres, no Docker, no embedding API. The model is optional and speaks
the OpenAI-compatible protocol, so Ollama, Groq, Cerebras, OpenRouter and Gemini
all work; set `PRECEDENT_BASE_URL`, `PRECEDENT_MODEL`, `PRECEDENT_API_KEY`.
With no model reachable, the deterministic fallback takes over.

## Where this is

**T0 is done.** The loop closes: the app fails, the failure becomes precedent,
the same task is halted and then succeeds — and `test_loop.py` asserts every
step of that, including that an unrelated edit is *not* gated.

```
python -m pytest -q        # 20 passed
```

**Not built yet, and not claimed:** the three-arm benchmark and its number
(A: no memory · B: prose in the prompt · C: binding gates), the churn and revert
harvesters, cross-repo transfer, and the web surface beyond the demo. The
headline claim of this project is a measurement, and until that benchmark runs
there is no measurement — only a working mechanism.

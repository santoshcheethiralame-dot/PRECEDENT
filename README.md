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

## The number

Two arms, five seeds, thirty tasks across three repos, three hundred runs.
Identical tasks, identical agent, identical seeds — **the only thing that differs
between arms is whether precedent is enforced.**

| | A — no memory | C — binding gates |
|---|---|---|
| pass rate | 53.3% | **73.3%** |
| pass rate on trapped tasks | 39.1% | **65.2%** |
| **repeat-failure rate** | **58.1%** | **23.3%** |
| false positives (on control tasks) | 0.0% | **0.0%** |
| regressions vs arm A | — | **0** |

Repeat-failure rate is the one that matters: of the tasks whose trap class had
already bitten once, how many bit again. Memory cuts it by **60%**, and does it
without blocking a single control task.

### It starts level and pulls away

Trap pass rate by position in the sequence. Arm C begins identical to arm A —
the ledger is empty — and diverges as precedent accumulates.

| tasks | A | C |
|---|---|---|
| 0–5 | 30% | 30% |
| 6–11 | 46% | 50% |
| 12–17 | 45% | 60% |
| 18–23 | 44% | **92%** |
| 24–29 | 30% | **91%** |

### Where it does not work

| trap class | A | C | |
|---|---|---|---|
| schema without migration | 57% | 88% | caught |
| types without regenerate | 35% | 70% | caught |
| plugin not declared | 25% | 52% | partly caught |
| **hand-edited generated file** | **33%** | **33%** | **not caught at all** |

The last row is the honest one. A co-change rule asks whether the right
directory moved. An agent that hand-edits `client/generated.py` instead of
running the generator *does* touch the right directory — with the wrong content.
Structural rules cannot see that. Catching it needs a `forbidden_edit` holding,
which this failure signal cannot produce on its own.

### Four caveats, stated plainly

1. **The agent is synthetic.** It performs each companion action with probability
   `p_recall` from a seeded generator. This measures the enforcement layer, not a
   language model.
2. **Arm B was not run.** Its entire mechanism is whether a model obeys a
   paragraph in its prompt, which a synthetic agent cannot answer. Rather than
   invent the comparison that is the whole point of the project, it is left
   unrun. `python -m precedent bench --arms A,B,C` runs it the moment a provider
   is reachable.
3. **The false-positive cost is not priced.** A blocked run is allowed to
   continue and can still pass, so a false alarm would show up as wasted work
   rather than as a failure. Under a hard block it would cost more.
4. **These figures replace an earlier run.** The first pass reported an 8.6%
   false-positive rate; it was an artifact of our own bytecode-cache bug, not a
   property of the design. A `.pyc` records source mtime to one-second
   granularity, and these runs write a module and import it inside the same
   second — so Python could serve the previous version and score a failing run
   as a pass. Arm C's learning reads run outcomes, so it inherited the error;
   arm A has no feedback loop and is unchanged to the decimal. The pre-fix
   report is kept as `bench/report.prebugfix.json`.

Reproduce:

```bash
python -m precedent bench --arms A,C --seeds 1,2,3,4,5   # ~150s, writes bench/report.json
```

## Where this is

**T0 and T1 are done.** The loop closes: the app fails, the failure becomes precedent,
the same task is halted and then succeeds — and `test_loop.py` asserts every
step of that, including that an unrelated edit is *not* gated.

```
python -m pytest -q        # 27 passed
```

**Not built yet, and not claimed:** arm B (needs a provider), the churn and
revert harvesters, cross-repo transfer, and the web surface beyond the demo —
the tape, the docket, the case file and the overruled page. `bench/report.json`
already carries the data each of those pages renders.

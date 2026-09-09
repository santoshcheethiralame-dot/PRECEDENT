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

## Use it on your own repo

```bash
python -m precedent init                                  # learn this repo's habits
python -m precedent rule "models/*.py needs migrations/"  # or just tell it
python -m precedent why models/patient.py                 # what applies here?
python -m precedent gate .                                # exits 1 if a rule fires
python -m precedent off 4                                 # this rule is wrong
python -m precedent status                                # what it caught this week
python -m precedent hook                                  # git pre-commit hook
```

**`init` is the one that matters**, because an empty ledger on day one is
useless. It reads your commit history and proposes rules before anything has
gone wrong. On real repositories it finds real things — in `caliper` it worked
out that `results/` never moves without `docs/`, which is a working practice
nobody had written down.

It is also willing to find nothing. On a repo whose history shows no habit
strong enough to be a rule it says so, because inventing one would be worse.

Three tests decide whether a pairing becomes a proposal:

| | |
|---|---|
| **support** | seen together often enough to be a habit, not a coincidence |
| **confidence** | P(B given A) — touching A really does mean touching B |
| **asymmetry** | P(A given B) is *low* — otherwise the two simply move together, and the data cannot tell you which is the trigger |

The third is the one that took measuring. Without it, an initial commit that
touches every directory makes everything "always" pair with everything, and two
things that genuinely move as one support *"A needs B"* exactly as much as
*"B needs A"*.

Everything `init` proposes lands **advisory**. History is evidence about habits,
not proof that breaking one causes harm — `precedent confirm <n>` promotes, and
empanelment still gates the promotion. A rule *you* write binds immediately,
because you know your own repo — but it is still replayed against past work, and
demoted if it would have blocked something that already succeeded.

`gate` exits 1 when a precedent fires, so it drops into a pre-commit hook or CI
without ceremony. `off` mutes a rule without deleting the case that produced it:
a tool that blocks you once for a bad reason and offers no way out gets
uninstalled, and everything it ever learned goes with it.

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
| pass rate | 53.3% | **74.0%** |
| pass rate on trapped tasks | 39.1% | **66.1%** |
| **repeat-failure rate** | **58.1%** | **22.1%** |
| false positives (on control tasks) | 0.0% | 8.6% |
| regressions vs arm A | — | **0** |

Repeat-failure rate is the one that matters: of the tasks whose trap class had
already bitten once, how many bit again. Memory cuts it by **62%**.

### It starts level and pulls away

Trap pass rate by position in the sequence. Arm C begins identical to arm A —
the ledger is empty — and diverges as precedent accumulates.

| tasks | A | C |
|---|---|---|
| 0–5 | 30% | 30% |
| 6–11 | 46% | 54% |
| 12–17 | 45% | 60% |
| 18–23 | 44% | **92%** |
| 24–29 | 30% | **91%** |

### Where it does not work

| trap class | A | C | |
|---|---|---|---|
| schema without migration | 57% | 88% | caught |
| types without regenerate | 35% | 70% | caught |
| plugin not declared | 25% | 52% | partly caught |
| **hand-edited generated file** | **33%** | **40%** | **partly caught, and it was 0% before** |

The last row took a new template to move at all. A co-change rule asks whether
the right directory moved, and an agent that hand-edits `client/generated.py`
instead of running the generator *does* touch the right directory — with the
wrong content. `forbidden_edit` is the obvious fix and the wrong one, because a
legitimate regeneration touches that same path and empanelment would rightly
demote the rule.

What separates them is **whether the generator ran**. So the recorder learned to
see commands, and `must_run` asks that question — with the rule read out of the
file's own words (`GENERATED FILE - run tools/gen.py, do not edit by hand`),
not from anything we hardcoded. Where commands are invisible, it abstains: a
gate that fires on missing evidence fires on everything.

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
4. **All three false positives are one rule**, and it exposes a real limit.
   `co_change(docs/*.md -> registry.py)` fires on control tasks that edit `docs/`
   alone. Empanelment did not catch it because no past successful run had ever
   touched `docs/` by itself, so the false-positive test passed vacuously — it
   can only refute a rule with evidence it has. The deeper problem is that
   **co-occurrence gives correlation, not direction**: `docs/` and `registry.py`
   always moved together, so the useful rule and the useless one are equally
   supported by the data, and the derivation picked a direction arbitrarily. It
   is now at least deterministic. This is unsolved.
5. **An earlier run was scored under a bytecode-cache bug** and is kept as
   `bench/report.prebugfix.json`. A `.pyc` records source mtime to one-second
   granularity, and these runs write a module and import it inside the same
   second — so Python could serve the previous version and score a failing run
   as a pass.

Reproduce:

```bash
python -m precedent bench --arms A,C --seeds 1,2,3,4,5   # ~150s, writes bench/report.json
```

## Where this is

**T0 and T1 are done.** The loop closes: the app fails, the failure becomes precedent,
the same task is halted and then succeeds — and `test_loop.py` asserts every
step of that, including that an unrelated edit is *not* gated.

```
python -m pytest -q        # 66 passed
```

**Not built yet, and not claimed:** arm B. Its mechanism is whether a language
model obeys a paragraph in its prompt, so it needs a real provider in all three
arms — and until it runs, *"gates beat warnings"* is a thesis, not a finding.

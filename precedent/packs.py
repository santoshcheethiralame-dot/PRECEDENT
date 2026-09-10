"""The mistakes every coding agent makes, that every user recognises.

Mined rules describe one repository's habits. These are different: they are the
failures that show up everywhere, and a person should not have to be burned by
them once each before the tool knows about them.

Two tiers, and the split is about false positives rather than severity:

  BINDING     the pattern is unambiguous. A live AWS key is never intentional,
              and `pdb.set_trace()` is never meant to be committed.
  ADVISORY    the pattern is usually wrong but legitimately happens - tests do
              get deleted during real refactors - so it informs and does not
              block. `precedent on <n>` promotes it if you disagree.

Every rule here is installed only when the repository shows it applies, and
every one can be switched off.
"""
from __future__ import annotations

from pathlib import Path

# regex, glob, says, binding
RULES: list[dict] = [
    # ---- secrets -------------------------------------------------------
    dict(key="aws_key", template="must_not_appear", binding=True,
         regex=r"AKIA[0-9A-Z]{16}", glob="**",
         says="Never commit an AWS access key."),
    dict(key="private_key", template="must_not_appear", binding=True,
         regex=r"-----BEGIN [A-Z ]*PRIVATE KEY-----", glob="**",
         says="Never commit a private key."),
    dict(key="token", template="must_not_appear", binding=True,
         regex=r"\b(ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,})",
         glob="**", says="Never commit an API token."),

    # ---- debugging left behind ----------------------------------------
    dict(key="pdb", template="must_not_appear", binding=True, langs={"py"},
         regex=r"\b(pdb|ipdb)\.set_trace\(|\bbreakpoint\(\)", glob="**/*.py",
         says="Take the debugger breakpoint out before this lands."),
    dict(key="debugger", template="must_not_appear", binding=True, langs={"js"},
         regex=r"^\s*debugger\s*;?\s*$", glob="**/*.{js,ts,jsx,tsx}",
         says="Take the debugger statement out before this lands."),
    dict(key="console", template="must_not_appear", binding=False, langs={"js"},
         regex=r"console\.(log|debug)\(", glob="**/*.{js,ts,jsx,tsx}",
         says="Leftover console.log in the code you just changed."),

    # ---- making the red go away the wrong way --------------------------
    dict(key="deleted_test", template="must_not_remove", binding=False,
         regex=r"^\s*(def test_|it\(|test\(|func Test)", glob="**/{test,tests,spec,__tests__}/**",
         says="You deleted a test. If it was wrong, say so; do not just remove it."),
    dict(key="skipped_test", template="must_not_appear", binding=False,
         regex=r"@(pytest\.mark\.)?(skip|xfail)|\.(skip|todo)\(|@unittest\.skip",
         glob="**/{test,tests,spec,__tests__}/**",
         says="You skipped a test instead of fixing it."),

    # ---- unfinished work presented as finished -------------------------
    dict(key="stub", template="must_not_appear", binding=False,
         regex=r"NotImplementedError|TODO: implement|FIXME|XXX:", glob="**",
         says="A stub or TODO was left in the change."),
]


def _looks_like(repo: Path) -> set[str]:
    """Only install what this repository can actually trip over."""
    langs: set[str] = set()
    if any(repo.glob("**/*.py")) or (repo / "pyproject.toml").is_file():
        langs.add("py")
    if (repo / "package.json").is_file() or any(repo.glob("**/*.ts")) \
            or any(repo.glob("**/*.js")):
        langs.add("js")
    return langs


def applicable(repo: Path) -> list[dict]:
    langs = _looks_like(Path(repo))
    return [r for r in RULES if not r.get("langs") or (r["langs"] & langs)]


def manifest_pairs(repo: Path) -> list[dict]:
    """A manifest and its lockfile move together, or the next install differs."""
    repo = Path(repo)
    out = []
    for manifest, lock in (("package.json", "package-lock.json"),
                           ("package.json", "yarn.lock"),
                           ("package.json", "pnpm-lock.yaml"),
                           ("pyproject.toml", "poetry.lock"),
                           ("pyproject.toml", "uv.lock"),
                           ("Gemfile", "Gemfile.lock"),
                           ("go.mod", "go.sum")):
        if (repo / manifest).is_file() and (repo / lock).is_file():
            out.append(dict(key=f"lock_{lock}", template="co_change", binding=True,
                            trigger=manifest, required=lock,
                            says=f"Changing {manifest} means updating {lock} too."))
    return out

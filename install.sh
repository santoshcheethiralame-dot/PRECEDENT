#!/usr/bin/env bash
# PRECEDENT — one line, and your agent stops repeating itself.
#
#   curl -fsSL https://raw.githubusercontent.com/<owner>/precedent/main/install.sh | bash
#
# There is nothing to install. The engine is Python's standard library, the
# ledger is one SQLite file, and the plugin is a single .ts file. This script
# only puts them where your agent will find them.

set -euo pipefail

REPO="${PRECEDENT_REPO:-https://github.com/santoshcheethiralame-dot/precedent}"
HOME_DIR="${PRECEDENT_HOME:-$HOME/.precedent}"
PORT="${PRECEDENT_PORT:-4000}"
PROJECT="${1:-$PWD}"

say() { printf '  %s\n' "$*"; }

command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1 || {
  echo "precedent needs python 3.12 or newer, and could not find one." >&2; exit 1; }
PY=$(command -v python3 || command -v python)

"$PY" - <<'CHECK' || { echo "precedent needs python 3.12 or newer." >&2; exit 1; }
import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)
CHECK

# 1. the engine
if [ -d "$HOME_DIR/.git" ]; then
  say "updating $HOME_DIR"
  git -C "$HOME_DIR" pull --quiet --ff-only
else
  say "fetching precedent into $HOME_DIR"
  git clone --quiet --depth 1 "$REPO" "$HOME_DIR"
fi

# 2. the plugin, where opencode looks for it
if [ -d "$PROJECT" ]; then
  mkdir -p "$PROJECT/.opencode/plugins"
  cp "$HOME_DIR/plugin/precedent.ts" "$PROJECT/.opencode/plugins/precedent.ts"
  say "plugin installed in $PROJECT/.opencode/plugins"
fi

# 3. a launcher
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/precedent" <<LAUNCH
#!/usr/bin/env bash
exec "$PY" -m precedent "\$@"
LAUNCH
chmod +x "$HOME/.local/bin/precedent"
export PYTHONPATH="$HOME_DIR${PYTHONPATH:+:$PYTHONPATH}"

# 4. and the stop script, because anything that starts a process should
cat > "$HOME_DIR/stop.sh" <<'STOP'
#!/usr/bin/env bash
pkill -f "precedent serve" 2>/dev/null || true
echo "  precedent stopped."
STOP
chmod +x "$HOME_DIR/stop.sh"

say ""
say "done. nothing else was installed — no database, no container, no key."
say ""
say "  precedent serve          # the ledger your agent talks to (port $PORT)"
say "  precedent gate .         # does any binding precedent fire on this tree?"
say "  precedent docket         # what this repo has learned"
say "  precedent board          # the board, at http://127.0.0.1:8850/board.html"
say ""
say "add $HOME/.local/bin to PATH, and export PYTHONPATH=$HOME_DIR"
say "stop everything with $HOME_DIR/stop.sh"

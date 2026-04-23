#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# ── Python interpreter ────────────────────────────────────────────────────────
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "Error: no Python interpreter found. Install Python 3.11+ and try again." >&2
    exit 1
fi

PYTHON_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Using Python $PYTHON_VERSION at $("$PYTHON" -c "import sys; print(sys.executable)")"

# ── Virtual environment ───────────────────────────────────────────────────────
if [[ -d "$VENV_DIR" ]]; then
    echo "Virtual environment already exists at .venv — skipping creation."
else
    echo "Creating virtual environment at .venv ..."
    "$PYTHON" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# ── Core dependencies ─────────────────────────────────────────────────────────
echo ""
echo "Installing core requirements ..."
pip install --quiet --upgrade pip
pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
echo "Core requirements installed."

# ── Optional dependencies ─────────────────────────────────────────────────────
echo ""
read -r -p "Install optional dependencies (ChromaDB / semantic search)? [y/N] " answer
case "$answer" in
    [Yy]*)
        echo "Installing optional requirements ..."
        pip install --quiet -r "$SCRIPT_DIR/requirements-optional.txt"
        echo "Optional requirements installed."
        ;;
    *)
        echo "Skipping optional requirements."
        ;;
esac

echo ""
echo "Setup complete. Run ./run.sh to start the application."

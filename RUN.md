# Running Money4Band

**Requirements:** Python 3.10+ and Docker (installed and running).

## One command (any OS)

```bash
python run.py
```

The launcher auto-detects [`uv`](https://docs.astral.sh/uv/) and uses it when
present (fast); otherwise it creates a local `.venv` and installs with `pip`.
Then it starts the app. Any arguments are forwarded to the CLI:

```bash
python run.py --help
python run.py status
```

### Convenience wrappers

| OS | Command |
|----|---------|
| Windows | `run.bat`  (or double-click it) |
| macOS / Linux | `./run.sh` |

Both just call `run.py`, so behaviour is identical everywhere.

## Manual setup (if you prefer)

```bash
# With uv (recommended)
uv sync --no-dev
uv run python main.py

# With pip
python -m venv .venv
# Windows:        .venv\Scripts\activate
# macOS / Linux:  source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

> **Note:** run the app with the *same* interpreter you installed into.
> `uv run` or activating `.venv` handles this automatically; calling a global
> `python` after installing into a venv will not see the dependencies.

The first run creates `config/user-config.json` from the template and walks
you through setup.

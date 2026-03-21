"""Setup progress tracker — serializes step completion to allow resuming."""

import json
import logging
import os

PROGRESS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    ".setup_progress.json",
)


def load_progress() -> dict:
    """Load saved progress from disk. Returns empty dict if none exists."""
    if not os.path.isfile(PROGRESS_FILE):
        return {}
    try:
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        logging.warning("Corrupt setup progress file; starting fresh.")
        return {}


def save_progress(completed_steps: list[int]) -> None:
    """Persist the list of completed step numbers."""
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    data = {"completed_steps": sorted(set(completed_steps))}
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logging.debug("Setup progress saved: steps %s", completed_steps)


def clear_progress() -> None:
    """Remove the progress file after a successful full run."""
    if os.path.isfile(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
        logging.debug("Setup progress file cleared.")


def is_step_done(progress: dict, step: int) -> bool:
    """Check whether *step* was already completed in a previous run."""
    return step in progress.get("completed_steps", [])

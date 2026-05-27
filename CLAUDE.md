# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the Pomodoro timer app
python pomodoro.py
```

No build, lint, or test steps. The app is a standalone Python script with zero dependencies beyond Python 3's standard library (tkinter must be available in the Python install).

## Architecture

Single-file desktop Pomodoro timer (`pomodoro.py`) using Python + tkinter. No frameworks, no external packages.

- **`PomodoroApp` class** — owns all state and UI. Constructor builds the window (440x440, frameless, dark theme), binds drag/right-click events, restores saved config, and calls `set_mode()`.
- **Timer loop** — `_tick()` runs every 1000ms via `root.after()`. `after_id` tracks the scheduled callback so it can be cancelled on pause/reset.
- **State machine** — `running` / `paused` flags, with `remaining_seconds` and `total_seconds`. Modes defined in the `MODES` dict at module level.
- **Auto-switching** — when a timer finishes (`_on_finish`), work sessions auto-switch to break (long break every 4th session); breaks auto-switch back to work.
- **Config persistence** — `pomodoro_config.json` in the same directory, read on startup and written on close. Stores window position, topmost flag, session count, and per-mode minute values.

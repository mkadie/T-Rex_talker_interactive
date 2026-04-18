# `upstream_patches/` — modified T-Rex Talker source files

Files in this directory originated in the upstream
[T-Rex Talker](https://github.com/mkadie) project, which is released
under the **MIT License** (see `../NOTICE`). They have been modified
to integrate the Subprogram framework that is the main contribution
of this repository.

## License boundary

- The unmodified portions of these files remain under MIT. The
  original copyright notice is preserved at the top of each file.
- The **modifications** in these files are released under
  **PolyForm Noncommercial License 1.0.0** (see `../LICENSE`),
  the same license that covers the rest of this repo.

Because the upstream license is MIT, anyone who only uses the
unmodified upstream portions of these files may continue to do so
under MIT. Anyone who uses the modifications — or installs this
overlay onto a T-Rex Talker device — is subject to PolyForm-NC 1.0.0
for those changes.

## What each file adds

| File | Purpose of modification |
|------|-------------------------|
| `action.py` | Recognize `submenu` / `list` values ending in `.py` (and an explicit `subprogram` key) as subprogram launches and emit `"subprogram:<path>"`. |
| `machine.py` | New `_launch_subprogram()` method, a `subprogram:` branch in the press handler, and startup support for `mode = stim_games/<file>.py` in `config.txt`. |
| `config_reader.py` | Add `"mode"` to the config allowlist so the boot-into-subprogram setting survives `apply_config`. |
| `config.txt` | Commented `mode` example (no behavioural change). |
| `menu_system.md` | Documentation updates: subprogram launch syntax, `subprogram` key row, `mode` row, implementation status entry, version history. |

## How to apply

Overwrite the corresponding file in your T-Rex Talker checkout. The
install helper at `../install.sh` / `../install.ps1` does this
automatically; see the top-level README for the full flow.

If you prefer to review the changes as a diff before applying them,
compare each file here against the same filename in your current
T-Rex Talker checkout (e.g. `diff -u /path/to/trextalkv3/action.py
action.py`).

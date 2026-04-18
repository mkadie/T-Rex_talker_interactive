# Pull Request

## Summary

What does this PR change, and why?

## Type of change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New subprogram / stim game
- [ ] Framework improvement (Subprogram base class, loader, dispatcher)
- [ ] Documentation only
- [ ] Chore (tooling, CI, license metadata)

## License certification

By submitting this PR I certify that:

- [ ] My new code is my own work (or I have the right to contribute
      it) and I am submitting it under the
      **PolyForm Noncommercial License 1.0.0** of this repository
      (see `LICENSE`).
- [ ] If this PR modifies any file under `upstream_patches/`, I have
      kept the existing MIT attribution header intact, and the
      modifications remain under PolyForm Noncommercial 1.0.0.
- [ ] I have not bundled or redistributed any third-party code
      incompatible with PolyForm Noncommercial 1.0.0.

## Tests / verification

- [ ] `py_compile` passes on all modified Python files.
- [ ] If I added a new subprogram:
  - [ ] It subclasses `Subprogram` OR exposes a `run(machine, config=None)`
        function.
  - [ ] A sidecar `.cfg` exists if it needs tunables.
  - [ ] It is listed in `menus/games.menu` (unless intentionally hidden).
  - [ ] It's documented in `T-Rex_Talker_Subprogram.md` §9.
- [ ] I verified the device behaviour on real hardware, or I explained
      why I could not.

Paste test output or device observations here.

## Breaking changes

- [ ] None.
- [ ] Yes — details:

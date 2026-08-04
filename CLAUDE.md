# Projects

A personal collection of standalone projects — notebooks, learning material, and
self-contained applications. Each top-level directory is its own project.

## Runtime environment (applies to everything in this repo)

**All applications here are run from Windows Command Prompt on a laptop.**

This is the user's stated environment as of August 2026 and applies to any new
project unless they say otherwise. It has consequences worth getting right the
first time, because a wrong instruction wastes their time rather than mine:

- **Use `python`, not `python3`.** On Windows, `python3` often triggers the
  Microsoft Store placeholder rather than running anything. `py` is a valid
  fallback where the launcher is installed.
- **Command Prompt, not PowerShell or bash.** So: `xcopy /E /I` not `cp -r`,
  `del` not `rm`, `dir` not `ls`, `%USERPROFILE%` not `~`, and `cd /d` when the
  path may be on another drive.
- **Never write `~` in a path.** CMD does not expand it; it creates a directory
  literally named `~`.
- **Prefer zero-install.** Standard library only where practical. Avoiding
  `pip install` removes an entire category of setup failure, and matters more
  here than saving effort with a dependency.
- **Give exact copy-pasteable commands**, and say which directory each runs
  from. Relative-path assumptions are the most common cause of "it doesn't
  work" — most commands here must run from inside the project directory.
- **Test instructions before giving them.** Setup steps in this repo have
  shipped broken twice; run them verbatim first.

## Projects

- `PortfolioAccountant/` — accounting, tax and forensic toolkit for a property
  and business portfolio. Stdlib only. Has its own README, COMPLIANCE.md, and
  agent definitions in `.claude/agents/`. Run its tests with
  `python -m unittest discover -s tests` from inside the project directory.
- `WarrantyVault/` — Expo / React Native receipt and warranty tracker.
- `EE_AI_From_Scratch/`, `Learn_AI_Engineering/` — tutorial projects.
- Various standalone notebooks at the root.

## Note on CI

Cloudflare Pages is connected to this repository (two projects) and fails on
every commit. The cause is `WarrantyVault/package.json` — Pages auto-detects it
and attempts a Node build, but it is a React Native app with no `build` script
and no static output. This is a dashboard configuration issue, not a code
problem, and is unrelated to any given change.

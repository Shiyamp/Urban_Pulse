# Copilot instructions for this workspace

This repository is currently a minimal Python workspace, not a large app or framework project. No repo-local AI instruction files or README were found, and there is no established build/test pipeline in the checked-in files.

## What the codebase looks like
- The workspace is effectively a scratch/utility Python area.
- The observable Python files are simple scripts such as `hello.py`, `distance.py`, and `lambda.py`.
- Prefer a straightforward script/module layout; do not assume a package, service, or web app structure unless the user explicitly adds one.
- Keep changes local and minimal unless a larger project structure is introduced.

## Working conventions
- Favor plain Python over framework scaffolding.
- Prefer self-contained functions and short scripts rather than introducing architecture layers, dependency injection, or project generators.
- If you add new files, keep them small and directly runnable with the standard Python interpreter.
- Use simple, readable variable names and avoid excessive abstraction for tiny scripts.

## Execution and validation
- Run Python scripts directly when validating behavior, e.g. `python hello.py` or `py distance.py` on Windows.
- There is no project-specific test command or CI workflow in this repo; validate with the smallest direct execution that exercises the changed behavior.
- If a change is not immediately runnable, add the smallest possible script or function to demonstrate and verify it.

## Dependency and integration guidance
- Use the standard library before adding third-party packages.
- If a dependency is needed, prefer the lightest practical option and document it in the script or alongside the change.
- Do not add infrastructure such as Docker, FastAPI, Flask, or a full app package unless this is explicitly required by the task.

## When editing
- Match the style of the surrounding script; this repo is not using an established app pattern or naming convention beyond plain Python.
- Preserve compatibility with direct execution and minimal user setup.
- If you need to add shared logic, prefer a single helper module or function over creating a bigger project structure.

## Default assumption
- Treat this as a lightweight Python utility repo. Make the smallest viable change, keep it readable, and verify it by running the relevant script directly.

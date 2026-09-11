# Agent Skills Contributor Guide

This repository contains reusable skills for AI coding agents. Keep every skill portable across agents and operating systems.

## Layout

```text
skills/
  <skill-name>/
    SKILL.md
    scripts/       # optional helper programs
    references/    # optional supporting material
    assets/        # optional templates and static resources
    tests/         # optional focused tests
    evals/         # optional development evaluations documented by agentskills.io
```

- Use a lowercase kebab-case directory name.
- `SKILL.md` is required and its frontmatter `name` must match the directory name.
- Keep supporting files inside the owning skill directory.

## Writing Skills

- Write a specific `description` that states both what the skill does and when to trigger it.
- Keep `SKILL.md` focused. Put detailed guidance in `references/` and deterministic work in `scripts/`.
- Do not hard-code user names, home directories, or platform-specific installation paths.
- Prefer scripts only when they provide a repeatable result; document required runtimes, inputs, outputs, and failure behavior.
- Add `skill-runtime.json` only when a skill exposes a deterministic JSON tool. Prose-only workflow skills do not need artificial runtime wrappers.

## Validation

From the repository root, verify discovery after structural or frontmatter changes:

```sh
bunx skills add . --list
```

Run the narrowest available test for modified scripts or fixtures. For example:

```sh
uv run --with 'pillow==12.3.0' --with pytest pytest skills/photo-processing/tests/test_photo.py
```

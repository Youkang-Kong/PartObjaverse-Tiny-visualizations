---
name: commit-push
description: Group pending changes into self-contained commits and push them. Use proactively after the user has verified that a small feature, bugfix, or refactor works end-to-end. Each commit MUST correspond to one finished, validated unit of work; never push half-implemented changes.
---

# commit-push

Owns the "ship the work that's already verified" step for this fork.

## When to invoke

Trigger this skill when **any** of the following holds:

1. The user just confirmed something works (e.g. "跑通了", "OK", "good", "ship it", or finished a `verify`-style step) and there are uncommitted changes.
2. The user explicitly says "commit", "push", "提交", "推一下", or similar.
3. You finished an autonomous task that's small enough to verify yourself (e.g. a config edit + dry-run) and the working tree is dirty.

Do **NOT** invoke for:
- Work that has not been run / validated yet — finish verification first.
- Mid-refactor states where tests / scripts can't run.
- Files outside this repository.

## Repo facts (preload)

- Remote `origin` = `https://github.com/DQSSSSS/partsgen_trellis.2.git`, default branch `main`.
- A GitHub PAT is baked into the remote URL — `git push` Just Works; do not re-prompt for credentials.
- `.claude/settings.json` is the **project-local** Claude Code config and IS committed (model routing, in-repo Edit allow). Treat it like normal source.
- `.claude/settings.local.json` is per-user UI state (theme etc.) — never commit.
- `CLAUDE.md` is project documentation — commit when it materially changes alongside code, otherwise leave it.
- `partgen/` is part of this project (copy of the upstream remesh_datamaker code, now owned here). Commit its changes like any other source.
- The repo is large (data/checkpoint paths in scripts). Never `git add -A` — always add explicit paths.

## Workflow

1. **Survey state** (always run these in parallel):
   - `git status`
   - `git diff --stat`
   - `git log -5 --oneline` (commit-message style reference)

2. **Group changes into atomic commits.** Each group must:
   - Represent ONE verified unit of work (feature / fix / refactor / docs).
   - Compile/run in isolation if reasonable.
   - Have a clear "why" you can express in 1–2 sentences.
   If multiple unrelated changes are pending, make multiple commits — not one mega-commit.

3. **Exclude unsafe paths automatically**:
   - `.claude/settings.local.json` (per-user UI state)
   - `results/`, `outputs/`, `*.glb`, `*.mp4`, `*.ply`, `*.npz`, `*.pth`, `*.pt`, `*.safetensors` (artifacts / checkpoints)
   - Any path containing secrets (`.env`, `*token*`, `*credential*`)
   If one of these is staged, unstage it and warn the user.

4. **Write commit messages** in the repo's existing style (short imperative subject; body explains *why*, not *what*). Example shape:

   ```
   <area>: <one-line subject in present tense>

   - bullet 1 (why / behavior change)
   - bullet 2 (any caveats)

   Co-Authored-By: Claude Opus 4 <noreply@anthropic.com>
   ```

5. **Commit then push** (sequential — push depends on commit succeeding):
   - `git add <explicit paths>` for each group
   - `git commit -m "$(cat <<'EOF' ... EOF)"` (heredoc so multi-line bodies stay clean)
   - After all groups committed: `git push`

6. **Verify push** with `git status` and report:
   - Which commits were created (hashes + subjects).
   - What was deliberately **left uncommitted** and why (e.g. settings.json, artifact dirs).

## Safety rules

- Never `--amend`, never `push --force`, never skip hooks.
- Never commit files that didn't appear in `git status` output you just observed (no speculative adds).
- If a pre-commit hook fails: investigate, fix, then create a NEW commit. Do not bypass.
- If the user has not actually verified the change (no run / no test), refuse to commit and ask them to verify first.
- If branch is not `main`, ask before pushing.

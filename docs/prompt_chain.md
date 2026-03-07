# Prompt Chain

ActionC64U was developed as a deterministic prompt sequence from the workspace
root at `/mnt/c/test/action`.

## Locations

- workspace root: `/mnt/c/test/action`
- repo root: `/mnt/c/test/action/actionc64u`
- prompt files: `/mnt/c/test/action/prompt-1.txt` through
  `/mnt/c/test/action/prompt-18.txt`

## How To Run The Chain

From the workspace root, point Codex at the next prompt file and let it work in
the repo:

```text
read prompt-1.txt to get started on your task.
```

Then continue in order:

- `prompt-2.txt`
- `prompt-3.txt`
- ...
- `prompt-18.txt`

The prompts are cumulative. Each one assumes the previous prompt was completed,
verified, and committed before moving on.

## Recommended Operator Workflow

1. Start in `/mnt/c/test/action`.
2. Let Codex read the next `prompt-<n>.txt`.
3. Wait for code, docs, tests, and commit completion.
4. Verify the reported quality gate locally when needed.
5. Move to the next prompt file.

## Repo Guidance

The repo-local workflow and constraints are documented in:

- [AGENTS.md](/mnt/c/test/action/actionc64u/AGENTS.md)
- [README.md](/mnt/c/test/action/actionc64u/README.md)

The prompt chain ends at `prompt-18.txt`. There is no prompt after that in this
series.

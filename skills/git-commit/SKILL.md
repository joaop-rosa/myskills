---
name: git-commit
description: "Analyze git changes and commit with AI-generated message. Use ONLY when the user explicitly requests to commit staged changes (e.g., 'commit', 'faça o commit', 'commitar'). NEVER auto-commit after code changes or in subsequent turns unless explicitly asked."
---

# Git Commit

Use this skill **ONLY when the user explicitly asks to commit** in their current prompt.

> [!IMPORTANT]
> **Strict Execution Rules:**
> 1. **Explicit Request Only:** Do NOT commit automatically after completing a task, generating code, editing files, or finishing a prompt. Only perform a commit when the user explicitly commands it in that specific message (e.g., "commite isso", "faça o commit", "commit").
> 2. **No Subsequent Auto-Commits:** Committing once does NOT authorize auto-committing on future messages or tasks. Each commit requires a separate, explicit user request.
> 3. **Staged Changes Only:** Inspect and commit ONLY what is already staged. Do NOT run `git add .` or stage arbitrary files unless explicitly instructed by the user.
> 4. **No Push:** Do NOT push to remote. Only commit locally.

---

Follow these steps in order. Do NOT skip ahead or run `git commit` before completing all verification steps.

## Step 1 — Collect context

Check current branch and repository status:

- Branch name:
  Run `git branch --show-current`
- Repository status:
  Run `git status -s`

## Step 2 — Inspect staged changes

Run:
```bash
git diff --staged
```

## Step 3 — Verify before proceeding

Read the output of `git diff --staged` from Step 2:

- **If the output is empty (no staged changes):**
  - **STOP HERE.**
  - **DO NOT commit.**
  - Inform the user that there are no staged changes to commit.
  - Suggest staging the desired files first (e.g., `git add <files>`).
- **Only if the output is non-empty:** continue to Step 4.

## Step 4 — Generate commit message

Based **only** on the staged changes from Step 2:

1. Determine the type of changes:
   - `feat`: new feature
   - `fix`: bug fix
   - `refactor`: code refactoring without behavior change
   - `perf`: performance improvement
   - `test`: adding or updating tests
   - `docs`: documentation changes
   - `style`: formatting, missing semi colons, etc.
   - `chore`: maintenance, dependencies, build tasks
2. Draft a concise commit message (1-2 sentences) that focuses on the **"why"** rather than the "what".
3. Follow the convention:
   ```
   <type>(<branch-name>): <generated message>
   ```
   *(If the branch name is generic like `main`, `master`, or `dev`, or if scoped context is clearer, format appropriately, e.g. `<type>(<scope>): <message>` or `<type>(<branch-name>): <message>`)*.
4. Present the drafted message clearly to the user before or alongside running the commit.

## Step 5 — Commit

Take the exact message crafted in Step 4 and run:

```bash
git commit -m "<your message here>"
```

**DO NOT push to remote.** Just commit locally.
Once the commit is made, conclude the response. Do NOT schedule or run any further git commits on subsequent tasks unless the user explicitly requests another commit.

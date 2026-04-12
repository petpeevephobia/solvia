# Git workflow across multiple computers

Use this when you work on the same repository from more than one machine (for example a laptop and a desktop). The idea is simple: **push when you leave one device**, **pull when you open the project on another**.

## Before you start working (any machine)

1. Open a terminal in the project root (this folder).
2. Optional: check state and branch.
   - `git status` — a clean tree avoids merge surprises; commit or stash local changes if needed.
   - `git branch` — confirm you are on the branch you intend (for example `main`).
3. Download the latest commits from the remote (usually `origin` on GitHub):
   ```bash
   git fetch origin
   ```
4. Update your current branch to include those commits:
   - If your branch already **tracks** the remote (typical after `git clone`), run:
     ```bash
     git pull
     ```
   - Otherwise pull explicitly, for example:
     ```bash
     git pull origin main
     ```

After a successful `git pull`, your working copy matches the remote branch you pulled (plus any local commits you have not pushed yet).

## When you finish on a machine

So the other device can see your work:

```bash
git add -A
git commit -m "Short, clear description of what changed"
git push origin <branch-name>
```

Replace `<branch-name>` with the branch you use (for example `main`).

**Habit:** end a session with **commit + push**; start the next session with **pull**.

## First-time setup on a new computer

If this repo is not cloned there yet:

```bash
git clone <repository-url>
cd solvia
```

Use the HTTPS or SSH URL from your Git host. After that, use **pull** / **push** as above.

## Environment and local-only files

After pulling on a new machine, you may still need a local `.env` (it is not committed). Copy from the example and fill in secrets:

```bash
cp .env.example .env
```

On Windows, if `cp` is not available: `copy .env.example .env`. See [README.md](README.md) for full setup.

## Set upstream tracking (optional, once per branch)

If `git pull` asks you to specify upstream or you want plain `git pull` to work without naming `origin`:

```bash
git branch -u origin/main main
```

Adjust `main` if your default branch has another name.

## If `git pull` fails

- **Would overwrite local changes:** commit your work, or `git stash`, then pull again. Only discard changes if you are sure you do not need them.
- **Merge conflicts:** Git will list conflicted files; resolve them, then `git add` those files and `git commit` to complete the merge.
- **Authentication:** use SSH keys or a personal access token as required by your host; see your Git provider’s documentation.

## Related commands

| Goal | Command |
|------|--------|
| See remotes | `git remote -v` |
| See recent commits | `git log --oneline -10` |
| Save uncommitted work temporarily | `git stash` (later: `git stash pop`) |

This file is reference only; it does not change how Git behaves. For project setup (Docker, migrations, dev servers), see [README.md](README.md).

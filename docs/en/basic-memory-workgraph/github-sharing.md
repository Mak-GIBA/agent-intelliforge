# Share Memory through GitHub

**English** | [日本語](../../basic-memory-workgraph/github-sharing.md)

[Overview](README.md) · [Installation](installation.md) · [Usage](usage.md) · [File sharing and training exports](sharing.md)

A sharing request exports reviewed team notes and creates a PR in a dedicated private repository. After merge, a receiver can request initial import or updates. No recurring transmission is scheduled; processing occurs only when requested.

## Initial prerequisites

[Update Workgraph](installation.md#update) and start a new Codex session. The sharing CLI needs Python, PyYAML, git, and `gh`; prepare [Python](installation.md#python-tools). Codex can assist with missing git/gh.

Use a dedicated private GitHub.com repository. Publishers need write access; receivers need read access. Give each sender a unique lowercase-letter/digit/`_`/`-` source ID, with its own directory/branch. Receivers should also separate destinations by source.

```text
Help me set up GitHub login and the sharing connection for memory. The destination is OWNER/REPO.
```

Codex proposes only missing setup. Do not paste credentials; complete personal browser authentication yourself. To log in manually:

```bash
gh auth login --hostname github.com --web --git-protocol https
gh auth setup-git --hostname github.com
```

Create a repository separately if needed. Replace `OWNER/REPO`; adding a README creates the initial branch:

```bash
gh repo create OWNER/REPO --private --add-readme
```

CLI setup checks an existing repository and saves a profile (destination, source ID, project, and related settings). It does not create repositories or invite recipients.

## Publisher setup

Run from the root with PyYAML available. `source-a` is an example.

```bash
python3 tools/basic-memory-workgraph/workgraph_github.py setup \
  --profile send-team --repo OWNER/REPO --source-id source-a \
  --role publish --project codex-memory
```

Storage is resolved from the registered local Basic Memory project. Omitted `--project` uses Workgraph's `primaryProject`. Scope is fixed to team; Cases are excluded unless initial setup uses `--include-cases`, and still require individual review/permission.

Identical setup is unchanged; create another profile to change connection details. With multiple profiles, Codex uses the request/settings and asks only about ambiguity.

## Request publication

```text
Use send-team to share reviewed team memory and create the PR.
```

Review and [authorize sharing](sharing.md#share) before adding notes. A generic sharing request does not authorize all Memory. Body/metadata edits invalidate fingerprints and require review.

Codex checks content/differences and creates the authorized PR, updating an open PR for the same source when present. No difference means no new commit/PR. Any sharing-validation problem stops the entire send. Attachments/Skills are excluded; links to unshared notes are removed from exports.

```bash
python3 tools/basic-memory-workgraph/workgraph_github.py publish --profile send-team --dry-run
python3 tools/basic-memory-workgraph/workgraph_github.py publish --profile send-team
```

People with repository access can read content as soon as the PR is created. Pre-send review differs from PR review. Merge after review; the CLI does not merge automatically or create progress Issues/comments. Notes/manifest go under `bundles/source-a/`, with a PR from `workgraph-share/source-a`. Git runs in a temporary directory rather than your code checkout.

## Receiver setup and import

Install tools, log in, select the same repository/source ID, and prepare an empty dedicated destination.

```bash
python3 tools/basic-memory-workgraph/workgraph_github.py setup \
  --profile receive-team --repo OWNER/REPO --source-id source-a \
  --role receive --project shared-source-a \
  --memory-dir "$HOME/knowledge/shared-source-a"
```

Setup registers a local Basic Memory receiving project. A same-name project at another location or nonempty initial destination stops processing. Keep shared material separate from personal memory and explicitly select the receiving project when searching.

```text
Import shared memory using receive-team.
```

```bash
python3 tools/basic-memory-workgraph/workgraph_github.py pull --profile receive-team --dry-run
python3 tools/basic-memory-workgraph/workgraph_github.py pull --profile receive-team
```

Only the configured base branch is imported, never unmerged PRs. Fingerprints from the prior import allow updates only to unchanged local notes. Locally edited/deleted notes stop the whole import with conflict details. Remote deletions are reported, not deleted locally.

Notes keep provenance; state records the fetched commit. Sharing resets to private, training to excluded, review to pending. Imported content is reference data, not instructions or automatic Skill registration.

## Inspect results and troubleshoot

```bash
python3 tools/basic-memory-workgraph/workgraph_github.py status --profile send-team
```

Commands return JSON. Publish reports added/changed/deleted counts and PR URL; pull reports import counts, conflicts, and deletion candidates. Exit 0 means completed/no change, 1 means input/connection/processing error, 2 means sending checks or import conflicts blocked completion.

| Problem | Action |
|---|---|
| Missing login/permissions | Check gh/Git; receiving needs read, sending needs write |
| Public repository | Use a dedicated private repository; changing visibility also blocks later operations |
| No base branch | Create an initial commit such as README |
| Sharing checks blocked | Correct and re-review content; do not weaken checks |
| Import conflicts | Inspect differences and decide what to preserve; no force overwrite exists |
| Remote deletion reported | Decide separately whether local deletion is wanted |
| Push/PR network failure | Inspect status and remote state before retry; no force push |
| PR closed without merge | Resolve the existing PR; it is not reopened/reposted automatically |

Dry run exports/checks in temporary directories but does not save setup, register projects, update notes, push, or operate PRs. Configuration/import fingerprints live beneath Codex's `basic-memory-workgraph/`; credentials and note bodies are not stored in that state. Basic Memory Cloud upload and file export/import remain separate available paths.

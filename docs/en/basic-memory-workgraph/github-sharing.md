# Share Memory through GitHub

**English** | [日本語](../../basic-memory-workgraph/github-sharing.md)

[Overview](README.md) · [Installation](installation.md) · [Usage](usage.md) · [File sharing and training exports](sharing.md)

You and a friend can contribute knowledge to a private GitHub repository and use it from your own Codex sessions.
After connecting once, ask to sync shared memory to publish and receive together.
Only designated, reviewed notes are sent; your entire personal memory is not uploaded.
This is a Workgraph extension and does not require a Basic Memory Cloud subscription.

```text
Your shared notes     → private GitHub → friend's PC
Friend's shared notes → private GitHub → your PC
```

Enter the prompt examples in Codex chat and the commands in a terminal.
Replace `OWNER/REPO` with your actual sharing repository.
Commands below target the legacy Linux / WSL installation. For other installation layouts, ask Codex to locate the installed sharing CLI first.

<a id="initial-prerequisites"></a>

## 1. Prepare both computers

[Install or update Workgraph](installation.md) on both PCs, then start new Codex sessions.
The sharing CLI requires Python, PyYAML, git, and GitHub CLI (`gh`); see [Python setup](installation.md#python-tools).

Use a dedicated private repository initialized with a README.
Both accounts need write access for combined sending and receiving.
The owner grants access and the friend accepts the invitation. Connecting does not create repositories or invite people.

```text
I want to share Basic Memory knowledge with a friend through GitHub.
The sharing repository is OWNER/REPO.
Help install or update Workgraph, prepare git and gh, and log in to GitHub on this PC.
Check that the repository exists, is private, and that I have access. Help only with missing steps.
Do not send any memory yet.
```

Complete browser authentication yourself when required; never paste credentials into chat.
For manual login:

```bash
gh auth login --hostname github.com --web --git-protocol https
gh auth setup-git --hostname github.com
```

If a new sharing repository is needed, its owner can create it separately:

```bash
gh repo create OWNER/REPO --private --add-readme
```

<a id="connect-once-then-sync"></a>

## 2. Connect once on each PC

Both people connect to the same repository from their own computers.

```text
Connect to OWNER/REPO using connect.
Enable merging my own validated sharing PRs and automatically importing friends' sources merged into this repository.
Do not designate notes for sharing or send them yet.
```

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/basic-memory-workgraph/workgraph_github.py" connect --repo OWNER/REPO
```

`connect` reuses an existing publishing profile. For a fresh setup, it uses your GitHub login as the source ID and a registered personal memory project.
Ambiguous selections require `--project` / `--source-id`. Different people must use different source IDs.
You normally do not need to configure a receiver or directory for each friend.

Connecting opts into merging your own validated PRs and importing merged sources in this repository, including sources added later.
The repository owner should therefore manage its membership.
Connecting alone does not authorize notes for sharing or upload them.

## 3. Review candidates before the first upload

First ask for candidate notes and proposed changes.

```text
Find memory notes that could be useful to share with my friend.
Remove personal or confidential information from the proposal, and list the candidate notes and proposed changes.
Do not edit the originals, grant sharing permission, or send anything yet.
```

Read the list and note contents before approving. To share only some candidates, name the notes or their list numbers.

```text
I approve sharing the proposed candidates with the listed changes.
Apply sharing designation and content review to those notes, then sync sending and receiving with OWNER/REPO.
Do not authorize training use.
```

Codex reviews only the approved notes and checks content and differences before sending.
A pull request (PR) records proposed changes on GitHub. People with repository access can read the content as soon as the PR exists.
Before merging, `sync` verifies that your PR matches the current reviewed export and changes only your source directory.
It does not bypass GitHub protection settings or merge your friend's PRs.

## 4. Ask to sync during normal use

After the initial setup:

```text
Sync shared memory.
```

`sync` performs these steps:

1. Publish designated, reviewed notes.
2. Merge your own validated PR.
3. Import friends' sources merged into the same sharing repository.

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/basic-memory-workgraph/workgraph_github.py" sync
```

Your friend runs the same operation on their PC. After they sync their shared notes, your next sync can receive the update.
This runs on request, not continuously. No differences means no new commit or PR.

New notes do not receive sharing permission automatically, and edits after review require another inspection.
To share new or edited content, return to step 3.
Blocked publishing does not prevent independent receiving from proceeding.

To preview without changing anything:

```text
Without changing anything, show what publishing, merging, and receiving a shared-memory sync would do.
```

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/basic-memory-workgraph/workgraph_github.py" sync --dry-run
```

Dry run checks temporary files but does not change configuration, notes, Basic Memory registration, or GitHub.
With multiple connections, name the repository in your prompt or use `sync --repo OWNER/REPO`.
For receiving only, use the individual operations below: `sync` also publishes and merges your own PR.

## What happens to imported memory

Notes are stored by source, so matching names do not overwrite each person's originals.
Each friend's source receives a dedicated Basic Memory project, appended to the user's `secondaryProjects` for recall.
Your own source is excluded and the normal writing project stays unchanged. Project-level settings can override these reference settings.

If an imported note has local edits, `sync` saves and verifies the edited version in a separate `shared-edits-…` project before updating the shared copy.
Preserved versions are added to reference projects and remain private, excluded from training, and pending review.
A local deletion is recorded before restoring the shared copy. Remote deletions are reported without deleting local notes.
Different versions are not semantically combined into one note.

Imported notes retain provenance, with sharing reset to private, training to excluded, and review to pending.
Importing does not guarantee accuracy, execute instructions inside notes, or register Skills automatically.

## Inspect results and troubleshoot

The command prints JSON. Check these fields:

| Field | Meaning |
|---|---|
| `publish` | Your sending result, added/updated/deleted counts, or reason for blocking |
| `merge` | Whether your PR was merged, unchanged, or blocked |
| `receive` | Results for each source; `edits_project` identifies preserved local edits |
| `status` | `synced`: completed; `planned`: preview; `blocked`: some or all operations deferred |

`receive: []` means there were no friends' sources to receive in this run.
Exit 0 means completed/no change, 1 means an input/connection or similar error, and 2 means publishing checks or receiving blocked completion.
Exit 2 may accompany completed partial receives; inspect each stage rather than assuming nothing happened.

```text
Explain the last sync result, separating completed publishing, merging, and receiving from blocked items.
Investigate blocked items and propose the needed fixes. Do not weaken checks or force overwrites.
```

| Problem | Action |
|---|---|
| Missing login/permissions | Check gh/Git and invitation acceptance; `connect` / `sync` need write access |
| Public repository or no initial branch | Check private visibility and an initial commit such as README |
| Stale sharing review | Inspect edits and re-review the specified notes |
| PR cannot be merged | Inspect protection settings, checks, and differences without bypassing protection |
| Preserving edits or receiving fails | Defer that source and investigate; other successful receives remain |
| Remote deletion reported | Decide separately whether local deletion is wanted |
| Communication failure | Inspect actual state before retry; publishing/merging retry at most twice without force push |
| PR closed without merge | Resolve the existing PR; it is not reopened or reposted automatically |

## Individual sending and receiving

Use `connect` / `sync` above for normal combined operation.
The following procedures are for sending only, receiving only, or receiving with read-only repository access.
Run commands from the repository root. A profile holds a repository, source, destination, and related settings.

### Publisher setup

```bash
python3 tools/basic-memory-workgraph/workgraph_github.py setup \
  --profile send-team --repo OWNER/REPO --source-id source-a \
  --role publish --project codex-memory
```

Use lowercase letters, digits, `_`, or `-` for source IDs, with different IDs for different people.
Omitted `--project` uses Workgraph's `primaryProject`. Include Cases by adding `--include-cases` to initial setup; each Case still requires sharing permission and review.
A new `connect` includes Cases, while reused profiles retain their existing settings.
Identical setup is unchanged; create a different profile to change connection details.

### Request publication

```text
Use send-team to publish reviewed team memory and create the PR. Do not merge it.
```

```bash
python3 tools/basic-memory-workgraph/workgraph_github.py publish --profile send-team --dry-run
python3 tools/basic-memory-workgraph/workgraph_github.py publish --profile send-team
```

`publish` never merges automatically. Validation problems stop the entire send; an existing open PR for the source is updated.
Attachments and Skills are excluded, and links to unshared notes are removed from exported copies.
Notes and the manifest go under `bundles/source-a/`; the branch is `workgraph-share/source-a`.
Git runs in temporary directories, not your coding checkout.

### Receiver setup and import

Receiving alone requires read access. Select the sender's source ID and an empty dedicated destination.

```bash
python3 tools/basic-memory-workgraph/workgraph_github.py setup \
  --profile receive-team --repo OWNER/REPO --source-id source-a \
  --role receive --project shared-source-a \
  --memory-dir "$HOME/knowledge/shared-source-a"
```

```text
Import shared memory using receive-team. Do not publish my memory or merge PRs.
```

```bash
python3 tools/basic-memory-workgraph/workgraph_github.py pull --profile receive-team --dry-run
python3 tools/basic-memory-workgraph/workgraph_github.py pull --profile receive-team
```

`pull` imports merged data only. Local edits or deletions stop the entire import with conflict details; edits are not archived as they are with `sync`.
Manual setup registers the receiving project but does not automatically add it to reference settings.
A nonempty initial destination or a same-name project at a different location also stops setup. Remote deletions do not delete local notes.

```bash
python3 tools/basic-memory-workgraph/workgraph_github.py status --profile send-team
```

Sharing configuration and import fingerprints live beneath Codex's `basic-memory-workgraph/`.
Authentication uses existing gh/Git settings; credentials and note bodies are not stored in sharing configuration or state.
No scheduled transmission or upload from save hooks is installed. Basic Memory Cloud and file exports remain separate sharing options.

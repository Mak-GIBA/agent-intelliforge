# Install, update, and remove SpecKit Upstream

**English** | [日本語](../../speckit-upstream/installation.md)

[Overview](README.md) · [Usage](usage.md) · [Documentation](../README.md)

## Requirements

Requires Linux / WSL2, Bash, Python 3.11+, network access to pinned GitHub files (no GitHub login), and Codex for Skill use. Installing SpecKit CLI additionally needs Python venv/pip and PyPI. Codex itself is not installed. Run as a normal user without sudo; `PYTHON_BIN` selects Python. See the [README](../../../README.md) for retrieval and run from the script directory.

Distribution 2.1.0 assembles embedded upgrades on a pinned base. 2.0.5 build failures were fixed on 2026-10-10, followed by tests/machine update/diagnosis. 2.0.6 shares Research 2.5.0 upgrades; offline builds/self-tests were checked. [Validation (Japanese)](../../design-research/validation.md) separates bundled, assembled, and real-machine checks.

## Install for the user

```bash
# Preview assembly; no arguments has the same effect
bash install_speckit_upstream.sh --dry-run

# Install after successful assembly and verification
bash install_speckit_upstream.sh --apply

# List distributed Codex entries
bash install_speckit_upstream.sh --list-skills
```

No arguments / `--dry-run` previews without network, destination changes, or inspection. It does not establish install readiness or absence of edits. `--version` and `--list-skills` describe the distribution rather than installed state.

```bash
export PATH="$HOME/.local/bin:$PATH"
speckit-workbench doctor
```

To select another existing Python:

```bash
PYTHON_BIN=/absolute/path/python3.12 bash install_speckit_upstream.sh --dry-run
```

If `specify` is missing, assembly's installation stage creates a venv and fetches `specify-cli==1.0.8` plus dependencies. Existing CLI must satisfy `version` / `init --help` checks or installation stops. This is not a guarantee of full compatibility or publisher authentication.

## Assembly and offline use

Both originals at `d3f46e0d591b45cb2423317030a489b91566e891` are fetched/verified, then Research 2.6.0 and Upstream 2.1.0 are built/tested before selected installation. Distribution `--doctor`, `--self-test`, and `--extract` also assemble first.

```bash
bash install_speckit_upstream.sh --build-only ./offline-installers
```

Output must be empty/unused; success emits both scripts/logs without installation. For network-free assembly, prepare genuine unchanged pinned originals:

```bash
bash install_speckit_upstream.sh \
  --base-dir /absolute/path/pinned-base --offline --build-only ./offline-installers

# After a successful build, install without fetching/checking SpecKit CLI
bash ./offline-installers/install_speckit_upstream.sh --apply --skip-specify
```

`--offline` requires `--base-dir`. `--skip-specify` on the wrapper does not suppress base retrieval. On the generated installer it skips SpecKit CLI acquisition/compatibility checks; later official integration still needs compatible `specify`. `attach --docs-only` prepares documents without that integration. See [shared assembly details](../design-research/installation.md#assembly-and-offline-use).

## Options

| Assembly option | Effect |
|---|---|
| `--help` / `-h`, `--version` | Help/version |
| None / `--dry-run` | Preview only |
| `--list-skills` | Distribution entries only |
| `--base-dir DIR` | Two pinned originals |
| `--offline` | No base retrieval; local base required |
| `--build-only DIR` | Both installers/logs, no install |
| `--extract-bundle DIR` | Offline upgrade source/test extraction |
| `--bundle-self-test` | Offline contract tests |

Use list/build/extract-bundle/bundle-self-test individually, without installation arguments. `--dry-run --build-only DIR` previews only.

| Forwarded option | Effect |
|---|---|
| `--apply` | User-wide installation |
| `--update` | Include unchanged owned assets; apply requires `--apply` |
| `--skip-specify` | Skip SpecKit acquisition/checks |
| `--doctor` | Read-only global diagnosis, alone |
| `--self-test` | Assembled tests, alone |
| `--extract DIR` | Extract readable assembled assets, alone; writes files |

## Destinations

| Default path | Content |
|---|---|
| `~/.local/bin/speckit-workbench` | Launcher |
| `~/.local/bin/specify` | Launcher if CLI installed here |
| `~/.local/share/speckit-workbench/releases/2.1.0/` | Code/templates/references/guides |
| `~/.local/share/speckit-workbench/tooling/specify-1.0.8/` | Optional dedicated venv |
| `~/.local/share/speckit-workbench/backups/` | Prior assets |
| `~/.config/speckit-workbench/install.json` | Managed hashes/state |
| `~/.agents/skills/upstream-*/` | Workflow Skills/metadata |
| `~/.agents/skills/speckit-workbench/` | Shared Skill |

Override `XDG_DATA_HOME`, `XDG_CONFIG_HOME`, `SWB_BIN_DIR`, or `SWB_SKILL_DIR` with absolute paths. `SWB_SKILL_DIR` names the shared Skill itself; workflow Skills are siblings. Ensure Codex discovers custom locations and repeat variables for updates/diagnosis/removal; add custom bin directory to PATH.

Global installation does not modify ECC, Basic Memory, hooks, Codex config/AGENTS, app code/DB, or Git remotes. Project documents are a separate stage.

## Prepare a project

Replace `/absolute/path/app` with an existing directory (empty is allowed). `APP` is the item-ID prefix.

```bash
# Preview additions
speckit-workbench attach --project /absolute/path/app --system APP --mode existing

# Confirm the target and apply
speckit-workbench attach --project /absolute/path/app --system APP --mode existing --apply
```

New projects use `--mode new`; other modes are `existing`, `change`, `bug`, `refactor`. Skills guide this preparation when needed. Missing official assets are initialized by `specify init` in temporary storage, then `.specify/` and official `speckit-*` Skills are transferred. Default setup also prepares bug extension/custom append preset there and may use network. Existing integration is retained; unknown/incomplete/conflicting layouts stop rather than force overwrite.

| Attach option | Purpose |
|---|---|
| `--docs-only` | Workbench docs/config only, no official initialization |
| `--without-bug` | Omit bug extension in new official integration |
| `--docs-dir docs/upstream` | Document destination under `docs/` |
| `--approval-profile normal` | `small` / `normal` / `critical` granularity |

Attach places templates; it neither decides/approves specifications nor implements apps. Reattaching retains documents, initial mode, and approval profile. See [usage](usage.md).

## Update and verify

```bash
bash install_speckit_upstream.sh --dry-run --update
bash install_speckit_upstream.sh --apply --update
speckit-workbench doctor
speckit-workbench doctor --project /absolute/path/app
speckit-workbench commands
```

Only unchanged managed assets update; manual edits stop even with `--update`. Identical reruns skip; SpecKit itself is not automatically upgraded. Releases/backups remain. Restart Codex and check `$upstream-` candidates plus installed version/path in doctor.

2.1.0 adds the project overview, brief flow, and v3 bindings to published research evidence. It retains the single Research entry, workstream/integration contracts, and existing v1/v2 bindings. New templates have three primary documents plus generated navigation. Existing documents/approval history do not migrate on attach or Skill update; use [optional migration](usage.md#migrate-existing-material-to-three-documents). Content/requirement/evidence changes need normal review. Research [installation/update](../design-research/installation.md) is separate. See [outputs and review order](../upstream-research-workflow.md).

From 1.2.0 or earlier, approvals not bound to ordinary Markdown become `LEGACY_APPROVAL_UNBOUND`. Keep history, review actual content, explicitly approve, then gate. `gate --write` alone cannot repair this, and reattach is unnecessary.

## Remove

```bash
# Preview removal only
speckit-workbench uninstall

# Remove unchanged managed files
speckit-workbench uninstall --apply
```

Project documents, SpecKit CLI/venv, and backups remain. Edited assets remain and empty Skill folders may remain. Repeat custom destination variables.

## Troubleshoot and inspect sources

Build-test failure stops before installation: inspect [results (Japanese)](../../design-research/validation.md). Check Python, PATH/custom bin directory, existing specify version/help, and conflicts. `--update` cannot force edits. Missing candidates need new session/discovery checks. For `.specify` conflicts inspect existing integration or select docs-only. Stale gate approval needs fresh review and explicit approval for target IDs.

```bash
# Inspect upgrade sources/tests without network
bash install_speckit_upstream.sh --extract-bundle /tmp/speckit-upstream-upgrade
bash install_speckit_upstream.sh --bundle-self-test

# These assemble first and may require network
bash install_speckit_upstream.sh --doctor
bash install_speckit_upstream.sh --extract /tmp/speckit-upstream-source
bash install_speckit_upstream.sh --self-test
```

Extract into unused/empty directories. Upgrade source and assembled assets differ. Installed `speckit-workbench doctor` avoids the distribution's assembly stage. Embedded hashes detect damage, not publisher identity. Bundled tests, assembled tests, and real host/external-tool checks have distinct scope.

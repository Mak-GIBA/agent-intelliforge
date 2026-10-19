# Install, update, and remove Design Research

**English** | [日本語](../../design-research/installation.md)

[Documentation](../README.md) · [Overview](README.md) · [Usage](usage.md) · [Validation (Japanese)](../../design-research/validation.md)

## Requirements

Requires Linux / WSL2 / macOS, Bash, Python 3.11+, write access, and normally network access to pinned GitHub scripts. Harness execution needs authenticated Codex, a working command sandbox, and project-specific verification tools. Version 2.7.0 assembly/custom assets use the Python standard library; no GitHub login is needed. Codex, app dependencies, browsers, MCP, and other LLM API keys are not installed. macOS real-machine checks remain unperformed. Select Python with `PYTHON_BIN` if necessary.

Assembly failures were corrected on 2026-10-10, followed by offline builds, both self-tests, and machine update/diagnosis. See [separate validation scopes (Japanese)](../../design-research/validation.md).

## First installation

Download from the [README](../../../README.md#quick-start) and run in the script directory. **No arguments actually installs.**

```bash
# Preview assembly and installation first
bash install_design_research.sh --dry-run

# First installation
bash install_design_research.sh

# List distribution entry points
bash install_design_research.sh --list-skills
```

New user-wide Skills go in `~/.agents/skills/design-research/`. Check `$design-research` in a new session. `--list-skills` describes distribution entries, not installed state; `--version` describes the script version.

For project-local use, replace the absolute path:

```bash
bash install_design_research.sh --project /absolute/path/repo
```

New project placement is `PROJECT/.agents/skills/design-research/`. `--skills-dir PATH` selects a custom Skill parent. Repeat the destination on update/status/removal; `--project` and `--skills-dir` are mutually exclusive.

## Assembly and offline use

The distribution fetches both original installers at `d3f46e0d591b45cb2423317030a489b91566e891`, checks SHA-256, applies bundled upgrades, builds both tools, and installs the selected one. Even distribution `--status`/`--doctor` first assembles and may use network. `--dry-run` only previews: no downloads, destination changes, or existing-install inspection, and thus no proof installation will succeed.

To emit ordinary redistributable installers into empty/unused storage:

```bash
bash install_design_research.sh --build-only ./offline-installers
```

Success emits both scripts and logs without installing them. The built Research installer itself installs without network; actual source research needs separate access. For network-free assembly, provide both unchanged original scripts at the pinned commit, not an old upgrade wrapper:

```bash
bash install_design_research.sh \
  --base-dir /absolute/path/pinned-base --offline --build-only ./offline-installers

# Install from the successfully generated script
bash ./offline-installers/install_design_research.sh --update
```

`--offline` requires `--base-dir`. Generated Upstream can skip SpecKit CLI download with `--skip-specify`; setting that flag on the distribution wrapper alone does not skip pinned-base retrieval.

## Update an existing version

```bash
bash install_design_research.sh --dry-run --update
bash install_design_research.sh --update
```

Normal reruns keep the existing owned Skill. `--update` is explicit. A single existing legacy user/project `.codex/skills` or `CODEX_HOME/skills` location is reused without moving/duplicating it. Multiple candidates need a selected parent via `--skills-dir`.

Edits/missing/extra files stop ordinary update/removal. After review, `--update --force` copies and hash-checks the complete old directory before switching. Local edits/additions remain in backup and are not automatically merged into the new version. Unmanaged same-name directories are never overwritten.

Updates back up/retire 2.3.0's five shortcuts only when unchanged/owned; keep edited/unmanaged ones. The current entry is `$design-research`. Existing research/run records remain unless [explicitly migrated](usage.md#migrate-older-material-into-one-report).

## Status and diagnosis

```bash
bash install_design_research.sh --status --json
bash install_design_research.sh --doctor --json
```

For offline diagnosis use built ordinary installers or `--base-dir PATH --offline`. Check `state: "installed"`, `version: "2.7.0"`, `modified: false`. New 2.5.0 runs add saved responsibility stages, post-measurement explanation, and itemized review alongside metric contracts; existing run contracts/archives/edit protection remain. Ordinary update handles unchanged managed assets. No MCP/model/hook settings change.

2.6.0 separates new topics' local execution records from published reports and adds export/verification of selected evidence. See [outputs and review order](../upstream-research-workflow.md). Existing topics and earlier execution contracts are preserved.

`absent` means missing, `unmanaged` unknown ownership; extra files count as changes except Python caches. Status can exit normally for absent installation, so do not infer installed from exit alone.

| Doctor field | Meaning |
|---|---|
| `installed_integrity` | Ownership/hash integrity |
| `installed_harness_ready` | Current harness assets present |
| `harness_environment_ready` | Codex structured-exec flags and sandbox launch |
| `ready` | Assets and runtime ready |

Missing readiness returns 2. Diagnosis neither calls models nor academic APIs; authentication, model responses, real searches, and GUI dispatch are separate. Repair host sandbox support before retrying.

## Options

| Assembly option | Effect |
|---|---|
| `--help` / `-h`, `--version` | Help/distribution version |
| `--dry-run` | Preview only, no network or destination inspection |
| `--list-skills` | Distribution entries, not installed state |
| `--base-dir DIR` | Two specified original scripts |
| `--offline` | Prohibit base retrieval; needs local base |
| `--build-only DIR` | Emit both ordinary installers/logs, no install |
| `--extract-bundle DIR` | Offline upgrade sources/tests extraction |
| `--bundle-self-test` | Offline bundled contract tests |

Use `--list-skills`, `--build-only`, `--extract-bundle`, or `--bundle-self-test` individually, without install arguments. `--dry-run --build-only DIR` only previews generation.

| Forwarded option / variable | Effect |
|---|---|
| `--skills-dir PATH` / `--project PATH` | Custom/project placement |
| `--update` / `--force` | Update; explicitly back up edited owned assets before replacement/removal |
| `--uninstall` | Remove with backup |
| `--status` / `--doctor` | Installed state/environment |
| `--self-test` | Assembled installer tests |
| `--extract DIR` | Extract assembled Skill assets to unused/empty directory |
| `--print-mcp-config` | Optional TOML example, no registration |
| `--json` | JSON results except MCP's TOML |
| `PYTHON_BIN` | Python 3.11+, default `python3` |
| `CODEX_HOME` | Include its `skills` in legacy discovery |

Assembled modes are mutually exclusive; do not combine diagnosis/tests/extraction with updates/removal.

<a id="資材とバックアップ"></a>
<a id="展開して確認する解除する"></a>

## Assets, backups, and removal

Assets are under the selected parent's `design-research/`, verified by SHA-256. Ownership is `.design-research-install.json`. Backups are one level above the Skill parent at `.design-research-backups/<destination-id>/<time-and-id>/`, normally under `~/.agents/.design-research-backups/`. Switching stages beside the destination and restores on failure; backups can be copied across filesystems. Concurrent runs and symlinked destinations/parents are refused.

```bash
bash install_design_research.sh --dry-run --uninstall
bash install_design_research.sh --uninstall
```

After deliberate review, edited assets can use `--uninstall --force`. Research outputs, caches, and backups remain. No dedicated automatic restore command exists. Personal `config.toml`, hooks, MCP, and Workgraph settings are untouched.

<a id="困ったとき"></a>

## Troubleshoot and inspect assets

```bash
# Extract/check bundled upgrade assets without network
bash install_design_research.sh --extract-bundle /tmp/design-research-upgrade
bash install_design_research.sh --bundle-self-test
```

Use empty/unused extraction targets. `--extract-bundle` exposes upgrade source/tests; `--extract` exposes assembled assets. Root `tools/design-research/` alone cannot regenerate the current full distribution; see [maintenance](../development.md#design-research-embedded-assets).

Build-test failure stops before installation; inspect [results (Japanese)](../../design-research/validation.md). Check Python / `PYTHON_BIN`, network or local pinned originals, and original hashes when assembly fails. Multiple/unmanaged Skills need ownership inspection and explicit destination. Preserve/review edits before considering force. Retained old shortcuts do not change the current entry. Missing candidates need actual `SKILL.md` placement/new session checks. For execution stops, see [resumption](usage.md#stop-and-resume).

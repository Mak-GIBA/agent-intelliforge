# Install, update, and remove Workgraph

**English** | [日本語](../../basic-memory-workgraph/installation.md)

[Overview](README.md) · [Usage](usage.md) · [Sharing](sharing.md) · [Reference](reference.md) · [Troubleshooting](troubleshooting.md) · [Documentation](../README.md)

Run terminal examples at the repository root unless stated otherwise. Conversation examples go in Codex.

## Before running

Use the complete repository. **First installation without arguments writes to your environment.** There is no initial-install dry run; `--dry-run` is available with `--update`. Codex Plugin installation support and network access are required.

| Prepared component | Behavior |
|---|---|
| uv / uvx | Fetch/run Astral's installer if missing; may expose uvx matching existing uv |
| Python 3.12 | `uv python install 3.12` |
| Basic Memory | uv tool installation; try upgrading an existing version and potentially reinstall with prereleases if hooks are unsupported |
| Official Plugin | `bm install codex`, otherwise Codex marketplace commands |
| Workgraph | Place this repository's code, policy, and schemas |

Initial Basic Memory/Plugin versions are not pinned. Network sources include Astral, Python/package distributions, and Plugin sources. `--update` refreshes local Workgraph assets, not external packages. See [file layout](reference.md). A managed common AGENTS block routes sharing requests to the guide, but installation neither configures a sharing destination nor sends data. GitHub sharing separately needs git, gh, and login. Initial installation has no global rollback; earlier external installations may remain after failure.

<a id="start"></a>

## First installation

Requires Linux / WSL2 with Codex CLI, Python 3, and curl. Clone, or enter your existing checkout:

```bash
git clone https://github.com/Mak-GIBA/agent-intelliforge.git
cd agent-intelliforge
bash install_basic_memory_workgraph.sh
```

The installer prepares uv/uvx, Basic Memory, the official Codex Plugin, a storage project, schemas, settings, and extra hooks. ECC settings remain unchanged.

| Initial setting | Default |
|---|---|
| Basic Memory project | `codex-memory` |
| Markdown directory | `~/knowledge/codex-memory/` |
| Codex home | `~/.codex/`, or `CODEX_HOME` |
| Reusable-knowledge evaluation | `smart`: evaluate when a candidate exists |
| Automatic Correction capture | `off`: explicit requests only |
| Automatic Case capture | `off`: explicit requests only |
| Skill packaging | `review`: assess only, no automatic registration |
| Sharing / training | Neither authorized |

Set project and directory together for a different new destination:

```bash
MEMORY_PROJECT=work-memory \
MEMORY_DIR="$HOME/knowledge/work-memory" \
bash install_basic_memory_workgraph.sh
```

For an existing installation, use [update](#update). Ordinary installation with omitted storage arguments uses the defaults above.

### Verify in Codex

Start a new session and inspect `/plugins` for `codex@basic-memory`. In `/hooks`, check `basic_memory_workgraph.py recall` (UserPromptSubmit) and `basic_memory_workgraph.py save` (Stop), applying required trust settings. Restart Codex if needed. A Stop gating check alone does not announce active capture evaluation. Continue with [daily use](usage.md#daily).

<a id="python-tools"></a>

### Prepare Python for updates, exports, and Skill registration

`--update`, sharing/JSONL/registration, and local memory retrieval need PyYAML. Placing configuration files uses the standard library; retrieval runtime validation is separate.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r tools/basic-memory-workgraph/requirements-export.txt
source .venv/bin/activate
python3 -c 'import yaml; print(yaml.__version__)'
```

Activate this environment for later examples. In another terminal, return to the repository and rerun `source .venv/bin/activate`. If venv is unavailable, prepare your OS's Python venv support. The Python used for automatic Skill registration must also be able to import PyYAML.

<a id="recall-runtime"></a>

### Bind a retrieval runtime

First installation checks the Basic Memory executable and its Python environment. For an existing installation, bind an installed compatible executable by absolute path:

```bash
BM_RECALL_CLI="/absolute/path/to/basic-memory" \
bash install_basic_memory_workgraph.sh --configure-only
```

`--update` accepts the same environment variable; the configuration helper also accepts `--recall-cli`. Omitting it preserves the existing binding. Configuration checks the executable version and PyYAML before writing, rolling back modified configuration files on write failure. Binding does not upgrade Basic Memory or migrate its database.

Local projects read registered Markdown directly. Cloud projects use the bound CLI and report connection failures as unavailable. `workgraph_recall.py doctor` checks execution; `prepare --mode plan` checks project retrieval. A successful version check alone does not prove retrieval works.

<a id="update"></a>

## Update

Updating has two stages: obtain revised code, then apply it. The update command itself performs no Git operations or downloads.

### Obtain revised code

```bash
git status --short
```

If clean and you want the published revision:

```bash
git pull --ff-only
```

Inspect and preserve uncommitted changes first. Skip Git retrieval when applying local edits; without Git, place the complete revised repository yourself.

### Preview and apply

Prepare [Python](#python-tools) once, then run:

```bash
source .venv/bin/activate

# Preview updates without writing
bash install_basic_memory_workgraph.sh --update --dry-run

# Apply updates
bash install_basic_memory_workgraph.sh --update
```

The updater detects the existing destination from `primaryProject` and Basic Memory registration. It updates configuration, hooks, CLI, references, schemas, and graph index while retaining capture modes, other hooks, and normal notes. It does not upgrade Basic Memory or external Plugins. Open a new Codex session afterward.

### Read update results

| JSON field | Meaning |
|---|---|
| `dry_run` | `true` means inspection only |
| `project` / `memory_dir` | Detected target |
| `configuration` | Storage and modes to apply |
| `changed` | Updated files, or planned files during preview |
| `preserved` | Schemas/indexes retained without overwrite, with reasons |

`changed: []` means no update was needed. Check `echo $?`: 0 means success/no change; 1 means input, dependency, or processing error; 2 means customized files were preserved. **Exit 2 is not total update failure:** safe changes are applied while edited schemas/indexes remain. Dry run changes nothing.

`preserved.path` is the current file; `template` is the revised reference. Keep customizations or merge needed definitions manually. There is no force-overwrite option. Prior files are backed up as `.bak.*`; write failures restore changed files and retain backups. Identical reruns do not create more backups.

| Purpose | Command | Schema handling |
|---|---|---|
| Initial install | `bash install_basic_memory_workgraph.sh` | Create/update |
| Existing installation update | `bash install_basic_memory_workgraph.sh --update` | Migrate known old versions safely |
| Modes, policy, hooks only | `bash install_basic_memory_workgraph.sh --configure-only` | No schema changes |

<a id="update-details"></a>

### Update details

Basic Memory registration is read from the first matching configuration: `BASIC_MEMORY_CONFIG_DIR/config.json`, otherwise `XDG_CONFIG_HOME/basic-memory/config.json`, otherwise `~/.basic-memory/config.json`.

```bash
bash install_basic_memory_workgraph.sh --update \
  --basic-memory-config "/path/to/basic-memory/config.json" --dry-run
```

Use `MEMORY_PROJECT` / `--project` for another registered local project. `MEMORY_DIR` / `--memory-dir` must match its registered path. Unregistered, unknown, or cloud destinations are not guessed.

To update only schemas, specify the registered Markdown directory:

```bash
python3 tools/basic-memory-workgraph/install_schemas.py --memory-dir "$HOME/knowledge/codex-memory"
```

Managed YAML fields/body are compared against historical distributions. Basic Memory's `permalink`, dates, and unmanaged metadata remain intact. Definition changes, body edits, or potentially lossy comments are preserved and reported as customization. Current schemas are not reformatted. Ordinary installation uses the same migration.

<a id="uninstall"></a>

## Remove

```bash
bash tools/basic-memory-workgraph/remove_workgraph_hooks.sh
```

Removal deletes extra hooks, their configuration/state/CLI copies, and the shared-memory AGENTS block. GitHub profiles and import fingerprints are also removed; received notes and GitHub data remain. Back up needed configuration/state first: reconfiguring a nonempty destination without its import state will stop to avoid overwriting it.

Basic Memory, the official Plugin, notes, schemas, registered Skills and manifests, `basic-memory.json`, the common policy, and disabled automatic compaction checkpoints remain.

# Select and install kits

**English** | [日本語](../installation.md)

[Repository overview](../../README.md) · [Documentation](README.md)

[install_all.sh](../../install_all.sh) selects individual kits with `--only` or installs all of them. It calls their installers in order, so sources, destinations, and file protection differ by kit. Preview first, then apply with `--apply`. For native Windows, Claude Code, or the shared CLI, use [OS and host support](cross-platform.md). This Bash path retains the existing Codex installation model; Plugin migration is explicit.

## Requirements

Clone the complete repository: the bulk script alone lacks installers/assets. Installing all standard kits targets Linux / WSL2 and needs Bash, Python 3.11+ as `python3` with venv/pip, Node.js 20+/npm, Git, curl, installed Codex CLI, and network access to distributions. Updating Workgraph needs PyYAML in the same Python; see [Python setup](basic-memory-workgraph/installation.md#python-tools).

Codex must provide the required Plugin, MCP, and app-server commands. Individual selection needs only that kit's prerequisites. kotonoha alone prepares missing Python/Node.js user-locally. Design Research 2.5.0 / Upstream 2.0.6 builds require Python 3.11+. GitHub authentication, model login, and document rendering need the separate preparation described in each guide.

## Install

```bash
git clone https://github.com/Mak-GIBA/agent-intelliforge.git
cd agent-intelliforge
bash install_all.sh --list
bash install_all.sh --dry-run
bash install_all.sh --apply
```

No arguments / `--dry-run` displays commands without invoking individual installers, downloading, or writing to installation destinations. It does not verify prerequisite execution or network connectivity. `--apply` runs kits in this order:

| ID | Default operation | Details |
|---|---|---|
| `workgraph` | Basic Memory, official Plugin, Workgraph/hooks/project; existing installation uses settings-preserving `--update` | [Guide](basic-memory-workgraph/installation.md) |
| `ux-stack` | OOUI, cognitive guidance, visual UX verification, Product Design / Build Web Apps, browser tools | [Guide](codex-ux-stack/installation.md) |
| `speckit` | Build/verify both research tools from pinned base, install SpecKit CLI and Workbench/Skills | [Guide](speckit-upstream/installation.md) |
| `github-pm` | Skill and common Codex guidance; gh is separately selected | [Guide](codex-github-pm/installation.md) |
| `design-research` | Build/verify both distributions, install research Skill/harness | [Guide](design-research/installation.md) |
| `ecc` | Native ECC originals and on-demand entries | [Guide](codex-ecc/installation.md) |
| `office` | OfficeCLI, document libraries, Workbench | [Guide](codex-office/installation.md) |
| `kotonoha` (`yomiyasu` compatible) | Integrated Japanese workflow plus missing Python/Node.js/lint environment | [Guide](codex-yomiyasu/installation.md) |
| `herdr` | Herdr, wrapper, Bash integration | [Guide](herdr/installation.md) |

UX Stack recommends kotonoha for Japanese copy. Both are included in all-kits installation; select them together with:

```bash
bash install_all.sh --only ux-stack,kotonoha --dry-run
bash install_all.sh --only ux-stack,kotonoha --apply
```

`--only` accepts comma-separated names or repeated flags; duplicate IDs collapse and execution follows table order. Asset paths are based on the script location, so absolute invocation from another directory works.

Upstream and Design Research must each be selected; neither installs the other:

```bash
bash install_all.sh --only speckit,design-research,kotonoha --dry-run
bash install_all.sh --only speckit,design-research,kotonoha --apply
```

Both distributions normally fetch/verify pinned original installers and build them. Bulk installation does not forward `--base-dir`, `--offline`, or `--build-only`. Use the [Research](design-research/installation.md#assembly-and-offline-use) / [Upstream](speckit-upstream/installation.md#assembly-and-offline-use) procedures for offline builds/redistribution. See [validation (Japanese)](../design-research/validation.md) for build/update/diagnosis results and earlier stopping conditions.

## Rerun, update, and remove

Individual protection rules control existing settings and edits; bulk installation never forwards `--force`. Existing Workgraph is detected under `CODEX_HOME`, default `~/.codex`, and updated while preserving project/modes. This path does not upgrade Basic Memory or external Plugins, or fall back to first-install reset for incomplete state.

Other kits use their normal installation paths; rerunning all kits is not a guarantee of upgrading every kit. Design Research updates need individual `--update`, Upstream `--apply --update`. Select versions, optional features, custom destinations, and removal through each guide. Herdr has no uninstall switch; remove its managed Bash integration manually. Optional Office MCP, Docling, and OS packages are not selected by the bulk wrapper.

## Partial failure

The wrapper checks selected scripts/assets before starting. If one fails, it continues the rest and reports each outcome and unfinished count. There is no global rollback of successful installs. Fix the cause and rerun all or select the failed ID. An individual interruption code 130/143 stops later installers.

| Exit | Meaning |
|---|---|
| `0` | Preview/list/help complete, or every selected installation succeeded |
| `1` | One or more installs unfinished; inspect ID/logs |
| `2` | Invalid arguments or missing selected installer/assets; no install started |
| `130` / `143` | Interrupted; earlier completed work retained |

`COMPLETE` establishes installer completion, not real-session Skill selection, model quality, or finished apps/documents. Restart Codex and run the kit's diagnosis/first-use checks.

<p align="center">English | <a href="README.ja.md">日本語</a></p>

<p align="center">
  <img src="docs/assets/agent-intelliforge-logo.png" alt="Agent Intelliforge" width="960">
</p>

<h1 align="center">Agent Intelliforge</h1>

<p align="center"><strong>Purpose-built kits for research, design, implementation, and reusable knowledge in Codex.</strong></p>

<p align="center">
  <a href="docs/en/README.md"><img src="https://img.shields.io/badge/Codex-Skills_%26_Tooling-0f172a?style=flat-square" alt="Codex Skills &amp; Tooling"></a>
  <a href="docs/en/cross-platform.md"><img src="https://img.shields.io/badge/Platform-Linux_%2F_WSL2_%2F_Windows-475569?style=flat-square" alt="Linux / WSL2 / Windows"></a>
</p>

<p align="center"><a href="#quick-start">Get started</a> · <a href="#kits">Kits</a> · <a href="#workflow">Examples</a> · <a href="docs/en/README.md">Documentation</a></p>

---

Agent Intelliforge adds workflows and tools for research, design, verification, and document editing to Codex. Choose the kits you need for an existing project: clarify requirements, compare technical approaches, design and test screens, or manage work on GitHub. For Japanese writing, the custom kotonoha Skill combines meiseki and yomiyasu.

Codex is the primary host. Linux / WSL2 uses the existing Bash installers; native Windows and Claude Code have a separate Plugin installation path. Claude Code support is experimental.

Workgraph helps carry useful knowledge into later tasks. Codex reviews obstacles, verified workarounds, and user corrections, then evaluates whether to save them with their evidence and applicability conditions. The aim is to avoid repeating investigations and corrections. Settings control which kinds of knowledge can be saved.

<a id="quick-start"></a>
<a id="はじめに"></a>

## Get started

The standard bulk installer targets Linux / WSL2. Install the Codex CLI and check the [requirements and configuration changes](docs/en/installation.md#requirements). Individual guides describe each kit's OS, Python, and Node.js requirements.

```bash
git clone https://github.com/Mak-GIBA/agent-intelliforge.git
cd agent-intelliforge

# List available kits and preview execution
bash install_all.sh --list
bash install_all.sh --dry-run
```

To start with Japanese writing, install kotonoha. It also prepares missing Python, Node.js, and lint tools in a user-local environment.

```bash
bash install_all.sh --only kotonoha --apply
```

To add screen design and verification:

```bash
bash install_all.sh --only ux-stack,kotonoha --apply
```

`bash install_all.sh --apply` installs all kits. Without arguments, the bulk installer only previews the plan; `--apply` performs installation. Individual installers have different defaults, so read their guides before running them directly. See [rerunning, updating, and removing kits](docs/en/installation.md#rerun-update-and-remove).

### Shared CLI, Windows, and Claude Code

The `intelliforge` CLI selects a kit and host. On Linux / WSL2, Codex uses the existing installers. Native Windows and Claude Code use the hosts' official Plugin management commands. The shared CLI is distributed as a Python package.

```bash
# Run in the cloned repository; install CLI in an isolated uv tool environment
uv tool install .
intelliforge inspect --only kotonoha
intelliforge install --only kotonoha --apply

# Claude Code works without Codex (experimental)
intelliforge inspect --agent claude --only kotonoha
intelliforge install --agent claude --only kotonoha --apply
```

The standalone Japanese kit installer can also prepare Python: use `bash install_kotonoha.sh --apply`, or `.\install_kotonoha.ps1 --apply` on Windows.

Use PowerShell on Windows. Pass `--config core.longpaths=true` when cloning so Git can check out archived research files with long paths. `python intelliforge.py inspect` previews the plan, and `install_all.ps1` is another installation entry point. Plugin hooks and helpers require `intelliforge` on PATH.

```powershell
git clone --config core.longpaths=true https://github.com/Mak-GIBA/agent-intelliforge.git
cd agent-intelliforge
uv tool install .
intelliforge inspect --only kotonoha
intelliforge install --only kotonoha --apply
```

The maintained installation definitions are [`tools/*/kit.json`](tools). They expose Skill names, sources, dependencies, destinations, and configuration changes. Use `inspect --json` to inspect the selected path. Conflicts with existing Skills or hooks stop installation rather than triggering an automatic migration. See [OS and host support](docs/en/cross-platform.md) for details, updates, removal, and validation limits.

<a id="kits"></a>

## Kits by purpose

Follow a kit's link for its overview, installation, and examples. Use its ID with `install_all.sh --only`.

| ID | Kit | Purpose |
|---|---|---|
| `workgraph` | [Basic Memory Workgraph](docs/en/basic-memory-workgraph/README.md) | Save reusable knowledge from attempts, obstacles, verified workarounds, and contextual corrections. |
| `ux-stack` | [Codex UX Stack](docs/en/codex-ux-stack/README.md) | Design screens around objects and actions, then implement and review them with screenshots and browser operations. |
| `speckit` | [SpecKit Upstream](docs/en/speckit-upstream/README.md) | Turn goals, concerns, and use cases into requirements; integrate technical research into design and verification plans. |
| `github-pm` | [GitHub Project Director](docs/en/codex-github-pm/README.md) | Investigate and organize Issues, PRs, Projects, ownership, deadlines, dependencies, and progress through conversation. |
| `design-research` | [Design Research](docs/en/design-research/README.md) | Compare core approaches using primary sources and experiments, reporting conditions, results, and unverified claims. |
| `ecc` | [Codex ECC](docs/en/codex-ecc/README.md) | Keep ECC originals and read specialized Python, error-handling, and security procedures when needed. |
| `office` | [Office Workbench](docs/en/codex-office/README.md) | Read and edit PDF, Word, and PowerPoint files while protecting originals and checking differences and rendering. |
| `kotonoha` (compatible ID: `yomiyasu`) | [kotonoha and Japanese writing](docs/en/codex-yomiyasu/README.md) | Improve Japanese structure and explanations while preserving meaning and conditions. |
| `herdr` | [Herdr](docs/en/herdr/README.md) | Open or reuse the terminal workspace associated with the working directory. |

<a id="workflow"></a>

## After installation

Open the target project in Codex and enter a request in the conversation. These examples assume the corresponding kits are installed.

### Clarify what to build and how to verify it

```text
$upstream-new I want an app that searches internal documents and answers with supporting evidence. Organize the users, requirements, design, and verification plan.
```

### Compare approaches before choosing technology

```text
$design-research Compare ways to improve this project's search accuracy and test them under matching evaluation conditions.
```

### Explain a design clearly in Japanese

```text
$kotonoha Revise this design document in Japanese so readers can follow the mechanism and practical changes. Preserve technical terms and conditions.
```

Start with Upstream for overall requirements and design, or Design Research for a specific technical comparison. For a search app, integrate the research findings into the overall design and use UX Stack to check the search screens and interactions. Use kotonoha to finish Japanese design documents and reports.

Each kit also works independently. When combining them, follow the separate procedures for adopting research findings, approving designs, and implementing the app. See [upstream workflows](docs/en/speckit-upstream/usage.md) and [research workstreams and reassessment](docs/en/speckit-upstream/reassessment.md).

## Installation and operation

- **Start with what you need.** Select kits with `--only`. ECC procedures and additional kotonoha guidance are read only when relevant.
- **Inspect changes before applying them.** Guides describe sources, destinations, configuration handling, updates, and removal. Protection and optional features vary by kit.
- **Keep evidence of verification.** Self-tests, regression tests, and writing comparisons have documented conditions and limitations.

Installation success and output quality are evaluated separately. See [UX validation (Japanese)](docs/codex-ux-stack/validation.md), [research validation (Japanese)](docs/design-research/validation.md), and [Japanese writing evaluation](docs/codex-yomiyasu/validation.md).

## Before running agents in parallel

Consider expanding swap to reduce the risk of out-of-memory termination when builds, tests, and browser checks overlap. Swap moves some memory pages from RAM to disk; frequent swapping can slow work substantially. Also stagger expensive tests or other resource-heavy processes. [Red Hat's swap guide](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/managing_storage_devices/getting-started-with-swap)

Check current RAM and swap first. The 16 GiB below is an example; choose a size based on existing swap, concurrent workloads, and free disk space.

```bash
free -h
swapon --show
```

<details>
<summary>Linux: add a 16 GiB swap file</summary>

For Ubuntu and similar systems with an ext4 / XFS root filesystem. Check `df -h /` and leave sufficient free space after allocating 16 GiB. Existing swap is retained; the command stops if the target file already exists. Btrfs requires its [filesystem-specific procedure](https://btrfs.readthedocs.io/en/latest/Swapfile.html).

```bash
df -h /
findmnt -no FSTYPE /

sudo bash <<'SWAP'
set -eu
swapfile=/swapfile-agent-intelliforge
case "$(findmnt -no FSTYPE /)" in
  ext4|xfs) ;;
  *) echo 'This procedure requires ext4 / XFS.' >&2; exit 1 ;;
esac
if [ -e "$swapfile" ] || [ -L "$swapfile" ]; then
  echo "$swapfile already exists; stopping." >&2
  exit 1
fi
umask 077
dd if=/dev/zero of="$swapfile" bs=1M count=16384 status=progress
chmod 600 "$swapfile"
mkswap "$swapfile"
swapon "$swapfile"
# Keep enabled after reboot
if ! grep -qE '^/swapfile-agent-intelliforge[[:space:]]' /etc/fstab; then
  printf '%s\n' "$swapfile none swap defaults 0 0" >> /etc/fstab
fi
if [ -d /run/systemd/system ]; then
  systemctl daemon-reload
fi
SWAP

swapon --show
free -h
```

This follows the [swap-file setup procedure](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/managing_storage_devices/getting-started-with-swap).

</details>

<details>
<summary>WSL2: set swap to 16 GB</summary>

Open the configuration in Windows PowerShell. Ensure free space on the Windows disk that will hold the swap file.

```powershell
notepad "$env:USERPROFILE\.wslconfig"
```

Preserve existing settings and add or change only `swap` in the `[wsl2]` section. Add the section if it does not exist.

```ini
[wsl2]
swap=16GB
```

Save the file and all WSL work, then run this in PowerShell. It stops every WSL distribution.

```powershell
wsl --shutdown
```

Restart WSL and check `free -h` and `swapon --show` inside Linux. This setting applies to all WSL2 distributions. See [Microsoft's WSL configuration guide](https://learn.microsoft.com/en-us/windows/wsl/wsl-config#wslconfig).

</details>

## Documentation and development

| Topic | Guide |
|---|---|
| Requirements, selection, updates | [Bulk installation](docs/en/installation.md) |
| Kit-specific installation and examples | [Documentation index](docs/en/README.md) |
| Knowledge capture, sharing, and review | [Workgraph usage](docs/en/basic-memory-workgraph/usage.md), [GitHub sharing and prompts](docs/en/basic-memory-workgraph/github-sharing.md), [file sharing](docs/en/basic-memory-workgraph/sharing.md), [troubleshooting](docs/en/basic-memory-workgraph/troubleshooting.md) |
| Maintained sources, distribution builds, verification | [Development guide](docs/en/development.md) |

Root-level `install_*.sh` files are the existing installation entry points. The shared CLI lives in `src/agent_intelliforge/`, maintained sources and kit definitions in `tools/`, generated Plugins in `plugins/`, guides and evaluation material in `docs/`, and regression tests in `tests/`. Edit maintained sources and regenerate distribution files; see [distribution development](docs/en/cross-platform-development.md).

The bulk installer, Workgraph, and Codex ECC need the complete repository. Other kits can use their individual scripts alone. Design Research and Upstream fetch and verify a pinned base before building; offline use needs [advance preparation](docs/en/design-research/installation.md#assembly-and-offline-use).

This repository combines custom workflows and management tools with external Skills, Plugins, and CLIs. Codex, Basic Memory, SpecKit, ECC, Playwright, meiseki, and yomiyasu remain maintained by their respective providers. Kit guides identify their sources and distinguish upstream components from custom functionality.

## License

Original code and documentation in this repository are covered by [LICENSE](LICENSE), except where a separate license or attribution is provided. Third-party materials retain their respective licenses and copyright notices. See [third-party notices](THIRD_PARTY_NOTICES.md) for bundled materials and dependencies.

<a id="start"></a>
<a id="python-tools"></a>
<a id="update"></a>
<a id="daily"></a>
<a id="modes"></a>
<a id="correction-mode"></a>
<a id="progressive-mode"></a>
<a id="share"></a>
<a id="training"></a>
<a id="troubleshooting"></a>
<a id="audit"></a>
<a id="details"></a>
<a id="update-details"></a>
<a id="uninstall"></a>
<a id="development"></a>

For Workgraph setup, updates, settings, sharing, and troubleshooting, use the [Workgraph guide](docs/en/basic-memory-workgraph/README.md).

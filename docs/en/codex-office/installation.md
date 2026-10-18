# Install, update, and remove Office Workbench

**English** | [日本語](../../codex-office/installation.md)

[Overview](README.md) · [Usage](usage.md)

## Requirements and installation

The Bash installer primarily targets Linux / WSL2 with glibc on x86_64 or ARM64. A macOS download path exists but has not been tested on a real machine. Native Windows and Alpine are outside this Bash path; see the [shared CLI](../cross-platform.md) for the Windows Plugin path. Requires Bash, Python 3.11 or later, venv, pip, and an installed Codex. First installation connects to GitHub and PyPI.

```bash
bash install_codex_office.sh
bash install_codex_office.sh --apply
export PATH="$HOME/.local/bin:$PATH"
office-workbench doctor
```

The Skill is placed in `~/.agents/skills/office-workbench/` and the CLI in `~/.local/bin/office-workbench`. Application files, OfficeCLI, and venvs live in `${XDG_DATA_HOME:-~/.local/share}/codex-office/releases/`; management metadata lives in `${XDG_CONFIG_HOME:-~/.config}/codex-office/install.json`. Existing ECC, Basic Memory, hooks, AGENTS, and shell configuration are unchanged.

## Rendering and optional features

```bash
bash install_codex_office.sh --system-deps
bash install_codex_office.sh --install-system-deps --apply
```

`--system-deps` prints commands for missing rendering and font dependencies. `--install-system-deps --apply` installs OS packages on Ubuntu / Debian, using sudo when needed. Those OS changes are outside automatic rollback. Prepare dependencies through your own package manager on other systems. Fonts are not bundled.

| Option | Effect |
|---|---|
| `--with-mcp --apply` | Register `codex-office-workbench` with official `codex mcp add`; only this option changes Codex configuration |
| `--with-docling --apply` | Install Docling in a large separate venv; conversion may later fetch models |
| `--officecli /absolute/path/officecli --apply` | Reuse the specified binary without modifying or deleting it |

An existing MCP with the same name is not overwritten. Failed registration leaves the core installation in place and reports the unfinished MCP step. Installing Docling does not automatically run OCR or model processing.

## Update, remove, and inspect

```bash
bash install_codex_office.sh --apply --force
bash install_codex_office.sh --uninstall
bash install_codex_office.sh --uninstall --apply
bash install_codex_office.sh --self-test
bash install_codex_office.sh --extract /tmp/codex-office-review
```

Ordinary reruns retain the same configuration. Explicit updates build a new release and retain old releases and backups. `--force` still refuses edited managed files. Repeat flags for optional features you want in the rebuilt installation. Do not move `releases/` containing venvs.

If you added MCP, first remove your registration with `office-workbench mcp-disable --apply`. Uninstall removes managed entry points, the Skill, and metadata, while retaining documents, old releases, and backups.

Self-tests mock network and Codex; PDF tests are skipped if the real libraries are unavailable. `--extract` writes sources and `README_JA.md` to an empty or unused directory. `--assets-only --apply` is a network-free diagnostic mode that places entry assets only; without editing engines, it is not ready for document work.

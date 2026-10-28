# Shared CLI, operating systems, and hosts

**English** | [日本語](../cross-platform.md)

[README](../../README.md) · [Existing bulk path](installation.md) · [Validation (Japanese)](../cross-platform-validation.md)

`intelliforge` selects an installation path by OS/host, defaulting to Codex. Existing Linux / WSL2 installers remain; native Windows and Claude Code use Plugins. Claude is experimental and uses its own CLI/authentication without requiring Codex.

| Target | Path | Existing installations |
|---|---|---|
| Codex on Linux / WSL2 | Existing bulk/individual scripts | Names, defaults, configuration, ownership retained |
| Codex on Linux / WSL2 with `--plugin` | Official Plugin CLI, separate assets | Explicit opt-in; conflicts with Skills/hooks stop |
| Codex on native Windows | Official Plugin CLI, Python adapters | No automatic migration |
| Claude Code | Claude Plugin CLI, separate assets | Codex settings untouched; real-host/model checks unperformed |
| Herdr | CLI and directory wrapper | No Plugin; new path does not edit shell settings |

## Inspect before installing

Shared CLI requires Python 3.11+ and the chosen host's CLI. Windows Plugin installation does not require admin privileges, Bash, WSL, or Docker. The standalone Japanese installer can prepare missing Python/Node.js; that is separate from installing the shared CLI. Use [uv tool environments](https://docs.astral.sh/uv/guides/tools/); this package is not published to PyPI.

```bash
git clone https://github.com/Mak-GIBA/agent-intelliforge.git
cd agent-intelliforge
uv tool install .
intelliforge list
intelliforge inspect --only kotonoha --json
```

Build a standard wheel from the checkout. Package construction neither fetches kit dependencies nor updates host configuration. Source/generated mismatches stop construction.

`inspect`, and installation/update/removal without `--apply`, display definitions without networking, dependencies, or host Plugin CLI execution. Inspect [kit definitions](../../tools) and generated bulk-script comments for sources, Skills, dependencies, destinations, and settings.

## Install

Japanese writing uses `$kotonoha`. The kit ID and plugin name are also `kotonoha`; the former ID is retired. See [kotonoha](kotonoha/installation.md).

```bash
# Linux / WSL2: existing Codex path; host can be omitted
intelliforge install --only kotonoha --apply

# Explicitly select the Codex Plugin path
intelliforge install --agent codex --plugin --only kotonoha --apply

# Claude Code
intelliforge install --agent claude --only kotonoha --apply
```

PowerShell supports the same CLI, plus checkout entry points:

```powershell
git clone --config core.longpaths=true https://github.com/Mak-GIBA/agent-intelliforge.git
cd agent-intelliforge
uv tool install .
.\install_all.ps1 --only kotonoha
.\install_all.ps1 --only kotonoha --apply
```

`core.longpaths` is applied to the new clone only, before checkout, not Git's global settings; archived research has long paths. See [Git clone](https://git-scm.com/docs/git-clone).

Plugin hooks/Skills invoke `intelliforge` on PATH; installation checks its presence. Generated [Codex Plugins](https://developers.openai.com/plugins/build/plugins) and [Claude Plugins](https://code.claude.com/docs/en/plugins-reference) are registered through official host commands, from a managed local marketplace whose stable path survives package updates.

Select multiple kits with `--only ux-stack,design-research,kotonoha`; `--agent both` installs separate host assets. Each kit still needs its external prerequisites: gh/login for GitHub, LibreOffice/fonts for full Office rendering, and so on.

## Update, diagnose, remove

Update the checkout under your own Git workflow, then reinstall the CLI package and update kits:

```bash
uv tool install --force .
intelliforge update --agent claude --only kotonoha --apply
intelliforge doctor --agent claude --only kotonoha
intelliforge uninstall --agent claude --only kotonoha --apply
```

Codex Plugin management uses `--agent codex --plugin`. The default Linux path delegates updates to individual installers; unsupported operations are not guessed.

```bash
# Update upstream yomiyasu only; retain custom rules and auxiliary Skills
intelliforge update --agent claude --only kotonoha --upstream-only --apply
# Change automatic invocation permission
intelliforge update --agent claude --only kotonoha --mode explicit --apply
intelliforge update --agent claude --only kotonoha --mode auto --apply
# Locate installed assets and upstream originals
intelliforge locate --agent claude --only kotonoha
intelliforge locate --agent claude --only kotonoha --upstream
```

Updates verify ownership/hashes and refuse unmanaged/edited assets, symlinks/junctions, unsafe relative paths, or case-colliding names. Staging/backups allow asset restoration on placement/registration failures. Host CLI external state is not independently rewritten; inspect that host's list after failure. Removal detaches only managed assets while retaining backups, settings, upstreams, dependencies, notes, and research outputs.

## Execute research and UX evaluation

Existing Skill entries remain; Claude names include `/design-research:design-research`, `/ux-stack:ux-gan-harness`, and `/speckit:upstream-new`. Generated commands connect to shared dispatch:

```bash
intelliforge kit-run design-research --agent claude -- doctor --project <project>
intelliforge kit-run design-research --agent claude -- research --project <project> --brief "Approaches and constraints to compare" --slug comparison --allow-network
intelliforge kit-run ux-stack --agent claude -- audit --project <project> --url http://localhost:3000
intelliforge kit-run speckit --agent claude -- doctor --project <project>
```

Claude reuses role prompts, JSON schemas, budgets, and artifact checks, parsing structured `claude -p` output. Unstructured/failed executions cannot count as success. UX uses bundled Playwright rather than assuming another product's browser capability. Existing authorization, fact preservation, independent review, and evidence rules remain.

Native Windows Codex evaluation needs supported [Windows sandboxing](https://learn.chatgpt.com/docs/windows/windows-sandbox). Claude evaluation needs Node.js 24+ and pinned [Microsoft MXC SDK](https://github.com/microsoft/mxc), explicitly using Windows ProcessContainer, Linux Bubblewrap, or macOS Seatbelt. Missing OS/backend support stops rather than bypasses isolation. Windows CI does not prove Windows 11 isolation.

Use PowerShell syntax for Windows experiment commands; arbitrary Bash strings are not translated. Claude's [official PowerShell tool](https://code.claude.com/docs/en/env-vars) is enabled only inside child processes, not persistent settings. Native host executables are preferred; official npm `.cmd` layouts are resolved to their JavaScript entry through Node, never unknown batch shims.

```bash
# Test read-only isolation using temporary files, without model calls
intelliforge doctor --agent codex --only design-research --isolation-smoke
intelliforge doctor --agent claude --only design-research --isolation-smoke
```

## Kit-specific preparation

- **Japanese writing:** separate custom/upstream versions and locations; leave originals unchanged and verify release commit/blob/size through the original installer.
- **Workgraph:** retain original policy/templates, per-session turn IDs for Claude events, Plan write prohibition, explicit arming, one Stop evaluation. MCP requires `uvx`. Existing projects/notes are not migrated; project/schema setup is explicit.
- **ECC:** new paths read official tag/commit-recorded originals when needed; existing Codex keeps native ECC management. No mass enabling of Skills or arbitrary MCPs.
- **Office:** pinned OfficeCLI and original Python requirements, verified Windows x64/ARM64 hashes. MCP, Docling, and system renderers remain optional.
- **Herdr:** reuse existing executable; on Windows x64, missing binaries use pinned verified official ZIP. Use `intelliforge kit-run herdr --agent <host> -- <directory>`; unknown session formats stop.

Full native-Windows and Claude real-model workflows remain untested in this environment. Distinguish [recorded checks from remaining validation (Japanese)](../cross-platform-validation.md).

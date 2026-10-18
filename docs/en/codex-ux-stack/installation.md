# Install, update, and remove UX Stack

**English** | [日本語](../../codex-ux-stack/installation.md)

[Overview](README.md) · [Usage](usage.md) · [Validation (Japanese)](../../codex-ux-stack/validation.md) · [Documentation](../README.md)

## Requirements and installation

This Bash path needs Linux / WSL2, Bash, Python 3.10+, Node.js 20+, npm, and authenticated Codex with structured exec output, Plugin, and MCP support. Harness execution also needs Git, Chromium OS libraries, and a working Codex sandbox.

Run from the repository root or copy the standalone script:

~~~bash
bash install_codex_ux_stack.sh --help
bash install_codex_ux_stack.sh --dry-run
bash install_codex_ux_stack.sh
bash install_codex_ux_stack.sh --doctor
~~~

**No arguments installs.** `--dry-run` only previews without downloads, registrations, or destination writes. Installation does not log in, add app dependencies, or migrate data.

## Options

| Option | Behavior |
|---|---|
| None | Install missing standard components |
| `--deep` | Also install pinned ux-critique |
| `--force` | Replace/re-register unchanged owned assets |
| `--dry-run` | Preview install/removal |
| `--status` | Inspect files/registration without browser launch |
| `--doctor` | Also test Chromium and Codex sandbox |
| `--uninstall` | Remove unchanged owned assets only |
| `--extract PATH` | Extract to empty/unused directory, without installation |
| `--codex-home PATH` | Codex configuration/runtime destination |
| `--skills-root PATH` | New Skills destination |
| `--bin-dir PATH` | Launcher destination |
| `--no-browser-download` | Skip Chromium download; readiness remains separate |
| `--help` / `-h` | Help |

Existing Skills are checked in the specified location, Codex Skills, and `~/.agents/skills` to avoid duplicates. Unmanaged/edited assets are preserved even with `--force`. Disabled Plugins are not silently enabled; the cause is reported.

## Sources, versions, and destinations

| Asset | Version/source | New destination |
|---|---|---|
| ooui-design/references | Bundled 1.1.2 OOUI/cognitive guidance | `~/.agents/skills/ooui-design/` |
| Product Design / Build Web Apps | Codex-managed `openai-curated-remote`; actual versions recorded | Codex Plugin environment |
| web-design-guidelines | `vercel-labs/agent-skills`, `063bee94c3f4df8453406c830b0a7df0f2860278` | `~/.agents/skills/web-design-guidelines/` |
| ux-critique | `Thecsiz/ux-critique`, `3da293cafb639195bf71797590081d4ffb0045ba` | `~/.agents/skills/ux-critique/` |
| Harness/Skill/shared guidance | Bundled 1.1.2 | `~/.agents/skills/ux-gan-harness/` |
| Browser runtime | Playwright 1.63.0 / MCP 0.0.83, embedded lockfile | `CODEX_HOME/ux-stack/runtime/` |
| Launcher | Calls bundled Bash harness | `~/.local/bin/ux-gan-harness` |
| State/backups | Hashes, versions, outcomes, previous files | `CODEX_HOME/ux-stack/` |

`CODEX_HOME` defaults to `~/.codex`. Chromium uses Playwright cache or `PLAYWRIGHT_BROWSERS_PATH`. The default MCP uses a pinned Node entry and downloaded Chromium path; existing MCP settings are protected. Assets are checked before placement; previous files are saved under `backups/`.

There is no `skills@latest` dependency. Sources are defined in [sources.json](../../../tools/codex-ux-stack/sources.json), browser dependencies in the [lockfile](../../../tools/codex-ux-stack/browser/package-lock.json). Upstream licenses/references are retained; absent licenses are recorded in `UPSTREAM_SOURCE.json`.

ooui-design and harness receive the same maintained guidance. The harness carries its own references rather than depending on another Skill's path. Japanese writing uses separately installed kotonoha or existing yomiyasu. Current `status`/`doctor` reports compatibility-entry yomiyasu availability; absence does not fail UX installation. Existing Memory is read only; unavailable Memory does not block work or trigger setup.

## Update and verify

~~~bash
bash install_codex_ux_stack.sh --status
bash install_codex_ux_stack.sh --doctor
bash install_codex_ux_stack.sh
bash install_codex_ux_stack.sh --force
bash install_codex_ux_stack.sh --deep --force
~~~

Use `--force` to update 1.0.0 / 1.1.0. No arguments adds missing ooui-design but retains an existing unchanged harness. Diagnosis checks new references and reports old harness assets as unready. Unmanaged/edited same-name Skills remain protected.

Per-component output is `INSTALLED`, `SKIP`, or `FAILED`. Failure returns exit 1 / `INCOMPLETE`; earlier components remain and can be retried. There is no global Plugin/MCP rollback. Failed file replacement restores its immediately previous assets. `COMPLETE` means install operations ended, not model/app/browser success. Restart Codex if `$ooui-design` / `$ux-gan-harness` is absent; an absolute launcher path works outside PATH.

## Remove and recover

~~~bash
bash install_codex_ux_stack.sh --uninstall --dry-run
bash install_codex_ux_stack.sh --uninstall
~~~

Remove only unchanged owned items. Preexisting or edited assets/configuration, app outputs, browser cache, and backups remain. Browser runtime is protected if retained dependents need it; incomplete removal is reported. To reconcile manual edits, compare destination, `manifest.json`, and backups; preserve edits elsewhere before clearing/reinstalling a destination and reapplying needed changes.

<a id="troubleshooting"></a>

## Troubleshooting

| Problem | Action |
|---|---|
| Missing Plugin | `codex plugin list --available --json` |
| Missing Skill candidate | Inspect destination and disabled settings |
| Missing/old design references | `--force` for unchanged owned assets; preserve custom Skill content first |
| Chromium failure | Diagnose and prepare Playwright OS libraries |
| Existing custom MCP retained | Inspect it; harness may log failure and use local fallback |
| bwrap / namespace denial | Repair host sandbox support; do not bypass isolation |
| Manual-edit refusal | Compare hashes/content and preserve edits before updating |
| Download/npm failure | Existing assets remain; fix cause and rerun |
| Launcher missing | Run `~/.local/bin/ux-gan-harness doctor` or add its bin directory to PATH |

References: [Codex noninteractive](https://developers.openai.com/codex/noninteractive/), [Skills](https://developers.openai.com/codex/skills/), [Playwright MCP](https://github.com/microsoft/playwright-mcp), [Linux sandbox](https://github.com/openai/codex/blob/main/codex-rs/linux-sandbox/README.md).

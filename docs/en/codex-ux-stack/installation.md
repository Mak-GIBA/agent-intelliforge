# Install, update, and remove UX Stack

**English** | [日本語](../../codex-ux-stack/installation.md)

[Overview](README.md) · [Usage](usage.md) · [Validation (Japanese)](../../codex-ux-stack/validation.md) · [Documentation](../README.md)

## Update managed components only

```bash
bash install_codex_ux_stack.sh --update
ux-gan-harness doctor --project /path/to/app --check-mcp
```

`--update` updates managed components and adds the new bundled Core Skill, `ux-visual-design`.
It does not add missing Plugins, external MCP servers or optional Skills, or restore removed/disabled servers.
Previous versions are backed up; manual edits and unmanaged same-name resources remain protected.
No arguments still installs; `--force` can add missing components.

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
| `--visual-tools whimsical,figma` | Register selected official Remote MCP; preserve manual/disabled settings; authenticate separately |
| `--doctor --check-design-mcp` | Diagnose connection, authentication and advertised capabilities without external writes |
| `--update` | Update existing managed components without adding missing Plugins/MCP |
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
| ooui-design/references | Bundled 1.4.0 OOUI/cognitive guidance | `~/.agents/skills/ooui-design/` |
| ux-visual-design | Bundled 1.4.0 Skill, contracts, editable output and MCP helper | `~/.agents/skills/ux-visual-design/` |
| Product Design / Build Web Apps | Codex-managed `openai-curated-remote`; actual versions recorded | Codex Plugin environment |
| web-design-guidelines | `vercel-labs/agent-skills`, `063bee94c3f4df8453406c830b0a7df0f2860278` | `~/.agents/skills/web-design-guidelines/` |
| ux-critique | `Thecsiz/ux-critique`, `3da293cafb639195bf71797590081d4ffb0045ba` | `~/.agents/skills/ux-critique/` |
| Harness/Skill/shared guidance | Bundled 1.4.0 | `~/.agents/skills/ux-gan-harness/` |
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

Use `--update` to update existing managed components only. No arguments adds missing ooui-design but retains an existing unchanged harness. Diagnosis checks new references and reports old harness assets as unready. Unmanaged/edited same-name Skills remain protected.

Per-component output is `INSTALLED`, `SKIP`, or `FAILED`. Failure returns exit 1 / `INCOMPLETE`; earlier components remain and can be retried. There is no global Plugin/MCP rollback. Failed file replacement restores its immediately previous assets. `COMPLETE` means install operations ended, not model/app/browser success. Restart Codex if `$ooui-design` / `$ux-gan-harness` is absent; an absolute launcher path works outside PATH.

## Optional design MCP

```bash
bash install_codex_ux_stack.sh --visual-tools whimsical,figma
codex mcp login whimsical
codex mcp login figma
bash install_codex_ux_stack.sh --doctor --check-design-mcp
```

Official URLs are `https://mcp.whimsical.com/mcp` and `https://mcp.figma.com/mcp`.
Registration uses the native Codex app-server configuration API and changes only selected entries.
Registration and OAuth are separate. If diagnosis reports an existing alternate registration name,
use it with `codex mcp login`. Credentials remain in the native host and out of the install manifest.

Status does not connect and reports `not_probed`. Doctor distinguishes missing configuration,
connection failure, required authentication, advertised tools and target write access.
It never writes to an external design, so `write_permission: not_tested` is expected.
Runtime discovery uses names, descriptions and schemas rather than assuming legacy names.
Limit writes to requested files/frames/nodes; code-based Figma tools use the official host Skill.

Core remains installed after optional setup failure. `design_mcp_pending` records retryable state.
If registration succeeded but verification was interrupted, a rerun reuses the entry without
assuming ownership; it remains on uninstall. Manual and edited entries are protected.
`core_ready` and `design_mcp_ready` are independent. Update never adds an unowned provider.

The additional distribution supports
`intelliforge install --only ux-stack --agent codex --plugin --visual-tools whimsical,figma --apply` and
`intelliforge doctor --only ux-stack --agent codex --plugin --check-design-mcp`.
Omit `--apply` or use `--dry-run` for a nonmutating preview. Codex-specific registration is rejected for Claude.

Official instructions: [Whimsical](https://whimsical.com/integrations/codex),
[Figma Remote MCP](https://developers.figma.com/docs/figma-mcp-server/remote-server-installation/),
[Codex MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

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

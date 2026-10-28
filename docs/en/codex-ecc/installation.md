# Install, update, and restore ECC

**English** | [日本語](../../codex-ecc/installation.md)

[Overview](README.md) · [Usage](usage.md)

## Requirements

Requires Linux / WSL2, Bash, Python 3.11 or later as `python3`, Git, and a Codex CLI with `codex plugin` and `codex app-server`. First installation and updates need access to ECC's distribution source. Use the complete repository; the shell script alone is insufficient. Codex, Python, and Git are not installed for you. Run examples at the repository root.

## First installation

**No arguments previews the plan without network or configuration changes.**

```bash
bash install_ecc.sh
bash install_ecc.sh --apply
bash install_ecc.sh --doctor
```

The installer checks local configuration and same-name Skills, then queries Codex's ECC registration and installation. If missing, it registers `affaan-m/ECC` and installs `ecc@ecc`. Existing originals are reused. Normal application does not explicitly upgrade the marketplace; Codex manages versions and cache.

It then sets ECC's enabled flag to `false`, places the entry Skills and management CLI, and diagnoses them. On first installation, independent Firecrawl and Chrome DevTools MCPs are added by default. Same-name existing entries, disabled entries, and the old `context7-mcp` name are retained without duplicate registration. Hooks are not automatically trusted.

stdio MCPs need Node.js and `npx`, and fetch npm packages on first start. Firecrawl provides web search and page extraction; Chrome DevTools provides browser diagnostics. This selection is not evidence of better accuracy than existing tools. Firecrawl was not included in the earlier comparative trials.

Firecrawl uses the [official keyless hosted endpoint](https://github.com/firecrawl/firecrawl-mcp-server#hosted-mcp-keyless-free-tier), `https://mcp.firecrawl.dev/v2/mcp`. Search, scrape, and parse are available with rate limits. Site crawling (`crawl`) and URL discovery (`map`) require authentication.

| Selection | Candidates | Intended use |
|---|---|---|
| `recommended` | Firecrawl, Chrome DevTools | Web search, page extraction, and browser diagnostics; first-install default |
| `research` | Context7, Parallel Search | Documentation and web research; unnecessary if existing search is sufficient |
| `browser` | Playwright, Chrome DevTools | UI interaction, console/network inspection, performance |
| `cloudflare` | Context7, Cloudflare Docs | Official Cloudflare documentation |
| `none` | No new MCPs | Use ECC Skills only; retain existing MCPs |

```bash
# Preview without network or changes first
bash install_ecc.sh --mcps recommended,browser,cloudflare
# Select connections on first application or an installed-environment update
bash install_ecc.sh --apply --mcps recommended,browser,cloudflare
bash install_ecc.sh --update --apply --mcps research
```

Names are `firecrawl`, `context7`, `playwright`, `chrome-devtools`, `parallel-search`, `cloudflare-docs`, and `sequential-thinking`. Combine presets and names with commas; duplicates are collapsed. `none` cannot be combined. Unknown names fail before configuration changes or ECC downloads.

Sequential Thinking is opt-in only. In the limited 6-question × 2-trial comparison, both conditions answered 12/12 correctly, while mean processing time rose from 29.176 to 51.7875 seconds; the criterion for routine use was not met. This does not rule out benefits on other tasks.

Token Optimizer is not registered. It reduced returned text when rereading within a conversation, but failed twice to retrieve important values in a new conversation without the prior body. The measured package was `@ooples/token-optimizer-mcp@7.4.3`, distinct from the unversioned ECC catalog package. Returned-text volume does not establish billing savings or accuracy improvements. See [conditions, outputs, and selection rationale (Japanese)](../../codex-ecc/mcp-evaluation.md).

New stdio packages use measured, pinned versions; reevaluate before upgrading their registration definitions. New Playwright and Chrome DevTools entries use headless isolated profiles. Chrome DevTools disables usage statistics and CrUX URL queries. New entries forward `HTTP_PROXY`, `HTTPS_PROXY`, and `NO_PROXY` from the launch environment without storing their values. Existing connections are not changed. A usable browser is required; neither browsers nor Node.js are installed here. Cloudflare Docs and Parallel Search use URL connections. Public search worked without authentication in the recorded test; service limits and future authentication requirements remain the providers' responsibility. GitHub uses an existing official integration or `gh`; Jira and Confluence are not automatically registered.

## Options

| Option | Behavior / default |
|---|---|
| `--apply` | Apply installation, updates, or restoration |
| `--dry-run` | Preview; also the no-argument default |
| `--doctor` | Inspect placement, managed files, original resolution, and disabled state |
| `--update` | Update ECC and management assets in an already managed installation |
| `--mcps SELECTION` | First-install default `recommended`; otherwise reuse the saved selection |
| `--restore` | Restore managed configuration and entry points; keep ECC itself |
| `--json` | JSON output |
| `--codex-home PATH` | `CODEX_HOME`, otherwise `~/.codex` |
| `--skills-root PATH` | Default `~/.agents/skills` |
| `--codex COMMAND` | Default `codex` |
| `--cwd PATH` | Resolution / diagnosis directory; default current directory |

`--apply` and `--dry-run` are mutually exclusive. `--doctor`, `--update`, and `--restore` are mutually exclusive. Do not combine `--doctor` with `--apply`, or `--mcps` with diagnosis/restoration. Reuse custom paths for every subsequent operation.

Preview checks local configuration and files only. Actual source/version queries happen during application. Diagnosis uses an independent app-server without starting a conversation or model processing; Codex may retrieve metadata.

## Placement and configuration

Originals stay in Codex's Plugin cache; their path is not fixed. `config.toml` contains `[plugins."ecc@ecc"]` with `enabled = false`. Entry Skills use the user Skill directory. The CLI, state, and owner-only backups live under `${CODEX_HOME:-~/.codex}/ecc-on-demand/`. Existing TOML comments and unrelated configuration are retained. Independent MCP selection is recorded for later application; changing to `none` does not remove existing connections, including older managed Sequential Thinking entries. When older state has no selection, new candidates default to `recommended` while prior restoration metadata remains. Backups are `config.before-ecc-on-demand.<id>.toml` with owner-only permissions. MCP diagnosis checks configuration, not launch/authentication/search success. Inline-table/dotted-key ECC settings require manual conversion to a normal `[plugins."ecc@ecc"]` table before editing. Basic Memory, independent MCPs, other Plugins, and Skill-list limits are retained.

## Updates and recovery

```bash
bash install_ecc.sh --update
bash install_ecc.sh --update --apply
```

Updates use `plugin marketplace upgrade ecc` and `plugin add ecc@ecc`, then refresh management assets from the repository. Edited managed files stop processing. Earlier management-only installations retain their restoration metadata.

Backups are created before installation/update changes. Failures restore ECC's disabled flag and report the cause and backup path. First-install recovery metadata is retained in `bootstrap.json`; a successful `--apply` retry continues from it. Retry failed updates with `--update --apply`. Do not delete recovery metadata or backups manually. A new session is needed; the shared daemon is not restarted. The local catalog seen by `--doctor` may differ from a real session containing remote Plugins.

## Restore

```bash
bash install_ecc.sh --restore
bash install_ecc.sh --restore --apply
```

An ECC installation that existed beforehand returns to its originally recorded enabled value; this can resume bulk registration and startup hooks. If this installer originally installed ECC, it leaves the originals present but disabled. Managed entry points and the CLI are removed, while unrelated later configuration, backups, ECC, the marketplace, and hook trust are preserved.

Unchanged managed MCP entries are removed; preexisting connections remain. Edited managed files, MCP credentials/arguments, or enabled values cause a stop rather than being discarded. If initial installation failed before creating management state, first complete `--apply` successfully.

## Troubleshooting

| Symptom | Check |
|---|---|
| Missing Codex commands | `codex plugin --help`, `codex app-server --help` |
| `ecc` marketplace belongs to another provider | Inspect `codex plugin marketplace list --json`; it is not replaced |
| No `ecc@ecc` in catalog | Inspect the original error and `codex plugin list --available --json`; do not substitute another Plugin |
| Same-name Skill or manual edits | Preserve and reconcile your files before retrying |
| Missing originals | Diagnose; for managed installations, try `--update --apply` |

See [management details](../ecc-on-demand.md) for search, disabled behavior, and restoration.

See the [management guide](../ecc-on-demand.md#runtime-binding-and-multilingual-tdd) for Python selection, four-entry migration, and multilingual TDD.

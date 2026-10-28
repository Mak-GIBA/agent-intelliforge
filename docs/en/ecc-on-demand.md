# Read ECC only when needed

**English** | [日本語](../ecc-on-demand.md)

ECC originals remain in Codex's native Plugin cache; only short entry Skills appear in the initial list. Requires Python 3.11 or later, Linux / WSL2, Codex, and its native ECC Plugin. If ECC is missing, use the [installer](codex-ecc/installation.md) to obtain originals and configure this integration together.

## Apply and inspect

Run from the repository root:

```bash
python3 tools/ecc-on-demand/ecc_on_demand.py apply
python3 tools/ecc-on-demand/ecc_on_demand.py doctor
```

`apply` sets `plugins."ecc@ecc".enabled = false` and places `ecc-tdd`, `ecc-python`, `ecc-errors`, `ecc-security`, and `ecc-library` under `~/.agents/skills/`. The CLI, state, and owner-only configuration backups live in `${CODEX_HOME:-~/.codex}/ecc-on-demand/`. Originals, Basic Memory, existing MCPs, and Skill-list limits are unchanged.

First-time defaults add Firecrawl and Chrome DevTools independently. Existing same-name settings, disabled entries, and the old `context7-mcp` connection remain intact. Chrome DevTools needs Node.js, `npx`, and a usable browser; GitHub uses an existing official integration or `gh`.

Firecrawl uses the [official keyless hosted endpoint](https://github.com/firecrawl/firecrawl-mcp-server#hosted-mcp-keyless-free-tier) for rate-limited search, scrape, and parse. The `crawl` and `map` tools require authentication. Firecrawl was not evaluated in the earlier comparative trials; the default selection does not establish better accuracy.

```bash
python3 tools/ecc-on-demand/ecc_on_demand.py apply --mcps recommended,browser,cloudflare
python3 tools/ecc-on-demand/ecc_on_demand.py apply --mcps none
```

Place `--mcps` after `apply`. `research` selects Context7 and Parallel Search; `browser` selects Playwright and Chrome DevTools; `cloudflare` selects Context7 and Cloudflare Docs. Combine presets/names with commas. The selection is saved for later application and root-installer updates. Switching to `none` or another selection does not delete or disable prior connections, including previously managed ones. New packages use measured pinned versions; existing versions and arguments are preserved.

Sequential Thinking is explicit-only and Token Optimizer is excluded. The recorded comparison found no accuracy gain for the former and failures to recover required information in a new conversation for the latter. The default connections provide document lookup and browser access, not proven accuracy improvements. See [evaluation (Japanese)](../codex-ecc/mcp-evaluation.md) and [available selections](codex-ecc/installation.md).

Put `--codex-home PATH`, `--skills-root PATH`, and `--cwd PATH` before the subcommand. Same-name unmanaged Skills or edited managed files stop application. Existing TOML comments and unrelated settings are preserved. Inline tables and dotted-key ECC configuration are not edited automatically; first convert them to a normal `[plugins."ecc@ecc"]` table. Check changes in a new session; the running shared daemon is not restarted.

## Entry points

| Entry | Original |
|---|---|
| `ecc-tdd` | Language-neutral `tdd-workflow` and relevant testing guidance |
| `ecc-python` | `python-patterns` |
| `ecc-errors` | `error-handling` |
| `ecc-security` | `security-review` |
| `ecc-library` | Search up to 5 candidates and read 1–3 relevant originals |

Automatic selection is enabled; use `$ecc-library` explicitly if desired. Existing specialized React, Cloudflare, GitHub, and memory Skills take priority. Current user, developer, and project instructions override upstream TDD or deployment preferences.

```bash
python3 tools/ecc-on-demand/ecc_on_demand.py search 'Python tests' --json
python3 tools/ecc-on-demand/ecc_on_demand.py search 'DB migration' --json
python3 tools/ecc-on-demand/ecc_on_demand.py resolve api-design --json
```

`resolve` returns the body path, Skill directory, Plugin root, and version. Resolve relative references from their original location. Missing originals produce an error rather than a guessed fallback cache. Search is lightweight ranking over names, descriptions, explicit language, and nearest-project manifests, not full semantic understanding; use technical terms or exact names when needed.

Installation and explicit updates get the authoritative catalog through native `skills/list`. Queries verify and read the saved inventory without starting Codex. Diagnosis compares that snapshot with the current native inventory. No conversation, model call, or SessionStart hook is started. Reading selected bodies still consumes context even if the initial list is smaller.

## Update and restore

```bash
python3 tools/ecc-on-demand/ecc_on_demand.py update
python3 tools/ecc-on-demand/ecc_on_demand.py restore
```

`update` uses `codex plugin marketplace upgrade ecc --json` and `codex plugin add ecc@ecc --json`. Failures still return ECC to disabled and report diagnostics. Codex may request hook trust after updating; this tool does not approve it. Paths are resolved from the new native catalog, so versioned entry paths need no manual replacement. Refresh entry assets/the CLI with `apply` from a new checkout; use `install_ecc.sh --update --apply` to update both originals and management assets.

`configure-ecc` or direct `codex plugin add` can re-enable ECC. If `doctor` detects this, run `apply` again.

`restore` returns ECC to its original enabled value and removes managed entries and the CLI. It removes unchanged managed MCP entries but retains preexisting connections. Added credentials or arguments stop removal. If ECC was first installed by the new root installer, originals remain disabled. Later unrelated settings and backups are retained. Edited files or enabled flags stop restoration rather than being overwritten.

## Disabled behavior

Disabling ECC stops bulk Skill registration, its bundled Chrome DevTools MCP, and its Codex SessionStart hook. Independent MCPs continue.

ECC 2.2.2's SessionStart injects the prior summary, instincts, learned Skills, and technology context; creates ECC storage; normally deletes ECC summaries older than 30 days; and conditionally registers observer sessions. Those startup behaviors stop, but saved data remains. Basic Memory hooks, Codex history, and Claude Code's ECC settings are separate.

`doctor` checks a fresh independent app-server catalog. Inspect new-session diagnostic logs as well if you need to confirm the model's actual list. Running sessions are unchanged. MCP checks inspect configuration only; startup, authentication, and operations need separate checks.

## Validation

```bash
python3 -m unittest discover -s tests -p 'test_ecc_on_demand.py' -v
```

Tests use isolated configuration and originals to cover reapplication, conflicts, restoration, successful/failed updates, missing data, search, and RPC retrieval. They do not update real ECC or personal settings.

## Runtime binding and multilingual TDD

Management requires Python 3.11+, independently of the project's programming language. The installer selects `PYTHON_BIN`, the recorded interpreter, then `python3`, validates it, and embeds its absolute path in the installed entry commands. Venv paths are retained. If the runtime is missing, select a replacement with `PYTHON_BIN=/path/to/python3.11 bash install_ecc.sh --apply`; the system Python is not changed.

Updates migrate owned four-entry installations to five entries while preserving backups, MCP settings, and saved selections. Modified or unowned entries block migration; partial failures roll back. Refresh templates from the repository installer, not the installed manager alone. Diagnosis executes the installed commands and verifies original-document resolution.

`ecc-tdd` can be selected automatically for feature implementation, bug fixes, and refactoring. It reads `tdd-workflow` and relevant language testing originals, checks an expected failing test, implements the minimal fix, then reruns tests after refactoring. Higher-priority instructions and project coverage criteria take precedence. Documentation-only tasks do not trigger it.

Both legacy and portable readers support `search 'testing' --language typescript --json`. Without the option, query language takes precedence over nearest-project manifests. Go/Golang, C++/CPP, and C#/CSharp are normalized; language-neutral guidance remains eligible. For monorepos, put `--cwd <target-directory>` before `search`. Exact-name `resolve tdd-workflow --json` remains available.

The installer/update obtains the authoritative inventory through native `skills/list` and stores an owned `catalog.json` with original-document hashes. Normal `search`/`resolve` verify and read that snapshot without starting a nested Codex process. Changed or missing originals require an explicit refresh with `install_ecc.sh --apply`; diagnosis compares the snapshot with the native inventory. No cache-version guessing is used.

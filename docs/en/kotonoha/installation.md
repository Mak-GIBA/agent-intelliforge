# Install, update and share kotonoha

[Overview](README.md) · [Usage](usage.md) · [Validation](../../kotonoha/validation.md)

```bash
bash install_kotonoha.sh --dry-run
bash install_kotonoha.sh --apply
bash install_kotonoha.sh --doctor
bash install_kotonoha.sh --update --apply
```

The default destination is ~/.agents/skills/kotonoha/. Use --skills-dir for its parent, or install_kotonoha.ps1 on Windows. The engine supports Python 3.10+, with a managed writing runtime using Python 3.11+, Node.js and pinned npm dependencies. Dependency preparation may download files during explicit installation. Writing itself does not install tools, change MCP/hooks/AGENTS.md or upload documents.

Migration preserves auto/explicit mode, backs up owned unedited entries and retires the three legacy Skill names. Modified, additional or unmanaged files stop preflight; --force does not discard edits. Exceptions during replacement restore prior directories. The former installer name and kit ID are retired; use kotonoha.

## Upstream maintenance

```bash
bash install_kotonoha.sh --check-update
python3 tools/kotonoha/update_upstreams.py check
cp -a tools/kotonoha/assets/kotonoha /tmp/kotonoha-baseline
python3 tools/kotonoha/update_upstreams.py prepare --source all --candidate /tmp/kotonoha-candidate
```

prepare freezes stable releases, commits, hashes, original files, adapter rules and differences in a separate candidate. Select one source with --source yomiyasu|meiseki and optionally --ref TAG. Active installations stay unchanged. Review normative changes and capability coverage, update the candidate adapter, and record reasons in review.json. Run the native 24-use comparison through evals/flow_native.py to create quality.json with reference, checker and final-output receipts. The shared budget is 60 minutes. Installers never invoke a model automatically.

```bash
python3.11 tools/kotonoha/evals/flow_native.py --candidate /tmp/kotonoha-candidate --baseline /tmp/kotonoha-baseline --runtime "$HOME/.agents/.kotonoha-runtime"
python3 tools/kotonoha/update_upstreams.py verify --candidate /tmp/kotonoha-candidate
python3 tools/kotonoha/update_upstreams.py promote --candidate /tmp/kotonoha-candidate
```

verify binds outputs and quality records to the exact candidate. promote replaces repository originals, rules, adapters and integrated revisions together. Missing/stale evidence, critical semantic errors, unintegrated writing changes and unresolved regressions hold adoption. --update --upstream-only retains the active version and reports UPSTREAM_REVIEW_REQUIRED for an unintegrated release. API/network failure also preserves the active version. Hashes do not prove publisher identity or human approval.

The comparison runner needs Python 3.11+ and an authenticated Codex CLI. It fixes the configured model and reasoning effort per call and consumes model time and credits. Fixed fixtures do not prove general capability retention; include unseen tasks when reviewing substantial changes.

## Removal and sharing

Preview with --uninstall --dry-run; apply with --uninstall --apply. Edited or extra files prevent removal; backups remain. A shared copy needs only the kotonoha folder, including resources.json for source integrity. Installation ownership .installer.json may be omitted from manual copies. Prepare the optional lint runtime on the recipient machine; exclude private settings, credentials and caches.

Version 4.1 requires the preserved FLOW.json rules and all paired native records/reviews. Supplied-guide v4.0 studies are historical evidence. Later rounds (--round 2, then at most --round 3) rerun every candidate case within the original deadline; answers edited outside the actual Skill run cannot replace its outputs.

## Migrate the former kit/plugin name

Preview `intelliforge update --only kotonoha --agent codex` (or `--agent claude`), then add `--apply`. The existing install method and writing mode are preserved. Only hash-verified owned resources are migrated. Dependencies are prepared at the new absolute path; the old environment remains under migration-backups. Coexisting names, user edits, unknown ownership and linked paths stop migration. Stop the old CLI before applying.

Host CLI commands install and verify the new plugin before retiring the old registration. A disabled plugin requires a host CLI that supports disabling; current Codex CLI cannot perform that migration and stops without changes. Host caches/settings are not edited directly. Original yomiyasu OSS identifiers, licenses and historical evaluation records retain their names.

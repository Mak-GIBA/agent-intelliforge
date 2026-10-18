# Install, update, and remove kotonoha

**English** | [日本語](../../codex-yomiyasu/installation.md)

[Overview](README.md) · [Usage](usage.md) · [Validation (Japanese)](../../codex-yomiyasu/kotonoha-validation.md)

## Requirements and installation

kotonoha prepares Python, Node.js, and lint tools in a user-local environment when needed. Compatible existing tools are reused; no sudo, OS package manager, or persistent PATH modification is used. Install the host, such as Codex, separately.

Linux / WSL2 needs Bash, curl or wget, tar, and a hashing utility. Windows uses PowerShell.

```bash
bash install_kotonoha.sh                 # Preview installation
bash install_kotonoha.sh --apply         # Install Skills and lint environment
bash install_kotonoha.sh --doctor        # Diagnose placement, hashes, and lint environment
```

```powershell
.\install_kotonoha.ps1                  # Preview installation
.\install_kotonoha.ps1 --apply
.\install_kotonoha.ps1 --doctor
```

Bulk installation uses `bash install_all.sh --only kotonoha --apply`; shared CLI installation uses `intelliforge install --only kotonoha --apply`. When only the Japanese kit is selected, the Windows bulk entry can delegate to the standalone bootstrap even without Python/uv.

### Names and destinations

Use `$kotonoha` for normal writing/revision; `$yomiyasu` is the same workflow's compatibility entry. `$paragraph-writing` handles structure only, and `$japanese-direct-writing` excessive hedges only.

The default parent is `~/.agents/skills/`. If using `--skills-dir PATH`, repeat it for diagnosis/update/removal. The internal kit ID, Plugin name, and management directory retain `yomiyasu` for compatibility. The old `install_codex_yomiyasu.sh` is built from the same maintained source.

Same-name unmanaged Skills or duplicates elsewhere are not overwritten/registered again. All selected Skills are checked/prepared before placement. Failed directory switching restores Skills already switched.

### Runtime and upstream originals

When Python is missing, pinned uv prepares Python 3.11. Node.js uses a reviewed 24 LTS official distribution verified by hash; lint dependencies use a lockfile.

Runtime lives in `.kotonoha-runtime` beside the Skill parent. Python bootstrap lives in the user-data directory's `agent-intelliforge/kotonoha-bootstrap`. Plugin installations use kit state `dependencies/kotonoha`. Runtime/backups survive removal.

Initial installation resolves latest stable meiseki/yomiyasu Releases to commits. yomiyasu files are checked against Git blob IDs and sizes; meiseki against reviewed SHA-256 values. Unreviewed meiseki rule changes stop without replacing existing Skills. Identical reruns do not update upstreams automatically. Auxiliary Skills use bundled assets without contacting their original Gist/ZIP.

Without Python, preview reports bootstrap scope without downloads. Use existing Python through `PYTHON_BIN` for a complete argument-specific preview. Diagnosis/help without `--apply` does not download Python.

## Select components

Standalone `--only` selects individual Skills: `all` (default), `yomiyasu`, `kotonoha`, `paragraph-writing`, or `japanese-direct-writing`. In contrast, bulk/shared CLI `--only kotonoha` and `--only yomiyasu` both select the whole Japanese kit.

```bash
bash install_kotonoha.sh --only paragraph-writing --apply
bash install_kotonoha.sh --only japanese-direct-writing --apply
bash install_kotonoha.sh --only yomiyasu --doctor
```

With compatible Python already present, auxiliary-only installation needs no upstream fetch.

## Updates and invocation modes

Obtain the revised installer, inspect changes, and apply:

```bash
bash install_kotonoha.sh --check-update
bash install_kotonoha.sh --update
bash install_kotonoha.sh --update --apply
bash install_kotonoha.sh --doctor
```

`--check-update` checks stable upstreams and bundled custom/auxiliary assets, also reporting unsupported meiseki changes. `--update` without `--apply` previews without network; application resolves/verifies releases before placement. Auxiliary-only checks/updates use bundled versions without network.

Use `--force --apply` to refresh bundled entries/configuration/auxiliaries while retaining upstream versions. Old installations missing required upstream files must first use `--update --apply`; `upstream/UNICODE-LICENSE.txt` is required from the 2.0 series onward.

Edited/missing managed files stop even with `--force`. Prior assets are backed up as Skill-named ZIPs under `.yomiyasu-installer-backups/`. If only old temporary-directory cleanup fails after completion, the completed operation and remaining path are reported.

Existing modes remain. New Skills inherit managed yomiyasu's mode, or default to `auto` when all are new. Change modes explicitly:

```bash
bash install_kotonoha.sh --mode explicit --force --apply
bash install_kotonoha.sh --mode auto --force --apply
```

`auto` permits relevant automatic selection; yomiyasu's compatibility entry remains explicit-only. `explicit` requires naming each Skill and sets `allow_implicit_invocation: false` in `agents/openai.yaml`. No every-answer proofreading hook is installed.

## Update upstream only or pin a release

```bash
bash install_kotonoha.sh --update --upstream-only
bash install_kotonoha.sh --update --upstream-only --apply
bash install_kotonoha.sh --check-update --upstream-ref v1.1.1
bash install_kotonoha.sh --update --upstream-ref v1.1.1 --apply
```

`--upstream-only` requires `--update` and refreshes only yomiyasu's upstream originals. It preserves kotonoha, meiseki, custom rules/version, `references/explanation.md`, auxiliaries, and runtime. `--upstream-ref` selects a stable Release tag, not the custom Skill version.

## Remove and inspect

```bash
bash install_kotonoha.sh --uninstall
bash install_kotonoha.sh --uninstall --apply
bash install_kotonoha.sh --only paragraph-writing --uninstall --apply
bash install_kotonoha.sh --only japanese-direct-writing --uninstall --apply
bash install_kotonoha.sh --self-test
bash install_kotonoha.sh --extract /tmp/yomiyasu-review
```

Default removal targets all managed Japanese Skills; use `--only` for one. Manual edits/additions stop before any selected Skill is removed.

`--doctor` checks placement, hashes, modes, known conflicts, and runtime without network. It does not disable other proofreading Skills. `--project PATH` selects a project for conflict diagnosis.

Self-tests use temporary state and mocked upstream responses to check lifecycle and tools, not real distribution network access or writing quality. Model studies such as `evals/run_study.py` / `evals/explanation_study.py` are explicit operations and never run during installation. `--extract` writes embedded assets into an empty/unused directory without installation. `--self-test` / `--extract` cannot combine with `--only`.

## Sources and dependencies

`--source-dir PATH --apply` accepts local Git checkouts, managed snapshots, or old v1.0.4 flat originals for yomiyasu. It checks the format and uses bundled reviewed meiseki originals. Upstream network fetches are skipped, but missing runtimes/dependencies still require access. Use it only for installation/update including yomiyasu, never with `--upstream-ref`.

Runtime preparation failure leaves Skills unswitched. Owned partial caches and prepared runtime are reusable. Distributions are defined for Linux glibc, macOS, and Windows x64 / ARM64; definition is not real-machine validation. See [tested operations/platforms (Japanese)](../../codex-yomiyasu/kotonoha-validation.md).

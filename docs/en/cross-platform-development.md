# Edit and verify distribution assets

**English** | [日本語](../cross-platform-development.md)

[Installation](cross-platform.md) · [Validation (Japanese)](../cross-platform-validation.md) · [Development](development.md)

Maintained sources are separate from generated distribution copies; standalone installers remain supported.

| Location | Role | Edit? |
|---|---|---|
| `tools/<kit>/kit.json` | Skills, sources, dependencies, destinations, settings | Maintained source |
| Kit `assets`, `skill`, `workbench` | Rules, checks, harness | Maintained source |
| `tools/design-research-upgrade/` | Build current Research / Upstream from pinned base | Maintained source |
| `src/agent_intelliforge/` | Shared CLI, ownership, OS/host adapters | Maintained source |
| `tools/intelliforge/build.py` | Generate resources, Plugins, comments | Maintained source |
| `plugins/codex/`, `plugins/claude/` | Host-format Plugins | Generated |
| `tools/intelliforge/resources/runtime/` | Distribution copies with OS/host adapters | Generated |
| `install_*.sh`, `install_kotonoha.ps1` | Standalone installers | Generate through matching builders |

GitHub/Office sources were extracted from verified ZIPs. `EXTRACTED.json` records original distribution/payload hashes; `payload-layout.json` and `bootstrap.sh.in` retain the single-file format. Herdr separates Python source and Bash bootstrap. That structural extraction did not alter those distributions' execution behavior.

## Regenerate

```bash
# Generate/check standalone installers from their maintained sources
python tools/kotonoha/build_installer.py
python tools/kotonoha/build_installer.py --check
python tools/codex-github-pm/build_installer.py --check
python tools/codex-office/build_installer.py --check
python tools/herdr/build_installer.py --check

# Build and verify current Research / Upstream from the pinned base
python tools/design-research-upgrade/build_installers.py --out <empty-assembly-directory>

# Use the assembled sources above to generate Plugins and runtime assets
python tools/intelliforge/build.py --assembled-source <assembly-directory>
python tools/intelliforge/build.py --assembled-source <assembly-directory> --check
```

Without `--assembled-source`, the builder fetches the pinned research base, verifies hashes, and executes build tests first. Generation does not install kits. Prepare fixed files with the existing `--base-dir` / `--offline` procedure for offline assembly; do not build current research Plugins solely from the old root sources.

`build.py` connects only OS/host dependencies in distribution copies, converting host invocation, namespace, and explicit-use settings. Upstream yomiyasu/ECC originals do not pass through transformation. Decision rules, research schemas, and evidence checks are not separately reimplemented per host.

Definitions generate CLI previews and bulk-entry comments. Regenerate when changing Skills or dependencies. `source-manifest.json` tracks source/output hashes and rejects packaging stale assets.

## Verify packages

```bash
python -B -m unittest discover -s tests -p test_intelliforge.py -v
python -B -m unittest discover -s tests -v
bash -n install_all.sh
bash -n install_kotonoha.sh
bash install_kotonoha.sh --self-test
uv build
```

Standard wheel/sdist include CLI, installers, definitions, Plugins, and runtime assets. Construction does not register Plugins or install kit dependencies. Install the console entry with `uv tool install .`, `pipx install .`, or isolated-venv `pip install .`.

Windows CI covers shared CLI, ownership, process cleanup, distributions, and packaging; POSIX tests remain on Linux. `.gitattributes` enforces LF so checkout does not invalidate hashes. Distribution reads/writes/subprocesses use UTF-8; generated copies fill omitted encodings without changing explicit ones or maintained sources. Native Windows 11 isolation and Claude model evaluation remain separate from static/mock CI.

## Real-machine evaluation

Use temporary homes, host settings, and Skill directories. Verify installation, rerun, mode switches, updates/upstream-only updates, diagnosis, removal, manual-edit protection, and dependency-failure recovery.

Research/UX comparisons need matched material/model/reasoning/budgets, structured output, independent roles, isolation, evidence, privacy, and interruption checks. On Windows test actual read/write restrictions, OS updates, PowerShell, Job Object cleanup, paths with spaces/Japanese, junctions, and concurrency. Report unperformed/blocked checks accurately, separating output quality from installation success.

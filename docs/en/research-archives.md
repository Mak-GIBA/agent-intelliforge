# Research evidence archives

Validation guides retain summaries, conditions, failures and limitations. Historical run state, repeated inputs, writing outputs, ratings and old study assets live in a downloadable archive. Normal installation and offline tests do not fetch it.

[日本語](../research-archives.md) · [Development](development.md) · [Registry](../research-archives.json)

## Archived records

The [2026-10-27 archival release](https://github.com/Mak-GIBA/agent-intelliforge/releases/tag/research-archive-20261027-871cb8ad) preserves 2,414 files from commit `871cb8adf0f7c278d22c72c4fbb21fadc5882f72`, with their original bytes, relative paths and license notices. The compressed archive is about 12.3 MiB. Summaries remain in Git; 2,254 files totaling about 59.9 MiB leave the current tracked tree.

It contains historical Research runs, kotonoha evaluations and older writing-study assets. Moving the records did not rerun models or regrade outputs. Failed and held results remain alongside successful results.

The registry pins the archive digest, source commit and file count. The included `inventory.json` records every file's SHA-256, size and original mode. These checks establish content identity, not human approval or output quality.

## Verify and restore

Use Python 3.11 or later from the repository root. Verification downloads the archive and checks both the compressed file and every member:

```bash
python scripts/research_archive.py verify
```

To read the records, restore them into a directory that does not exist yet. The command never overwrites an existing destination. Original `docs/` and `tools/` paths appear inside that directory.

```bash
python scripts/research_archive.py restore --destination .artifacts/evidence-archives/20261027
```

For offline use, download the archive from the release in advance and pass `--archive /path/to/archive.tar.gz` to either command. Use `--id` to select an entry if multiple archives are registered.

Restoring records does not start a model or external service. To rerun an old experiment, separately recreate its recorded source commit, dependencies and model conditions. Detailed links in historical documents may point to files at the source commit. For the 4.1.1 editorial verifier, pass the restored `docs/codex-yomiyasu/evidence/editorial-v411` directory as `--native`, following the [original conditions](../codex-yomiyasu/evidence/editorial-v411/README.md).

## What stays in Git

ECC captures needed by offline tests, normative baseline data, migration history, upstream originals and licenses remain tracked. Generated Plugins, standalone installers and runtime bundles remain available through their existing installation paths.

Keep new bulky execution records in a working directory. Publish concise conditions, results, limitations and evidence locations in the validation guides. CI's `check-tree` command rejects reintroduction of archived file areas. Git history is retained, so the smaller current tree does not imply an equivalent reduction in a full-history clone.

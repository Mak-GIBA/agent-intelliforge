# Read Codex ECC Skills on demand

**English** | [日本語](../../codex-ecc/README.md)

[Documentation](../README.md) · [Installation](installation.md) · [Usage](usage.md) · [Choosing MCPs (Japanese)](../../codex-ecc/mcp-evaluation.md)

Use ECC's specialized procedures only when the task needs them. The kit obtains ECC originals through Codex's standard Plugin system and keeps the always-visible Skills as short entry points. Python implementation, error handling, and security review have dedicated entries; search for other procedures by purpose instead of loading everything upfront.

[install_ecc.sh](../../../install_ecc.sh) requires the full repository, including `tools/ecc-on-demand/`. No arguments previews the plan without network access; `--apply` installs and configures it.

## Components

| Component | Source | Purpose |
|---|---|---|
| Original ECC Plugin | `affaan-m/ECC` | Obtain through Codex when missing; reuse an existing installation |
| ECC entry Skills | This repository | Resolve the originals needed for a task |
| Management CLI | This repository | Apply, diagnose, search, resolve, update, and restore |

ECC is an external Plugin. This integration uses the standard Plugin commands for its originals, then disables the Plugin's bulk Skill registration, bundled startup hook, and bundled MCP. Basic Memory and independently configured MCPs are preserved.

## Reading order

1. [Installation](installation.md): requirements and configuration changes.
2. [Usage](usage.md): resolve originals through the entry Skills.
3. [Management details](../ecc-on-demand.md): CLI and disabled behavior.

## References

The guide uses native commands checked on 2026-10-03 with Codex CLI 0.160.0 and ECC 2.2.3. Available versions and original paths are resolved from the live Codex catalog. Upstream: [ECC](https://github.com/affaan-m/ECC).

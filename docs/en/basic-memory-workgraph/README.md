# Basic Memory Workgraph

**English** | [日本語](../../basic-memory-workgraph/README.md)

[Documentation](../README.md) · [Installation](installation.md) · [Usage and settings](usage.md)

Workgraph helps Codex retain knowledge from work in Basic Memory for later tasks. Codex reviews attempts, obstacles, and verified workarounds, selecting lessons useful beyond the current task. User corrections can be recorded with their context and desired output so similar requests can benefit from them before the first draft. Settings control which types are eligible.

[install_basic_memory_workgraph.sh](../../../install_basic_memory_workgraph.sh) requires the complete repository because it uses Python code and templates under `tools/basic-memory-workgraph/`.

## Components

| Component | Source | Role |
|---|---|---|
| uv / uvx and Python 3.12 | Astral tooling and Python runtime | Basic Memory execution; uvx also launches the official MCP |
| Basic Memory (`bm`) | Basic Memory | Store/search Markdown notes and their relations |
| `codex@basic-memory` Plugin | Basic Memory | Codex integration and Skills |
| Policies, schemas, graph index | This repository | Define Rule, Workflow, Validation, Correction, Case, and other records |
| Additional hooks | This repository | Prompt recall before work and evaluate capture value afterward |
| `workgraph_tools.py` / `workgraph_sequence.py` | This repository | Sharing, import, JSONL, structural audits, Skill registration, Case validation |
| `workgraph_github.py` and guide | This repository | Private-repository PR sharing and receiving merged updates |

Basic Memory supplies storage/search; Workgraph defines what to retain and how to reuse it. Hooks do not write notes themselves: Codex searches, judges, and saves. `update_workgraph.py` and `configure_workgraph.py` provide update/configuration helpers.

## Capabilities

Reuse conditional rules and verified procedures, retain contextual corrections, record improvement sequences as Cases, and connect independently useful records. Share reviewed knowledge or export explicitly approved Cases as training JSONL. GitHub sharing can create PRs and import merged updates. Repeated procedures can be reviewed for Skill packaging and, when enabled, validated and registered.

**Reusable-knowledge evaluation is enabled initially. Automatic Correction/Case capture and Skill registration require their respective settings.** This is not conversation logging: no qualifying knowledge means no write. Sharing and training permissions are separate; the kit does not train a model.

## Reading order

[Knowledge graph examples](knowledge-graph.md) show note relationships, Markdown, and reuse. Then read:

1. [Installation, updates, removal](installation.md).
2. [Usage and capture modes](usage.md).
3. [GitHub sharing and prompts](github-sharing.md): connect both PCs and exchange reviewed knowledge.
4. [File sharing and training exports](sharing.md).

For problems, use [troubleshooting](troubleshooting.md); for policies and internals, use [reference](reference.md).

## Sources

[Basic Memory](https://github.com/basicmachines-co/basic-memory), [uv](https://docs.astral.sh/uv/), and the maintained [capture policy (Japanese)](../../../tools/basic-memory-workgraph/memory-policy.md).

Workgraph is a custom extension. Updating it is separate from upgrading Basic Memory itself or the official Plugin; see [updates](installation.md#update).

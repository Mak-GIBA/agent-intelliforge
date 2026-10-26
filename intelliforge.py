#!/usr/bin/env python3
# intelliforge-manifest:begin
# Kit: workgraph — Basic Memory Workgraph
# Skills: CLI integration
# Source: https://github.com/basicmachines-co/basic-memory (existing pinned source or official plugin policy; inspect source definition below)
# Destination: {agent_home}/basic-memory-workgraph
# Destination: {agent_home}/hooks
# Settings: owned UserPromptSubmit/Stop hooks; memory settings and guidance blocks
# Edit: tools/basic-memory-workgraph/kit.json
# Inspect: intelliforge inspect --only workgraph
# Regenerate: python tools/intelliforge/build.py
# Kit: ux-stack — UX Stack
# Skills: ux-gan-harness, ooui-design
# Source: https://github.com/vercel-labs/agent-skills (063bee94c3f4df8453406c830b0a7df0f2860278)
# Source: https://github.com/Thecsiz/ux-critique (3da293cafb639195bf71797590081d4ffb0045ba (optional deep install))
# Destination: {skills_home}/ux-gan-harness
# Destination: {skills_home}/ooui-design
# Destination: {agent_home}/ux-stack/runtime
# Settings: selected plugins and MCP configuration; owned CLI launchers
# Edit: tools/codex-ux-stack/kit.json
# Inspect: intelliforge inspect --only ux-stack
# Regenerate: python tools/intelliforge/build.py
# Kit: speckit — SpecKit Upstream
# Skills: upstream-new, upstream-existing, upstream-change, upstream-bug, upstream-refactor, upstream-check, upstream-review, upstream-approve
# Source: https://github.com/github/spec-kit (verified base d3f46e0d591b45cb2423317030a489b91566e891 plus maintained upgrade layers)
# Destination: {skills_home}/upstream-*
# Destination: {data_home}/speckit-upstream
# Destination: {bin_home}/swb
# Settings: owned per-user CLI/skills; per-project initialization remains explicit
# Edit: tools/speckit-upstream/kit.json
# Inspect: intelliforge inspect --only speckit
# Regenerate: python tools/intelliforge/build.py
# Kit: github-pm — GitHub Project Director
# Skills: github-project-director
# Source: https://cli.github.com/ (existing pinned source or official plugin policy; inspect source definition below)
# Destination: {skills_home}/github-project-director
# Settings: owned user-level AGENTS guidance only; no GitHub mutations during install
# Edit: tools/codex-github-pm/kit.json
# Inspect: intelliforge inspect --only github-pm
# Regenerate: python tools/intelliforge/build.py
# Kit: design-research — Design Research
# Skills: design-research
# Source: https://github.com/Mak-GIBA/agent-intelliforge (verified base d3f46e0d591b45cb2423317030a489b91566e891 plus maintained upgrade layers)
# Destination: {skills_home}/design-research
# Destination: {agent_home}/design-research
# Settings: owned skills and runtime; experiment network/source-change permissions remain explicit
# Edit: tools/design-research/kit.json
# Inspect: intelliforge inspect --only design-research
# Regenerate: python tools/intelliforge/build.py
# Kit: ecc — ECC on demand
# Skills: ecc-library, ecc-python, ecc-errors, ecc-security
# Source: https://github.com/affaan-m/ECC (legacy: official ecc@ecc plugin; portable: stable released tag plus recorded commit)
# Destination: {skills_home}/ecc-*
# Destination: {agent_home}/ecc-on-demand
# Settings: owned ECC config/MCP blocks; other tools and opt-outs preserved
# Edit: tools/ecc-on-demand/kit.json
# Inspect: intelliforge inspect --only ecc
# Regenerate: python tools/intelliforge/build.py
# Kit: office — Office Workbench
# Skills: office-workbench
# Source: https://github.com/iOfficeAI/OfficeCLI (v1.0.153; tools/codex-office/versions.json contains pins and hashes)
# Destination: {skills_home}/office-workbench
# Destination: {data_home}/codex-office
# Destination: {bin_home}/office-workbench
# Settings: MCP only on explicit selection; no implicit system package installation
# Edit: tools/codex-office/kit.json
# Inspect: intelliforge inspect --only office
# Regenerate: python tools/intelliforge/build.py
# Kit: yomiyasu — kotonoha Japanese writing
# Skills: kotonoha
# Source: https://github.com/nanaism/yomiyasu (latest stable upstream release; local writing rules have independent version)
# Source: https://github.com/bamboo-nova/meiseki (latest stable release; normative changes require reviewed adapter)
# Destination: {skills_home}/kotonoha
# Destination: {skills_home}/../.kotonoha-runtime
# Settings: none
# Edit: tools/codex-yomiyasu/kit.json
# Inspect: intelliforge inspect --only yomiyasu
# Regenerate: python tools/intelliforge/build.py
# Kit: herdr — Herdr workspace reuse
# Skills: CLI integration
# Source: https://herdr.dev/ (legacy official installer/reuse; native Windows x64 pinned v0.9.3 with SHA-256)
# Destination: {bin_home}/herdr-open
# Settings: owned Bash guidance/function in legacy mode; native launchers in portable mode
# Edit: tools/herdr/kit.json
# Inspect: intelliforge inspect --only herdr
# Regenerate: python tools/intelliforge/build.py
# intelliforge-manifest:end
"""Checkout entry point; no package install or personal configuration changes."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from agent_intelliforge.cli import main

if __name__ == "__main__":
    raise SystemExit(main())

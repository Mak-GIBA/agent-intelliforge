# Sources and dependency policy

Checked 2026-10-02. This is a custom installer, not an official OpenAI/Microsoft/OfficeCLI product.

- OfficeCLI release v1.0.153 (pinned binary and text references):
  https://github.com/iOfficeAI/OfficeCLI/releases/tag/v1.0.153
  https://api.github.com/repos/iOfficeAI/OfficeCLI/releases/tags/v1.0.153
  Binary SHA-256 digests are locked in versions.json. They were obtained from GitHub release metadata; this is an integrity check, not a publisher signature or independent supply-chain audit.
- OfficeCLI Skill and command-help source:
  https://github.com/iOfficeAI/OfficeCLI/blob/v1.0.153/SKILL.md
  https://github.com/iOfficeAI/OfficeCLI/blob/v1.0.153/src/officecli/CommandBuilder.Help.cs
  Upstream Skill/LICENSE/NOTICE are downloaded on installation and verified with their Git blob identifiers. No upstream universal installer is executed. No auto-skill registration to other agents.
- OfficeCLI license (Apache-2.0):
  https://github.com/iOfficeAI/OfficeCLI/blob/v1.0.153/LICENSE
  https://github.com/iOfficeAI/OfficeCLI/blob/v1.0.153/NOTICE
- MarkItDown (Microsoft; MIT):
  https://github.com/microsoft/markitdown
  https://github.com/microsoft/markitdown/releases
  Only PDF/DOCX/PPTX extras. No Azure/LLM client configuration or conversion plugins enabled by this wrapper.
- pypdf:
  https://pypdf.readthedocs.io/en/stable/
  https://pypi.org/project/pypdf/6.15.0/
- pdfplumber:
  https://github.com/jsvine/pdfplumber
  https://pypi.org/project/pdfplumber/0.11.9/
- pypdfium2:
  https://pypdfium2.readthedocs.io/en/stable/
  https://pypi.org/project/pypdfium2/5.12.1/
  PDFium carries bundled third-party license notices; wheels retain those notices.
- Optional Docling MCP/local tooling:
  https://github.com/docling-project/docling-mcp
  https://pypi.org/project/docling-mcp/3.0.0/
  Separate venv. Model licenses/download sizes must be checked separately. CLI use is local; optional server is not registered by this kit.
- Codex Skills:
  https://developers.openai.com/codex/skills
  User Skills: ~/.agents/skills. Explicit and implicit invocation are supported.
- Codex MCP:
  https://developers.openai.com/codex/mcp
  Only explicit opt-in uses codex mcp add/remove. It is not a sandbox or access-control system.
- LibreOffice conversion and limitations:
  https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html
  https://help.libreoffice.org/latest/en-US/text/shared/guide/ms_import_export_limitations.html

Top-level Python requirements are pinned. Transitive requirements are resolved
on install and recorded in pip-freeze.txt; they are NOT shipped as a complete
hash-pinned lock. Wheels only, official PyPI index, no sdist builds. A platform
without compatible wheels stops instead of silently building arbitrary sources.
A reinstall may resolve different transitive dependencies. For organizational
rollout, create a reviewed platform-specific wheelhouse/lock in a separate release process.

# Office Workbench — PDF, Word, and PowerPoint

**English** | [日本語](../../codex-office/README.md)

[Documentation](../README.md) · [Installation](installation.md) · [Usage](usage.md)

Read PDF, DOCX, and PPTX files, then create or edit a working copy while protecting the original. Check text differences, document structure, and rendered page images separately. [install_codex_office.sh](../../../install_codex_office.sh) works alone: no arguments previews the plan, and `--apply` installs tools.

## Components

| Component | Source | Purpose |
|---|---|---|
| OfficeCLI 1.0.153 and references | OfficeCLI | Office document operations; explicitly reusing an existing binary is supported |
| MarkItDown | Microsoft | Extract text from PDF, DOCX, and PPTX |
| PDF / Office Python libraries | Their respective providers | Page manipulation, extraction, rendering, and limited Office editing |
| Entry Skill and `office-workbench` | This repository | Original-file protection, working copies, differences, and rendering checks |

No MCP is registered by default; select `--with-mcp` if needed. A separate optional Docling environment supports complex PDF structure analysis. This kit is custom integration, not an official Microsoft, OpenAI, or OfficeCLI product.

## Check the rendered document

Full-page Office rendering requires LibreOffice; Japanese rendering needs suitable fonts. Output is not guaranteed to match Word or PowerPoint exactly. Check specialized shapes, fonts, animations, and other advanced features in the Office application. MarkItDown extraction is not a layout-preserving round trip.

Use `--extract` to inspect the bundled guide. Start with [installation](installation.md), then [editing and verification](usage.md).

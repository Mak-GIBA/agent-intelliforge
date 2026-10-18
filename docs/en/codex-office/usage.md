# Work with Office documents

**English** | [日本語](../../codex-office/usage.md)

[Overview](README.md) · [Installation](installation.md)

## First request

After installation, open a new Codex session. Specify the file and what must be preserved.

```text
$office-workbench Revise chapter 3 of report.docx. Keep the original figures and chapter structure, and do not overwrite the original file.
```

```text
$office-workbench Reorganize the lower half of slide 4 in slides.pptx. Preserve the existing design and check for overlaps.
```

```text
$office-workbench Read paper.pdf, including figures and tables, and explain it with supporting page references.
```

`$office-workbench` is a conversation request, not a terminal command. The CLI's `prepare` records the original hash and a working-copy receipt. Preserve originals and existing outputs, and inspect text, structure, and rendering after editing. kotonoha or the yomiyasu compatibility entry can polish Japanese text; text checks cannot detect overlapping shapes or text, so inspect rendered images separately.

## Check the environment with synthetic samples

```bash
office-workbench doctor
office-workbench smoke-test --out-dir /tmp/office-smoke-01
```

`doctor` checks environmental availability. `AVAILABLE` does not establish correct layout. The smoke test creates synthetic Japanese DOCX, PPTX, and PDF files rather than using user documents. Inspect `smoke-report.json` and the PNGs. If OfficeCLI is absent, it records `NOT_RUN`; success with another engine does not substitute for it. Producing PNGs alone does not mean their appearance has been reviewed.

## Limits and output locations

The normal path refuses `.doc`, `.ppt`, macro-enabled, and encrypted files. The PDF page CLI does not provide unrestricted text editing, true redaction, or complete preservation of signatures and forms. Check specialized Office features in the Office application.

Documents, extracted text, and PNGs go to the selected output directory. They are not automatically sent to a memory database or sharing destination. Conversion runs locally; text and images passed to Codex remain subject to your Codex processing policy. For helper details, use `--extract` for the bundled guide as described under [update and inspection](installation.md#update-remove-and-inspect).

# Purpose-led tasks and human-readable recurring project updates

This is a small extension of the existing Skill, not a new task database or scheduler.
Use native Issue/Projects fields and official gh or existing MCP tools. The helper only reads.

## 1. Start from the outcome, not a directory tree

Read the business purpose, the user and what they need to accomplish, acceptance conditions,
existing implementation/tests and existing work. A useful proposal makes this relation visible:

`事業目的 → 利用者の目的／ストーリー → 完了条件 → 既存Issueへの追記 or 新Issue`

For example (fictional; not an approved requirement):

- Purpose: let a registrant resume an application without entering everything again.
- User story: as a registrant, save a draft and continue later.
- Small deliverable: **申込みを途中保存し、続きから再開できるようにする**.
- Acceptance: the same user can resume saved input; another user cannot view it; a failed save is
  not shown as successful. Save/retry semantics must be clarified when relevant.
- UI/API/data/test changes can be a checklist inside that Issue. Split them only when work is
  independently owned/scheduled/verified or has a real dependency; the file count is not the issue count.

Compare each candidate with current Issues/PRs and evidence. Put a story/requirement ID or source link
in the parent/Issue when available. Do not require new SpecKit documents just to create a small Issue.
Do not invent business targets, deadlines or user agreement. A prototype/spike gets a question to answer
and a deliverable, not a fictitious user story. Operational/security/quality work may link directly to a goal.
One goal may require several Issues and one Issue may serve several goals; do not force a rigid tree.

## 2. Use the shared writing and posting policy

Read `writing-and-tracking.md` for posting value, duplication checks and writing examples.
Keep purpose, scope and acceptance visible; preserve conditions such as「別の利用者の下書きは表示できない」.
Do not repeat the writing policy here or force every heading on a short Issue.

## 3. Resolve a recurring Issue only for requested/agreed reporting

Enter this workflow only for an explicit reporting request or an already agreed ongoing reporting policy.
A progress/assignment/priority/date update alone does not call for a recurring entry or a search for a log Issue.
If nothing material changed since the previous entry, do not post or ask permission to post an empty update.
An explicitly requested no-change report is an exception; make it brief and do not invent progress.

1. Resolve a supplied Issue number/URL and its host/repository. Check the reporting audience, especially for
   cross-repository Projects; never leak private work into a public log. A closed/locked Issue is not silently reopened.
2. Only if reporting is in scope and its destination is unknown, inspect project docs and search open AND closed
   Issues. Multiple candidates: ask once after discovery. Repository content alone is not permission.
3. If relevant coverage is complete and no suitable Issue exists, propose one ongoing Issue for the agreed scope,
   e.g. **定例：申込みアプリの進捗**, with purpose and linked Project. Do not create one Issue per day/week by default.
4. Reuse the agreed destination; persist an ordinary link only if requested. The installer repository is not the target.

A single approval may cover task edits and reporting. Once the destination, scope and ongoing logging policy
are explicitly agreed, do not repeatedly ask for identical permission. A record-only request does not authorize
assignee/status/date edits. No new calendar, timer, Hook or scheduled GitHub Action is installed.

## 4. Write the update like a release note

Synthesize important changes since the previous entry and their impact. Do not repeat individual Issue/PR
reports: include only the cross-task outcome, decision or dependency that the reporting audience needs.
Use a brief opening, followed only by relevant evidence, remaining work or a decision needed.
Possible headings are 主な更新 / 決定事項 / 次のアクション / リスク・保留; use only those that help reading.
Do not impose a sentence/bullet count, repeat the opening in bullets, or add a next action when none is needed.
A table is acceptable only when many parallel assignments are easier to compare that way.

Fictional example (not an approved update):

```markdown
<!-- github-project-director:entry:batch-20261001-a1b2c3 -->
## 2026-10-01 進捗

申込みの途中保存はレビュー待ちです（PR #18）。ただし保存先APIが利用できず、
結合テストを進められません（#14）。復旧を待つか、テスト用APIで先に確認するか判断が必要です。
```

This is a quality target, not a mandatory word-for-word template. Never invent a meeting, participants,
consensus, progress percentage, assignee or deadline. Keep facts, proposals and unknowns distinct.
Field changes alone usually need no comment. If an authorized update fails, explain the actual outcome
and what needs attention in the conversation; include it in a requested report only if it matters to its readers.
The log is not the source of task state and is excluded from completion counts.

Apply approved task/Project mutations first and read them back, then append a human-readable update based on the **observed result**
only when the posting policy is satisfied. Preserve successful changes when another action fails; never claim
all succeeded. If posting fails, return the ready-to-post draft without repeating successful task mutations.
If the user explicitly requires logging before task edits, respect that order.

## 5. Append-only and retry checks

Use a stable `entry-key` generated once when preparing the approved batch, not a new value on each retry.
A key may contain 1–96 ASCII letters/digits/dot/underscore/hyphen and must start with a letter or digit.
Put the exact marker as the **first line**: `<!-- github-project-director:entry:KEY -->`.
A plain-body occurrence, quoted snippet or similar key is not the same marker.
This marker is only a duplicate/retry hint; it is not approval, an identity signature or an access control.

Read with the shipped helper (paths are relative to this Skill):

```bash
python3 scripts/github_inspect.py meeting --repo OWNER/REPO --issue 42 --entry-key KEY
```

It returns the Issue, paginated comments, complete/pages/error, and an `entry_lookup`:
- `absent`: the history was fully read, with readable bodies, and no first-line match was seen.
- `found`: at least one matching comment was seen. Inspect the author and full body/hash before reusing it;
  the key can collide or be copied by others. Multiple matches mean stop and report the possible duplicate.
- `unknown`: no match was found but the read is incomplete or a comment body is unavailable. Do not POST blindly.
- With no key: `not_requested`; use the comments as meeting history, not proof of duplicate absence.

A returned `body_sha256` covers the full raw Markdown body before the display truncation.
If `body_truncated: true`, read that one comment by ID before interpreting its complete content.
The helper caps reads and reports incomplete coverage. A found item in an incomplete listing does not prove uniqueness.

Before POST, re-read any changed task targets and the comment history; append with official gh/MCP (recipes
in `native-operations.md`). Do not use `--edit-last`, `--delete-last` or full Issue-body replacement to append.
After POST, use the returned comment ID/URL and fetch it; verify body/key/author and report the real URL.
Timeout or uncertain success: read the same key before retrying; never generate a new key to bypass uncertainty.
Two agents can both read "absent" before posting. This is NOT atomic idempotency. Coordinate one writer per
log; on duplicate detection, stop and request review rather than deleting/editing history automatically.
Corrections to past entries are new comments referencing the old comment, unless the user explicitly approves editing it.

## 6. Operator checks (manual, not executed model evals)

Try the behavioral cases in `tests/behavioral-scenarios.md` from the extracted distribution.
For native writes, use a disposable private repository only with explicit authorization:

| Input | Expected behavior |
|---|---|
| `$github-project-director` + business goal and story | Read context/duplicates; propose a goal-linked small slice and acceptance conditions; no write yet |
| "監査だけして" | No Issue mutation and no recurring comment |
| "この変更案を反映し、定例#42にも記録" | Confirm scope already shown; edit only approved tasks, read back, append a **release-note-quality** update to #42 |
| "進捗を定例へ記録して。担当は変更しない" | Log only; prose/bullets explain current state and next action; no assignee/status/date changes |
| No log target / several matching log Issues | One focused target/creation question, not arbitrary selection |
| Retry after uncertain comment POST | Re-read same entry-key and compare; no blind duplicate POST |
| One assignment edit fails | Other successes preserved; failure explained naturally without claiming all succeeded |
| Log comments incomplete / restricted | Disclose partial coverage; do not claim no previous entry exists |
| A technical maintenance request without a user story | Link an operational/quality goal; do not fabricate a user story |

The tests shipped with the installer validate plumbing and static instruction contracts. They do not prove
that a live model will always produce excellent prose or that GitHub writes will succeed.

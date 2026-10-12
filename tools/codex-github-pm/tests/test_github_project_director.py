"""Offline regression tests. No real GitHub writes or Codex inference."""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


installer = module("pm_installer", ROOT / "scripts/install_github_pm.py")
inspect = module("pm_inspect", ROOT / "skills/github-project-director/scripts/github_inspect.py")


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "日本語 home ' $()"
        self.home.mkdir()
        self.target = self.home / ".agents/skills" / installer.NAME
        self.bin = self.home / ".local/bin"
        self.codex_home = self.home / ".codex"
        env = patch.dict(os.environ, {"CODEX_HOME": str(self.codex_home)})
        env.start()
        self.addCleanup(env.stop)

    def install(self, force=False, dry=False):
        with contextlib.redirect_stdout(io.StringIO()):
            installer.install(self.target, force, dry, False, self.bin, None)

    def snapshot(self):
        return {str(p.relative_to(self.home)): (p.read_bytes(), p.stat().st_mtime_ns)
                for p in self.home.rglob("*") if p.is_file()}

    def test_dry_run_has_no_persistent_changes(self):
        before = self.snapshot()
        with patch.object(installer, "download", side_effect=AssertionError("network")):
            self.install(dry=True)
        self.assertEqual(before, self.snapshot())

    def test_installs_skill_and_metadata(self):
        self.install()
        self.assertTrue((self.target / "SKILL.md").is_file())
        self.assertEqual(installer.load_owned(self.target)["version"], installer.VERSION)

    def test_reinstall_is_exact_noop(self):
        self.install()
        before = self.snapshot()
        self.install()
        self.assertEqual(before, self.snapshot())

    def test_preserves_local_edits_without_force(self):
        self.install()
        (self.target / "SKILL.md").write_text("user edits")
        before = self.snapshot()
        self.install()
        self.assertEqual(before, self.snapshot())

    def test_force_backs_up_and_preserves_extra_files(self):
        self.install()
        (self.target / "SKILL.md").write_text("user edits")
        (self.target / "custom.md").write_text("custom")
        self.install(force=True)
        self.assertEqual((self.target / "custom.md").read_text(), "custom")
        backups = list(self.target.parent.glob(".*.backup-*"))
        self.assertEqual(len(backups), 1)
        with zipfile.ZipFile(backups[0]) as archive:
            self.assertEqual(archive.read("SKILL.md").decode(), "user edits")
        self.assertEqual(list(self.target.parent.glob("*/SKILL.md")), [self.target / "SKILL.md"])

    def test_unmanaged_target_refused_even_force(self):
        self.target.mkdir(parents=True)
        (self.target / "SKILL.md").write_text("foreign")
        with self.assertRaises(ValueError):
            self.install(force=True)
        self.assertEqual((self.target / "SKILL.md").read_text(), "foreign")

    def test_invalid_manifest_preserved(self):
        self.install()
        (self.target / installer.MANIFEST).write_text("{")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.install(force=True)
        self.assertEqual(before, self.snapshot())

    def test_manifest_traversal_refused(self):
        self.install()
        (self.target / installer.MANIFEST).write_text(json.dumps({"name": installer.NAME, "files": {"../bad": "a" * 64}}))
        with self.assertRaises(ValueError):
            self.install(force=True)

    def test_symlink_target_refused(self):
        link = self.home / "link"
        link.symlink_to(self.home, target_is_directory=True)
        with self.assertRaises(ValueError):
            installer.safe_path(link / "skill")

    def test_symlink_inside_skill_refused(self):
        self.install()
        (self.target / "bad").symlink_to(self.home)
        with self.assertRaises(ValueError):
            self.install(force=True)

    def test_foreign_config_untouched(self):
        for path in (".codex/hooks.json", ".codex/config.toml", ".codex/basic-memory.json", "AGENTS.md", "knowledge/note.md"):
            p = self.home / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("never change this")
        before = self.snapshot()
        self.install()
        for p, value in before.items():
            self.assertEqual(self.snapshot()[p], value)

    def test_concurrent_lock_refused(self):
        self.target.parent.mkdir(parents=True)
        lock = self.target.parent / f".{installer.NAME}.install-lock"
        lock.mkdir()
        with self.assertRaises(FileExistsError):
            self.install()
        self.assertTrue(lock.exists())

    def test_staging_failure_retains_old_install(self):
        self.install()
        before = self.snapshot()
        with patch.object(installer.shutil, "copyfile", side_effect=OSError("simulated disk failure")):
            with self.assertRaises(OSError):
                self.install(force=True)
        self.assertEqual(before, self.snapshot())

    def test_uninstall_preserves_user_files_and_gh(self):
        self.install()
        (self.target / "custom.md").write_text("keep")
        with contextlib.redirect_stdout(io.StringIO()):
            installer.uninstall(self.target, False, False)
        self.assertEqual((self.target / "custom.md").read_text(), "keep")
        self.assertFalse((self.target / "SKILL.md").exists())

    def test_uninstall_refuses_modified(self):
        self.install()
        (self.target / "SKILL.md").write_text("edited")
        with self.assertRaises(ValueError):
            installer.uninstall(self.target, False, False)

    def test_uninstall_dry_run(self):
        self.install()
        before = self.snapshot()
        with contextlib.redirect_stdout(io.StringIO()):
            installer.uninstall(self.target, True, False)
        self.assertEqual(before, self.snapshot())

    def test_doctor_read_only_without_tools(self):
        self.install()
        before = self.snapshot()
        with patch.object(installer.shutil, "which", return_value=None), contextlib.redirect_stdout(io.StringIO()) as out:
            code = installer.doctor(self.target, "github.com")
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(out.getvalue())["gh"])
        self.assertEqual(before, self.snapshot())

    def test_final_swap_failure_restores_previous_install(self):
        self.install()
        before = self.snapshot()
        original = Path.rename
        def rename(path, target):
            if ".stage-" in path.name:
                raise OSError("simulated swap failure")
            return original(path, target)
        with patch.object(Path, "rename", rename):
            with self.assertRaises(OSError):
                self.install(force=True)
        after = self.snapshot()
        for name, value in before.items():
            self.assertEqual(after[name], value)
        self.assertTrue(all(".backup-" in name and name.endswith(".zip") for name in after.keys() - before.keys()))

    def test_new_payload_does_not_replace_unowned_collision(self):
        self.install()
        data = installer.load_owned(self.target)
        data["files"].pop("SKILL.md")
        (self.target / installer.MANIFEST).write_text(json.dumps(data))
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "user-added"):
            self.install(force=True)
        self.assertEqual(before, self.snapshot())

    def test_manifest_wrong_type_refused(self):
        self.install()
        (self.target / installer.MANIFEST).write_text("[]")
        with self.assertRaises(ValueError):
            self.install(force=True)

    def test_doctor_never_prints_mcp_credentials(self):
        self.install()
        def run(args, **kwargs):
            out = json.dumps([{"name": "github", "env": {"TOKEN": "never-print-this"}}])
            return subprocess.CompletedProcess(args, 0, out, "secret-should-stay-hidden")
        with patch.object(installer.shutil, "which", side_effect=lambda n: n), patch.object(installer, "run", side_effect=run), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(installer.doctor(self.target, "github.com"), 0)
        self.assertIn("github", out.getvalue())
        self.assertNotIn("never-print-this", out.getvalue())
        self.assertNotIn("secret-should-stay-hidden", out.getvalue())

    def test_gh_checksum_validated_without_archive_extraction(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as z:
            for name, body in [("gh_1.2.3_linux_amd64/bin/gh", b"fixture"), ("../../bad", b"never extract")]:
                entry = tarfile.TarInfo(name)
                entry.size = len(body)
                z.addfile(entry, io.BytesIO(body))
        archive = buf.getvalue()
        sha = hashlib.sha256(archive).hexdigest()
        def fetch(url, limit):
            return f"{sha}  gh_1.2.3_linux_amd64.tar.gz\n".encode() if url.endswith(".txt") else archive
        with patch.object(installer, "download", side_effect=fetch), patch.object(installer.platform, "system", return_value="Linux"), patch.object(installer.platform, "machine", return_value="x86_64"):
            self.assertEqual(installer.gh_release("1.2.3"), ("1.2.3", sha, b"fixture"))

    def test_gh_bad_checksum_rejected(self):
        with patch.object(installer, "download", side_effect=[b"0" * 64 + b"  gh_1.2.3_linux_amd64.tar.gz\n", b"bad"]), patch.object(installer.platform, "system", return_value="Linux"), patch.object(installer.platform, "machine", return_value="x86_64"):
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                installer.gh_release("1.2.3")

    def test_gh_invalid_version_no_network(self):
        with patch.object(installer, "download", side_effect=AssertionError("network")):
            with self.assertRaises(ValueError):
                installer.gh_release("$(bad)")


class InventoryTests(unittest.TestCase):
    def api(self, responses, limit=20):
        calls, iterator = [], iter(responses)
        def runner(args, **kwargs):
            calls.append((args, kwargs))
            data = next(iterator)
            if isinstance(data, Exception):
                raise data
            return subprocess.CompletedProcess(args, 0, json.dumps(data), "")
        return inspect.GitHub(max_pages=limit, runner=runner), calls

    def test_rest_paginates(self):
        api, calls = self.api([[{"id": i} for i in range(100)], [{"id": 100}]])
        data = api.pages("repos/a/b/issues?state=all")
        self.assertTrue(data["complete"])
        self.assertEqual(len(data["items"]), 101)
        self.assertIn("page=2", calls[1][0][-1])
        self.assertTrue(all(c[0][c[0].index("--method") + 1] == "GET" for c in calls))

    def test_rest_limit_explicit(self):
        api, _ = self.api([[{}] * 100], limit=1)
        self.assertFalse(api.pages("repos/a/b/issues")["complete"])

    def test_rest_second_page_failure_preserves_partial(self):
        api, _ = self.api([[{}] * 100, OSError("network")])
        data = api.pages("repos/a/b/issues")
        self.assertFalse(data["complete"])
        self.assertEqual(len(data["items"]), 100)

    def test_graphql_pagination(self):
        api, calls = self.api([{"data": {"x": {"nodes": [{"id": 1}], "pageInfo": {"hasNextPage": True, "endCursor": "next"}}}},
                               {"data": {"x": {"nodes": [{"id": 2}], "pageInfo": {"hasNextPage": False}}}}])
        out = api.connection("query($after:String){x{nodes{id}}}", {}, ["x"])
        self.assertTrue(out["complete"])
        self.assertEqual(json.loads(calls[1][1]["input"])["variables"]["after"], "next")

    def test_graphql_errors_not_empty(self):
        api, _ = self.api([{"data": None, "errors": [{"message": "private secret"}]}])
        out = api.connection("query{x}", {}, ["x"])
        self.assertFalse(out["complete"])
        self.assertNotIn("private secret", out["error"])

    def test_repeated_cursor_detected(self):
        page = {"data": {"x": {"nodes": [], "pageInfo": {"hasNextPage": True, "endCursor": "same"}}}}
        api, _ = self.api([page, page])
        self.assertIn("repeated", api.connection("query{x}", {}, ["x"])["error"])

    def test_graphql_limit_reported(self):
        api, _ = self.api([{"data": {"x": {"nodes": [], "pageInfo": {"hasNextPage": True, "endCursor": "n"}}}}], limit=1)
        self.assertFalse(api.connection("query{x}", {}, ["x"])["complete"])

    def test_mutation_rejected(self):
        api, calls = self.api([])
        with self.assertRaises(inspect.ReadError):
            api.request("graphql", {"query": "mutation{createIssue}"})
        self.assertEqual(calls, [])

    def test_rest_post_rejected(self):
        api, calls = self.api([])
        with self.assertRaises(inspect.ReadError):
            api.request("repos/a/b/issues", {"query": "query{x}"})
        self.assertEqual(calls, [])

    def test_repo_validation_rejects_shell_and_urls(self):
        for name in ("-R x", "a/b;touch bad", "https://github.com/a/b", "a/..", "a/b/c"):
            with self.subTest(name=name), self.assertRaises(argparse.ArgumentTypeError):
                inspect.repository(name)
        self.assertEqual(inspect.repository("Mak-GIBA/basic-memory-workgraph"), "Mak-GIBA/basic-memory-workgraph")

    def test_hostname_rejects_path_and_flags(self):
        for value in ("-x", "https://github.com", "a;bad", "a/b"):
            with self.assertRaises(argparse.ArgumentTypeError):
                inspect.hostname(value)

    def test_graphql_variables_not_shell(self):
        api, calls = self.api([{"data": {"x": 1}}])
        api.request("graphql", {"query": "query{x}", "variables": {"text": "$(touch /bad)"}})
        self.assertNotIn("shell", calls[0][1])
        self.assertIn("$(touch /bad)", calls[0][1]["input"])
        self.assertNotIn("$(touch /bad)", " ".join(calls[0][0]))

    def test_cli_failure_does_not_leak_stderr(self):
        api = inspect.GitHub(runner=lambda args, **kwargs: subprocess.CompletedProcess(args, 1, "", "token=secret"))
        with self.assertRaises(inspect.ReadError) as ctx:
            api.request("user")
        self.assertNotIn("secret", str(ctx.exception))

    def test_non_json_error(self):
        api = inspect.GitHub(runner=lambda args, **kwargs: subprocess.CompletedProcess(args, 0, "oops", ""))
        with self.assertRaises(inspect.ReadError):
            api.request("user")

    def test_snapshot_filters_prs_and_reads_all_collections(self):
        api, calls = self.api([{"full_name": "a/b"},
            [{"number": 1}, {"number": 2, "pull_request": {}}], [], [], [], [],
            {"data": {"repository": {"projectsV2": {"nodes": [], "pageInfo": {"hasNextPage": False}}}}}])
        data = inspect.snapshot(api, "a/b")
        self.assertEqual([x["number"] for x in data["issues"]["items"]], [1])
        self.assertTrue(data["linked_projects"]["complete"])
        self.assertEqual(len(calls), 7)

    def test_redirect_requires_confirmation(self):
        api, _ = self.api([{"full_name": "other/repo"}])
        with self.assertRaisesRegex(inspect.ReadError, "another name"):
            inspect.snapshot(api, "a/b")

    def test_body_truncation_marked(self):
        data = inspect.summarize(inspect.result([{"body": "x" * 13000}], True, 1), ("body",))
        self.assertTrue(data["items"][0]["body_truncated"])

    def test_project_field_values_pagination_disclosed(self):
        info = {"data": {"user": {"projectV2": {"id": "PVT"}}}}
        fields = {"data": {"user": {"projectV2": {"fields": {"nodes": [{"id": "F", "name": "期限", "dataType": "DATE"}], "pageInfo": {"hasNextPage": False}}}}}}
        items = {"data": {"user": {"projectV2": {"items": {"nodes": [{"id": "I", "content": None, "fieldValues": {"nodes": [], "pageInfo": {"hasNextPage": True}}}], "pageInfo": {"hasNextPage": False}}}}}}
        api, calls = self.api([info, fields, items])
        data = inspect.project(api, "owner", 1, "user")
        self.assertFalse(data["field_values_complete"])
        self.assertEqual(data["items_needing_field_pagination"], ["I"])
        self.assertTrue(all(json.loads(x[1]["input"])["query"].startswith("query") for x in calls))

    def test_unavailable_project_not_empty(self):
        api, _ = self.api([{"data": {"organization": {"projectV2": None}}}])
        with self.assertRaises(inspect.ReadError):
            inspect.project(api, "org", 1, "organization")

    def test_relations_read_native_endpoints(self):
        api, calls = self.api([{"number": 1}, {"number": 2}, [], [], []])
        inspect.relations(api, "a/b", 2)
        paths = [x[0][-1] for x in calls]
        self.assertTrue(any("/sub_issues" in x for x in paths))
        self.assertTrue(any("/dependencies/blocked_by" in x for x in paths))
        self.assertTrue(any("/dependencies/blocking" in x for x in paths))
        self.assertTrue(all(x[0][x[0].index("--method")+1] == "GET" for x in calls))


class SkillContractTests(unittest.TestCase):
    def test_implicit_enabled_and_natural_triggers(self):
        base = ROOT / "skills/github-project-director"
        self.assertIn("allow_implicit_invocation: true", (base / "agents/openai.yaml").read_text())
        text = (base / "SKILL.md").read_text()
        for phrase in ("Issue構成を見直して", "認証機能をIssueにして", "要件からタスクを洗い出して",
                       "大きすぎない", "2週間のタスク", "抜けているIssue"):
            self.assertIn(phrase, text)

    def test_workflow_has_read_approval_verify_and_no_dependency(self):
        text = (ROOT / "skills/github-project-director/SKILL.md").read_text()
        for phrase in ("analysis -> proposal -> user confirmation", "re-read", "verify", "complete/pages/error",
                       "same", "Basic Memory/ECC/SpecKitがなくても動く", "transactionality"):
            self.assertIn(phrase, text)

    def test_recipes_cover_requested_native_writes(self):
        text = (ROOT / "skills/github-project-director/references/native-operations.md").read_text()
        for phrase in ("gh issue create", "gh issue edit", "sub_issue_id", "dependencies/blocked_by",
                       "gh label create", "--add-assignee", "--milestone", "gh project item-add",
                       "--single-select-option-id", "--date", "--clear", "read:project", "fine-grained"):
            self.assertIn(phrase, text)


    def test_posting_policy_is_shared_by_entrypoints(self):
        # Contract regression only; model decisions are checked separately with fixed scenarios.
        base = ROOT / "skills/github-project-director"
        skill = (base / "SKILL.md").read_text()
        writing = (base / "references/writing-and-tracking.md").read_text()
        planning = (base / "references/planning-and-meetings.md").read_text()
        native = (base / "references/native-operations.md").read_text()
        for text in (skill, planning, native):
            self.assertIn("writing-and-tracking.md", text)
        for phrase in ("共有価値", "新情報", "範囲と場所", "変化がなければ投稿しない", "既に", "未承認", "会話"):
            self.assertIn(phrase, writing)
        for text in (skill, planning):
            self.assertNotIn("A progress/assignment update should propose the log entry", text)
            self.assertNotIn("2–4 sentence overview", text)
        for phrase in ("Write the update like a release note", "Synthesize", "not a mandatory word-for-word template"):
            self.assertIn(phrase, planning)

    def test_behavioral_fixture_covers_silence_and_important_information(self):
        import re
        text = (ROOT / "tests/behavioral-scenarios.md").read_text()
        cases = set(re.findall(r"^### (B\d+)", text, re.MULTILINE))
        self.assertEqual(cases, {f"B{i:02d}" for i in range(1, 18)})
        self.assertIn("実行結果ではない", text)


class MeetingReaderTests(unittest.TestCase):
    """Real helper with a fake gh transport; no GitHub writes."""
    def api(self, responses, limit=20, host="github.com"):
        calls, iterator = [], iter(responses)
        def runner(args, **kwargs):
            calls.append((args, kwargs))
            data = next(iterator)
            if isinstance(data, Exception):
                raise data
            return subprocess.CompletedProcess(args, 0, json.dumps(data), "")
        return inspect.GitHub(host=host, max_pages=limit, runner=runner), calls

    def issue(self, **overrides):
        return {"number": 42, "id": 4242, "html_url": "https://github.com/a/b/issues/42",
                "title": "定例：申込みアプリ", "body": "進捗と担当を記録する。",
                "state": "open", "locked": False, **overrides}

    def comment(self, num, body):
        return {"id": num, "html_url": f"https://github.com/a/b/issues/42#issuecomment-{num}",
                "body": body, "user": {"login": "reviewer"}, "created_at": "2026-09-30T00:00:00Z"}

    def test_empty_history_is_absent_only_when_complete(self):
        api, calls = self.api([self.issue(), []])
        data = inspect.meeting(api, "a/b", 42, "batch-1")
        self.assertEqual(data["entry_lookup"]["state"], "absent")
        self.assertTrue(data["entry_lookup"]["complete"])
        self.assertTrue(all(args[args.index("--method") + 1] == "GET" for args, _ in calls))

    def test_without_key_is_history_not_absence_check(self):
        api, _ = self.api([self.issue(), []])
        data = inspect.meeting(api, "a/b", 42)
        self.assertEqual(data["entry_lookup"]["state"], "not_requested")
        self.assertIsNone(data["entry_lookup"]["marker"])

    def test_second_page_match_found(self):
        first = [self.comment(i, "前回の報告") for i in range(100)]
        body = "<!-- github-project-director:entry:batch-1 -->\n# 今回の報告"
        api, calls = self.api([self.issue(), first, [self.comment(100, body)]])
        data = inspect.meeting(api, "a/b", 42, "batch-1")
        self.assertEqual(len(data["comments"]["items"]), 101)
        self.assertEqual(data["entry_lookup"]["matches"][0]["id"], 100)
        self.assertEqual(data["entry_lookup"]["state"], "found")
        self.assertIn("page=2", calls[-1][0][-1])

    def test_limit_is_unknown_not_absent(self):
        api, _ = self.api([self.issue(), [self.comment(i, "古い報告") for i in range(100)]], limit=1)
        data = inspect.meeting(api, "a/b", 42, "batch-1")
        self.assertFalse(data["entry_lookup"]["complete"])
        self.assertEqual(data["entry_lookup"]["state"], "unknown")

    def test_partial_failure_is_unknown_and_does_not_echo_secrets(self):
        api, _ = self.api([self.issue(), [self.comment(i, "古い報告") for i in range(100)], OSError("token=secret")])
        data = inspect.meeting(api, "a/b", 42, "batch-1")
        self.assertEqual(data["entry_lookup"]["state"], "unknown")
        self.assertEqual(len(data["comments"]["items"]), 100)
        self.assertNotIn("token=secret", json.dumps(data))

    def test_unreadable_body_is_unknown(self):
        api, _ = self.api([self.issue(), [self.comment(1, None)]])
        data = inspect.meeting(api, "a/b", 42, "batch-1")
        self.assertEqual(data["entry_lookup"]["state"], "unknown")
        self.assertIn("unavailable", data["comments"]["error"])
        self.assertIsNone(data["comments"]["items"][0]["body_sha256"])

    def test_found_on_incomplete_history_is_not_uniqueness_proof(self):
        first = [self.comment(0, "<!-- github-project-director:entry:batch-1 -->\n記録")]
        first += [self.comment(i, "別の報告") for i in range(1, 100)]
        api, _ = self.api([self.issue(), first], limit=1)
        data = inspect.meeting(api, "a/b", 42, "batch-1")
        self.assertEqual(data["entry_lookup"]["state"], "found")
        self.assertFalse(data["entry_lookup"]["complete"])

    def test_hash_covers_full_untruncated_body(self):
        body = "<!-- github-project-director:entry:batch-1 -->\n" + "あ" * 13000
        api, _ = self.api([self.issue(), [self.comment(1, body)]])
        data = inspect.meeting(api, "a/b", 42, "batch-1")
        c = data["comments"]["items"][0]
        self.assertTrue(c["body_truncated"])
        self.assertEqual(len(c["body"]), 12000)
        self.assertEqual(c["body_sha256"], hashlib.sha256(body.encode()).hexdigest())
        self.assertEqual(data["entry_lookup"]["matches"][0]["body_sha256"], c["body_sha256"])

    def test_marker_requires_exact_first_line(self):
        marker = "<!-- github-project-director:entry:batch-1 -->"
        api, _ = self.api([self.issue(), [self.comment(1, "引用\n" + marker),
                                            self.comment(2, "> " + marker),
                                            self.comment(3, "<!-- github-project-director:entry:batch-10 -->")]])
        data = inspect.meeting(api, "a/b", 42, "batch-1")
        self.assertEqual(data["entry_lookup"]["state"], "absent")

    def test_multiple_matches_are_reported_not_merged(self):
        body = "<!-- github-project-director:entry:batch-1 -->\n同じキー"
        api, _ = self.api([self.issue(), [self.comment(1, body), self.comment(2, body + "別内容")]])
        data = inspect.meeting(api, "a/b", 42, "batch-1")
        self.assertTrue(data["entry_lookup"]["multiple_matches"])
        self.assertEqual(len(data["entry_lookup"]["matches"]), 2)
        self.assertNotEqual(*[x["body_sha256"] for x in data["entry_lookup"]["matches"]])

    def test_pull_request_is_not_meeting_issue(self):
        api, calls = self.api([self.issue(pull_request={})])
        with self.assertRaises(inspect.ReadError):
            inspect.meeting(api, "a/b", 42)
        self.assertEqual(len(calls), 1)

    def test_redirect_or_wrong_issue_is_rejected(self):
        for values in ({"number": 41}, {"html_url": "https://github.com/a/c/issues/42"},
                       {"html_url": "https://evil.example/a/b/issues/42"}):
            with self.subTest(values=values):
                api, _ = self.api([self.issue(**values)])
                with self.assertRaises(inspect.ReadError):
                    inspect.meeting(api, "a/b", 42)

    def test_enterprise_host_and_closed_locked_status_preserved(self):
        api, calls = self.api([self.issue(html_url="https://git.example/a/b/issues/42",
                                         state="closed", locked=True), []], host="git.example")
        data = inspect.meeting(api, "a/b", 42)
        self.assertEqual(data["issue"]["state"], "closed")
        self.assertTrue(data["issue"]["locked"])
        self.assertTrue(all("git.example" in args for args, _ in calls))

    def test_invalid_key_is_rejected_before_network(self):
        for key in ("", "$(touch bad)", "../../x", "a\n-->", "あ", "x" * 97):
            with self.subTest(key=key):
                api, calls = self.api([])
                with self.assertRaises(argparse.ArgumentTypeError):
                    inspect.meeting(api, "a/b", 42, key)
                self.assertEqual(calls, [])
        self.assertEqual(inspect.entry_key("2026-09-30_batch.1"), "2026-09-30_batch.1")

    def test_cli_dispatches_meeting_without_mutation(self):
        argv = ["github_inspect.py", "meeting", "--repo", "a/b", "--issue", "42", "--entry-key", "batch-1"]
        with patch.object(sys, "argv", argv), patch.object(inspect.shutil, "which", return_value="gh"), \
             patch.object(inspect, "meeting", return_value={"comments": {"complete": True}}) as call, \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(inspect.main(), 0)
        self.assertEqual(call.call_args.args[1:], ("a/b", 42, "batch-1"))
        self.assertIn("observed_at", json.loads(out.getvalue()))


class ExtendedSkillContractTests(unittest.TestCase):
    """Static policy checks, not proof of live model behavior."""
    def setUp(self):
        self.root = ROOT / "skills/github-project-director"
        self.skill = (self.root / "SKILL.md").read_text()
        self.ref = (self.root / "references/planning-and-meetings.md").read_text()
        self.native = (self.root / "references/native-operations.md").read_text()

    def test_explicit_and_implicit_invocation_coexist(self):
        meta = (self.root / "agents/openai.yaml").read_text()
        self.assertIn("$github-project-director", meta)
        self.assertIn("allow_implicit_invocation: true", meta)
        for value in ("Explicit invocation", "その後ろ／次の行", "書き込みの承認ではなく"):
            self.assertIn(value, self.skill)

    def test_goal_story_mapping_and_non_story_exception(self):
        for value in ("事業目的 → 利用者", "完了条件", "利用者の成果として確認できる単位", "架空のユーザーストーリーは作らない"):
            self.assertIn(value, self.skill)
        self.assertIn("current Issues/PRs", self.ref)

    def test_plain_issue_style_and_preserved_acceptance(self):
        for value in ("一読で理解", "目的 / やること / 完了条件 / 関連", "Conciseness must not remove"):
            self.assertIn(value, self.skill)
        self.assertIn("別の利用者", (self.root / "references/writing-and-tracking.md").read_text())

    def test_append_only_separate_from_actual_task_fields(self):
        for value in ("同じ定例Issue", "記録先", "record-only", "No scheduled job", "Exclude recurring log Issues"):
            self.assertIn(value, self.skill)
        for value in ("--edit-last", "--delete-last", "not user approval", "not make concurrent POSTs atomic"):
            self.assertIn(value, self.skill)

    def test_native_post_and_readback_recipes_present(self):
        for value in ("gh issue comment", "--body-file", "/comments", "--entry-key", "entry-key", "GET", "one transport"):
            self.assertIn(value, self.native)
        self.assertIn("append a human-readable update based on the **observed result**", self.ref)

    def test_new_reference_is_required_install_asset(self):
        self.assertEqual(installer.VERSION, "1.3.1")
        self.assertIn("references/planning-and-meetings.md", installer.members(installer.SOURCE))
        text = (ROOT / "scripts/install_github_pm.py").read_text()
        self.assertIn('"references/planning-and-meetings.md"', text)

    def test_manual_scenarios_disclose_live_model_limit(self):
        self.assertIn("manual, not executed model evals", self.ref)
        self.assertIn("They do not prove", self.ref)


class GlobalGuidanceTests(unittest.TestCase):
    setUp = InstallerTests.setUp
    install = InstallerTests.install
    snapshot = InstallerTests.snapshot

    @property
    def guide(self):
        return self.codex_home / "AGENTS.md"

    def remove(self, force=False, dry=False):
        with contextlib.redirect_stdout(io.StringIO()):
            installer.uninstall(self.target, dry, force)

    def seed(self, content, filename="AGENTS.md"):
        self.codex_home.mkdir(exist_ok=True)
        path = self.codex_home / filename
        path.write_bytes(content)
        return path

    def test_install_records_actual_escaped_path(self):
        self.install()
        record = installer.load_owned(self.target)["guidance"]
        self.assertEqual(record["home"], str(self.codex_home))
        raw = self.guide.read_bytes()
        self.assertIn(json.dumps(str(self.target / "SKILL.md"), ensure_ascii=False).encode(), raw)
        bounds = installer.block_bounds(raw)
        self.assertEqual(record["sha256"], hashlib.sha256(raw[slice(*bounds)]).hexdigest())

    def test_management_routing_survives_install_and_force_update(self):
        self.seed(b"Keep unrelated instructions.\n")
        self.install()
        record = installer.load_owned(self.target)
        record["version"] = "1.2.0"
        (self.target / installer.MANIFEST).write_text(json.dumps(record))
        self.guide.write_bytes(self.guide.read_bytes().replace("重要な変化".encode(), "旧ルール".encode()))
        self.install(force=True)
        guide = self.guide.read_text()
        skill = (self.target / "SKILL.md").read_text()
        for phrase in ("進捗を確認して", "残タスクを整理して", "今週の優先順位を見直して", "詰まっている作業は？"):
            self.assertIn(phrase, guide)
            self.assertIn(phrase, skill.split("---", 2)[1])
        self.assertIn("起動と投稿は別", guide)
        self.assertIn("英語の同等表現", guide)
        self.assertTrue(guide.startswith("Keep unrelated instructions.\n"))
        self.assertEqual(guide.count(installer.GUIDE_BEGIN.decode()), 1)
        self.assertNotIn("旧ルール", guide)
        self.assertTrue(list(self.codex_home.glob("*.zip")))
        self.assertEqual(installer.load_owned(self.target)["version"], "1.3.1")
        before = self.snapshot()
        self.install()
        self.assertEqual(before, self.snapshot())

    def test_existing_bytes_preserved_on_update_and_remove(self):
        before = "# 共通の指示\r\n既存の内容（改行なし）".encode()
        self.seed(before)
        self.install()
        self.assertTrue(self.guide.read_bytes().startswith(before))
        self.guide.write_bytes(self.guide.read_bytes() + b"\nUser-added later\n")
        self.install(force=True)
        self.assertEqual(self.guide.read_bytes().count(installer.GUIDE_BEGIN), 1)
        self.remove()
        self.assertEqual(self.guide.read_bytes(), before + b"\nUser-added later\n")

    def test_new_file_removed_but_existing_empty_file_preserved(self):
        self.install()
        self.remove()
        self.assertFalse(self.guide.exists())
        self.seed(b"")
        self.install()
        self.remove()
        self.assertEqual(self.guide.read_bytes(), b"")

    def test_existing_override_selected_and_base_preserved(self):
        self.seed(b"base instructions\n")
        override = self.seed(b"override instructions\n", "AGENTS.override.md")
        self.install()
        self.assertEqual(self.guide.read_bytes(), b"base instructions\n")
        self.assertIn(installer.GUIDE_BEGIN, override.read_bytes())
        self.remove()
        self.assertEqual(override.read_bytes(), b"override instructions\n")

    def test_empty_override_does_not_shadow(self):
        override = self.seed(b" \n", "AGENTS.override.md")
        self.install()
        self.assertTrue(self.guide.exists())
        self.assertEqual(override.read_bytes(), b" \n")

    def test_edited_block_refused_without_force(self):
        self.install()
        self.guide.write_bytes(self.guide.read_bytes().replace(b"GitHub URL", b"GitHub links"))
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "Edited global"):
            self.remove()
        self.assertEqual(before, self.snapshot())
        self.remove(force=True)
        backups = list(self.codex_home.glob("*.zip"))
        self.assertEqual(len(backups), 1)
        with zipfile.ZipFile(backups[0]) as archive:
            self.assertIn(b"GitHub links", archive.read("AGENTS.md"))

    def test_malformed_and_unowned_blocks_rejected_even_force(self):
        for content in (installer.GUIDE_BEGIN, installer.GUIDE_END,
                        installer.guidance_block(self.target),
                        installer.guidance_block(self.target) * 2):
            with self.subTest(content=content[:50]):
                self.seed(content)
                with self.assertRaises(ValueError):
                    self.install(force=True)
                self.assertEqual(self.guide.read_bytes(), content)
                self.assertFalse(self.target.exists())

    def test_changed_owner_refused_even_force(self):
        self.install()
        self.guide.write_bytes(installer.guidance_block(self.home / "another-skill"))
        with self.assertRaisesRegex(ValueError, "owner"):
            self.install(force=True)

    def test_second_skill_directory_cannot_claim_global_rule(self):
        self.install()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "Unowned global"):
            installer.install(self.home / "other-skills" / installer.NAME, True, False, False, self.bin, None)
        self.assertEqual(before, self.snapshot())

    def test_shadow_detected_by_doctor_and_update_but_can_uninstall(self):
        self.install()
        override = self.seed(b"later override\n", "AGENTS.override.md")
        with patch.object(installer.shutil, "which", return_value=None), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(installer.doctor(self.target, "github.com"), 2)
        self.assertIn("shadowed", json.loads(out.getvalue())["guidance"]["error"])
        with self.assertRaisesRegex(ValueError, "shadowed"):
            self.install(force=True)
        self.remove()
        self.assertEqual(override.read_bytes(), b"later override\n")

    def test_missing_block_is_not_silently_recreated(self):
        self.install()
        self.guide.write_bytes(b"only user instructions\n")
        with self.assertRaisesRegex(ValueError, "missing"):
            self.install(force=True)
        self.assertEqual(self.guide.read_bytes(), b"only user instructions\n")

    def test_symlink_global_file_and_parent_rejected(self):
        real = self.home / "real"
        real.mkdir()
        self.codex_home.symlink_to(real, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            self.install()
        self.codex_home.unlink()
        self.codex_home.mkdir()
        real_file = real / "AGENTS.md"
        real_file.write_text("keep")
        self.guide.symlink_to(real_file)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            self.install()
        self.assertEqual(real_file.read_text(), "keep")

    def test_global_lock_refuses_concurrent_other_skill_install(self):
        self.codex_home.mkdir()
        lock = self.codex_home / f".{installer.NAME}.install-lock"
        lock.mkdir()
        with self.assertRaises(FileExistsError):
            self.install()
        self.assertTrue(lock.exists())
        self.assertFalse((self.target.parent / lock.name).exists())

    def test_explicit_codex_home_wins_and_is_reused(self):
        custom = self.home / "custom codex"
        with contextlib.redirect_stdout(io.StringIO()):
            installer.install(self.target, False, False, False, self.bin, None, custom)
        self.assertTrue((custom / "AGENTS.md").is_file())
        self.assertFalse(self.guide.exists())
        self.install(force=True)
        self.remove()
        self.assertFalse((custom / "AGENTS.md").exists())

    def test_changing_recorded_home_refused(self):
        self.install()
        with self.assertRaisesRegex(ValueError, "different --codex-home"):
            installer.install(self.target, True, False, False, self.bin, None, self.home / "other")

    def test_legacy_upgrade_registers_and_backs_up(self):
        self.install()
        old = installer.load_owned(self.target)
        old.pop("guidance")
        old["version"] = "1.1.0"
        (self.target / installer.MANIFEST).write_text(json.dumps(old))
        self.guide.unlink()
        before = self.snapshot()
        self.install()
        self.assertEqual(before, self.snapshot())
        self.install(force=True)
        self.assertEqual(installer.load_owned(self.target)["version"], installer.VERSION)
        self.assertTrue(self.guide.is_file())
        with zipfile.ZipFile(next(self.target.parent.glob("*.zip"))) as archive:
            self.assertEqual(json.loads(archive.read(installer.MANIFEST))["version"], "1.1.0")

    def test_legacy_uninstall_leaves_unowned_global_file(self):
        self.install()
        old = installer.load_owned(self.target)
        old.pop("guidance")
        (self.target / installer.MANIFEST).write_text(json.dumps(old))
        self.guide.write_text("user-only")
        self.remove()
        self.assertEqual(self.guide.read_text(), "user-only")

    def test_global_write_failure_restores_old_skill(self):
        self.install()
        # Force a block replacement so publication actually writes global guidance.
        self.guide.write_bytes(self.guide.read_bytes().replace(b"GitHub URL", b"GitHub links"))
        before = self.snapshot()
        with patch.object(installer, "atomic_bytes", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                self.install(force=True)
        for name, content in before.items():
            self.assertEqual(self.snapshot()[name], content)

    def test_uninstall_swap_failure_restores_both_resources(self):
        self.seed(b"keep this\n")
        self.install()
        before = self.snapshot()
        original = Path.rename
        def rename(path, target):
            if ".stage-" in path.name:
                raise OSError("swap failure")
            return original(path, target)
        with patch.object(Path, "rename", rename):
            with self.assertRaises(OSError):
                self.remove()
        for name, content in before.items():
            self.assertEqual(self.snapshot()[name], content)

    def test_initial_swap_failure_removes_new_global_rule(self):
        original = Path.rename
        def rename(path, target):
            if ".stage-" in path.name:
                raise OSError("swap failure")
            return original(path, target)
        with patch.object(Path, "rename", rename):
            with self.assertRaises(OSError):
                self.install()
        self.assertFalse(self.target.exists())
        self.assertFalse(self.guide.exists())

    def test_dry_run_update_and_uninstall_leave_all_bytes_and_times(self):
        self.install()
        before = self.snapshot()
        self.install(force=True, dry=True)
        self.remove(dry=True)
        self.assertEqual(before, self.snapshot())

    def test_invalid_guidance_record_refused_before_writes(self):
        self.install()
        old = installer.load_owned(self.target)
        old["guidance"]["file"] = "../../other"
        (self.target / installer.MANIFEST).write_text(json.dumps(old))
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "Invalid global"):
            self.install(force=True)
        self.assertEqual(before, self.snapshot())

    def test_global_home_inside_skill_refused(self):
        with self.assertRaisesRegex(ValueError, "outside the Skill"):
            installer.install(self.target, False, False, False, self.bin, None, self.target / "global")
        self.assertFalse(self.target.exists())

    def test_intervening_global_edit_is_preserved(self):
        self.install()
        stage = self.home / "stage"
        stage.mkdir()
        old = installer.load_owned(self.target)
        change = installer.plan_guidance(self.target, old, None, True)
        self.guide.write_bytes(self.guide.read_bytes() + b"new unrelated instruction\n")
        current = self.guide.read_bytes()
        with self.assertRaisesRegex(ValueError, "changed during"):
            installer.publish(stage, self.target, change, old)
        self.assertEqual(self.guide.read_bytes(), current)
        self.assertTrue((self.target / "SKILL.md").exists())

    def test_force_update_swap_failure_restores_edited_global_bytes_and_mode(self):
        self.install()
        self.guide.write_bytes(self.guide.read_bytes().replace(b"GitHub URL", b"GitHub links"))
        self.guide.chmod(0o600)
        before = self.snapshot()
        original = Path.rename
        def rename(path, target):
            if ".stage-" in path.name:
                raise OSError("swap failure")
            return original(path, target)
        with patch.object(Path, "rename", rename):
            with self.assertRaises(OSError):
                self.install(force=True)
        for name, content in before.items():
            self.assertEqual(self.snapshot()[name], content)
        self.assertEqual(self.guide.stat().st_mode & 0o777, 0o600)

    def test_rollback_preserves_concurrent_global_edit_and_restores_skill(self):
        self.install()
        self.guide.write_bytes(self.guide.read_bytes().replace(b"GitHub URL", b"GitHub links"))
        original = Path.rename
        user_bytes = b"Concurrent user instruction\n"
        def rename(path, target):
            if ".stage-" in path.name:
                self.guide.write_bytes(user_bytes)
                raise OSError("swap failure")
            return original(path, target)
        with patch.object(Path, "rename", rename):
            with self.assertRaisesRegex(RuntimeError, "left untouched"):
                self.install(force=True)
        self.assertEqual(self.guide.read_bytes(), user_bytes)
        self.assertTrue((self.target / "SKILL.md").is_file())
        for backup in self.codex_home.glob("*.zip"):
            self.assertEqual(backup.stat().st_mode & 0o777, 0o600)

    def test_cli_custom_codex_home_and_dry_run(self):
        custom = self.home / "cli-custom"
        args = [sys.executable, str(ROOT / "scripts/install_github_pm.py"), "--skills-dir", str(self.target.parent),
                "--codex-home", str(custom)]
        cp = subprocess.run(args + ["--dry-run"], capture_output=True, text=True)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertFalse(custom.exists())
        cp = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertTrue((custom / "AGENTS.md").exists())
        cp = subprocess.run(args + ["--uninstall"], capture_output=True, text=True)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertFalse((custom / "AGENTS.md").exists())


if __name__ == "__main__":
    unittest.main()

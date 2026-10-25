"""Real Git round trips with fictional notes and an in-process GitHub CLI server."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

SOURCE = Path(__file__).resolve().parent.parent / "tools/basic-memory-workgraph"
sys.path.insert(0, str(SOURCE))
import workgraph_github as github
import workgraph_tools as wg
import configure_workgraph as configure


class FakeCLI:
    def __init__(self, base):
        self.base = base
        self.remote = base / "remote.git"
        self.registry = base / "registry.json"
        self.registry.write_text('{"projects": {}}')
        self.private, self.push, self.auth = True, True, True
        self.prs, self.calls = [], []
        self.fail_create_after = False
        self.fail_push_after = False
        self.fail_merge_after = False
        self.reject_merge = False
        self.before_push = None
        self.real = github.command
        self.git("init", "--bare", "--initial-branch=main", str(self.remote))
        self.seed = base / "seed"
        self.git("clone", str(self.remote), str(self.seed))
        (self.seed / "README.md").write_text("Fictional memory repository\n")
        self.git("add", ".", cwd=self.seed)
        self.git("commit", "-m", "Initialize", cwd=self.seed)
        self.git("push", "origin", "main", cwd=self.seed)

    def git(self, *args, cwd=None):
        result = subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
                                cwd=cwd, capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stderr)
        return result.stdout.strip()

    def __call__(self, args, cwd=None):
        self.calls.append(list(args))
        if args[0] == "git":
            # Production forbids file transports; this test permits its isolated bare repository.
            args = [str(self.remote) if a == "https://github.com/example/memories.git" else
                    "protocol.file.allow=always" if a == "protocol.file.allow=never" else a for a in args]
            if "push" in args and self.before_push:
                callback, self.before_push = self.before_push, None
                callback()
            result = self.real(args, cwd)
            if "push" in args and self.fail_push_after:
                self.fail_push_after = False
                raise wg.Invalid("Simulated response loss after push")
            return result
        if args[:3] == ["gh", "auth", "status"]:
            if not self.auth:
                raise wg.Invalid("Not authenticated")
            return ""
        if args[:2] == ["gh", "api"]:
            if args[-1] == "user":
                return json.dumps({"login": "Example-User"})
            endpoint = next(a for a in args if a.startswith("repos/"))
            method = args[args.index("--method") + 1] if "--method" in args else "GET"
            if "/pulls" not in endpoint:
                return json.dumps({"full_name": "example/memories", "private": self.private,
                                   "permissions": {"push": self.push}, "default_branch": "main"})
            def rest(p):
                return {"number": p["number"], "html_url": p["url"], "merged_at": p["mergedAt"],
                        "state": "open" if p["state"] == "OPEN" else "closed", "title": p["title"], "body": p["body"],
                        "base": {"ref": p["baseRefName"]}, "head": {"ref": p["headRefName"],
                        "sha": self.git("rev-parse", p["headRefName"], cwd=self.remote),
                        "repo": {"full_name": "example/memories"}}}
            if method == "GET":
                query = parse_qs(urlparse(endpoint).query)
                branch = query["head"][0].split(":", 1)[1]
                matches = [rest(p) for p in reversed(self.prs) if p["headRefName"] == branch]
                page = int(query["page"][0])
                return json.dumps(matches[(page - 1) * 100:page * 100])
            payload = json.loads(Path(args[args.index("--input") + 1]).read_text())
            if method == "PUT" and endpoint.endswith("/merge"):
                if self.reject_merge:
                    raise wg.Invalid("Merge rejected by protection")
                number = int(endpoint.split("/")[-2])
                p = next(p for p in self.prs if p["number"] == number)
                if payload["sha"] != self.git("rev-parse", p["headRefName"], cwd=self.remote):
                    raise wg.Invalid("Head changed")
                self.merge(number)
                if self.fail_merge_after:
                    self.fail_merge_after = False
                    raise wg.Invalid("Lost merge response")
                return json.dumps({"merged": True})
            if method == "POST":
                p = {"number": len(self.prs) + 1, "url": "https://github.com/example/memories/pull/" + str(len(self.prs) + 1),
                     "state": "OPEN", "mergedAt": None, "baseRefName": payload["base"],
                     "headRefName": payload["head"], "title": payload["title"], "body": payload["body"]}
                self.prs.append(p)
                if self.fail_create_after:
                    self.fail_create_after = False
                    raise wg.Invalid("Simulated response loss after PR creation")
                return json.dumps(rest(p))
            p = next(p for p in self.prs if p["number"] == int(endpoint.rsplit("/", 1)[1]))
            p.update(title=payload["title"], body=payload["body"])
            return json.dumps(rest(p))
        if args[:3] == ["bm", "project", "add"]:
            data = json.loads(self.registry.read_text())
            data["projects"][args[3]] = {"path": args[4], "mode": "local"}
            Path(args[4]).mkdir(parents=True, exist_ok=True)
            self.registry.write_text(json.dumps(data))
            return ""
        raise AssertionError(args)

    def merge(self, number=None):
        p = next(p for p in self.prs if p["state"] == "OPEN" and (number is None or p["number"] == number))
        self.git("fetch", "origin", cwd=self.seed)
        self.git("merge", "--no-edit", "origin/" + p["headRefName"], cwd=self.seed)
        self.git("push", "origin", "main", cwd=self.seed)
        p.update(state="MERGED", mergedAt="2026-01-01T00:00:00Z")


class GitHubSharingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.server = FakeCLI(self.root)
        self.patcher = patch.object(github, "command", self.server)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.memory = self.root / "source memory"
        self.memory.mkdir()
        self.receiver = self.root / "received"
        self.codex = self.root / "codex"
        self.codex.mkdir()
        (self.codex / "basic-memory.json").write_text('{"basicMemory":{"primaryProject":"source"}}')
        self.server.registry.write_text(json.dumps({"projects": {"source": {"path": str(self.memory), "mode": "local"}}}))
        self.sharing = github.Sharing(self.codex, self.server.registry)

    def setup(self, role="publish", **overrides):
        args = argparse.Namespace(profile=role, source_id="source", repo="example/memories", role=role,
            base=None, project=None, memory_dir=self.receiver if role == "receive" else None,
            include_cases=False, dry_run=False)
        for key, value in overrides.items():
            setattr(args, key, value)
        return self.sharing.setup(args)

    def note(self, rel="rules/units.md", body="Preserve denominator definitions.", review=True, **metadata):
        note = wg.Note(rel, {"title": "Units", "type": "rule", **metadata}, "\n" + body + "\n")
        path = self.memory / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(note.render())
        if review:
            wg.review(argparse.Namespace(memory_dir=self.memory, note=rel, sharing="team", training="excluded", dry_run=False))
        return path

    def snapshot(self):
        return {str(p.relative_to(self.codex)): p.read_bytes() for p in self.codex.rglob("*") if p.is_file()}

    def test_publish_update_no_change_merge_and_next_pr(self):
        self.note()
        self.note("rules/private.md", review=False)
        self.setup()
        result = self.sharing.publish(None)
        self.assertEqual(result["status"], "published")
        self.assertEqual(len(self.server.prs), 1)
        calls = len(self.server.calls)
        again = self.sharing.publish(None)
        self.assertEqual(again["status"], "unchanged")
        self.assertFalse(any("PATCH" in c for c in self.server.calls[calls:]))
        self.note(body="Align denominators before comparing values.")
        self.assertEqual(self.sharing.publish(None)["updated"], 1)
        self.assertEqual(len(self.server.prs), 1)
        self.server.merge()
        self.note(body="Include units with aligned denominators.")
        self.sharing.publish(None)
        self.assertEqual(len(self.server.prs), 2)
        tree = self.server.git("ls-tree", "-r", "--name-only", "workgraph-share/source", cwd=self.server.remote)
        self.assertNotIn("private.md", tree)
        self.assertFalse(any("--force" in c for c in self.server.calls))

    def test_pull_waits_for_merge_and_updates_preserve_provenance(self):
        self.note()
        self.setup()
        self.setup("receive")
        self.sharing.publish("publish")
        with self.assertRaises(wg.Invalid):
            self.sharing.pull("receive")
        self.assertFalse((self.receiver / "rules/units.md").exists())
        self.server.merge()
        result = self.sharing.pull("receive")
        self.assertEqual(result["imported"], 1)
        note = wg.load_note(self.receiver, "rules/units.md")
        self.assertEqual(note.metadata["sharing_scope"], "private")
        self.assertEqual(note.metadata["training_use"], "excluded")
        self.assertEqual(note.metadata["privacy_review"], "pending")
        self.assertEqual(note.metadata["import_source"]["repo"], "example/memories")
        before = (self.receiver / "rules/units.md").read_bytes()
        self.assertEqual(self.sharing.pull("receive")["unchanged"], 1)
        self.assertEqual((self.receiver / "rules/units.md").read_bytes(), before)
        self.note(body="New verified reference data.")
        self.sharing.publish("publish")
        self.server.merge()
        self.assertEqual(self.sharing.pull("receive")["imported"], 1)
        self.assertIn("New verified", (self.receiver / "rules/units.md").read_text())

    def test_conflicts_stop_entire_batch_and_local_deletion_is_protected(self):
        self.note()
        self.setup()
        self.setup("receive")
        self.sharing.publish("publish")
        self.server.merge()
        self.sharing.pull("receive")
        target = self.receiver / "rules/units.md"
        for original in ("Local edit\n", None):
            if original is None:
                target.unlink()
            else:
                target.write_text(original)
            self.note("rules/new.md")
            self.note(body="Upstream change: " + ("edited" if original else "deleted") + ".")
            self.sharing.publish("publish")
            self.server.merge()
            result = self.sharing.pull("receive")
            self.assertEqual(result["conflicts"], ["rules/units.md"])
            self.assertFalse((self.receiver / "rules/new.md").exists())
            self.assertEqual(target.read_text() if target.exists() else None, original)

    def test_removed_notes_are_reported_without_deletion(self):
        source = self.note()
        self.setup()
        self.setup("receive")
        self.sharing.publish("publish")
        self.server.merge()
        self.sharing.pull("receive")
        original = (self.receiver / "rules/units.md").read_bytes()
        source.unlink()
        self.assertEqual(self.sharing.publish("publish")["removed"], 1)
        self.server.merge()
        self.assertEqual(self.sharing.pull("receive")["removed"], ["rules/units.md"])
        self.assertEqual((self.receiver / "rules/units.md").read_bytes(), original)

    def test_setup_publish_and_pull_dry_run_do_not_mutate(self):
        self.note()
        before = self.snapshot()
        registry = self.server.registry.read_bytes()
        self.setup(dry_run=True)
        self.setup("receive", dry_run=True)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.server.registry.read_bytes(), registry)
        self.assertFalse(self.receiver.exists())
        self.setup()
        before = self.snapshot()
        remote = self.server.git("show-ref", cwd=self.server.remote)
        self.assertEqual(self.sharing.publish(None, True)["status"], "planned")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.server.git("show-ref", cwd=self.server.remote), remote)
        self.assertEqual(self.server.prs, [])
        self.sharing.publish(None)
        self.server.merge()
        self.setup("receive")
        before = self.snapshot()
        self.sharing.pull("receive", True)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.receiver / "rules/units.md").exists())

    def test_failed_checks_do_not_push_or_silently_export_subset(self):
        path = self.note()
        self.setup()
        path.write_text(path.read_text() + "Changed without review\n")
        self.note("rules/second.md")
        result = self.sharing.publish(None)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(self.server.prs, [])
        self.assertFalse(any(c[0] == "git" and "push" in c for c in self.server.calls))

    def test_empty_share_does_not_create_pr(self):
        self.note(review=False)
        self.setup()
        self.assertEqual(self.sharing.publish(None)["status"], "unchanged")
        self.assertEqual(self.server.prs, [])

    def test_public_repo_permission_and_auth_fail_closed(self):
        self.note()
        self.setup()
        for field in ("private", "push", "auth"):
            with self.subTest(field=field):
                setattr(self.server, field, False)
                with self.assertRaises(wg.Invalid):
                    self.sharing.publish(None)
                setattr(self.server, field, True)
        self.assertEqual(self.server.prs, [])

    def test_lost_create_response_retry_does_not_duplicate_pr(self):
        self.note()
        self.setup()
        self.server.fail_create_after = True
        with self.assertRaises(wg.Invalid):
            self.sharing.publish(None)
        self.assertIsNotNone(self.sharing.status(None)["pr_url"])
        self.sharing.publish(None)
        self.assertEqual(len(self.server.prs), 1)

    def test_lost_push_response_retry_creates_single_pr(self):
        self.note()
        self.setup()
        self.server.fail_push_after = True
        with self.assertRaises(wg.Invalid):
            self.sharing.publish(None)
        self.assertEqual(self.server.prs, [])
        self.sharing.publish(None)
        self.assertEqual(len(self.server.prs), 1)

    def test_existing_pr_description_is_recovered_after_failed_update(self):
        self.note()
        self.setup()
        self.sharing.publish(None)
        self.server.prs[0]["body"] = "Stale summary after a response failure"
        self.sharing.publish(None)
        self.assertNotIn("Stale summary", self.server.prs[0]["body"])
        self.assertEqual(len(self.server.prs), 1)

    def test_reverting_an_open_pr_back_to_base_is_pushed(self):
        self.note(body="Original memory.")
        self.setup()
        self.sharing.publish(None)
        self.server.merge()
        self.note(body="Intermediate revision.")
        self.sharing.publish(None)
        self.note(body="Original memory.")
        self.sharing.publish(None)
        diff = self.server.git("diff", "--name-only", "main", "workgraph-share/source", cwd=self.server.remote)
        self.assertEqual(diff, "")
        self.assertEqual(len(self.server.prs), 2)

    def test_pr_history_is_paginated_and_closed_unmerged_pr_is_not_reopened(self):
        self.note()
        self.setup()
        self.sharing.publish(None)
        original = self.server.prs[0]
        self.server.prs = [{**original, "number": i + 2, "state": "MERGED", "mergedAt": "2026-01-01"}
                           for i in range(100)] + [original]
        self.sharing.publish(None)
        pages = [c for c in self.server.calls if any("page=2" in a for a in c)]
        self.assertTrue(pages)
        original["state"] = "CLOSED"
        with self.assertRaises(wg.Invalid):
            self.sharing.publish(None)

    def test_concurrent_push_is_rejected_without_overwriting_remote(self):
        self.note()
        self.setup()
        self.sharing.publish(None)
        def advance_remote():
            self.server.git("fetch", "origin", cwd=self.server.seed)
            self.server.git("checkout", "-b", "workgraph-share/source", "origin/workgraph-share/source", cwd=self.server.seed)
            (self.server.seed / "reviewer.txt").write_text("Concurrent writer")
            self.server.git("add", ".", cwd=self.server.seed)
            self.server.git("commit", "-m", "Concurrent writer", cwd=self.server.seed)
            self.server.git("push", "origin", "workgraph-share/source", cwd=self.server.seed)
        self.note(body="A second sender revision.")
        self.server.before_push = advance_remote
        with self.assertRaises(wg.Invalid):
            self.sharing.publish(None)
        tree = self.server.git("ls-tree", "-r", "--name-only", "workgraph-share/source", cwd=self.server.remote)
        self.assertIn("reviewer.txt", tree)

    def test_base_advancing_while_pr_is_open_is_merged_without_unrelated_pr_changes(self):
        self.note()
        self.setup()
        self.sharing.publish(None)
        (self.server.seed / "README.md").write_text("Base advanced independently\n")
        self.server.git("add", ".", cwd=self.server.seed)
        self.server.git("commit", "-m", "Update repository README", cwd=self.server.seed)
        self.server.git("push", "origin", "main", cwd=self.server.seed)
        self.note(body="Second shared revision.")
        self.sharing.publish(None)
        diff = self.server.git("diff", "--name-only", "main...workgraph-share/source", cwd=self.server.remote)
        self.assertNotIn("README.md", diff)
        self.assertEqual(len(self.server.prs), 1)

    def test_untrusted_bundle_changes_fail_before_any_receiver_writes(self):
        self.note()
        self.setup()
        self.setup("receive")
        self.sharing.publish("publish")
        self.server.merge()
        bundle = self.server.seed / "bundles/source"
        with self.sharing.lock("receive"):
            pass
        pristine = {p.relative_to(bundle): p.read_bytes() for p in bundle.rglob("*") if p.is_file()}
        for kind in ("checksum", "secret", "traversal", "unlisted", "symlink", "public"):
            with self.subTest(kind=kind):
                shutil.rmtree(bundle)
                for rel, data in pristine.items():
                    path = bundle / rel
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                note = bundle / "rules/units.md"
                manifest = json.loads((bundle / "manifest.json").read_text())
                if kind == "checksum":
                    note.write_text(note.read_text() + "Tampered text\n")
                elif kind == "secret":
                    note.write_text(note.read_text() + "Contact: fictional@example.invalid\n")
                    manifest["notes"][0]["sha256"] = wg.sha(note.read_bytes())
                elif kind == "traversal":
                    manifest["notes"][0]["path"] = "../outside.md"
                elif kind == "unlisted":
                    (bundle / "unexpected.txt").write_text("Extra file")
                elif kind == "symlink":
                    note.unlink()
                    note.symlink_to("../../README.md")
                else:
                    manifest["scope"] = "public"
                (bundle / "manifest.json").write_text(json.dumps(manifest))
                self.server.git("add", "-A", cwd=self.server.seed)
                self.server.git("commit", "-m", "Fictional malicious bundle: " + kind, cwd=self.server.seed)
                self.server.git("push", "origin", "main", cwd=self.server.seed)
                before = self.snapshot()
                with self.assertRaises(wg.Invalid):
                    self.sharing.pull("receive")
                self.assertEqual(self.snapshot(), before)
                self.assertFalse((self.receiver / "rules/units.md").exists())

    def test_pull_write_failure_rolls_back_notes_and_state(self):
        self.note()
        self.setup()
        self.setup("receive")
        self.sharing.publish("publish")
        self.server.merge()
        self.sharing.pull("receive")
        before = (self.receiver / "rules/units.md").read_bytes()
        state_before = self.snapshot()
        self.note(body="New upstream value.")
        self.note("rules/new.md")
        self.sharing.publish("publish")
        self.server.merge()
        real = wg.atomic_file
        failed = False
        def fail_once(path, content, replace=False):
            nonlocal failed
            if path.name == "receive.json" and not failed:
                failed = True
                raise OSError("Simulated disk failure")
            return real(path, content, replace)
        with patch.object(wg, "atomic_file", fail_once):
            with self.assertRaises(OSError):
                self.sharing.pull("receive")
        self.assertEqual((self.receiver / "rules/units.md").read_bytes(), before)
        self.assertFalse((self.receiver / "rules/new.md").exists())
        self.assertEqual(self.snapshot(), state_before)

    def test_profiles_are_immutable_and_receiver_requires_separate_empty_project(self):
        self.note()
        self.setup()
        before = self.snapshot()
        with self.assertRaises(wg.Invalid):
            self.setup(source_id="other")
        with self.assertRaises(wg.Invalid):
            self.setup("receive", memory_dir=self.memory)
        self.assertEqual(self.snapshot(), before)
        with self.assertRaises(wg.Invalid):
            self.setup(profile="../../unsafe")
        with self.assertRaises(wg.Invalid):
            self.setup(profile="duplicate")

    def test_unrelated_remote_branch_change_is_rejected(self):
        self.note()
        self.setup()
        self.sharing.publish(None)
        self.server.git("fetch", "origin", cwd=self.server.seed)
        self.server.git("checkout", "-b", "workgraph-share/source", "origin/workgraph-share/source", cwd=self.server.seed)
        (self.server.seed / "other.txt").write_text("Unrelated remote edit")
        self.server.git("add", ".", cwd=self.server.seed)
        self.server.git("commit", "-m", "Other change", cwd=self.server.seed)
        self.server.git("push", "origin", "workgraph-share/source", cwd=self.server.seed)
        with self.assertRaises(wg.Invalid):
            self.sharing.publish(None)

    def test_installer_preserves_other_agents_and_installed_cli_runs(self):
        original = "Existing personal instructions.\n<!-- github-project-director:begin -->\nOther block\n<!-- github-project-director:end -->\n"
        (self.codex / "AGENTS.md").write_text(original)
        configure.configure(self.codex)
        installed = self.codex / "basic-memory-workgraph/workgraph_github.py"
        result = subprocess.run([sys.executable, str(installed), "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("publish", result.stdout)
        self.assertTrue((self.codex / "AGENTS.md").read_text().startswith(original))
        first = self.snapshot()
        configure.configure(self.codex)
        self.assertEqual(self.snapshot(), first)
        result = subprocess.run(["bash", str(SOURCE / "remove_workgraph_hooks.sh")],
            env={**os.environ, "CODEX_HOME": str(self.codex)}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(configure.SHARING_BEGIN, (self.codex / "AGENTS.md").read_text())
        self.assertTrue((self.codex / "AGENTS.md").read_text().startswith(original))

    def test_caller_git_environment_does_not_redirect_temporary_checkout(self):
        self.note()
        self.setup()
        original = self.server.git("show-ref", cwd=self.server.remote)
        with patch.dict(os.environ, {"GIT_DIR": str(self.server.remote), "GIT_WORK_TREE": str(self.memory),
                                    "GIT_INDEX_FILE": str(self.root / "external-index")}):
            self.sharing.publish(None, True)
        self.assertEqual(self.server.git("show-ref", cwd=self.server.remote), original)
        self.assertFalse((self.root / "external-index").exists())

    def test_remote_attributes_cannot_run_a_locally_configured_filter(self):
        self.note()
        self.setup()
        self.setup("receive")
        self.sharing.publish("publish")
        self.server.merge()
        (self.server.seed / ".gitattributes").write_text("*.md filter=trap\n")
        self.server.git("add", ".gitattributes", cwd=self.server.seed)
        self.server.git("commit", "-m", "Select a local filter", cwd=self.server.seed)
        self.server.git("push", "origin", "main", cwd=self.server.seed)
        home = self.root / "isolated-home"
        home.mkdir()
        marker = self.root / "filter-executed"
        (home / ".gitconfig").write_text('[filter "trap"]\n\tsmudge = touch ' + str(marker) + '; cat\n')
        with patch.dict(os.environ, {"HOME": str(home)}):
            self.sharing.pull("receive")
        self.assertFalse(marker.exists())

    def friend_bundle(self, source="friend", body="Friend's verified reference."):
        """A friend's separately merged, valid bundle; no friend's PR is auto-merged."""
        self.server.git("fetch", "origin", cwd=self.server.seed)
        self.server.git("merge", "--no-edit", "origin/main", cwd=self.server.seed)
        note = wg.Note("rules/units.md", {"title": "Units", "type": "rule", "sharing_scope": "team",
            "training_use": "excluded", "privacy_review": "pending"}, "\n" + body + "\n")
        bundle = self.server.seed / "bundles" / source
        (bundle / "rules").mkdir(parents=True, exist_ok=True)
        (bundle / note.path).write_text(note.render())
        (bundle / "manifest.json").write_text(wg.json_text({"version": 1, "scope": "team", "notes": [
            {"path": note.path, "sha256": wg.sha(note.render().encode())}]}))
        self.server.git("add", ".", cwd=self.server.seed)
        self.server.git("commit", "-m", "Friend's shared knowledge", cwd=self.server.seed)
        self.server.git("push", "origin", "main", cwd=self.server.seed)

    def connect_sync(self):
        self.setup()
        return self.sharing.connect("example/memories")

    def test_connect_reuses_publisher_and_is_idempotent(self):
        self.setup()
        before = self.snapshot()
        self.sharing.connect("example/memories", dry_run=True)
        self.assertEqual(before, self.snapshot())
        result = self.sharing.connect("example/memories")
        self.assertEqual(result["profile"], "publish")
        before = self.snapshot()
        self.sharing.connect("EXAMPLE/memories")
        self.assertEqual(before, self.snapshot())
        self.assertEqual(len(self.sharing.config()["profiles"]), 1)

    def test_connect_fresh_defaults_and_requires_selection_if_ambiguous(self):
        result = self.sharing.connect("example/memories")
        self.assertEqual(result["source_id"], "example-user")
        self.assertEqual(self.sharing.profile(result["profile"])[1]["project"], "source")
        self.assertEqual(self.sharing.sync()["status"], "synced")

    def test_sync_dry_run_leaves_configuration_registry_files_and_remote_unchanged(self):
        self.note()
        self.connect_sync()
        self.friend_bundle()
        before = self.snapshot()
        registry = self.server.registry.read_bytes()
        tree = self.server.git("show-ref", cwd=self.server.remote)
        result = self.sharing.sync(dry_run=True)
        self.assertEqual(result["status"], "planned")
        self.assertEqual(result["merge"]["status"], "planned")
        self.assertEqual(result["receive"][0]["imported"], 1)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(registry, self.server.registry.read_bytes())
        self.assertEqual(tree, self.server.git("show-ref", cwd=self.server.remote))
        self.assertFalse((self.root / "shared-memory").exists())

    def test_sync_merges_our_pr_discovers_friend_and_is_repeatable(self):
        self.note()
        self.connect_sync()
        self.friend_bundle()
        config = self.codex / "basic-memory.json"
        config.write_text(wg.json_text({"unrelated": 42, "basicMemory": {"primaryProject": "source",
            "secondaryProjects": ["existing"], "teamProjects": {"other": "preserved"}}}))
        result = self.sharing.sync()
        self.assertEqual(result["merge"]["status"], "merged")
        self.assertEqual(result["receive"][0]["imported"], 1)
        project = result["receive"][0]["project"]
        self.assertEqual(self.server.prs[0]["state"], "MERGED")
        updated = json.loads(config.read_text())
        self.assertEqual(updated["unrelated"], 42)
        self.assertEqual(updated["basicMemory"]["primaryProject"], "source")
        self.assertEqual(updated["basicMemory"]["secondaryProjects"], ["existing", project])
        self.assertEqual(updated["basicMemory"]["teamProjects"], {"other": "preserved"})
        self.assertEqual(self.sharing.sync()["receive"][0]["unchanged"], 1)
        self.assertEqual(len(self.server.prs), 1)
        self.assertFalse(any("--force" in c or "--admin" in c for c in self.server.calls))

    def test_sync_preserves_local_edits_privately_then_updates_shared_copy(self):
        self.connect_sync()
        self.friend_bundle()
        initial = self.sharing.sync()
        project = initial["receive"][0]["project"]
        root = Path(json.loads(self.server.registry.read_text())["projects"][project]["path"])
        target = root / "rules/units.md"
        target.write_text("My own local edit without valid frontmatter.\n")
        self.friend_bundle(body="Friend's updated reference.")
        before = target.read_bytes()
        planned = self.sharing.sync(dry_run=True)
        self.assertEqual(planned["receive"][0]["preserved_edits"], 1)
        self.assertEqual(target.read_bytes(), before)
        result = self.sharing.sync()
        self.assertEqual(result["receive"][0]["preserved_edits"], 1)
        self.assertIn("Friend's updated", target.read_text())
        edits = result["receive"][0]["edits_project"]
        archive = Path(json.loads(self.server.registry.read_text())["projects"][edits]["path"])
        saved = list(archive.rglob("*.md"))
        self.assertEqual(len(saved), 1)
        note = wg.parse_note(saved[0].read_text(), saved[0].relative_to(archive).as_posix())
        self.assertIn(before.decode(), note.body)
        self.assertEqual(note.metadata["sharing_scope"], "private")
        self.assertEqual(note.metadata["privacy_review"], "pending")
        self.assertEqual(note.metadata["training_use"], "excluded")
        self.assertIn(edits, json.loads((self.codex / "basic-memory.json").read_text())["basicMemory"]["secondaryProjects"])
        self.sharing.sync()
        self.assertEqual(len(list(archive.rglob("*.md"))), 1)

    def test_sync_records_local_deletion_and_keeps_remote_deletion_locally(self):
        self.connect_sync()
        self.friend_bundle()
        result = self.sharing.sync()
        project = result["receive"][0]["project"]
        root = Path(json.loads(self.server.registry.read_text())["projects"][project]["path"])
        (root / "rules/units.md").unlink()
        result = self.sharing.sync()
        self.assertEqual(result["receive"][0]["preserved_edits"], 1)
        archive = Path(json.loads(self.server.registry.read_text())["projects"][result["receive"][0]["edits_project"]]["path"])
        self.assertTrue(any("local_deletion: true" in p.read_text() for p in archive.rglob("*.md")))
        (self.server.seed / "bundles/friend/rules/units.md").unlink()
        (self.server.seed / "bundles/friend/manifest.json").write_text(wg.json_text({"version": 1, "scope": "team", "notes": []}))
        self.server.git("add", ".", cwd=self.server.seed)
        self.server.git("commit", "-m", "Remove remote note", cwd=self.server.seed)
        self.server.git("push", "origin", "main", cwd=self.server.seed)
        result = self.sharing.sync()
        self.assertEqual(result["receive"][0]["removed"], ["rules/units.md"])
        self.assertTrue((root / "rules/units.md").exists())

    def test_sync_stale_review_blocks_sending_but_still_receives(self):
        note = self.note()
        self.connect_sync()
        note.write_text(note.read_text() + "Unreviewed addition.\n")
        self.friend_bundle()
        result = self.sharing.sync()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["publish"]["status"], "blocked")
        self.assertEqual(result["merge"]["status"], "not_attempted")
        self.assertEqual(result["receive"][0]["imported"], 1)
        self.assertFalse(self.server.prs)

    def test_sync_merge_protection_blocks_only_sending_and_never_bypasses(self):
        self.note()
        self.connect_sync()
        self.friend_bundle()
        self.server.reject_merge = True
        result = self.sharing.sync()
        self.assertEqual(result["merge"]["status"], "blocked")
        self.assertEqual(result["merge"]["attempts"], 3)
        self.assertEqual(result["receive"][0]["imported"], 1)
        self.assertEqual(len(self.server.prs), 1)
        self.assertEqual(self.server.prs[0]["state"], "OPEN")

    def test_sync_recovers_lost_push_create_and_merge_responses(self):
        for failure in ("fail_push_after", "fail_create_after", "fail_merge_after"):
            self.note(body="Reviewed update: " + failure)
            if not self.sharing.config().get("connections"):
                self.connect_sync()
            setattr(self.server, failure, True)
            result = self.sharing.sync()
            self.assertEqual(result["status"], "synced", result)
            self.assertEqual(self.server.prs[-1]["state"], "MERGED")
        self.assertEqual(len(self.server.prs), 3)

    def test_sync_one_invalid_friend_does_not_block_other_sources(self):
        self.connect_sync()
        self.friend_bundle(source="good")
        self.friend_bundle(source="broken")
        (self.server.seed / "bundles/broken/rules/units.md").write_text("Tampered data.")
        self.server.git("add", ".", cwd=self.server.seed)
        self.server.git("commit", "-m", "Bad bundle", cwd=self.server.seed)
        self.server.git("push", "origin", "main", cwd=self.server.seed)
        result = self.sharing.sync()
        by_source = {p["source_id"]: p for p in result["receive"]}
        self.assertEqual(by_source["broken"]["status"], "blocked")
        self.assertEqual(by_source["good"]["imported"], 1)

    def test_sync_preservation_failure_leaves_local_edit_untouched(self):
        self.connect_sync()
        self.friend_bundle()
        result = self.sharing.sync()
        project = result["receive"][0]["project"]
        root = Path(json.loads(self.server.registry.read_text())["projects"][project]["path"])
        target = root / "rules/units.md"
        target.write_text("Keep my private edit.\n")
        original = wg.atomic_file
        def fail_archive(path, *args, **kwargs):
            if "local-edits" in Path(path).parts:
                raise OSError("Disk failure")
            return original(path, *args, **kwargs)
        with patch.object(wg, "atomic_file", side_effect=fail_archive):
            result = self.sharing.sync()
        self.assertEqual(result["receive"][0]["status"], "blocked")
        self.assertEqual(target.read_text(), "Keep my private edit.\n")
        self.assertEqual(self.sharing.sync()["receive"][0]["preserved_edits"], 1)

    def test_sync_external_edit_during_preservation_is_not_overwritten(self):
        self.connect_sync()
        self.friend_bundle()
        result = self.sharing.sync()
        project = result["receive"][0]["project"]
        root = Path(json.loads(self.server.registry.read_text())["projects"][project]["path"])
        target = root / "rules/units.md"
        target.write_text("First edit.\n")
        original = wg.atomic_file
        changed = False
        def race(path, *args, **kwargs):
            nonlocal changed
            result = original(path, *args, **kwargs)
            if not changed and "local-edits" in Path(path).parts:
                changed = True
                target.write_text("Concurrent second edit.\n")
            return result
        with patch.object(wg, "atomic_file", side_effect=race):
            result = self.sharing.sync()
        self.assertEqual(result["receive"][0]["status"], "blocked")
        self.assertEqual(target.read_text(), "Concurrent second edit.\n")
        result = self.sharing.sync()
        archive = Path(json.loads(self.server.registry.read_text())["projects"][result["receive"][0]["edits_project"]]["path"])
        copies = [p.read_text() for p in archive.rglob("*.md")]
        self.assertTrue(any("First edit." in x for x in copies))
        self.assertTrue(any("Concurrent second edit." in x for x in copies))

    def test_sync_same_named_notes_from_multiple_sources_and_own_source_exclusion(self):
        self.note()
        self.connect_sync()
        self.friend_bundle(source="friend-a", body="Author A")
        self.friend_bundle(source="friend-b", body="Author B")
        result = self.sharing.sync()
        self.assertEqual({p["source_id"] for p in result["receive"]}, {"friend-a", "friend-b"})
        registry = json.loads(self.server.registry.read_text())["projects"]
        for item in result["receive"]:
            root = Path(registry[item["project"]]["path"])
            self.assertIn("Author " + item["source_id"][-1].upper(), (root / "rules/units.md").read_text())
        self.assertIn("Preserve denominator", (self.memory / "rules/units.md").read_text())

    def test_sync_retries_non_force_push_after_concurrent_branch_update(self):
        self.note()
        self.connect_sync()
        self.sharing.publish("publish")
        def concurrent():
            self.server.git("fetch", "origin", cwd=self.server.seed)
            self.server.git("checkout", "workgraph-share/source", cwd=self.server.seed)
            (self.server.seed / "bundles/source/rules/units.md").write_text("Concurrent sender data")
            self.server.git("add", ".", cwd=self.server.seed)
            self.server.git("commit", "-m", "Concurrent sender", cwd=self.server.seed)
            self.server.git("push", "origin", "workgraph-share/source", cwd=self.server.seed)
            self.server.git("checkout", "main", cwd=self.server.seed)
        self.note(body="Current reviewed source.")
        # Use a valid remote bundle so the second attempt can safely inspect it.
        def valid_concurrent():
            concurrent()
            self.server.git("checkout", "workgraph-share/source", cwd=self.server.seed)
            p = self.server.seed / "bundles/source/rules/units.md"
            p.write_text(wg.Note("rules/units.md", {"title": "Units", "type": "rule"}, "\nConcurrent sender.\n").render())
            manifest = self.server.seed / "bundles/source/manifest.json"
            manifest.write_text(wg.json_text({"version": 1, "scope": "team", "notes": [
                {"path": "rules/units.md", "sha256": wg.sha(p.read_bytes())}]}))
            self.server.git("add", ".", cwd=self.server.seed)
            self.server.git("commit", "-m", "Valid concurrent bundle", cwd=self.server.seed)
            self.server.git("push", "origin", "workgraph-share/source", cwd=self.server.seed)
            self.server.git("checkout", "main", cwd=self.server.seed)
        self.server.before_push = valid_concurrent
        result = self.sharing.sync()
        self.assertEqual(result["status"], "synced", result)
        self.assertEqual(len(self.server.prs), 1)
        self.assertEqual(self.server.prs[0]["state"], "MERGED")

    def test_connect_fresh_dry_run_and_ambiguous_sync(self):
        before = self.snapshot()
        registry = self.server.registry.read_bytes()
        self.sharing.connect("example/memories", dry_run=True)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.server.registry.read_bytes(), registry)
        self.connect_sync()
        config = self.sharing.config()
        config["connections"]["other/memories"] = dict(config["connections"]["example/memories"])
        wg.atomic_file(self.sharing.config_path, wg.json_text(config), replace=True)
        with self.assertRaises(wg.Invalid):
            self.sharing.sync()
        self.assertEqual(self.sharing.sync("example/memories")["status"], "synced")

    def test_sync_discovery_failure_reports_completed_publish(self):
        self.note()
        self.connect_sync()
        original = github.GitHub.clone
        def fail_discovery(hub, path):
            if "workgraph-discover-" in str(path):
                raise wg.Invalid("Connection lost")
            return original(hub, path)
        with patch.object(github.GitHub, "clone", fail_discovery):
            result = self.sharing.sync()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["merge"]["status"], "merged")
        self.assertEqual(result["discovery"]["status"], "blocked")
        self.assertEqual(self.sharing.sync()["status"], "synced")

    def test_sync_japanese_and_quoted_note_names_merge_and_update(self):
        self.note('rules/日本語の検証 "例".md')
        self.connect_sync()
        self.assertEqual(self.sharing.sync()["status"], "synced")
        self.note('rules/日本語の検証 "例".md', body="Updated Japanese filename note.")
        self.sharing.publish("publish")
        self.assertEqual(self.sharing.sync()["merge"]["status"], "merged")

    def test_merge_rejects_unreviewed_or_unrelated_pr_content(self):
        self.note()
        self.connect_sync()
        self.sharing.publish("publish")
        self.server.git("fetch", "origin", cwd=self.server.seed)
        self.server.git("checkout", "workgraph-share/source", cwd=self.server.seed)
        (self.server.seed / "unrelated.txt").write_text("Not shared notes")
        self.server.git("add", ".", cwd=self.server.seed)
        self.server.git("commit", "-m", "Unrelated change", cwd=self.server.seed)
        self.server.git("push", "origin", "workgraph-share/source", cwd=self.server.seed)
        with self.assertRaises(wg.Invalid):
            self.sharing.merge_reviewed("publish")
        self.assertEqual(self.server.prs[0]["state"], "OPEN")

    def test_malformed_agents_block_stops_configuration_before_any_changes(self):
        for text in (configure.SHARING_END + configure.SHARING_BEGIN, configure.SHARING_BEGIN,
                     configure.SHARING_BEGIN * 2 + configure.SHARING_END * 2):
            with self.subTest(text=text):
                (self.codex / "AGENTS.md").write_text(text)
                before = self.snapshot()
                with self.assertRaises(ValueError):
                    configure.configure(self.codex)
                self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()

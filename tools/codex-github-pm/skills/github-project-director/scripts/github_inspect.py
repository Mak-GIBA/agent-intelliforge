#!/usr/bin/env python3
"""Read-only GitHub inventory via official gh. No tokens, caches or write commands.

Every collection reports completeness. REST and GraphQL pagination are explicit.
Writes remain native gh/MCP operations after the user reviews the proposed diff.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from typing import Any, Callable
from urllib.parse import urlsplit


class ReadError(RuntimeError):
    pass


def repository(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", value):
        raise argparse.ArgumentTypeError("Use an explicit OWNER/REPO, not a URL or command")
    if value.split("/")[1] in (".", ".."):
        raise argparse.ArgumentTypeError("Invalid repository name")
    return value


def hostname(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", value):
        raise argparse.ArgumentTypeError("Use a hostname only")
    return value


def positive(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Must be positive")
    return number


def result(items: list, complete: bool, pages: int, error: str | None = None) -> dict:
    return {"items": items, "complete": complete, "pages": pages, "error": error}


class GitHub:
    def __init__(self, host: str = "github.com", max_pages: int = 20,
                 runner: Callable = subprocess.run):
        self.host, self.max_pages, self.runner = host, max_pages, runner

    def request(self, endpoint: str, payload: dict | None = None) -> Any:
        if payload is not None and not payload.get("query", "").lstrip().startswith("query"):
            raise ReadError("Only GraphQL queries are allowed")
        if payload is not None and endpoint != "graphql":
            raise ReadError("Read helper does not POST REST resources")
        args = ["gh", "api", "--hostname", self.host, "--method", "GET" if payload is None else "POST",
                "-H", "Accept: application/vnd.github+json", endpoint]
        if payload is not None:
            args += ["--input", "-"]
        try:
            response = self.runner(args, input=json.dumps(payload) if payload is not None else None,
                                   capture_output=True, text=True, timeout=60, check=False,
                                   env={**os.environ, "GH_PROMPT_DISABLED": "1", "GH_PAGER": "cat"})
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ReadError(f"gh read did not complete: {type(exc).__name__}") from exc
        if response.returncode:
            # stderr can include credentials/server-supplied text. Do not echo it.
            raise ReadError(f"gh read failed (exit {response.returncode}) at {endpoint.split('?')[0]}; check auth, permissions and host support")
        try:
            data = json.loads(response.stdout)
        except ValueError as exc:
            raise ReadError("gh returned non-JSON output") from exc
        if payload is not None:
            if data.get("errors"):
                raise ReadError("GraphQL errors: requested data is unavailable; do not treat it as empty")
            return data.get("data")
        return data

    def pages(self, endpoint: str) -> dict:
        items = []
        for page in range(1, self.max_pages + 1):
            sep = "&" if "?" in endpoint else "?"
            try:
                data = self.request(f"{endpoint}{sep}per_page=100&page={page}")
                if not isinstance(data, list):
                    raise ReadError("Expected a REST list")
            except ReadError as exc:
                return result(items, False, page - 1, str(exc))
            items.extend(data)
            if len(data) < 100:
                return result(items, True, page)
        return result(items, False, self.max_pages, "page limit reached; not a complete inventory")

    def connection(self, query: str, variables: dict, path: list[str]) -> dict:
        items, cursor, seen = [], None, set()
        for page in range(1, self.max_pages + 1):
            try:
                data = self.request("graphql", {"query": query, "variables": {**variables, "after": cursor}})
                for part in path:
                    data = data[part]
                if not isinstance(data, dict) or not isinstance(data.get("nodes"), list):
                    raise ReadError("Expected GraphQL connection")
                items.extend(x for x in data["nodes"] if x is not None)
                info = data["pageInfo"]
                if not info["hasNextPage"]:
                    return result(items, True, page)
                cursor = info.get("endCursor")
                if not cursor or cursor in seen:
                    raise ReadError("Missing or repeated pagination cursor")
                seen.add(cursor)
            except (ReadError, TypeError, KeyError) as exc:
                return result(items, False, page - 1, str(exc))
        return result(items, False, self.max_pages, "page limit reached; not a complete inventory")


LINKED_PROJECTS = """query($owner:String!,$repo:String!,$after:String){
 repository(owner:$owner,name:$repo){projectsV2(first:100,after:$after){
 nodes{id number title url closed} pageInfo{hasNextPage endCursor}}}}"""
FIELDS = """fields(first:100,after:$after){nodes{
 ... on ProjectV2FieldCommon{id name dataType}
 ... on ProjectV2SingleSelectField{options{id name}}
 ... on ProjectV2IterationField{configuration{iterations{id title startDate duration}}}
 }pageInfo{hasNextPage endCursor}}"""
ITEMS = """items(first:100,after:$after){nodes{id isArchived
 content{__typename ... on Issue{id number title url state repository{nameWithOwner}}
 ... on PullRequest{id number title url state repository{nameWithOwner}}
 ... on DraftIssue{title}}
 fieldValues(first:100){nodes{__typename
 ... on ProjectV2ItemFieldDateValue{date field{... on ProjectV2FieldCommon{id name}}}
 ... on ProjectV2ItemFieldSingleSelectValue{name optionId field{... on ProjectV2FieldCommon{id name}}}
 ... on ProjectV2ItemFieldTextValue{text field{... on ProjectV2FieldCommon{id name}}}
 ... on ProjectV2ItemFieldNumberValue{number field{... on ProjectV2FieldCommon{id name}}}
 ... on ProjectV2ItemFieldIterationValue{iterationId title startDate duration field{... on ProjectV2FieldCommon{id name}}}
 }pageInfo{hasNextPage endCursor}}
 }pageInfo{hasNextPage endCursor}}"""


def summarize(collection: dict, keys: tuple) -> dict:
    collection["items"] = [{k: x[k] for k in keys if k in x} for x in collection["items"]]
    # Bound text sent to the model; truncation is explicitly visible per item.
    for item in collection["items"]:
        if isinstance(item.get("body"), str) and len(item["body"]) > 12000:
            item["body"] = item["body"][:12000]
            item["body_truncated"] = True
    return collection


def snapshot(api: GitHub, repo: str) -> dict:
    metadata = api.request(f"repos/{repo}")
    if str(metadata.get("full_name", "")).lower() != repo.lower():
        raise ReadError("Repository resolved to another name; confirm the redirect before proceeding")
    issues = api.pages(f"repos/{repo}/issues?state=all&sort=updated&direction=desc")
    issues["items"] = [x for x in issues["items"] if "pull_request" not in x]
    keys = ("id", "node_id", "number", "title", "body", "html_url", "state", "state_reason",
            "labels", "assignees", "milestone", "created_at", "updated_at", "closed_at", "comments")
    owner, name = repo.split("/")
    return {"repo": {k: metadata.get(k) for k in ("full_name", "html_url", "default_branch", "owner", "permissions", "archived")},
            "issues": summarize(issues, keys),
            "pull_requests": summarize(api.pages(f"repos/{repo}/pulls?state=all&sort=updated&direction=desc"),
                                       keys + ("draft", "merged_at")),
            "labels": api.pages(f"repos/{repo}/labels"),
            "milestones": api.pages(f"repos/{repo}/milestones?state=all"),
            "assignees": api.pages(f"repos/{repo}/assignees"),
            "linked_projects": api.connection(LINKED_PROJECTS, {"owner": owner, "repo": name}, ["repository", "projectsV2"]),
            "coverage_note": "Linked Projects only, not every user/org Project. Comments, full PR diffs and all issue relations require targeted follow-up. Body text may be truncated."}


def project(api: GitHub, owner: str, number: int, owner_type: str) -> dict:
    root = "user" if owner_type == "user" else "organization"
    header = f"query($owner:String!,$number:Int!,$after:String){{{root}(login:$owner){{projectV2(number:$number){{"
    data = api.request("graphql", {"query": f"query($owner:String!,$number:Int!){{{root}(login:$owner){{projectV2(number:$number){{id number title url closed}}}}}}",
                                    "variables": {"owner": owner, "number": number}})
    try:
        info = data[root]["projectV2"]
        if info is None:
            raise ReadError("Project not visible; confirm owner/type/number and permissions")
    except (TypeError, KeyError) as exc:
        raise ReadError("Project is unavailable") from exc
    variables = {"owner": owner, "number": number}
    fields = api.connection(header + FIELDS + "}}}", variables, [root, "projectV2", "fields"])
    items = api.connection(header + ITEMS + "}}}", variables, [root, "projectV2", "items"])
    truncated = [x["id"] for x in items["items"] if x.get("fieldValues", {}).get("pageInfo", {}).get("hasNextPage")]
    return {"project": info, "fields": fields, "items": items,
            "field_values_complete": not truncated, "items_needing_field_pagination": truncated,
            "coverage_note": "Date/single-select/text/number/iteration values included. Other field types retain __typename only. Fetch missing values before editing; null content is not an empty issue."}


def relations(api: GitHub, repo: str, number: int) -> dict:
    base = f"repos/{repo}/issues/{number}"
    try:
        parent = {"value": api.request(base + "/parent"), "complete": True}
    except ReadError as exc:
        parent = {"value": None, "complete": False, "error": str(exc),
                  "note": "A missing parent and unavailable permissions/API must be distinguished by a targeted read."}
    return {"issue": api.request(base), "parent": parent,
            "sub_issues": api.pages(base + "/sub_issues"),
            "blocked_by": api.pages(base + "/dependencies/blocked_by"),
            "blocking": api.pages(base + "/dependencies/blocking")}


def entry_key(value: str) -> str:
    """Validate a retry hint, not an authorization or a global idempotency key."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", value):
        raise argparse.ArgumentTypeError("entry-key: 1-96 ASCII letters/digits/dot/underscore/hyphen")
    return value


def meeting(api: GitHub, repo: str, number: int, key: str | None = None) -> dict:
    """Read a log Issue and paginated comments; never append or change a resource."""
    repo = repository(repo)
    if number < 1:
        raise ReadError("Issue number must be positive")
    if key is not None:
        key = entry_key(key)
    base = f"repos/{repo}/issues/{number}"
    issue = api.request(base)
    if not isinstance(issue, dict) or issue.get("number") != number or "pull_request" in issue:
        raise ReadError("The meeting target must be the selected Issue, not a pull request")
    address = urlsplit(str(issue.get("html_url", "")))
    if (address.scheme != "https" or address.hostname != api.host.lower()
            or address.path.rstrip("/").lower() != f"/{repo}/issues/{number}".lower()):
        raise ReadError("Issue resolved to another repository/host; confirm the destination")

    comments = api.pages(base + "/comments")
    marker = f"<!-- github-project-director:entry:{key} -->" if key else None
    matches = []
    unreadable = False
    for comment in comments["items"]:
        if not isinstance(comment, dict):
            raise ReadError("Invalid comment response")
        body = comment.get("body")
        comment["body_sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest() if isinstance(body, str) else None
        user = comment.get("user")
        comment["author_login"] = user.get("login") if isinstance(user, dict) else None
        if not isinstance(body, str):
            unreadable = True
            continue
        first_line = body.splitlines()[0] if body else ""
        if marker and first_line == marker:
            matches.append({k: comment.get(k) for k in
                            ("id", "html_url", "author_login", "body_sha256", "created_at", "updated_at")})
    if unreadable:
        comments["complete"] = False
        comments["error"] = "; ".join(x for x in (comments.get("error"), "Some comment bodies are unavailable") if x)
    state = ("not_requested" if marker is None else "found" if matches else
             "absent" if comments["complete"] else "unknown")
    issue_keys = ("id", "node_id", "number", "title", "body", "html_url", "state", "locked",
                  "labels", "created_at", "updated_at", "comments")
    return {
        "issue": summarize(result([issue], True, 1), issue_keys)["items"][0],
        "comments": summarize(comments, ("id", "html_url", "body", "body_sha256", "author_login",
                                         "created_at", "updated_at")),
        "entry_lookup": {"key": key, "marker": marker, "state": state, "matches": matches,
                         "complete": comments["complete"], "multiple_matches": len(matches) > 1},
        "coverage_note": "Read only. Marker matches are retry hints, not approval/identity proof. "
                         "Read a truncated comment in full before interpreting it. "
                         "Found in partial history is not uniqueness proof; read-before-write is not atomic.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hostname", type=hostname, default=os.environ.get("GH_HOST", "github.com"))
    parser.add_argument("--max-pages", type=positive, default=20)
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("snapshot", help="Repository metadata, issues, PRs and linked Projects")
    s.add_argument("--repo", type=repository, required=True)
    p = sub.add_parser("project", help="One explicitly selected Project with field IDs/options")
    p.add_argument("--owner", required=True)
    p.add_argument("--owner-type", choices=("user", "organization"), required=True)
    p.add_argument("--number", type=positive, required=True)
    r = sub.add_parser("relations", help="Native parent/sub-issues/dependency edges for one Issue")
    r.add_argument("--repo", type=repository, required=True)
    r.add_argument("--issue", type=positive, required=True)
    m = sub.add_parser("meeting", help="Recurring Issue, comment history and optional duplicate/retry lookup (read only)")
    m.add_argument("--repo", type=repository, required=True)
    m.add_argument("--issue", type=positive, required=True)
    m.add_argument("--entry-key", type=entry_key, help="Stable approved-batch key; not write authorization")
    args = parser.parse_args()
    if args.max_pages > 1000:
        parser.error("--max-pages must be <= 1000")
    if not shutil.which("gh"):
        parser.error("gh not installed; use an authorized GitHub MCP instead or install official GitHub CLI")
    api = GitHub(args.hostname, args.max_pages)
    try:
        if args.command == "snapshot":
            data = snapshot(api, args.repo)
        elif args.command == "project":
            data = project(api, args.owner, args.number, args.owner_type)
        elif args.command == "meeting":
            data = meeting(api, args.repo, args.issue, args.entry_key)
        else:
            data = relations(api, args.repo, args.issue)
        data["observed_at"] = datetime.now(timezone.utc).isoformat()
        data["hostname"] = args.hostname
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    except ReadError as exc:
        print(json.dumps({"error": str(exc), "complete": False}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

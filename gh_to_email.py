#!/usr/bin/env python3
"""Enumerate a GitHub user's commit emails across their public footprint.

Usage:
    python3 gh_to_email.py <username-or-url> [--max-pages-per-repo N]
                                             [--skip-events]
                                             [--out PATH]
                                             [--verbose]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

__version__ = "0.1.0"

API = "https://api.github.com"
UA = f"gh-to-email/{__version__} (+stdlib)"
POLITE_SLEEP = 0.1


def parse_user(arg: str) -> str:
    s = arg.strip().rstrip("/")
    s = re.sub(r"^https?://", "", s)
    s = re.sub(r"^github\.com/", "", s)
    s = s.split("?")[0].split("#")[0]
    s = s.split("/")[0]
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", s):
        raise SystemExit(f"invalid github username: {s!r}")
    return s


def gh_token() -> str:
    env = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if env:
        return env.strip()
    try:
        out = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, check=True
        )
        tok = out.stdout.strip()
        if tok:
            return tok
    except FileNotFoundError:
        pass
    except subprocess.CalledProcessError:
        pass
    raise SystemExit(
        "no auth token found.\n"
        "  either: set GITHUB_TOKEN env var with a personal access token\n"
        "          (create at https://github.com/settings/tokens — no scopes needed for public repos)\n"
        "  or:     install gh CLI and run `gh auth login`"
    )


class Client:
    def __init__(self, token: str, verbose: bool = False) -> None:
        self.token = token
        self.verbose = verbose
        self.rate_remaining = None
        self.rate_reset = None
        self.requests_made = 0

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"  [api] {msg}", file=sys.stderr)

    def _maybe_wait(self) -> None:
        if self.rate_remaining is None:
            return
        if self.rate_remaining < 100 and self.rate_reset:
            wait = max(0, self.rate_reset - int(time.time())) + 2
            if wait > 0:
                print(
                    f"  [rate-limit] only {self.rate_remaining} reqs left; "
                    f"sleeping {wait}s until reset",
                    file=sys.stderr,
                )
                time.sleep(wait)

    def get(self, path: str, params: dict | None = None) -> tuple[object, dict]:
        self._maybe_wait()
        url = API + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "User-Agent": UA,
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        self._log(f"GET {url}")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                headers = dict(resp.headers.items())
                body = resp.read()
                data = json.loads(body) if body else None
        except urllib.error.HTTPError as e:
            headers = dict(e.headers.items()) if e.headers else {}
            self._update_rate(headers)
            self._log(f"HTTP {e.code}")
            return e, headers
        self._update_rate(headers)
        self.requests_made += 1
        time.sleep(POLITE_SLEEP)
        return data, headers

    def _update_rate(self, headers: dict) -> None:
        try:
            self.rate_remaining = int(headers.get("X-RateLimit-Remaining", "0"))
            self.rate_reset = int(headers.get("X-RateLimit-Reset", "0"))
        except (TypeError, ValueError):
            pass

    def paginate(
        self, path: str, params: dict, max_pages: int = 100
    ) -> list:
        items: list = []
        p = dict(params)
        p.setdefault("per_page", 100)
        page = 1
        while page <= max_pages:
            p["page"] = page
            data, headers = self.get(path, p)
            if isinstance(data, urllib.error.HTTPError):
                if data.code in (404, 409, 451):
                    return items
                raise SystemExit(f"GET {path} failed: HTTP {data.code}")
            if not isinstance(data, list):
                return items
            items.extend(data)
            if len(data) < p["per_page"]:
                break
            link = headers.get("Link", "")
            if 'rel="next"' not in link:
                break
            page += 1
        return items


def list_owned_repos(client: Client, user: str) -> list[dict]:
    repos = client.paginate(
        f"/users/{user}/repos", {"type": "owner", "sort": "pushed"}
    )
    return [
        {
            "full_name": r["full_name"],
            "size": r.get("size", 0),
            "fork": r.get("fork", False),
            "default_branch": r.get("default_branch"),
            "pushed_at": r.get("pushed_at"),
        }
        for r in repos
    ]


def list_repo_commits(
    client: Client, full_name: str, author: str, max_pages: int
) -> list[dict]:
    items = client.paginate(
        f"/repos/{full_name}/commits",
        {"author": author},
        max_pages=max_pages,
    )
    out = []
    for c in items:
        commit = c.get("commit") or {}
        a = commit.get("author") or {}
        msg = commit.get("message") or ""
        out.append(
            {
                "repo": full_name,
                "sha": c.get("sha"),
                "email": a.get("email") or "",
                "name": a.get("name") or "",
                "date": (a.get("date") or "")[:10],
                "datetime": a.get("date") or "",
                "message_first_line": msg.split("\n", 1)[0][:200],
                "source": "repo",
            }
        )
    return out


def list_user_events(client: Client, user: str, max_pages: int = 3) -> list[dict]:
    return client.paginate(
        f"/users/{user}/events/public", {}, max_pages=max_pages
    )


def extract_from_events(events: list[dict]) -> list[dict]:
    out = []
    for ev in events:
        if ev.get("type") != "PushEvent":
            continue
        repo = (ev.get("repo") or {}).get("name") or ""
        when = ev.get("created_at") or ""
        date_only = when[:10]
        for c in (ev.get("payload") or {}).get("commits") or []:
            a = c.get("author") or {}
            msg = c.get("message") or ""
            out.append(
                {
                    "repo": repo,
                    "sha": c.get("sha"),
                    "email": a.get("email") or "",
                    "name": a.get("name") or "",
                    "date": date_only,
                    "datetime": when,
                    "message_first_line": msg.split("\n", 1)[0][:200],
                    "source": "event",
                }
            )
    return out


def dedupe_by_day(commits: list[dict]) -> list[dict]:
    seen: dict[tuple, dict] = {}
    for c in commits:
        if not c["email"]:
            continue
        key = (c["repo"], c["date"], c["email"].lower(), c["name"])
        prev = seen.get(key)
        if prev is None or c["datetime"] > prev["datetime"]:
            seen[key] = c
    return sorted(
        seen.values(), key=lambda r: (r["datetime"], r["repo"]), reverse=True
    )


def aggregate_emails(all_commits: list[dict]) -> list[dict]:
    by_email: dict[str, dict] = defaultdict(
        lambda: {
            "names": set(),
            "repos": set(),
            "first": None,
            "last": None,
            "first_commit": None,
            "last_commit": None,
            "count": 0,
            "samples": [],
        }
    )
    for c in all_commits:
        e = c["email"].lower()
        if not e:
            continue
        rec = by_email[e]
        rec["names"].add(c["name"])
        rec["repos"].add(c["repo"])
        rec["count"] += 1
        d = c["date"]
        if rec["first"] is None or d < rec["first"]:
            rec["first"] = d
            rec["first_commit"] = c
        if rec["last"] is None or d > rec["last"]:
            rec["last"] = d
            rec["last_commit"] = c
        if len(rec["samples"]) < 3:
            rec["samples"].append(
                {
                    "repo": c["repo"],
                    "sha": c["sha"],
                    "date": c["date"],
                    "message_first_line": c["message_first_line"],
                }
            )

    out = []
    for email, rec in by_email.items():
        out.append(
            {
                "email": email,
                "is_noreply": email.endswith("@users.noreply.github.com"),
                "names": sorted(n for n in rec["names"] if n),
                "first_seen": rec["first"],
                "last_seen": rec["last"],
                "commit_count": rec["count"],
                "repos": sorted(rec["repos"]),
                "first_commit": {
                    "repo": rec["first_commit"]["repo"],
                    "sha": rec["first_commit"]["sha"],
                    "date": rec["first_commit"]["date"],
                },
                "last_commit": {
                    "repo": rec["last_commit"]["repo"],
                    "sha": rec["last_commit"]["sha"],
                    "date": rec["last_commit"]["date"],
                },
                "samples": rec["samples"],
            }
        )
    return sorted(out, key=lambda r: r["commit_count"], reverse=True)


def render_summary(user: str, rollup: list[dict], stats: dict) -> str:
    lines = []
    lines.append("")
    lines.append(f"== {user} ==")
    lines.append(
        f"  repos scanned: {stats['repos_scanned']}  "
        f"events scanned: {stats['events_scanned']}  "
        f"unique commits (deduped by day): {stats['commits']}  "
        f"api requests: {stats['requests']}  "
        f"rate-limit left: {stats['rate_remaining']}"
    )
    lines.append("")
    if not rollup:
        lines.append("  no commits with emails found.")
        return "\n".join(lines)
    for r in rollup:
        noreply = "  [noreply]" if r["is_noreply"] else ""
        names = ", ".join(r["names"]) if r["names"] else "(no name)"
        lines.append(f"{r['email']}{noreply}")
        lines.append(f"  name(s): {names}")
        lines.append(
            f"  {r['commit_count']} commits across {len(r['repos'])} repos"
        )
        fc = r["first_commit"]
        lc = r["last_commit"]
        lines.append(
            f"  first: {r['first_seen']} in {fc['repo']}  ({(fc['sha'] or '')[:8]})"
        )
        lines.append(
            f"  last:  {r['last_seen']} in {lc['repo']}  ({(lc['sha'] or '')[:8]})"
        )
        if len(r["repos"]) <= 6:
            lines.append(f"  repos: {', '.join(r['repos'])}")
        else:
            lines.append(
                f"  repos: {', '.join(r['repos'][:6])} ... (+{len(r['repos']) - 6} more)"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("user", help="username or https://github.com/<user> URL")
    ap.add_argument("--max-pages-per-repo", type=int, default=20)
    ap.add_argument("--skip-events", action="store_true")
    ap.add_argument("--out", default=None, help="output JSON path")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--version", action="version", version=f"gh-to-email {__version__}")
    args = ap.parse_args()

    user = parse_user(args.user)
    client = Client(gh_token(), verbose=args.verbose)

    print(f"resolving user: {user}", file=sys.stderr)
    data, _ = client.get(f"/users/{user}")
    if isinstance(data, urllib.error.HTTPError):
        raise SystemExit(f"user not found or inaccessible: HTTP {data.code}")
    canonical = data.get("login") or user
    print(f"user ok: {canonical} (id={data.get('id')})", file=sys.stderr)

    print(f"listing owned public repos for {canonical}", file=sys.stderr)
    repos = list_owned_repos(client, canonical)
    print(f"  found {len(repos)} repos", file=sys.stderr)

    all_commits: list[dict] = []
    for i, r in enumerate(repos, 1):
        if r["size"] == 0:
            print(
                f"  [{i}/{len(repos)}] {r['full_name']} (empty, skip)",
                file=sys.stderr,
            )
            continue
        print(f"  [{i}/{len(repos)}] {r['full_name']}", file=sys.stderr)
        commits = list_repo_commits(
            client, r["full_name"], canonical, args.max_pages_per_repo
        )
        print(f"      {len(commits)} commits", file=sys.stderr)
        all_commits.extend(commits)

    events_count = 0
    if not args.skip_events:
        print("scanning recent public events", file=sys.stderr)
        events = list_user_events(client, canonical)
        events_count = len(events)
        ev_commits = extract_from_events(events)
        print(
            f"  {events_count} events -> {len(ev_commits)} commit refs",
            file=sys.stderr,
        )
        all_commits.extend(ev_commits)

    deduped = dedupe_by_day(all_commits)
    rollup = aggregate_emails(deduped)

    stats = {
        "repos_scanned": len(repos),
        "events_scanned": events_count,
        "commits": len(deduped),
        "requests": client.requests_made,
        "rate_remaining": client.rate_remaining,
    }

    out_path = args.out or f"{canonical}-emails.json"
    payload = {
        "user": canonical,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "repos_scanned": stats["repos_scanned"],
        "events_scanned": stats["events_scanned"],
        "rate_limit_remaining_end": stats["rate_remaining"],
        "api_requests": stats["requests"],
        "emails": rollup,
        "commits": deduped,
    }
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2, default=str)

    print(render_summary(canonical, rollup, stats))
    print(f"wrote {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

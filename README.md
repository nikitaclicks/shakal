# gh-to-email

Enumerate the email addresses a GitHub user has committed under across their
public footprint — owned repos plus recent cross-repo push activity.

Useful for: auditing your own commit footprint, hiring background-check
transparency, security research, and incident response.

## A note on responsible use

Every email this tool surfaces is **already public** — it comes straight from
GitHub's REST API, exactly the same data anyone can see by clicking through to
a commit page in the browser. This tool just aggregates and dedupes it.

That said, please don't:

- Use it to harass, dox, or out anyone
- Bulk-scrape strangers for marketing or recruiting spam
- Try to defeat someone's choice to use a `noreply.github.com` privacy alias

Reasonable uses include checking your own exposure, transparent reference
checks, legitimate security/abuse investigations, and forensic work. If
you're not sure whether your use case is OK, it probably isn't.

If you want to remove your real email from your own commits, GitHub has
instructions: <https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-personal-account-on-github/managing-email-preferences/setting-your-commit-email-address>.

## What you get

For a given user, the script produces:

- **Console summary** — per-email block with name(s), commit count, first/last
  seen date + repo + sha, list of repos.
- **`<user>-emails.json`** — structured dump with full per-commit detail
  (deduped to one row per `(repo, calendar-day, email)`).

Noreply privacy addresses (`*@users.noreply.github.com`) are flagged
separately — they're not real inboxes but the numeric prefix
(`12345+user@...`) still correlates to a GitHub user ID.

## Requirements

Two ways to run it:

**A. Standalone binary** (zero install — share with non-technical users)
- Single 8MB executable, no Python or `gh` needed
- Just needs a `GITHUB_TOKEN` (one-time, takes 1 minute — see [Sharing with someone else](#sharing-with-someone-else))
- Build with `./build.sh` (requires Python + PyInstaller on your machine)

**B. Run the Python script directly** (for development on this machine)
- Python 3.8+ (stdlib only, no pip deps)
- Auth via either:
  - [`gh` CLI](https://cli.github.com/) authenticated (`gh auth login`), or
  - `GITHUB_TOKEN` / `GH_TOKEN` env var

Authenticated requests give you 5000/hour — plenty for any single user scan.

## Usage

### Quick start

```bash
./run.sh octocat
./run.sh https://github.com/octocat
```

### Direct Python invocation

```bash
python3 gh_to_email.py octocat
python3 gh_to_email.py https://github.com/octocat --verbose
python3 gh_to_email.py torvalds --max-pages-per-repo 2 --skip-events
python3 gh_to_email.py octocat --out /tmp/out.json
```

### Flags

| flag | default | what it does |
| --- | --- | --- |
| `--max-pages-per-repo N` | 20 | cap commits-list pagination per repo (each page = 100 commits) |
| `--skip-events` | off | don't scan `/users/{u}/events/public` (saves 1–3 requests) |
| `--out PATH` | `<user>-emails.json` | write the JSON dump here |
| `--verbose` | off | log every API request to stderr |

## How it works (and why it's polite)

1. **`GET /users/{user}/repos?type=owner`** — paginate owned public repos.
2. For each repo, **`GET /repos/{owner}/{repo}/commits?author={user}`** —
   paginate the user's commits. The list endpoint already returns
   `commit.author.email`, `name`, `date`, and message, so we **never fetch
   individual commits**. That's the big efficiency win.
3. **`GET /users/{user}/events/public`** — captures recent push activity
   to repos the user *doesn't own* (last ~90 days, max ~300 events).
   `PushEvent.payload.commits[]` already carries email + sha, no extra calls.
4. Dedupe in-memory by `(repo, calendar_day, email)` so a 50-commit day
   collapses to one output row per unique email used that day.
5. Aggregate to per-email rollup (first/last seen, repos, samples).

### Rate-limit safety

- Reads `X-RateLimit-Remaining` on every response.
- If remaining drops below 100, sleeps until the reset timestamp.
- 100ms gap between requests.
- `--max-pages-per-repo` caps prolific repos so one bad input can't burn
  your entire hour.

Typical scan of a normal user: 10–30 API requests, <30 seconds.

## Example output

```
== exampleuser ==
  repos scanned: 12  events scanned: 30  unique commits (deduped by day): 87  api requests: 22  rate-limit left: 4978

alice@example.com
  name(s): Alice Example
  64 commits across 4 repos
  first: 2018-04-12 in exampleuser/repo-a  (aaaaaaaa)
  last:  2024-11-03 in exampleuser/repo-b  (bbbbbbbb)
  repos: exampleuser/repo-a, exampleuser/repo-b, exampleuser/repo-c, exampleuser/repo-d

12345678+exampleuser@users.noreply.github.com  [noreply]
  name(s): exampleuser
  23 commits across 2 repos
  first: 2021-08-01 in exampleuser/repo-e  (cccccccc)
  last:  2025-02-14 in exampleuser/repo-f  (dddddddd)
  repos: exampleuser/repo-e, exampleuser/repo-f
```

## Querying the JSON

```bash
# all emails found
jq '.emails[] | .email' octocat-emails.json

# non-noreply (real) emails only
jq '.emails[] | select(.is_noreply | not) | .email' octocat-emails.json

# emails active in a date range
jq '.commits[] | select(.date >= "2020-01-01" and .date <= "2020-12-31")' octocat-emails.json

# repos touched by a specific email
jq '.emails[] | select(.email == "foo@bar.com") | .repos' octocat-emails.json
```

## Sharing with someone else

The `dist/` folder is what you hand off. It contains:

- `gh-to-email` — the standalone binary
- `lookup.command` — a friendly double-click wrapper that prompts for a
  username and (on first run) walks them through getting a token

### Building

```bash
./build.sh
```

This creates `dist/gh-to-email` (~8MB).

**Cross-platform note:** PyInstaller produces a binary for whatever
OS + architecture you build on. A macOS arm64 build won't run on Intel macs,
Linux, or Windows. To ship to all four targets, build separately on each
(or, in the long run, wire up a GitHub Actions matrix). The standard four
targets to cover:

| target | build host needed |
| --- | --- |
| macOS arm64 (Apple Silicon) | macOS arm64 |
| macOS x86_64 (Intel) | macOS Intel |
| Linux x86_64 | Linux x86_64 |
| Windows x86_64 | Windows x86_64 |

The Python source (`gh_to_email.py`) is always portable — anyone with
Python 3.8+ can run it directly without a binary.

### Handoff to a non-technical user (macOS)

1. Zip the `dist/` folder and AirDrop / send it.
2. They unzip somewhere (e.g. Desktop) and **double-click `lookup.command`**.
3. macOS Gatekeeper will block the first run because the binary is unsigned:
   - In Finder, **right-click** `lookup.command` → **Open** → **Open** in the
     prompt. After that, double-click works normally.
   - Same dance for `gh-to-email` if they ever run it directly.
4. The wrapper walks them through creating a token at
   https://github.com/settings/tokens/new (no scopes needed for public repos).
   Token is saved to `~/.config/gh-to-email/token` (chmod 600) so they're only
   asked once.
5. After that, just double-click and type a username.

### CLI-style handoff (terminal users)

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
./gh-to-email octocat
```

## Limitations

- **Owned repos + 90-day events feed only** — doesn't use `/search/commits`,
  so historical contributions to other people's repos older than 90 days
  are missed. Adding that would mean a heavier rate limit (30/min) for
  ~5% more coverage; not worth it by default.
- **No patch content** — only commit metadata. Fine for finding emails;
  not enough for code-style fingerprinting.
- **No caching** — re-runs hit the API fresh. Fine for occasional use.

## License

MIT — see [LICENSE](LICENSE).

# gh-to-email

Enumerate the email addresses a GitHub user has committed under across their
public footprint — owned repos plus recent cross-repo push activity.

Useful for: auditing your own commit footprint, hiring background-check
transparency, security research, and incident response.

## Quick start (macOS — no install needed)

Skip the rest of this README if all you want is to use the tool:

1. **Download** the latest release zip:
   <https://github.com/nikitaclicks/shakal/releases/latest>
2. **Unzip** it (macOS does this for you when you double-click the `.zip`)
3. Open the unzipped folder and **double-click `gh-to-email.app`**
4. **First time only** — macOS shows a "developer cannot be verified" warning.
   See [Bypassing the first-run warning](#bypassing-the-first-run-warning) below.
5. The app walks you through making a free GitHub token (~1 minute, just
   click "Generate token" on the page it opens for you)
6. Type any GitHub username when prompted — results save to your Desktop
   as both a text summary and a JSON file

That's the whole thing. No Python, no `gh` CLI, no Terminal.

### Bypassing the first-run warning

macOS blocks unsigned apps from the internet. This is a **one-time** thing —
once approved, double-click works forever. Two ways to fix it; pick whichever
is easier.

#### Method A: Terminal (recommended — always works, 30 seconds)

1. Open **Terminal** (Cmd+Space, type `terminal`, press Enter)
2. In the Terminal window, type this **exactly** (note the trailing space —
   don't press Enter yet):
   ```
   xattr -dr com.apple.quarantine 
   ```
3. In Finder, **drag the unzipped folder** (`gh-to-email-0.1.1-macos-arm64`)
   onto the Terminal window. This pastes the path automatically.
4. Press **Enter**.
5. ✅ Done. Double-click `gh-to-email.app` — no warning, ever.

#### Method B: System Settings (no Terminal, but flaky on macOS 26)

> **⚠️ macOS 26 (Tahoe) quirk:** the first warning dialog has a "Move to
> Trash" button as the default — clicking it actually moves the app to
> Trash. If you did that, drag it back from Trash first.

1. Double-click `gh-to-email.app` — warning appears
2. Click **Done** (the small button, NOT "Move to Trash")
3. Open **System Settings** → **Privacy & Security**
4. Scroll all the way down to "Security"
5. If you see *"gh-to-email.app was blocked..."* → click **Open Anyway**,
   then confirm with Touch ID, then click **Open** in the next dialog
6. If you DON'T see that entry → the System Settings method isn't going
   to work on your macOS version. Use Method A above.

#### Method C (older macOS 14 and earlier only)

Right-click `gh-to-email.app` → **Open** → **Open** in the warning. This
shortcut was removed in macOS 15.

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

## Ways to run it

| For | Use |
| --- | --- |
| A friend / family member on macOS who just wants results | The `.app` from the [release zip](https://github.com/nikitaclicks/shakal/releases/latest) — see [Quick start](#quick-start-macos--no-install-needed) above |
| Terminal users on macOS | The bare `gh-to-email` binary (also in the release zip) — see [CLI usage](#cli-usage) |
| Developers / Linux / Windows | The Python script directly — see [Running the Python source](#running-the-python-source) |

## CLI usage

The release zip also includes a bare `gh-to-email` binary. Once you've
unzipped:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
./gh-to-email octocat
./gh-to-email https://github.com/octocat --verbose
./gh-to-email torvalds --max-pages-per-repo 2 --skip-events
```

If you have the [`gh` CLI](https://cli.github.com/) installed and logged in,
you can skip `GITHUB_TOKEN` — the binary will read your token via
`gh auth token` automatically.

## Running the Python source

For development, or on Linux/Windows where no binary is shipped:

- Python 3.8+ (stdlib only, no pip deps)
- Auth via either `gh auth login` or `GITHUB_TOKEN` / `GH_TOKEN` env var

```bash
python3 gh_to_email.py octocat
python3 gh_to_email.py https://github.com/octocat --verbose
python3 gh_to_email.py torvalds --max-pages-per-repo 2 --skip-events
python3 gh_to_email.py octocat --out /tmp/out.json
```

Authenticated requests give you 5000/hour — plenty for any single user scan.

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

## Building from source

If you're on Linux, Windows, or Intel Mac (none of which the release zip
supports), build your own binary:

```bash
git clone https://github.com/nikitaclicks/shakal
cd shakal
./build.sh
```

This produces `dist/<release-folder>.zip` matching your host OS + arch.

**Cross-platform note:** PyInstaller binaries are platform-specific. The
macOS .app is also macOS-only. The Python source (`gh_to_email.py`) is the
only fully portable piece.

| target | build host needed |
| --- | --- |
| macOS arm64 (Apple Silicon) | macOS arm64 |
| macOS x86_64 (Intel) | macOS Intel |
| Linux x86_64 | Linux x86_64 (no .app, CLI binary only) |
| Windows x86_64 | Windows x86_64 (no .app, CLI binary only) |

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

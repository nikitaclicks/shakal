gh-to-email — quick guide
=========================

WHAT IT DOES
  Finds the email addresses a GitHub user has committed under across
  their public repositories. Useful for auditing your own commit
  footprint or for legitimate research.

  All data comes from GitHub's public API — the tool just aggregates
  what's already visible to anyone.

HOW TO USE
  1. Double-click "gh-to-email.app"

  2. If macOS shows a warning ("cannot be opened" or "from an
     unidentified developer"):
       a. Close the warning
       b. RIGHT-click on gh-to-email.app (or two-finger tap)
       c. Choose "Open"
       d. Click "Open" again in the dialog
     You only need to do this ONCE per Mac.

  3. The first time, it'll help you create a GitHub token (1 minute,
     free). Your browser will open the right page automatically.

  4. After that, just type a GitHub username when prompted. Results
     save to your Desktop as a JSON file and a text summary.

THAT'S IT
  No installation, no Python, no Terminal. Just double-click.

ALSO INCLUDED
  gh-to-email   — same tool as a command-line binary (for terminal
                  users). Just run: ./gh-to-email <username>

SOURCE / ISSUES
  https://github.com/nikitaclicks/shakal

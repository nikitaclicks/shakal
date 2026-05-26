gh-to-email — quick guide
=========================

WHAT IT DOES
  Finds the email addresses a GitHub user has committed under across
  their public repositories. All data comes from GitHub's public
  API — the tool just aggregates what's already visible to anyone.

FIRST-TIME SETUP — bypass the macOS warning
  macOS will warn the first time you open this app because it's not
  signed by an Apple Developer (signing costs $99/year, not worth
  it for a hobby tool). You only need to bypass once.

  RECOMMENDED METHOD — Terminal (always works, 30 seconds):

    1. Open Terminal (Cmd+Space, type "terminal", press Enter)

    2. In the Terminal window, type EXACTLY this — with a SPACE
       at the end, and don't press Enter yet:

         xattr -dr com.apple.quarantine

    3. In Finder, drag the unzipped folder
       (gh-to-email-0.1.1-macos-arm64) onto the Terminal window.
       The folder's path appears automatically after what you typed.

    4. Press Enter.

    5. Done. Now double-click gh-to-email.app and it just works.


  ALTERNATIVE — System Settings (no Terminal, flaky on macOS 26):

    On macOS 26 (Tahoe), the warning dialog has a "Move to Trash"
    button as the default. Clicking it ACTUALLY MOVES the app to
    trash. If that happened, drag the app folder back out of trash.

    1. Double-click gh-to-email.app — warning appears
    2. Click "Done" (the small button, NOT "Move to Trash")
    3. Open System Settings → Privacy & Security
    4. Scroll all the way down to the "Security" section
    5. If you see "gh-to-email.app was blocked..." with an
       "Open Anyway" button — click it, confirm with Touch ID,
       and click "Open" in the next dialog
    6. If you DON'T see that entry, use the Terminal method above

HOW TO USE (after first-run bypass)
  1. Double-click gh-to-email.app

  2. The first time, the app will help you make a free GitHub
     token (1 minute). Your browser opens to the right page
     automatically — just scroll to the bottom and click
     "Generate token", then paste it back into the app.

  3. Type a GitHub username when prompted. Results save to your
     Desktop as a text summary and a JSON file.

That's it.

ALSO INCLUDED
  gh-to-email   — same tool as a command-line binary (for terminal
                  users). Just run: ./gh-to-email <username>

SOURCE / ISSUES
  https://github.com/nikitaclicks/shakal

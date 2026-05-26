on run
	try
		set appPath to POSIX path of (path to me)
		set binaryPath to appPath & "Contents/Resources/gh-to-email"
		set homeDir to POSIX path of (path to home folder)
		set configDir to homeDir & ".config/gh-to-email/"
		set tokenFile to configDir & "token"
		set desktopPath to POSIX path of (path to desktop folder)

		try
			do shell script "xattr -dr com.apple.quarantine " & quoted form of appPath
		end try

		set hasToken to false
		try
			set token to do shell script "cat " & quoted form of tokenFile
			if token is not "" then set hasToken to true
		end try

		if not hasToken then
			display dialog "First-time setup: this app needs a free GitHub access token (takes about 1 minute).

Click 'Open browser' to go to the GitHub token page. The form will be pre-filled — just scroll to the bottom and click 'Generate token'.

(No permissions needed. The token only raises the API rate limit.)" with title "gh-to-email — first-time setup" buttons {"Cancel", "Open browser"} default button "Open browser"

			do shell script "open 'https://github.com/settings/tokens/new?description=gh-to-email&scopes='"

			set tokenInput to display dialog "Paste the token you just generated:

(It starts with 'ghp_' followed by a long string. You can find it on the GitHub page after clicking 'Generate token'.)" with title "gh-to-email — paste your token" default answer "" buttons {"Cancel", "Save"} default button "Save"
			set token to text returned of tokenInput

			if token is "" then
				display dialog "No token entered. Run me again when you have one." with title "gh-to-email" buttons {"OK"} default button "OK"
				return
			end if

			do shell script "mkdir -p " & quoted form of configDir
			do shell script "printf '%s' " & quoted form of token & " > " & quoted form of tokenFile
			do shell script "chmod 600 " & quoted form of tokenFile
		end if

		set userInput to display dialog "Enter a GitHub username or profile URL:

(e.g. 'octocat' or 'https://github.com/octocat')" with title "gh-to-email" default answer "" buttons {"Cancel", "Look up"} default button "Look up"
		set username to text returned of userInput
		if username is "" then return

		set safeUsername to do shell script "echo " & quoted form of username & " | sed 's|https\\{0,1\\}://github.com/||; s|/.*||'"
		set outputJson to desktopPath & safeUsername & "-emails.json"
		set outputTxt to desktopPath & safeUsername & "-emails.txt"

		set runCmd to "GITHUB_TOKEN=" & quoted form of token & " " & quoted form of binaryPath & " " & quoted form of username & " --out " & quoted form of outputJson & " 2>&1"

		try
			set output to do shell script runCmd
		on error errMsg
			display dialog "Lookup failed:

" & errMsg with title "gh-to-email — error" buttons {"OK"} default button "OK"
			return
		end try

		do shell script "printf '%s\\n' " & quoted form of output & " > " & quoted form of outputTxt

		set choice to display dialog "Done. Results saved to your Desktop:
   " & safeUsername & "-emails.txt
   " & safeUsername & "-emails.json

Open the text summary now?" with title "gh-to-email — finished" buttons {"Open JSON", "Open text", "Done"} default button "Open text"
		set b to button returned of choice
		if b is "Open text" then
			do shell script "open " & quoted form of outputTxt
		else if b is "Open JSON" then
			do shell script "open " & quoted form of outputJson
		end if
	on error errMsg number errNum
		if errNum is -128 then return
		display dialog "Unexpected error: " & errMsg with title "gh-to-email" buttons {"OK"} default button "OK"
	end try
end run

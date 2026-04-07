on run argv
	set tweetText to item 1 of argv
	set the clipboard to tweetText

	tell application "Google Chrome"
		activate
		if (count of windows) is 0 then
			make new window
		end if
		tell window 1
			set newTab to make new tab with properties {URL:"https://x.com/compose/post"}
		end tell
	end tell

	-- Wait for the composition box to be ready
	delay 5

	tell application "System Events"
		-- Paste the tweet content
		keystroke "v" using {command down}
		delay 1
		-- Send the tweet (Cmd + Enter)
		keystroke return using {command down}
	end tell
end run

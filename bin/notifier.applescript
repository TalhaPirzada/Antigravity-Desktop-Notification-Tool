-- Antigravity Notifier applet source.
-- Reads a 4-line payload (message, title, subtitle, sound) from a file whose
-- path is passed through the AGY_PAYLOAD environment variable (fallback: /tmp/agy_notify_payload.txt)
-- and posts a notification attributed to this applet (which carries the Antigravity icon).
on run
	set payloadPath to "/tmp/agy_notify_payload.txt"
	try
		set envPath to do shell script "printf %s \"$AGY_PAYLOAD\""
		if envPath is not "" then set payloadPath to envPath
	end try
	set rawText to ""
	try
		set rawText to do shell script "cat " & quoted form of payloadPath
	end try
	set AppleScript's text item delimiters to linefeed
	set parts to text items of rawText
	set AppleScript's text item delimiters to ""
	set theMessage to "Notification"
	set theTitle to "Antigravity"
	set theSubtitle to ""
	set theSound to ""
	if (count of parts) > 0 then set theMessage to item 1 of parts
	if (count of parts) > 1 then set theTitle to item 2 of parts
	if (count of parts) > 2 then set theSubtitle to item 3 of parts
	if (count of parts) > 3 then set theSound to item 4 of parts
	if theSound is not "" then
		display notification theMessage with title theTitle subtitle theSubtitle sound name theSound
	else
		display notification theMessage with title theTitle subtitle theSubtitle
	end if
end run

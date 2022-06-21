## Names for XTERM Colors

`names.py` contains a single dict with all the color names and hex codes linked to the XTERM color IDs.

`colors.html` is just a nice way to visualize them.

**NOTES**

- This list does not include the 0-15 system colors.
- The color names are stored here as a dict, where the key is the XTERM color index and the values are a tuple of the color name and the associated hex color.
- All of the colors are formatted with only the first letter capitalized and with the spelling "grey" rather than "gray".
- Due to my particular use-case, I have some duplicates in here. If you want all 240 colors to have unique names, you'll need to rename a few. Here are the duplicates:
	-	Lime - 40,46
	-	Electric green - 41,47
	-	Spring green - 48,49
	-	Twilight - 61,62
	-	Sea green - 37,73
	-	Rain blue - 60,74
	-	Chartreuse - 83,119
	-	Verdigris - 85,86
	-	Violet - 98,99
	-	Pistachio - 113,114
	-	Heather - 134,135
	-	Melon - 156,157
	-	Magenta - 164,200,201
	-	Obsidian - 232,233
	- Soot - 234,235


Hi!

Thank you for downloading 'Quick Text Editor'! It's not the best editor you can
find out there, but I hope it satisfies your needs.

For any questions, problems or suggestions, visit:
https://github.com/Mohyoo/Quick-Text-Editor



## Just to know
Please don't put the program in a protected folder, as it's designed to be
portable. Doing so will cause silent issues with reading/writing permissions.

There is a 'fonts' folder here, I recommend installing the 'JetBrains Mono' and
'Open Sans' fonts provided there. They are nice and clean, and work well for
this program.



## Optional Configuration
In the program directory, there will be (after the first launch) a 'config.json'
file. Its options should be clear, but just in case, here is the explanation of
the necessary options:

- 'text_font_priority': This is a list of font types. If the first one is
   installed, the program will use it, otherwise it'll check the others in the
   written order.
- 'ui_font_priority': Same as above, but for UI elements.
- 'text_font_size': Font size for the text area.
- 'ui_font_size': Font size for the UI elements.
- 'indent_size': How many spaces to insert when pressing TAB.
- 'max_undo': How many undo steps to remember (lower = faster).
- 'big_file_size': Minimum file size (MB) to trigger a warning before opening.
- 'independent_windows': If true, each instance of this editor will spawn its
   own process. Slightly slower at startup, but recommended if you often open
   big files.

To reset settings, simply delete the 'config.json' file.

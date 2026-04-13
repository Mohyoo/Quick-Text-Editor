<div align="center">
  <h4 style="margin: 0; font-family: Arial, sans-serif; color: #d73a49; padding: 5px">Palestine Children, Women and Men are dying...</h4>
  <img src="Assets/Palestine.jpg" alt="Palestine Flag" style="width: 375px; border-radius: 3%;">
</div><br>


## About
Quick Text Editor is just - you know - a handy plain text editor intended for simple use and designed to be cross platform. Not the best in its type, but still functional.<br>
> ***Under development. Help is highly appreciated!***

| Light Mode | Dark Mode |
| :---: | :---: |
| ![Screenshot Light](Assets/screenshot_light.png) | ![Screenshot Dark](Assets/screenshot_dark.png) |


## Before Usage
Please don't put the program in a protected folder, as it's designed to be
portable. Doing so will cause silent issues to save configuration settings.

There is a 'Fonts' folder in the program directory, I recommend installing the
'JetBrains Mono' and 'Open Sans' fonts provided there. They are nice and clean
and work well for this program.

To reset settings, simply go to 'Quick Text Editor' directory and delete the
'config.json' file.


## Compile From Source
You can bundle the program easily using PyInstaller or cx_Freeze, but I recommend using Nuitka for a small performance gain:
```
pip install tkinterdnd2, Nuitka
cd "where/main.py/is"
python -m nuitka --deployment --disable-cache=all --standalone --prefer-source-code --noinclude-setuptools-mode=error --plugin-enable=tk-inter --enable-plugin=anti-bloat --python-flag=-S --python-flag=-O --python-flag=no_asserts --python-flag=no_docstrings --lto=yes --remove-output --windows-console-mode=disable --windows-icon-from-ico="Assets/icon.ico" --product-name="Quick Text Editor" --file-version=1.0.0 --output-filename=quick-text-editor main.py
```
> If you have a **Static Python** distribution, add this argument `--static-libpython=yes` to create a standalone release that doesn't rely on system shared libraries.
import os
import sys
import json
import tempfile
import platform
from pathlib import Path
    
try:
    from tkinter import font
    from tkinter import (Tk, Frame, Button, Text, Label, Scrollbar, Toplevel, Entry, IntVar,
                         END, X, Y, LEFT, RIGHT, BOTH, FLAT)
    from tkinter.messagebox import askyesno, askyesnocancel, showerror
    from tkinter.filedialog import askopenfilename, asksaveasfilename
    from tkinterdnd2 import DND_FILES, TkinterDnD
    
except Exception as e:
    print(f'Error: {e}')
    print("Perhaps you didn't install a required module? Use 'pip' to install it.")
    sys.exit(1)

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, 'config.json')
ENCODING = 'utf-8'
ENCODING_ERROR_HANDLER = 'replace'
UI_FONT_PRIORITY = [    # For UI elements, not for text area.
    'Open Sans',
    'Segoe UI',
    'San Francisco',
    'Helvetica Neue',
    'Ubuntu',
    'Cantarell',
    'Verdana', 
    'Arial', 
]
DEFAULT_CONFIG = {
    'geometry': '800x600',
    'maximized': False,
    'font_priority': [    # For the text area only.
        'JetBrains Mono',
        'Cascadia Code',
        'Consolas',
        'Source Code Pro',
        'Ubuntu Mono',
        'Courier New',
        'Courier'
    ],
    'font_size': 12,
    'dark_mode': True,
    'dark_bg': '#020617',
    'dark_fg': '#e5e7eb',
    'light_bg': '#ffffff',
    'light_fg': '#000000',
    'indent_size': 4,
    'max_undo': 128,
    'wrap': False,
}
SYSTEM = platform.system()
PREFIX_KEY = 'Command' if SYSTEM == 'Darwin' else 'Control'

def load_config():
    """Load settings from the config file."""
    if os.path.exists(CONFIG_FILE):
        try:
            # raise Exception(':P')
            with open(CONFIG_FILE, 'r', encoding=ENCODING, errors=ENCODING_ERROR_HANDLER) as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception as e:
            print(f'Failed to load config: {e}')
            return DEFAULT_CONFIG
    return DEFAULT_CONFIG

def save_config(config):
    """Save settings safely using a temporary file to prevent corruption."""
    fd, temp_path = tempfile.mkstemp(dir=SCRIPT_DIR, text=True)
    try:
        # raise Exception(':P')
        with os.fdopen(fd, 'w', encoding=ENCODING) as f:
            json.dump(config, f, indent=4)
        os.replace(temp_path, CONFIG_FILE)
        
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        # showerror("Configuration Error", f"Failed to save settings!\nError: {e}")
        print(f'Failed to save config: {e}')

# --- THE EDITOR ---
def quick_text_editor(initial_path=None):
    """Launch the quick graphical text editor."""
    # Internal State
    config = load_config()
    geometry  = config['geometry']
    maximized = config['maximized']
    font_priority = config['font_priority']
    font_size = config['font_size']
    dark_mode = config['dark_mode']
    dark_bg = config['dark_bg']
    dark_fg = config['dark_fg']
    light_bg = config['light_bg']
    light_fg = config['light_fg']
    indent_size = config['indent_size']
    max_undo = config['max_undo']
    wrap = config['wrap']
    
    current_file_path = initial_path
    initial_content_hash = None
    editing_big_file = False
    last_mtime = None

    # --- ACTIONS ---
    def show_shortcuts():
        win = Toplevel(root)
        win.title('Keyboard Shortcuts')
        win.resizable(False, False)
        win.transient(root)
        win.grab_set()

        bg = '#020617' if dark_mode else '#ffffff'
        fg = '#e5e7eb' if dark_mode else '#000000'
        win.configure(bg=bg)
        
        shortcuts_text = (
            'Ctrl-N          →  New File\n'
            'Ctrl-O          →  Open File\n'
            'Ctrl-S          →  Save File\n'
            'Ctrl-Shift-S    →  Save File As\n'
            'Ctrl-T          →  Toggle Theme\n'
            'Ctrl-W          →  Toggle Word-Wrap\n'
            'Ctrl-F          →  Find/Search\n'
            'Ctrl-(+)        →  Zoom In\n'
            'Ctrl-(-)        →  Zoom Out\n'
            'Ctrl-C          →  Copy (whole line if no selection)\n'
            'Ctrl-X          →  Cut (whole line if no selection)\n'
            'Ctrl-A          →  Select All\n'
            'Ctrl-D          →  Duplicate Line\n'
            'Ctrl-Backspace  →  Delete Previous Word\n'
            'Ctrl-Del        →  Delete Next Word\n'
            'Tab             →  Indent (4 Spaces)\n'
            'Shift-Tab       →  Unindent (4 spaces)\n'
        )
        if SYSTEM == 'Darwin':
            shortcuts_text = shortcuts_text.replace('Ctrl-', '⌘-')

        label = Label(win, text=shortcuts_text, justify='left', font=(text_font[0], 12),
                      bg=bg, fg=fg, padx=20, pady=16)
        button = Button(win, text='Close', command=win.destroy, font=ui_font,
                        relief=FLAT, bg='#1e293b' if dark_mode else '#e5e7eb', fg=fg, padx=12, pady=4)
        
        label.pack()
        button.pack(pady=(0, 12))
        
        win.update_idletasks()
        x = root.winfo_rootx() + (root.winfo_width() - win.winfo_width()) // 2
        y = root.winfo_rooty() + (root.winfo_height() - win.winfo_height()) // 2
        win.geometry(f'+{x}+{y}')

    def on_ctrl_backspace(event):
        text_field.delete(text_field.index('insert -1c wordstart'), 'insert')
        return 'break'

    def on_ctrl_delete(event):
        text_field.delete('insert', 'insert wordend')
        return 'break'
    
    def on_ctrl_a(event):
        text_field.tag_add('sel', '1.0', 'end-1c')
        return 'break'
    
    def on_ctrl_x(event):
        if not text_field.tag_ranges('sel'):
            line_start, line_end = text_field.index('insert linestart'), text_field.index('insert lineend +1c')
            root.clipboard_clear()
            root.clipboard_append(text_field.get(line_start, line_end))
            text_field.delete(line_start, line_end)
        else:
            text_field.event_generate('<<Cut>>')
        return 'break'

    def on_ctrl_c(event):
        if not text_field.tag_ranges('sel'):
            root.clipboard_clear()
            root.clipboard_append(text_field.get('insert linestart', 'insert lineend +1c'))
        else:
            text_field.event_generate('<<Copy>>')
        return 'break'

    def on_ctrl_d(event):
        line_start = text_field.index('insert linestart')
        line_end = text_field.index('insert lineend')
        line_content = text_field.get(line_start, line_end)
        # Insert a newline and the content at the start of the next line
        text_field.insert(f"{line_end}", f"\n{line_content}")
        return 'break'

    def on_tab(event):
        text_field.insert('insert', ' ' * indent_size)
        return 'break'

    def on_shift_tab(event):
        line_start = "insert linestart"
        head = text_field.get(line_start, f"{line_start} + {indent_size}c")
        if head.startswith(' '):
            num_spaces = len(head) - len(head.lstrip(' '))
            text_field.delete(line_start, f"{line_start} + {num_spaces}c")
        return 'break'
        
    def change_font(delta):
        nonlocal font_size, text_font
        if font_size <= 12: step = 1
        elif font_size <= 24: step = 2
        elif font_size <= 48: step = 4
        else: step = 8
        new_size = font_size + delta * step
        new_size = min(96, new_size)
        new_size = max(7, new_size)
        if 7 <= new_size <= 96 and new_size != font_size:
            font_size = new_size
            text_font[-1] = font_size
            text_field.config(font=text_font)

    def update_v_scrollbar(*args):
        size = text_field.yview()
        if size == (0.0, 1.0):
            v_scrollbar.grid_remove()
        else:
            v_scrollbar.set(*size)
            v_scrollbar.grid() 

    def update_h_scrollbar(*args):
        size = text_field.xview()
        if size == (0.0, 1.0) or text_field.cget('wrap') != 'none':
            h_scrollbar.grid_remove()
        else:
            h_scrollbar.set(*size)
            h_scrollbar.grid()
            
    def apply_theme():
        if dark_mode:
            root.config(bg='#0f172a')
            top_frame.config(bg='#001033')
            text_field.config(bg=dark_bg, fg=dark_fg, insertbackground='#e5e7eb')
            theme_btn.config(bg='#1e293b', fg='#e5e7eb', text='☀ Light')
            for btn in [new_btn, open_btn, save_btn, save_as_btn, shortcuts_btn, plus_btn, minus_btn, wrap_btn, search_btn]:
                btn.config(bg='#1e293b', fg='#e5e7eb', activebackground='#334155')
        else:
            root.config(bg='#f8fafc')
            top_frame.config(bg='#2d5ac4')
            text_field.config(bg=light_bg, fg=light_fg, insertbackground='black')
            theme_btn.config(bg='#e5e7eb', fg='black', text='🌙 Dark')
            for btn in [new_btn, open_btn, save_btn, save_as_btn, shortcuts_btn, plus_btn, minus_btn, wrap_btn, search_btn]:
                btn.config(bg='#e5e7eb', fg='black', activebackground='#d1d5db')

    def toggle_theme(event=None):
        nonlocal dark_mode
        dark_mode = not dark_mode
        apply_theme()
    
    def toggle_wrap(event=None):
        nonlocal wrap
        if text_field.cget('wrap') == 'none':
            text_field.config(wrap='word')
            wrap_btn.config(text='⇉ Unwrap')
        else:
            text_field.config(wrap='none')
            wrap_btn.config(text='⤶ Wrap')
        update_h_scrollbar()
        wrap = not wrap
    
    def open_search(event=None):
        search_win = Toplevel(root)
        search_win.title('Find')
        search_win.attributes('-topmost', True)
        search_win.transient(root)
        search_win.minsize(300, 55)
        
        win_w, win_h = 350, 60
        search_win.minsize(300, 55)
        
        root.update_idletasks()
        x = root.winfo_rootx() + (root.winfo_width() - win_w) // 2
        y = root.winfo_rooty() + (root.winfo_height() - win_h) // 2
        search_win.geometry(f'{win_w}x{win_h}+{x}+{y}')
        
        bg = dark_bg if dark_mode else light_bg
        fg = dark_fg if dark_mode else light_fg
        search_win.configure(bg=bg, padx=10, pady=10)

        entry = Entry(search_win, font=(text_font[0], 12), bg=bg, fg=fg, insertbackground=fg, highlightbackground=fg, highlightthickness=1, bd=0)
        entry.pack(side=LEFT, padx=5, ipady=5, fill=X, expand=True)
        entry.focus_set()

        def on_search_close():
            text_field.tag_remove('found', '1.0', END)
            search_win.destroy()

        search_win.protocol("WM_DELETE_WINDOW", on_search_close)
        text_field.tag_config('found', background='#eab308', foreground='black')

        def find_text(*_):
            query = entry.get()
            text_field.tag_remove('found', '1.0', END)
            if not query: return
            match_len = IntVar()
            idx = '1.0'
            while True:
                idx = text_field.search(query, idx, nocase=1, stopindex=END, count=match_len)
                if not idx: break
                lastidx = f"{idx}+{match_len.get()}c"
                text_field.tag_add('found', idx, lastidx)
                idx = lastidx

        find_btn = Button(search_win, text='Find All', command=find_text, font=ui_font, bg=bg, fg=fg, relief=FLAT)
        find_btn.pack(side=LEFT)
        if dark_mode: find_btn.config(bg='#1e293b', fg='#e5e7eb', activebackground='#334155')
        else: find_btn.config(bg='#e5e7eb', fg='black', activebackground='#d1d5db')
        entry.bind('<Return>', find_text)
    
    def handle_exception(exc, val, tb):
        import traceback
        err = ''.join(traceback.format_exception(exc, val, tb))
        print(f"\nInternal Error Caught:\n{err}")
        showerror("Internal Error", f"An unexpected error occurred:\n{val}")
    
    # --- FILE HANDLING ---
    def set_title():
        name = os.path.basename(current_file_path) if current_file_path else "Untitled"
        root.title(f"{name} - Quick Text Editor")
    
    def check_file_size(path):
        nonlocal editing_big_file
        was_editing_big_file = bool(editing_big_file)
        editing_big_file = False
        size_limit = 4 * 1024 * 1024
        file_size = os.path.getsize(path)
        
        if file_size > size_limit:
            size_mb = int(file_size / (1024 * 1024))
            response = askyesno(
                "Big File Warning", 
                f"The file is {size_mb} MB. Opening large files may cause the editor to freeze.\n\nContinue anyway?",
                default='no',
                icon='warning',
                parent=root,
            )
            if response is True: editing_big_file = True
            else: editing_big_file = was_editing_big_file
            return response
        return True
    
    def handle_drop(event):
        nonlocal current_file_path
        path = event.data.strip('{}')
        if not os.path.isfile(path):
            return

        # Confirm dropping
        current_content = text_field.get('1.0', 'end-1c')
        if is_modified():
            response = askyesno(
                "Confirm",
                f"Discard changes and open '{os.path.basename(path)}'?",
                default='no',
                parent=root,
            )
            if not response: return
        
        if not check_file_size(path): return
        try:
            with open(path, 'r', encoding=ENCODING, errors=ENCODING_ERROR_HANDLER) as f:
                content = f.read()
            text_field.delete('1.0', END)
            text_field.insert('1.0', content)
            current_file_path = path
            update_mtime()
            update_initial_hash()
            set_title()
        except Exception as e:
            print(f"Drop error: {e}")
    
    def new_file(event=None):
        nonlocal current_file_path
        if is_modified():
            response = askyesno(
                "Confirm",
                "Discard current text and start new?",
                default='no',
                parent=root,
            )
            if not response: return
        
        text_field.delete('1.0', END)
        current_file_path = None
        set_title()

    def open_file(event=None):
        nonlocal current_file_path, editing_big_file
        if is_modified():
            response = askyesno(
                "Confirm",
                "Discard current text and open another file?",
                default='no',
            )
            if not response: return
        
        path = askopenfilename()
        if path and check_file_size(path):
            try:
                with open(path, 'r', encoding=ENCODING, errors=ENCODING_ERROR_HANDLER) as f:
                    content = f.read()
                text_field.delete('1.0', END)
                text_field.insert('1.0', content)
                current_file_path = path
                update_mtime()
                update_initial_hash()
                set_title()
            except Exception as e:
                print(f"Error opening file: {e}")

    def save_file(event=None):
        nonlocal current_file_path
        if not current_file_path:
            current_file_path = asksaveasfilename(
                initialfile=(text_field.get('1.0', 'end-1c').strip().split() or ['Text'])[0],
                defaultextension='.txt',
                filetypes=[('Plain Text', '*.txt'), ('All files', '*.*')],
                title='Save As'
            )
        
        if current_file_path:
            try:
                content = text_field.get('1.0', 'end-1c')
                # raise Exception(':P')
                with open(current_file_path, 'w', encoding=ENCODING, errors=ENCODING_ERROR_HANDLER) as f:
                    f.write(content)
                update_mtime()
                update_initial_hash()
                set_title()
                return True
            except Exception as e:
                print(f"Error saving file: {e}")
                showerror("File Save Error", f"Could not save file:\n{e}")
                return False
    
    def save_file_as(event=None):
        nonlocal current_file_path
        old_path = current_file_path
        current_file_path = None         # Force the dialog in save_file()
        if not save_file():
            current_file_path = old_path # Restore if user cancels
    
    def get_content_hash():
        if editing_big_file: return None
        return hash(text_field.get('1.0', 'end-1c'))

    def update_initial_hash():
        nonlocal initial_content_hash
        initial_content_hash = get_content_hash()
    
    def is_modified():
        if editing_big_file: return True
        if not current_file_path:
            current_text = text_field.get('1.0', 'end-1c')
            return bool(current_text)
        else:
            return get_content_hash() != initial_content_hash
    
    def update_mtime():
        nonlocal last_mtime
        if current_file_path and os.path.exists(current_file_path):
            last_mtime = os.path.getmtime(current_file_path)
            
    def check_external_modification(event=None):
        nonlocal last_mtime
        if not current_file_path or not os.path.exists(current_file_path):
            return
        
        try: current_mtime = os.path.getmtime(current_file_path)
        except: return
        
        if last_mtime and current_mtime > last_mtime:
            last_mtime = current_mtime
            
            msg = f"'{os.path.basename(current_file_path)}' was modified externally."
            icon = 'question'
            
            if is_modified():
                msg += "\n\nWARNING: You have unsaved changes in the editor. Reloading will overwrite them!"
                icon = 'warning'
            
            response = askyesno(
                "File Conflict",
                f"{msg}\n\nReload from disk?",
                icon=icon,
                parent=root,
            )
            if response:
                try:
                    with open(current_file_path, 'r', encoding=ENCODING, errors=ENCODING_ERROR_HANDLER) as f:
                        content = f.read()
                    text_field.delete('1.0', END)
                    text_field.insert('1.0', content)
                    update_initial_hash()

                except Exception as e:
                    print(f"Reload error: {e}")
    
    def on_close():
        nonlocal geometry, maximized
        # Check if there are changes
        should_prompt = False
        if is_modified(): should_prompt = True
        if should_prompt:
            response = askyesnocancel(
                "Unsaved Changes",
                "Save changes before exiting?",
                default='cancel',
                parent=root,
            )
            if response is True:
                if not save_file():
                    return
            elif response is None:
                return
        
        # Save states
        if root.state() == 'zoomed': maximized = True
        else:
            try: maximized = True if root.attributes('-zoomed') else False
            except: maximized = False
        
        root.state('normal')
        geometry = root.geometry()
        
        # Prepare and save final config
        final_config = {
            'geometry': geometry,
            'maximized': maximized,
            'font_priority': font_priority,
            'font_size': font_size,
            'dark_mode': dark_mode,
            'dark_bg': dark_bg,
            'dark_fg': dark_fg,
            'light_bg': light_bg,
            'light_fg': light_fg,
            'indent_size': indent_size,
            'max_undo': max_undo,
            'wrap': wrap,
        }
        save_config(final_config)
        root.destroy()

    # --- UI SETUP ---
    root = TkinterDnD.Tk()
    root.geometry(geometry)
    root.minsize(700, 150)
    root.protocol('WM_DELETE_WINDOW', on_close)
    root.bind('<FocusIn>', check_external_modification)
    root.report_callback_exception = handle_exception
    if maximized:
        try: root.state('zoomed')
        except:
            try: root.wm_state('zoomed')
            except:
                try: root.attributes('-zoomed', True)
                except: pass
    
    # Font Type
    text_font = next((f for f in font_priority if f in font.families()), 'monospace')
    text_font = [text_font, font_size]
    ui_font = next((f for f in UI_FONT_PRIORITY if f in font.families()), 'TkDefaultFont')
    ui_font = [ui_font, 11]
    
    # Key Bindings
    root.bind_all(f'<{PREFIX_KEY}-plus>', lambda e: change_font(1))
    root.bind_all(f'<{PREFIX_KEY}-equal>', lambda e: change_font(1))
    root.bind_all(f'<{PREFIX_KEY}-minus>', lambda e: change_font(-1))
    root.bind_all(f'<{PREFIX_KEY}-n>', new_file)
    root.bind_all(f'<{PREFIX_KEY}-o>', open_file)
    root.bind_all(f'<{PREFIX_KEY}-s>', save_file)
    root.bind_all(f'<{PREFIX_KEY}-Shift-s>', save_file_as)
    root.bind_all(f'<{PREFIX_KEY}-w>', toggle_wrap)
    root.bind_all(f'<{PREFIX_KEY}-t>', toggle_theme)
    root.bind_all(f'<{PREFIX_KEY}-f>', open_search)

    # Top Bar
    top_frame = Frame(root)
    top_frame.pack(fill=X)

    # Left Side Buttons
    new_btn = Button(top_frame, text='📄 New', font=ui_font, command=new_file, relief=FLAT)
    open_btn = Button(top_frame, text='📂 Open', font=ui_font, command=open_file, relief=FLAT)
    save_btn = Button(top_frame, text='💾 Save', font=ui_font, command=save_file, relief=FLAT)
    save_as_btn = Button(top_frame, text='💾 Save As', font=ui_font, command=save_file_as, relief=FLAT)
    
    new_btn.pack(side=LEFT, padx=(6, 2), pady=6)
    open_btn.pack(side=LEFT, padx=2)
    save_btn.pack(side=LEFT, padx=2)
    save_as_btn.pack(side=LEFT, padx=2)

    # Right Side Buttons
    theme_btn = Button(top_frame, text='🌙 Dark', font=ui_font, command=toggle_theme, relief=FLAT)
    wrap_btn = Button(top_frame, text='⤶ Wrap', font=ui_font, command=toggle_wrap, relief=FLAT)
    shortcuts_btn = Button(top_frame, text='⌨ Shortcuts', font=ui_font, command=show_shortcuts, relief=FLAT)
    plus_btn = Button(top_frame, text='A⁺', font=ui_font, command=lambda: change_font(1), relief=FLAT)
    minus_btn = Button(top_frame, text='A⁻', font=ui_font, command=lambda: change_font(-1), relief=FLAT)
    search_btn = Button(top_frame, text='🔍 Find', font=ui_font, command=open_search, relief=FLAT)
    
    minus_btn.pack(side=RIGHT, padx=(2, 6), pady=6)
    plus_btn.pack(side=RIGHT, padx=2)
    shortcuts_btn.pack(side=RIGHT, padx=2)
    theme_btn.pack(side=RIGHT, padx=2)
    wrap_btn.pack(side=RIGHT, padx=2)
    search_btn.pack(side=RIGHT, padx=2)

    # Text Area
    text_frame = Frame(root)
    text_frame.pack(expand=True, fill=BOTH)
    text_field = Text(text_frame, wrap='none', font=text_font, relief=FLAT, undo=True, maxundo=max_undo)
    h_scrollbar = Scrollbar(text_frame, orient='horizontal', command=text_field.xview)
    text_field.config(xscrollcommand=update_h_scrollbar)
    text_field.grid(row=0, column=0, sticky='nsew')
    h_scrollbar.grid(row=1, column=0, sticky='ew')

    text_field.focus_set()
    text_field.drop_target_register(DND_FILES)
    text_field.dnd_bind('<<Drop>>', handle_drop)
    # This command might be needed in linux for drag&drop: sudo apt-get install tk-dev
   
    text_field.bind(f'<{PREFIX_KEY}-BackSpace>', on_ctrl_backspace)
    text_field.bind(f'<{PREFIX_KEY}-Delete>', on_ctrl_delete)
    text_field.bind(f'<{PREFIX_KEY}-x>', on_ctrl_x)
    text_field.bind(f'<{PREFIX_KEY}-c>', on_ctrl_c)
    text_field.bind('<Tab>', on_tab)
    text_field.bind('<Shift-Tab>', on_shift_tab)
    text_field.bind(f'<{PREFIX_KEY}-a>', on_ctrl_a)
    text_field.bind(f'<{PREFIX_KEY}-d>', on_ctrl_d)

    v_scrollbar = Scrollbar(text_frame, command=text_field.yview)
    v_scrollbar.grid(row=0, column=1, sticky='ns')
    text_frame.grid_columnconfigure(0, weight=1)
    text_frame.grid_rowconfigure(0, weight=1)
    text_field.config(yscrollcommand=update_v_scrollbar)
    
    # Final touches
    if wrap: toggle_wrap()
    apply_theme()
    set_title()
    
    # Open file if available and hash it
    if current_file_path and os.path.exists(current_file_path) and check_file_size(current_file_path):
        try:
            with open(current_file_path, 'r', encoding=ENCODING, errors=ENCODING_ERROR_HANDLER) as f:
                text_field.insert('1.0', f.read())
            update_mtime()
            update_initial_hash()
        except Exception as e:
            print(f"Startup file load error: {e}")
    
    # Start
    try: root.mainloop()
    except (KeyboardInterrupt, EOFError): print("Editor closed via terminal interrupt.")

if __name__ == '__main__':
    # Supports opening a file passed as an argument: python script.py my_file.txt
    target_path = str(Path(sys.argv[1])) if len(sys.argv) > 1 else None
    quick_text_editor(target_path)
    sys.exit(0)
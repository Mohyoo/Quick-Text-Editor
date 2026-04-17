import os
import sys
import json
from pathlib import Path

# --- CONFIG ---
SYSTEM = sys.platform
IS_COMPILED = getattr(sys, 'frozen', False) or '__compiled__' in globals()

if IS_COMPILED:
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))   # Where our main bin is
    exe_name = 'quick-text-editor'     # The bin name
    EXECUTABLE = os.path.join(APP_DIR, exe_name)                 # Full bin path
else:
    EXECUTABLE = sys.executable        # python.exe or just python in Linux/macOS
    APP_DIR = os.path.dirname(os.path.abspath(__file__))         # Where main.py is

os.chdir(APP_DIR)    # Keep the script portable
CONFIG_FILE = os.path.join(APP_DIR, 'config.json')
LOCK_FILE = os.path.join(APP_DIR, 'app.lock')
QUEUE_FILE = os.path.join(APP_DIR, 'queue.txt')
LOG_FILE = os.path.join(APP_DIR, 'console_log.log')
ICO_FILE = os.path.join(APP_DIR, 'assets', 'icon')    # For Tk, 'Assets' and 'assets' are the same
ENCODING = 'utf-8'
ENCODING_ERROR_HANDLER = 'surrogateescape'
PREFIX_KEY = 'Command' if SYSTEM == 'darwin' else 'Control'

DEFAULT_CONFIG = {
    'geometry': '800x600',
    'maximized': False,
    'text_font_priority': [
        'JetBrains Mono',
        'Cascadia Code',
        'Consolas',
        'Source Code Pro',
        'Ubuntu Mono',
        'Courier New',
        'Courier'
    ],
    'ui_font_priority': [
        'Open Sans',
        'Segoe UI',
        'San Francisco',
        'Helvetica Neue',
        'Ubuntu',
        'Cantarell',
        'Verdana', 
        'Arial', 
    ],
    'text_font_size': 12,
    'ui_font_size': 11,
    'dark_mode': True,
    'dark_bg': '#020617',
    'dark_fg': '#e5e7eb',
    'light_bg': '#ffffff',
    'light_fg': '#000000',
    'indent_size': 4,
    'max_undo': 128,
    'big_file_size': 4,
    'wrap': False,
    'independent_windows': True,
}

path_exist = os.path.exists
base_name = os.path.basename
lock = None
mother_root = None
secondary_windows = 0

if IS_COMPILED:
    # The app will be compiled as GUI, no console will appear so we need an error logger
    # This is only needed at startup, as most other runtime errors will be displayed in a dialog
    # So even if a file race happens at startup, we'll get the same error by the last app instance that wrote it
    import atexit
    class LOG(object):
        """Handle writing stdout and stderr to a file."""
        def __init__(self, filename):
            try:
                # 'w' mode safely overwrites, eliminating the need for os.remove()
                # buffering=1 enables line-buffering, significantly boosting performance
                # by avoiding forced flushes on every single string chunk.
                self.file = open(filename, 'w', encoding=ENCODING, buffering=1)
                self.enabled = True
                
                # Ensure the file closes cleanly when the program terminates
                atexit.register(self.close)
            except:
                # Catch specific OS errors (PermissionError, IOError)
                self.file = None
                self.enabled = False

        def write(self, data):
            if self.enabled and data:
                try:
                    self.file.write(data)
                    # Removed manual self.file.flush() here. 
                    # Line-buffering handles it without killing performance.
                except Exception:
                    pass

        def flush(self):
            # Ensure physical disk write (Data Integrity)
            if self.enabled and not self.file.closed:
                try: self.file.flush()
                except Exception: pass

        def close(self):
            if self.enabled and not self.file.closed:
                self.flush()
                self.file.close()
                self.enabled = False

        def __getattr__(self, attr):
            # Delegate methods securely, checking if file is still open
            if self.enabled and not self.file.closed: 
                return getattr(self.file, attr)
            return lambda *args, **kwargs: None

        def isatty(self):
            return False

    # Initialize and override stdout & stderr
    logfile = LOG(LOG_FILE)
    sys.stdout = logfile
    sys.stderr = logfile

def load_config():
    """Load settings from the config file."""
    if path_exist(CONFIG_FILE):
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
    import tempfile
    # Clean the config JSON
    for key in config.copy().keys():
        if key not in DEFAULT_CONFIG:
            del config[key]
    
    temp_path = ''
    try:
        # raise Exception(':P')
        fd, temp_path = tempfile.mkstemp(dir=APP_DIR, text=True)
        with os.fdopen(fd, 'w', encoding=ENCODING, errors='replace') as f:
            json.dump(config, f, indent=4)
        os.replace(temp_path, CONFIG_FILE)
        
    except Exception as e:
        if path_exist(temp_path):
            os.remove(temp_path)
        print(f'Failed to save config: {e}')

def get_lock():
    """Lock an internal program file to tell other instances to come here."""
    try:
        f = open(LOCK_FILE, 'w')
        if SYSTEM == 'win32':
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Success: We are the Primary
        return f
        
    except Exception as e:
        # Failure: We are the secondary, or someone else has the lock
        print(f"Error: {e}\n(This is probably a second instance, so it's normal)")
        return None

# --- EDITOR ---
class QuickTextEditor:
    """The main window of the GUI editor with all of its widgets."""
    # Config is applied for all instances
    global config
    config = load_config()    # This will be loaded at script startup because its in the class level
    
    geometry  = config['geometry']
    maximized = config['maximized']
    text_font_priority = config['text_font_priority']
    ui_font_priority = config['ui_font_priority']
    text_font_size = config['text_font_size']
    ui_font_size = config['ui_font_size']
    dark_mode = config['dark_mode']
    dark_bg = config['dark_bg']
    dark_fg = config['dark_fg']
    light_bg = config['light_bg']
    light_fg = config['light_fg']
    indent_size = config['indent_size']
    max_undo = config['max_undo']
    big_file_size = config['big_file_size']
    wrap = config['wrap']
        
    def __init__(self, initial_path=None, is_primary=True):
        """Intialize the quick text editor attributes."""
        # Instance-specific attributes
        self.is_primary = is_primary
        self.current_file_path = initial_path
        self.initial_content_hash = None
        self.editing_big_file = False
        self.in_search_window = False
        self.last_mtime = None
        self.queue_check_interval = 128
        self.external_check_interval = 1024
        self.queue_check_id = None
        self.external_check_id = None
        self.closed = False
        self.size_limit = self.big_file_size * 1024 * 1024
        
        # Shift the window a little bit if it's another instance
        # if (not lock or not self.is_primary) or (INDEPENDENT_WINDOWS):
        dimensions = self.geometry.replace('x', '+').split('+')
        if len(dimensions) == 4:
            from random import randint, choice
            w, h, x, y = dimensions
            shifted_x = int(x) + randint(5, 35) * choice([-1, 1])
            shifted_y = int(y) + randint(5, 35) * choice([-1, 1])
            self.geometry = f"{w}x{h}+{shifted_x}+{shifted_y}"
        
        # Load & Launch
        self.setup_ui()
        self.launch()
    
    def setup_ui(self):
        """Create and configure the window wigdtes (buttons, bars, etc)."""
        global mother_root, secondary_windows, ui_font, text_font
        # --- UI SETUP ---
        if self.is_primary:
            self.root = TkinterDnD.Tk()
            self.root.report_callback_exception = self.handle_exception    # One for all
            mother_root = self.root
        else:
            self.root = Toplevel(mother_root)
            secondary_windows += 1
            
        self.root.geometry(self.geometry)
        self.root.minsize(310, 150)
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
        self.root.after(512, self.set_icon)    # Set icon after 0.5s to avoid hanging while loading UI
        if self.maximized:
            try: self.root.state('zoomed')
            except:
                try: self.root.wm_state('zoomed')
                except:
                    try: self.root.attributes('-zoomed', True)
                    except: pass
                    
        # Font Type (Applied for all instances)
        if self.is_primary:
            text_font = next((f for f in self.text_font_priority if self.check_font_exists(f)), 'monospace')
            text_font = [text_font, self.text_font_size]
            ui_font = next((f for f in self.ui_font_priority if self.check_font_exists(f)), 'TkDefaultFont')
            ui_font = [ui_font, self.ui_font_size]
        
        # Key Bindings
        self.root.bind(f'<{PREFIX_KEY}-plus>', lambda e: self.change_font(1))
        self.root.bind(f'<{PREFIX_KEY}-equal>', lambda e: self.change_font(1))
        self.root.bind(f'<{PREFIX_KEY}-minus>', lambda e: self.change_font(-1))
        self.root.bind(f'<{PREFIX_KEY}-n>', self.new_file)
        self.root.bind(f'<{PREFIX_KEY}-o>', self.open_file)
        self.root.bind(f'<{PREFIX_KEY}-s>', self.save_file)
        self.root.bind(f'<{PREFIX_KEY}-Shift-s>', self.save_file_as)
        self.root.bind(f'<{PREFIX_KEY}-w>', self.toggle_wrap)
        self.root.bind(f'<{PREFIX_KEY}-t>', self.toggle_theme)
        self.root.bind(f'<{PREFIX_KEY}-f>', self.open_search)

        # Top Bar
        self.top_frame = Frame(self.root)
        self.top_frame.pack(fill=X)

        # Left Side Buttons
        self.new_btn = Button(self.top_frame, text='📄 New', font=ui_font, command=self.new_file, relief=FLAT)
        self.open_btn = Button(self.top_frame, text='📂 Open', font=ui_font, command=self.open_file, relief=FLAT)
        self.save_btn = Button(self.top_frame, text='💾 Save', font=ui_font, command=self.save_file, relief=FLAT)
        self.save_as_btn = Button(self.top_frame, text='💾 Save As', font=ui_font, command=self.save_file_as, relief=FLAT)
        
        self.new_btn.pack(side=LEFT, padx=(6, 2), pady=6)
        self.open_btn.pack(side=LEFT, padx=2)
        self.save_btn.pack(side=LEFT, padx=2)
        self.save_as_btn.pack(side=LEFT, padx=2)

        # Right Side Buttons
        self.theme_btn = Button(self.top_frame, text='🌙 Dark', font=ui_font, command=self.toggle_theme, relief=FLAT)
        self.wrap_btn = Button(self.top_frame, text='⤶ Wrap', font=ui_font, command=self.toggle_wrap, relief=FLAT)
        self.shortcuts_btn = Button(self.top_frame, text='⌨ Shortcuts', font=ui_font, command=self.show_shortcuts, relief=FLAT)
        self.plus_btn = Button(self.top_frame, text='A⁺', font=ui_font, command=lambda: self.change_font(+1), relief=FLAT)
        self.minus_btn = Button(self.top_frame, text='A⁻', font=ui_font, command=lambda: self.change_font(-1), relief=FLAT)
        self.search_btn = Button(self.top_frame, text='🔍 Find', font=ui_font, command=self.open_search, relief=FLAT)
        
        self.minus_btn.pack(side=RIGHT, padx=(2, 6), pady=6)
        self.plus_btn.pack(side=RIGHT, padx=2)
        self.shortcuts_btn.pack(side=RIGHT, padx=2)
        self.theme_btn.pack(side=RIGHT, padx=2)
        self.wrap_btn.pack(side=RIGHT, padx=2)
        self.search_btn.pack(side=RIGHT, padx=2)

        # Text Area
        self.text_frame = Frame(self.root)
        self.text_frame.pack(expand=True, fill=BOTH)
        self.text_field = Text(self.text_frame, wrap='none', font=text_font, relief=FLAT, undo=True, maxundo=self.max_undo)
        self.h_scrollbar = Scrollbar(self.text_frame, orient='horizontal', command=self.text_field.xview)
        self.text_field.config(xscrollcommand=self.update_h_scrollbar)
        self.text_field.grid(row=0, column=0, sticky='nsew')
        self.h_scrollbar.grid(row=1, column=0, sticky='ew')

        self.text_field.focus_set()
        self.text_field.drop_target_register(DND_FILES)
        self.text_field.dnd_bind('<<Drop>>', self.handle_drop)
        # This command might be needed in linux for drag&drop: sudo apt-get install tk-dev
        
        # Key bindings
        self.text_field.unbind_class("Text", f"<{PREFIX_KEY}-o>")
        self.text_field.unbind_class("Text", f"<{PREFIX_KEY}-t>")
        self.text_field.unbind_class("Text", f"<{PREFIX_KEY}-s>")
        self.text_field.unbind_class("Text", f"<{PREFIX_KEY}-n>")
        self.text_field.unbind_class("Text", f"<{PREFIX_KEY}-w>")
        self.text_field.unbind_class("Text", f"<{PREFIX_KEY}-plus>")
        self.text_field.unbind_class("Text", f"<{PREFIX_KEY}-equal>")
        self.text_field.unbind_class("Text", f"<{PREFIX_KEY}-minus>")
        self.text_field.bind(f'<{PREFIX_KEY}-BackSpace>', self.on_ctrl_backspace)
        self.text_field.bind(f'<{PREFIX_KEY}-Delete>', self.on_ctrl_delete)
        self.text_field.bind(f'<{PREFIX_KEY}-x>', self.on_ctrl_x)
        self.text_field.bind(f'<{PREFIX_KEY}-c>', self.on_ctrl_c)
        self.text_field.bind('<Tab>', self.on_tab)
        self.text_field.bind('<Shift-Tab>', self.on_shift_tab)
        self.text_field.bind(f'<{PREFIX_KEY}-a>', self.on_ctrl_a)
        self.text_field.bind(f'<{PREFIX_KEY}-d>', self.on_ctrl_d)
        
        # Vertical Scrollbar
        self.v_scrollbar = Scrollbar(self.text_frame, command=self.text_field.yview)
        self.v_scrollbar.grid(row=0, column=1, sticky='ns')
        self.text_frame.grid_columnconfigure(0, weight=1)
        self.text_frame.grid_rowconfigure(0, weight=1)
        self.text_field.config(yscrollcommand=self.update_v_scrollbar)
        
        # Right-click context menu
        self.context_menu = Menu(self.root, tearoff=0, font=ui_font)
        acc_key = '⌘' if SYSTEM == 'darwin' else 'Ctrl'
        distance = ' ' * 7
        
        self.context_menu.add_command(label='↩️ Undo', accelerator=f"{distance}{acc_key}+Z", command=self.handle_undo)
        self.context_menu.add_command(label='↪️ Redo', accelerator=f"{distance}{acc_key}+Y", command=self.handle_redo)
        self.context_menu.add_separator()
        self.context_menu.add_command(label='✂ Cut', accelerator=f"{distance}{acc_key}+X", command=lambda: self.text_field.event_generate('<<Cut>>'))
        self.context_menu.add_command(label='⧉ Copy', accelerator=f"{distance}{acc_key}+C", command=lambda: self.text_field.event_generate('<<Copy>>'))
        self.context_menu.add_command(label='📋 Paste', accelerator=f"{distance}{acc_key}+V", command=lambda: self.text_field.event_generate('<<Paste>>'))
        self.context_menu.add_command(label='❌ Delete', accelerator=f"{distance}Backspace/Del", command=lambda: self.text_field.delete('sel.first', 'sel.last') if self.text_field.tag_ranges('sel') else None)
        self.context_menu.add_separator()
        self.context_menu.add_command(label=f'⛶ Select All', accelerator=f"{distance}{acc_key}+A", command=lambda: self.on_ctrl_a(None))

        self.text_field.bind('<Button-3>', self.show_context_menu)
        if SYSTEM == 'darwin':
            self.text_field.bind('<Button-2>', self.show_context_menu)
        
        # Final touches
        if self.wrap: self.toggle_wrap(startup=True)
        self.apply_theme()
        self.set_title()
    
    def set_icon(self):
        if SYSTEM == 'win32':
            # Looks like Tk can find 'Assets' even if we type 'assets'
            self.root.iconbitmap(ICO_FILE+'.ico')
        else:
            from tkinter import PhotoImage
            icon = PhotoImage(file=ICO_FILE+'.png')
            self.root.wm_iconphoto(True, icon)
    
    def launch(self):
        """Launch the window with a file (if any)."""
        # Set current path to None in case of errors
        # the load_file_into_editor function will auto re-assign the current path to the opened file
        path = self.current_file_path
        self.current_file_path = None
        
        # Open file if available and hash it
        if path and path_exist(path):
            state = self.load_file_into_editor(path)    # This will auto assign current_path to opened file
            if state is not True:
                print(f"Startup file load error: {state}")
                self.root.after(256, lambda: showerror("File Opening Error", f"Error opening file: {state}", parent=self.root))
                
        elif path and not path_exist(path):
            # Immediately use a temporary path variable to avoid scheduled 'file deleted' popup when focusing on error dialog
            def ask_create_file():
                # Ask to create the missing file
                response = askyesno(
                    "Absent File",
                    f"File '{path}' not found!\nWould you like to create this file?",
                    icon='question',
                    default='yes',
                    parent=self.root,
                )
                # If YES, write an empty file
                if response is True:
                    try:
                        # raise Exception(':P')
                        dirname = os.path.dirname(path)
                        if dirname: os.makedirs(dirname, exist_ok=True)
                        with open(path, 'w', encoding=ENCODING, errors=ENCODING_ERROR_HANDLER):
                            pass
                        state = self.load_file_into_editor(path)        # This will auto assign current_path to opened file
                        if state is not True:
                            print(f"Startup file load error: {state}")
                            showerror("File Opening Error", f"Error opening file: {state}", parent=self.root)
                    except Exception as e:
                        showerror("Creation Error", f"Error while creating file '{path}': {e}", parent=self.root)
            # Schedule the dialog to appear after 256ms so it's well attached to the main window
            self.root.after(256, ask_create_file)
        
        # Start
        self.external_check_id = self.root.after(self.external_check_interval, self.check_external_modification)
        if self.is_primary:
            if not INDEPENDENT_WINDOWS: self.queue_check_id = self.root.after(self.queue_check_interval, self.check_queue)
            try: self.root.mainloop()
            except (KeyboardInterrupt, EOFError):
                print("Editor closed via terminal interruption.")
                sys.exit(0)
         
    def handle_exception(self, exc, val, tb):
        """Handle internal Tk errors without freezing the app."""
        import traceback
        # Check for manual interruption or EOF
        if issubclass(exc, (KeyboardInterrupt, EOFError)):
            print("\nUser requested termination.")
            self.root.destroy()
            sys.exit(0)
        # Show error instead of breaking the app
        err = ''.join(traceback.format_exception(exc, val, tb))
        print(f"\nInternal Error Caught:\n{err}")
        showerror("Internal Error", f"An unexpected error occurred:\n{val}", parent=self.root)

    def check_font_exists(self, font_name):
        """Check if the given font type exist in the system."""
        # Instead of loading the entire system font, let Tk ask the system for one font at a time
        actual_family = font.Font(family=font_name).actual("family")
        return actual_family.lower() == font_name.lower()
   
    # --- ACTIONS ---
    def show_shortcuts(self):
        """Show a simple dialog containing useful keyboard shortcuts."""
        # Create a separate window
        win = Toplevel(self.root)
        win.title('Keyboard Shortcuts')
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()
        win.focus_set()

        bg = '#020617' if self.dark_mode else '#ffffff'
        fg = '#e5e7eb' if self.dark_mode else '#000000'
        win.configure(bg=bg)
        
        # Prepare shortcuts text
        shortcuts_text = (
            'Ctrl-N          →  New File\n'
            'Ctrl-O          →  Open File(s)\n'
            'Ctrl-S          →  Save File\n'
            'Ctrl-Shift-S    →  Save File As\n'
            'Ctrl-T          →  Toggle Theme\n'
            'Ctrl-W          →  Toggle Word-Wrap\n'
            'Ctrl-F          →  Find/Search\n'
            'Ctrl-Z          →  Undo\n'
            'Ctrl-Y          →  Redo\n'
            'Ctrl-(+)        →  Zoom In\n'
            'Ctrl-(-)        →  Zoom Out\n'
            'Ctrl-C          →  Copy (whole line if no selection)\n'
            'Ctrl-X          →  Cut (whole line if no selection)\n'
            'Ctrl-A          →  Select All\n'
            'Ctrl-D          →  Duplicate Line(s)\n'
            'Ctrl-Backspace  →  Delete Previous Word\n'
            'Ctrl-Del        →  Delete Next Word\n'
            'Tab             →  Indent (4 Spaces)\n'
            'Shift-Tab       →  Unindent (4 spaces)\n'
        )
        if SYSTEM == 'darwin':
            shortcuts_text = shortcuts_text.replace('Ctrl-', '⌘-')
        
        # Create button & label
        label = Label(win, text=shortcuts_text, justify='left', font=(text_font[0], ui_font[1]),
                      bg=bg, fg=fg, padx=20, pady=16)
        button = Button(win, text='Close', command=win.destroy, font=ui_font,
                        relief=FLAT, bg='#1e293b' if self.dark_mode else '#e5e7eb', fg=fg, padx=12, pady=4)
        
        label.pack()
        button.pack(pady=(0, 12))
        
        # Center the window
        win.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - win.winfo_width()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - win.winfo_height()) // 2
        win.geometry(f'+{x}+{y}')

    def on_ctrl_backspace(self, event):
        """Handle CTRL-BACKSPACE."""
        # Delete previous word
        self.text_field.delete(self.text_field.index('insert -1c wordstart'), 'insert')
        return 'break'

    def on_ctrl_delete(self, event):
        """Handle CTRL-DELETE."""
        # Delete next word
        self.text_field.delete('insert', 'insert wordend')
        return 'break'
    
    def on_ctrl_a(self, event):
        """Handle CTRL-A."""
        # Select all text
        self.text_field.tag_add('sel', '1.0', 'end-1c')
        return 'break'
    
    def on_ctrl_x(self, event):
        """Handle CTRL-X."""
        if not self.text_field.tag_ranges('sel'):
            # Cut the entire line
            line_start, line_end = self.text_field.index('insert linestart'), self.text_field.index('insert lineend +1c')
            text_to_cut = self.text_field.get(line_start, line_end)
            if not text_to_cut: return
            self.root.clipboard_clear()
            self.root.clipboard_append(text_to_cut)
            self.text_field.delete(line_start, line_end)
        else:
            # Cut selection
            self.text_field.event_generate('<<Cut>>')
        return 'break'

    def on_ctrl_c(self, event):
        """Handle CTRL-C."""
        if not self.text_field.tag_ranges('sel'):
            # Copy the entire line
            self.root.clipboard_clear()
            self.root.clipboard_append(self.text_field.get('insert linestart', 'insert lineend +1c'))
        else:
            # Copy selection
            self.text_field.event_generate('<<Copy>>')
        return 'break'

    def on_ctrl_d(self, event):
        """Handle CTRL-D."""
        try:
            # If text is selected, duplicate the selection
            start, end = self.text_field.index("sel.first"), self.text_field.index("sel.last")
            content = self.text_field.get(start, end)
            self.text_field.insert(end, content)
        except:
            # Otherwise, duplicate current line
            line_start = self.text_field.index('insert linestart')
            line_end = self.text_field.index('insert lineend')
            line_content = self.text_field.get(line_start, line_end)
            self.text_field.insert(f"{line_end}", f"\n{line_content}")
        return 'break'

    def on_tab(self, event):
        """Handle pressing TAB by inserting spaces instead."""
        try:
            # Get range of selected lines
            start_line = int(self.text_field.index("sel.first").split('.')[0])
            end_line = int(self.text_field.index("sel.last").split('.')[0])
            
            for i in range(start_line, end_line + 1):
                self.text_field.insert(f"{i}.0", ' ' * self.indent_size)
        except:
            # No selection, just insert spaces at cursor
            self.text_field.insert('insert', ' ' * self.indent_size)
        return 'break'

    def on_shift_tab(self, event):
        """Handle SHIFT-TAB by unindenting lines(s)."""
        try:
            # Determine range: selected lines or just current line
            if self.text_field.tag_ranges("sel"):
                start_line = int(self.text_field.index("sel.first").split('.')[0])
                end_line = int(self.text_field.index("sel.last").split('.')[0])
            else:
                start_line = end_line = int(self.text_field.index("insert").split('.')[0])

            for i in range(start_line, end_line + 1):
                # Check for spaces at the start of the line
                line_start = f"{i}.0"
                content = self.text_field.get(line_start, f"{line_start}+{self.indent_size}c")
                if content.startswith((' ', '\t')):
                    # Remove up to indent_size leading spaces
                    num_to_del = len(content) - len(content.lstrip(' ').lstrip('\t'))
                    self.text_field.delete(line_start, f"{line_start}+{num_to_del}c")
        except Exception as e:
            print(f"Shift-Tab error: {e}")
        return 'break'
        
    def change_font(self, delta):
        """Increase/decrease text field font size."""
        global text_font
        # Determine font size jump step
        if self.text_font_size <= 12: step = 1
        elif self.text_font_size <= 24: step = 2
        elif self.text_font_size <= 48: step = 4
        else: step = 8
        new_size = self.text_font_size + delta * step
        # Restrict to min/max size
        new_size = min(96, new_size)
        new_size = max(7, new_size)
        if 7 <= new_size <= 96 and new_size != self.text_font_size:
            self.text_font_size = new_size
            text_font[-1] = self.text_font_size
            self.text_field.config(font=text_font)

    def update_v_scrollbar(self, *args):
        """Show/hide the vertical scrollbar."""
        # Show v-scrollbar for vertically long text, otherwise hide
        size = self.text_field.yview()
        if size == (0.0, 1.0):
            self.v_scrollbar.grid_remove()
        else:
            self.v_scrollbar.set(*size)
            self.v_scrollbar.grid() 

    def update_h_scrollbar(self, *args):
        """Show/hide the horizontal scrollbar."""
        # Show h-scrollbar for horizontally long text, otherwise hide
        size = self.text_field.xview()
        if size == (0.0, 1.0) or self.text_field.cget('wrap') != 'none':
            self.h_scrollbar.grid_remove()
        else:
            self.h_scrollbar.set(*size)
            self.h_scrollbar.grid()
            
    def apply_theme(self):
        """Apply dark/light theme colors to widgets."""
        # Determine the buttons to change their colors
        buttons = (
            self.new_btn, self.open_btn, self.save_btn, self.save_as_btn, self.shortcuts_btn, self.plus_btn,
            self.minus_btn, self.wrap_btn, self.search_btn, self.theme_btn,
        )
        
        if self.dark_mode:
            # Switch to dark theme
            self.root.config(bg='#0f172a')
            self.top_frame.config(bg='#243B49')
            self.text_field.config(bg=self.dark_bg, fg=self.dark_fg, insertbackground='#e5e7eb')
            self.theme_btn.config(text='☀ Light')
            self.context_menu.config(bg='#1e293b', fg='#e5e7eb', activebackground='#334155', activeforeground='#ffffff')
            for btn in buttons:
                btn.config(bg='#212121', fg='#e5e7eb', activebackground='#334155')
            self.save_btn.config(fg='#c084fc')
        else:
            # Switch to light theme
            self.root.config(bg='#f8fafc')
            self.top_frame.config(bg='#2d5ac4')
            self.text_field.config(bg=self.light_bg, fg=self.light_fg, insertbackground='black')
            self.theme_btn.config(text='🌙 Dark')
            self.context_menu.config(bg='#F5F5F5', fg='#000000', activebackground='#e5e7eb', activeforeground='#000000')
            for btn in buttons:
                btn.config(bg='#e5e7eb', fg='black', activebackground='#d1d5db')
            self.save_btn.config(fg='#581c87')

    def toggle_theme(self, event=None):
        """Toggle current theme by inverting the dark_mode state."""
        # Change theme & apply it
        self.dark_mode = not self.dark_mode
        self.apply_theme()
        return 'break'
    
    def toggle_wrap(self, startup=False, event=None):
        """Wrap/unwrap text field content."""
        if self.text_field.cget('wrap') == 'none':
            # Turn ON word-wrap
            self.text_field.config(wrap='word')
            self.wrap_btn.config(text='⇉ Unwrap')
        else:
            # Turn OFF word-wrap
            self.text_field.config(wrap='none')
            self.wrap_btn.config(text='⤶ Wrap')
        # Show h-scrollbar if word-wrap is OFF, otherwise hide it
        self.update_h_scrollbar()
        # Toggle the state only when the user click, not at startup
        if not startup: self.wrap = not self.wrap
    
    def open_search(self, event=None):
        """Open a small dialog to search for a word."""
        if self.in_search_window:
            # Forbid opening more than one search window
            return
        if self.editing_big_file:
            showerror("Search Disabled", f"Search feature is disabled for big files. I apologize because " \
                      "I'm still looking for a way to enable it without freezing the app. I hope you understand ;-;",
                      icon='question', parent=self.root)
            return
        self.in_search_window = True
            
        # Create a small new window
        search_win = Toplevel(self.root)
        search_win.title('Find')
        search_win.attributes('-topmost', True)
        search_win.transient(self.root)
        search_win.minsize(300, 55)
        
        win_w, win_h = 350, 60
        search_win.minsize(300, 55)
        
        bg = self.dark_bg if self.dark_mode else self.light_bg
        fg = self.dark_fg if self.dark_mode else self.light_fg
        search_win.configure(bg=bg, padx=10, pady=10)
        
        # Create a small label to type the search term
        entry = Entry(search_win, font=ui_font, bg=bg, fg=fg, insertbackground=fg, highlightbackground=fg, highlightthickness=1, bd=0)
        entry.pack(side=LEFT, padx=5, ipady=5, fill=X, expand=True)
        entry.focus_set()

        def on_search_close():
            # Clear highlighting & close
            self.text_field.tag_remove('found', '1.0', END)
            search_win.destroy()
            self.in_search_window = False

        search_win.protocol("WM_DELETE_WINDOW", on_search_close)
        self.text_field.tag_config('found', background='#eab308', foreground='black')

        def find_text(*_):
            # Highlight matches
            query = entry.get()
            self.text_field.tag_remove('found', '1.0', END)
            if not query: return
            match_len = IntVar()
            idx = '1.0'
            while True:
                idx = self.text_field.search(query, idx, nocase=1, stopindex=END, count=match_len)
                if not idx: break
                lastidx = f"{idx}+{match_len.get()}c"
                self.text_field.tag_add('found', idx, lastidx)
                idx = lastidx
        
        # Create a button
        find_btn = Button(search_win, text='Find All', command=find_text, font=ui_font, bg=bg, fg=fg, relief=FLAT)
        find_btn.pack(side=LEFT)
        if self.dark_mode: find_btn.config(bg='#1e293b', fg='#e5e7eb', activebackground='#334155')
        else: find_btn.config(bg='#e5e7eb', fg='black', activebackground='#d1d5db')
        entry.bind('<Return>', find_text)
        
        # Center the small window
        self.root.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - win_w) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - win_h) // 2
        search_win.geometry(f'{win_w}x{win_h}+{x}+{y}')
    
    def show_context_menu(self, event):
        """Display the right-click menu at the cursor position."""
        self.context_menu.tk_popup(event.x_root, event.y_root)
        return "break"
    
    def handle_undo(self):
        """Cancel last change."""
        try: self.text_field.edit_undo()
        except: pass  # Nothing to undo

    def handle_redo(self):
        """Repeat last change."""
        try: self.text_field.edit_redo()
        except: pass  # Nothing to redo
    
    # --- FILE HANDLING ---
    def check_queue(self):
        """Check if other instances requested opening file(s)."""
        global lock
        if not self.is_primary: return
        if INDEPENDENT_WINDOWS: return
        # if self.closed: return
        
        # Check if another instance requested opening a file
        if os.path.exists(QUEUE_FILE):    # If it exists, a queue is confirmed
            try:
                # raise Exception(':P')
                with open(QUEUE_FILE, 'r', encoding=ENCODING, errors=ENCODING_ERROR_HANDLER) as q:
                    paths = q.read().splitlines()
                os.remove(QUEUE_FILE)
                for p in paths:
                    # Open as Toplevel instead of root
                    QuickTextEditor(p, is_primary=False)
                    
            except Exception as e:
                import subprocess
                print(f'Error reading/removing queue file: {e}')
                print('Switched to slow free-instance mode, where each program instance has its own memory allocation.')
                # Release the lock and allow other instances to launch direcly as primary
                if hasattr(lock, 'close'): lock.close()
                lock = None
                save_config({**config, 'independent_windows': True})
                # Relaunch as a primary instance
                arg = ''
                if IS_COMPILED: args = [EXECUTABLE, arg]     # app.bin file.txt
                else: args = [EXECUTABLE, sys.argv[0], arg]  # python script.py file.txt
                subprocess.Popen(args)
                
        # Tell the main loop to open it after 0.5s
        if lock:
            self.queue_check_id = self.root.after(self.queue_check_interval, self.check_queue)
         
    def check_external_modification(self, event=None):
        """Check if currently opened file was edited/deleted externally."""
        # This is a draft or a big file, no need to check
        if self.editing_big_file or self.closed: return
        if not self.current_file_path:
            self.external_check_id = self.root.after(self.external_check_interval, self.check_external_modification)
            return
        
        # Check if it's been deleted.
        elif not path_exist(self.current_file_path):
            # Temporarily clear path to prevent scheduled FocusIn loops while y/n dialog is focused
            temp_path = self.current_file_path
            self.current_file_path = None
            self.last_mtime = 0
            msg = f"'{base_name(temp_path)}' has been deleted externally.\n\nSave now?"
            # Ask to re-save deleted file
            response = askyesno(
                "File Deleted",
                msg,
                icon='warning',
                default='yes',
                parent=self.root,
            )
            if response is True:
                # Re-write saved file
                self.current_file_path = temp_path
                if self.save_file():
                    self.update_mtime()
                    self.update_initial_hash()
                else:
                    self.current_file_path = None
            self.set_title()
            self.external_check_id = self.root.after(self.external_check_interval, self.check_external_modification)
            return
        
        # Check if it's been modified.
        try:
            current_mtime = os.path.getmtime(self.current_file_path)
        except:
            self.external_check_id = self.root.after(self.external_check_interval, self.check_external_modification)
            return
        
        if self.last_mtime and current_mtime > self.last_mtime:
            self.last_mtime = current_mtime
            msg = f"'{base_name(self.current_file_path)}' was modified externally."
            icon = 'question'
            
            if self.is_modified():
                msg += "\n\nWARNING: You have unsaved changes in the editor. Reloading will overwrite them!"
                icon = 'warning'
            
            # Ask to reload from file
            response = askyesno(
                "File Conflict",
                f"{msg}\n\nReload from disk?",
                icon=icon,
                default='yes',
                parent=self.root,
            )
            
            if response and self.check_file_size(self.current_file_path):
                try:
                    with open(self.current_file_path, 'r', encoding=ENCODING, errors=ENCODING_ERROR_HANDLER) as f:
                        content = f.read()
                    # Realod, save to undo stack, and scroll up
                    # Here is a bug of scrolling to bottom when clicking Ctrl-Z. I don't wanna reset the undo history
                    if not self.editing_big_file: self.initial_content_hash = hash(content)
                    self.text_field.config(autoseparators=False)
                    self.text_field.edit_separator()
                    self.text_field.delete('1.0', END)
                    self.text_field.insert('1.0', content)
                    del content
                    self.text_field.edit_separator()
                    self.text_field.config(autoseparators=True)
                    self.text_field.mark_set("insert", "1.0")
                    self.text_field.see("1.0")
                    
                except Exception as e:
                    print(f"Reload error: {e}")
                    showerror("File Reload Error", f"Could not reload file:\n{e}", parent=self.root)
            else:
                # Initial hash becomes the modified file hash
                self.update_initial_hash(from_file=True)
        self.external_check_id = self.root.after(self.external_check_interval, self.check_external_modification)
        
    def check_file_size(self, path):
        """Check if the chosen file is big or not."""
        # Check if the chosen file is big
        was_editing_big_file = bool(self.editing_big_file)
        self.editing_big_file = False
        file_size = os.path.getsize(path)
        
        # Ask before opening it
        if file_size > self.size_limit:
            size_mb = int(file_size / (1024 * 1024))
            response = askyesno(
                "Big File Warning", 
                f"The file is {size_mb} MB. Opening large files may cause the editor to freeze, and some features will be disabled.\n\nContinue anyway?",
                default='no',
                icon='warning',
                parent=self.root,
            )
            if response is True: self.editing_big_file = True
            else: self.editing_big_file = was_editing_big_file
            return response
        return True
         
    def load_file_into_editor(self, path):
        """Helper to load content into the current text field."""
        if not os.path.isfile(path):
            showerror("File Opening Error", f"Path '{path}' is not a file!", parent=self.root)
            return True
        if not self.check_file_size(path):
            return True
        try:
            with open(path, 'r', encoding=ENCODING, errors=ENCODING_ERROR_HANDLER) as f:
                content = f.read()
        except Exception as e:
            return e
        else:
            if not self.editing_big_file: self.initial_content_hash = hash(content)
            self.text_field.edit_reset()
            self.text_field.delete('1.0', END)
            self.text_field.insert('1.0', content)
            del content
            self.text_field.mark_set("insert", "1.0")
            self.text_field.see("1.0")
            self.text_field.edit_reset()
            self.text_field.config(undo=not self.editing_big_file)
            self.current_file_path = path
            self.update_mtime()
            self.set_title()
            return True
       
    def handle_drop(self, event):
        """Close current file/draft and open dragged & dropped files."""
        # TkinterDnD2 returns multiple files as a brace-enclosed string
        paths = self.root.tk.splitlist(event.data)
        if not paths: return

        # Handle the first file in the current window
        first_path = paths[0]
        if os.path.isfile(first_path):
            # Confirm dropping if the current window is modified
            if self.is_modified():
                response = askyesnocancel(
                    "Confirm",
                    f"Discard changes and open the new file?",
                    default='no',
                    parent=self.root,
                )
                if response is False: first_path = None
                elif response is None: return 'break'
        
        if first_path:
            state = self.load_file_into_editor(first_path)
            if state is not True:
                print(f"Dropped file error: {state}")
                showerror("Drop Error", f"Dropped file error: {state}", parent=self.root)
                
        # Handle additional files by opening new instances
        if len(paths) > 1:
            if INDEPENDENT_WINDOWS:
                import subprocess
                
            for extra_path in paths[1:]:
                if os.path.isfile(extra_path):
                    if INDEPENDENT_WINDOWS:
                        # Relaunch as a primary instance
                        arg = os.path.abspath(extra_path)
                        if IS_COMPILED: args = [EXECUTABLE, arg]     # app.bin file.txt
                        else: args = [EXECUTABLE, sys.argv[0], arg]  # python script.py file.txt
                        subprocess.Popen(args)
                    else:
                        # Launch as secondary instances (Toplevel windows)
                        QuickTextEditor(extra_path, is_primary=False)
        return 'break'
     
    def new_file(self, event=None):
        """Close current file/draft and create a new draft."""
        # Check for unsaved changes before
        if self.is_modified():
            response = askyesno(
                "Confirm",
                "Discard current text and start new?",
                default='no',
                parent=self.root,
            )
            if not response: return
        
        # Clear current text & open a new draft
        self.text_field.delete('1.0', END)
        self.text_field.edit_reset()
        self.text_field.config(undo=True)
        self.current_file_path = None
        self.update_mtime()
        self.update_initial_hash()
        self.set_title()
        return 'break'

    def open_file(self, event=None):
        """Open select file(s) dialog."""      
        # Open file dialog & check selected file size
        paths = askopenfilename(multiple=True, parent=self.root)
        if not paths: return 'break'
        first_path = paths[0]
        
        # Check for unsaved changes
        if self.is_modified():
            response = askyesnocancel(
                "Confirm",
                "Discard current text and open the new file(s)?",
                default='no',
                parent=self.root,
            )
            if response is False: first_path = None
            elif response is None: return 'break'
        
        if first_path:
            state = self.load_file_into_editor(first_path)
            if state is not True:
                print(f"Error opening file: {state}")
                showerror("File Opening Error", f"Error opening file: {state}", parent=self.root)
        
        # Handle additional files by opening new instances
        if len(paths) > 1:
            if INDEPENDENT_WINDOWS:
                import subprocess
                
            for extra_path in paths[1:]:
                if os.path.isfile(extra_path):
                    if INDEPENDENT_WINDOWS:
                        # Relaunch as a primary instance
                        arg = os.path.abspath(extra_path)
                        if IS_COMPILED: args = [EXECUTABLE, arg]     # app.bin file.txt
                        else: args = [EXECUTABLE, sys.argv[0], arg]  # python script.py file.txt
                        subprocess.Popen(args)
                    else:
                        # Launch as secondary instances (Toplevel windows)
                        QuickTextEditor(extra_path, is_primary=False)
        return 'break'

    def save_file(self, event=None):
        """Write current edited content to file."""
        if not self.current_file_path:
            # If this is an unsaved draft, ask for a saving path
            self.current_file_path = asksaveasfilename(
                initialfile=(self.text_field.get('1.0', 'end-1c').strip().split() or ['Text'])[0],
                defaultextension='.txt',
                filetypes=[('Plain Text', '*.txt'), ('All files', '*.*')],
                title='Save As',
                parent=self.root,
            )
        
        if self.current_file_path:
            try:
                import tempfile
                # raise Exception(':P')
                # Write to a temp file then replace temp with current file
                content = self.text_field.get('1.0', 'end-1c')
                fd, temp_path = tempfile.mkstemp(dir=APP_DIR, text=True)
                with os.fdopen(fd, 'w', encoding=ENCODING, errors=ENCODING_ERROR_HANDLER) as f:
                    f.write(content)
                os.replace(temp_path, self.current_file_path)
                self.update_mtime()
                self.update_initial_hash()
                self.set_title()
                return True
            except Exception as e:
                print(f"Error saving file: {e}")
                showerror("File Save Error", f"Could not save file:\n{e}", parent=self.root)
                return False
    
    def save_file_as(self, event=None):
        """Open a save as dialog."""
        # Temporarily clear the current file path to force a save-as dialog
        old_path = self.current_file_path
        self.current_file_path = None
        if not self.save_file():
            self.current_file_path = old_path
    
    def get_content_hash(self):
        """Quickly hash the content of the text field for comparison."""
        # Get content hash quickly
        if self.editing_big_file: return None
        return hash(self.text_field.get('1.0', 'end-1c'))

    def update_initial_hash(self, from_file=False):
        """Quickly hash the content of draft or the loaded file."""
        if from_file and path_exist(self.current_file_path) and not self.editing_big_file:
            # Update the hash of the loaded file (if any)
            with open(self.current_file_path, 'r', encoding=ENCODING, errors=ENCODING_ERROR_HANDLER) as f:
                self.initial_content_hash = hash(f.read())
        else:
            # Update the hash of the current text field (for drafts or reloaded content)
            self.initial_content_hash = self.get_content_hash()
    
    def update_mtime(self):
        """Get the time of the currently opened file for external modification detection."""
        # Get the modification time of the last loaded file
        if self.current_file_path and path_exist(self.current_file_path):
            self.last_mtime = os.path.getmtime(self.current_file_path)
        else:
            self.last_mtime = 0
    
    def set_title(self):
        """Change the window title."""
        # Change the main window title
        name = base_name(self.current_file_path) if self.current_file_path else "Untitled"
        self.root.title(f"{name} - Quick Text Editor")

    def is_modified(self):
        """Compare hashes to detect text modification."""
        # Check if the file/draft was modified or not
        if self.editing_big_file: return True
        if not self.current_file_path:
            current_text = self.text_field.get('1.0', 'end-1c')
            return bool(current_text)
        else:
            return self.get_content_hash() != self.initial_content_hash

    def on_close(self):
        """Check for unsaved work, save config and close."""
        import gc
        global config, secondary_windows
        
        # Check if there are changes
        should_prompt = False
        if self.is_modified(): should_prompt = True
        if should_prompt:
            response = askyesnocancel(
                "Unsaved Changes",
                "Save changes before exiting?",
                default='cancel',
                parent=self.root,
            )
            if response is True:
                if not self.save_file():
                    return
            elif response is None:
                return
        
        # Save states
        if self.root.state() == 'zoomed': self.maximized = True
        else:
            try: self.maximized = True if self.root.attributes('-zoomed') else False
            except: self.maximized = False
        
        self.root.state('normal')
        self.geometry = self.root.geometry()
        
        # Save final config
        final_config = {
            'geometry': self.geometry,
            'maximized': self.maximized,
            'text_font_size': self.text_font_size,
            'dark_mode': self.dark_mode,
            'wrap': self.wrap,
        }
        
        for key in config:
            if key not in final_config:
                final_config[key] = config[key]
        
        final_config = {key: final_config[key] for key in config}
        save_config(final_config)
        
        # Clear text & Unregister DND to sever the Tcl/Python reference cycle
        self.text_field.delete('1.0', END)
        self.text_field.edit_reset()
        self.text_field.drop_target_unregister()
        
        # Unbind all events and protocols to clear CallWrappers
        self.text_field.bindtags(('',))
        self.root.bindtags(('',))
        self.text_field.destroy()
        
        # Stop & cancel scheduled checks
        # if self.is_primary:
            # self.check_queue = lambda: None
            # self.check_external_modification = lambda: None
            # try: self.root.after_cancel(self.queue_check_id)        
            # except: pass
            # try: self.root.after_cancel(self.external_check_id)
            # except: pass
        
        # If this is the PRIMARY window, destory it if it's alone
        # If other windows are open, just hide the primary window
        self.closed = True
        if self.is_primary:
            if secondary_windows > 0:
                self.root.withdraw()
                # Leave the hidden window empty to free memory
                # Shortcuts & Search toplevel windows aren't an issue since they are only created when clicked
                for widget in self.root.winfo_children():
                    if not isinstance(widget, Toplevel):
                        widget.destroy()
                        del widget
            else:
                # Primary window is alone, kill & close everything
                self.closed = True
                self.root.destroy()
            
        # If a secondary window is closed, just destroy it
        # If it's the last, close mother root as well
        else:
            secondary_windows -= 1
            self.root.destroy()
            del self.root
            # If the primary is hidden AND this was the last secondary, kill the app
            if secondary_windows == 0 and mother_root.wm_state() == 'withdrawn':
                mother_root.destroy()
        
            # Blast everything, I don't care
            for attr in vars(self).copy().keys(): delattr(self, attr)
        gc.collect()

# --- MAIN ---
def manage_multi_path_request(requested_paths: list):
    """If the primary instance starts with multi passed paths as arguments, this will handle it."""
    main_path = requested_paths[0]
    if len(requested_paths) == 1:
        # Only one path was requested, launch directly
        launch_as_primary(main_path)
    else:
        # Launch the first path here and queue others
        if INDEPENDENT_WINDOWS:
            for path in requested_paths[1:]:
                import subprocess
                arg = os.path.abspath(path)
                if IS_COMPILED: args = [EXECUTABLE, arg]     # app.bin file.txt
                else: args = [EXECUTABLE, sys.argv[0], arg]  # python script.py file.txt
                subprocess.Popen(args)
        else:
            queue_paths = '\n'.join(requested_paths[1:])
            try:
                with open(QUEUE_FILE, 'a', encoding=ENCODING, errors=ENCODING_ERROR_HANDLER) as f:
                    f.write(queue_paths + '\n')
            except Exception as e:
                # I can't go further in handling permission errors
                print(f'Error opening other requested files: {e}')
        launch_as_primary(main_path)

def launch_as_primary(file_path=''):
    """Launch the full GUI as Tk root."""
    try:
        from tkinter import font
        from tkinter import (Tk, Frame, Button, Text, Label, Scrollbar, Toplevel, Entry, IntVar, Menu,
                             END, X, Y, LEFT, RIGHT, BOTH, FLAT)
        from tkinter.messagebox import askyesno, askyesnocancel, showerror
        from tkinter.filedialog import askopenfilename, asksaveasfilename
        from tkinterdnd2 import DND_FILES, TkinterDnD
        globals().update(locals())
    except Exception as e:
        print(f'Error: {e}')
        print("Perhaps you didn't install a required module? Use 'pip' to install it.")
        sys.exit(1)

    QuickTextEditor(file_path)

def main():
    """The main logic for organizing multi-instances and multi-paths requests."""
    global INDEPENDENT_WINDOWS, lock
    # Check if a file paths was passed at startup (python main.py file1.txt file2.txt etc)
    requested_paths = sys.argv[1:] if len(sys.argv) > 1 else ['']
    requested_paths = [str(Path(path)) if path else '' for path in requested_paths]
    
    INDEPENDENT_WINDOWS = config['independent_windows']
    has_write = True
    
    if not INDEPENDENT_WINDOWS:
        has_write = not path_exist(QUEUE_FILE) or os.access(QUEUE_FILE, os.W_OK)
        
    if INDEPENDENT_WINDOWS:
        # Lock is only needed to organize instances in one process, but here each instance is a process
        lock = True
    else:
        # Check if a previous primary instance is dominating
        lock = get_lock()
        
    if lock or not has_write:
        # We are Primary: Start the main window with the main path, and queue the others (if any)
        if not has_write:
            print('Queue file is inaccessible.')
            print('Switched to slow free-instance mode, where each program instance has its own memory allocation.')
        try: os.remove(QUEUE_FILE)
        except: pass
        manage_multi_path_request(requested_paths)
        
    else:
        # We are Secondary: Write to queue and exit
        try:
            # raise Exception(':P')
            queue_paths = '\n'.join(requested_paths)
            with open(QUEUE_FILE, 'a', encoding=ENCODING, errors=ENCODING_ERROR_HANDLER) as f:
                f.write(queue_paths + '\n')
            sys.exit(0)
        except Exception as e:
            print(f'Error writing queue file: {e}')
            print('Switched to slow free-instance mode, where each program instance has its own memory allocation.')
            # Launch as a primary instance for the first path, and queue others to be opened after
            manage_multi_path_request(requested_paths)

if __name__ == '__main__':
    try:
        main()
    finally:
        # Clean up before exiting
        if lock:    # Only the primary instance having the lock can clean the QUEUE file
            try: os.remove(QUEUE_FILE)
            except: pass
            if path_exist(LOCK_FILE):
                if hasattr(lock, 'close'): lock.close()
                try: os.remove(LOCK_FILE)
                except: pass
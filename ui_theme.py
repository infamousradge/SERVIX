"""Shared Classic Blue desktop controls; no additional runtime dependencies."""
import tkinter as tk
from tkinter import ttk, font
from PIL import Image, ImageDraw, ImageTk

BG = '#F3F7FB'
BLUE = '#0876D1'
TEXT = '#142033'


def center_window(window, width, height):
    width = min(width, window.winfo_screenwidth() - 40)
    height = min(height, window.winfo_screenheight() - 80)
    x = max(0, (window.winfo_screenwidth() - width) // 2)
    y = max(0, (window.winfo_screenheight() - height) // 2)
    window.geometry(f'{width}x{height}+{x}+{y}')


def configure_theme(root):
    root.option_add('*Font', '{Segoe UI} 11')
    root.option_add('*TCombobox*Listbox.font', '{Segoe UI} 11')
    for name in ('TkDefaultFont', 'TkTextFont', 'TkMenuFont'):
        font.nametofont(name).configure(family='Segoe UI', size=11)
    style = root.style
    style.configure('Treeview', font=('Segoe UI', 11), rowheight=36,
                    background='white', fieldbackground='white', borderwidth=0)
    style.configure('Treeview.Heading', font=('Segoe UI', 11, 'bold'),
                    background='#EAF1F8', foreground=TEXT, padding=9)
    style.map('Treeview', background=[('selected', '#D9ECFF')],
              foreground=[('selected', TEXT)])
    style.configure('TLabel', font=('Segoe UI', 11))
    style.configure('TButton', font=('Segoe UI', 11, 'bold'), padding=(12, 7))
    style.configure('TEntry', font=('Segoe UI', 11), padding=5)
    style.configure('TCombobox', font=('Segoe UI', 11), padding=5)
    style.configure('Capsule.TNotebook', background=BG, borderwidth=0)
    style.layout('Capsule.TNotebook.Tab', [])


class CapsuleNotebook(tk.Frame):
    """Native notebook pages with wrapping, keyboard-accessible raised pill tabs."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self.bar = tk.Frame(self, bg=BG)
        self.bar.pack(fill='x', pady=(0, 10))
        self.notebook = ttk.Notebook(self, style='Capsule.TNotebook')
        self.notebook.pack(fill='both', expand=True)
        self.buttons = []
        self._last_width = None
        self.bar.bind('<Configure>', self._layout)
        self.notebook.bind('<<NotebookTabChanged>>', self._refresh)

    def add(self, child, text='', **kwargs):
        self.notebook.add(child, text=text, **kwargs)
        label = text.strip()
        # Old numbered workflow labels are preserved in the native notebook metadata.
        if '. ' in label and label.split('. ', 1)[0].isdigit():
            label = label.split('. ', 1)[1]
        width = font.Font(family='Segoe UI', size=11, weight='bold').measure(label) + 36
        button = tk.Canvas(self.bar, width=width, height=46, bg=BG,
                           highlightthickness=0, takefocus=True, cursor='hand2')
        button.label = label
        button.page = str(child)
        button.images = {}
        for active in (False, True):
            image = Image.new('RGBA', (width * 2, 92))
            draw = ImageDraw.Draw(image)
            draw.rounded_rectangle((2, 8, width * 2 - 2, 90), radius=40, fill='#CDD9E7')
            draw.rounded_rectangle((2, 2, width * 2 - 2, 82), radius=40,
                                   fill=BLUE if active else '#FFFFFF',
                                   outline='#0564B5' if active else '#DDE6F0', width=2)
            draw.line((42, 6, width * 2 - 42, 6), fill='#54A8EC' if active else '#FFFFFF', width=2)
            button.images[active] = ImageTk.PhotoImage(image.resize((width, 46), Image.Resampling.LANCZOS), master=self)
        button.bind('<Button-1>', lambda e, page=child: self.select(page))
        button.bind('<Return>', lambda e, page=child: self.select(page))
        button.bind('<space>', lambda e, page=child: self.select(page))
        button.bind('<Right>', lambda e, b=button: self._step(b, 1))
        button.bind('<Left>', lambda e, b=button: self._step(b, -1))
        button.bind('<FocusIn>', self._refresh)
        button.bind('<FocusOut>', self._refresh)
        self.buttons.append(button)
        self._layout()
        self._refresh()

    def select(self, tab=None):
        result = self.notebook.select(tab) if tab is not None else self.notebook.select()
        self._refresh()
        return result

    def _step(self, button, delta):
        target = self.buttons[(self.buttons.index(button) + delta) % len(self.buttons)]
        self.select(target.page)
        target.focus_set()
        return 'break'

    def _layout(self, event=None):
        width = event.width if event else self.bar.winfo_width()
        if event and width == self._last_width:
            return
        self._last_width = width
        row = used = 0
        for button in self.buttons:
            size = int(button.cget('width')) + 8
            if used and used + size > max(1, width):
                row += 1
                used = 0
            button.place(x=used, y=row * 50)
            used += size
        self.bar.configure(height=(row + 1) * 50 if self.buttons else 0)

    def _refresh(self, event=None):
        selected = self.notebook.select()
        for button in self.buttons:
            active = button.page == selected
            button.delete('all')
            button.create_image(0, 0, anchor='nw', image=button.images[active])
            button.create_text(int(button.cget('width')) // 2, 21,
                               text=button.label, fill='white' if active else TEXT,
                               font=('Segoe UI', 11, 'bold'))
            if self.focus_get() == button:
                button.create_rectangle(18, 8, int(button.cget('width')) - 18, 34,
                                        outline='white' if active else BLUE, dash=(2, 2))

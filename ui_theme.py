"""Shared Classic Blue desktop controls; no additional runtime dependencies."""
import tkinter as tk
from tkinter import ttk, font
from PIL import Image, ImageDraw, ImageTk

BG = '#F3F7FB'
BLUE = '#0876D1'
TEXT = '#142033'
NAVY = '#071A3D'
MUTED = '#6E7B8D'
BORDER = '#DDE6F0'


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
    # The Windows default ttk theme adds raised gray borders to every table
    # cell and control. Clam keeps these surfaces flat and visually consistent.
    try:
        style.theme_use('clam')
    except tk.TclError:
        pass
    style.configure('Treeview', font=('Segoe UI', 11), rowheight=42,
                    background='white', fieldbackground='white', borderwidth=0,
                    relief='flat')
    style.configure('Treeview.Heading', font=('Segoe UI', 11, 'bold'),
                    background='#EEF3F8', foreground='#3B4D63', padding=(11, 10),
                    borderwidth=0, relief='flat')
    style.map('Treeview', background=[('selected', '#D9ECFF')],
              foreground=[('selected', TEXT)])
    style.configure('Search.Treeview', font=('Segoe UI', 10), rowheight=36,
                    background='white', fieldbackground='white', borderwidth=0,
                    relief='flat')
    style.configure('Search.Treeview.Heading', font=('Segoe UI', 10, 'bold'),
                    background='#EAF3FC', foreground='#294B6B', padding=(12, 10),
                    borderwidth=0, relief='flat')
    style.map('Search.Treeview', background=[('selected', '#D9ECFF')],
              foreground=[('selected', NAVY)])
    style.configure('TLabel', font=('Segoe UI', 11))
    style.configure('TButton', font=('Segoe UI', 11, 'bold'), padding=(14, 9),
                    background='#EAF3FC', foreground=NAVY, borderwidth=0)
    style.map('TButton', background=[('pressed', '#D4E8FB'), ('active', '#DDEEFF')])
    style.configure('TEntry', font=('Segoe UI', 11), padding=(10, 8),
                    fieldbackground='white', borderwidth=1, relief='flat')
    style.configure('TCombobox', font=('Segoe UI', 11), padding=(11, 8),
                    fieldbackground='white', background='#EAF3FC', foreground=TEXT,
                    bordercolor='#D7E3F0', lightcolor='#D7E3F0', darkcolor='#D7E3F0',
                    arrowsize=15, arrowcolor=BLUE)
    style.map('TCombobox', fieldbackground=[('readonly', 'white'), ('focus', 'white')],
              bordercolor=[('focus', BLUE), ('readonly', '#D7E3F0')],
              arrowcolor=[('active', '#0564B5'), ('readonly', BLUE)],
              selectbackground=[('readonly', '#EAF3FC')],
              selectforeground=[('readonly', TEXT)])
    style.configure('Capsule.TNotebook', background=BG, borderwidth=0)
    style.layout('Capsule.TNotebook.Tab', [])


class CapsuleNotebook(tk.Frame):
    """Native notebook pages with wrapping, keyboard-accessible raised pill tabs."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self.bar = tk.Frame(self, bg=BG)
        self.bar.pack(fill='x', pady=(2, 12))
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
        width = font.Font(family='Segoe UI', size=11, weight='bold').measure(label) + 44
        button = tk.Canvas(self.bar, width=width, height=50, bg=BG,
                           highlightthickness=0, takefocus=True, cursor='hand2')
        button.label = label
        button.page = str(child)
        button.images = {}
        for active in (False, True):
            image = Image.new('RGBA', (width * 2, 100))
            draw = ImageDraw.Draw(image)
            draw.rounded_rectangle((2, 10, width * 2 - 2, 98), radius=44, fill='#CBD8E6')
            if active:
                for y in range(4, 90):
                    t = (y - 4) / 86
                    top, bottom = (21, 139, 226), (5, 103, 190)
                    color = tuple(round(a + (b - a) * t) for a, b in zip(top, bottom))
                    draw.line((3, y, width * 2 - 3, y), fill=color)
                draw.rounded_rectangle((3, 4, width * 2 - 3, 90), radius=44,
                                       outline='#0564B5', width=2)
                draw.line((42, 7, width * 2 - 42, 7), fill='#6DBCF5', width=2)
            else:
                draw.rounded_rectangle((3, 4, width * 2 - 3, 90), radius=44,
                                       fill='#FFFFFF', outline='#D7E3F0', width=2)
                draw.line((42, 7, width * 2 - 42, 7), fill='#FFFFFF', width=2)
            button.images[active] = ImageTk.PhotoImage(image.resize((width, 50), Image.Resampling.LANCZOS), master=self)
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
            button.place(x=used, y=row * 54)
            used += size
        self.bar.configure(height=(row + 1) * 54 if self.buttons else 0)

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
                left, top, right, bottom, radius = 7, 2, int(button.cget('width')) - 7, 48, 23
                color = '#FFFFFF' if active else BLUE
                button.create_line(left + radius, top, right - radius, top,
                                   fill=color, dash=(2, 2))
                button.create_line(left + radius, bottom, right - radius, bottom,
                                   fill=color, dash=(2, 2))
                for x1, y1, x2, y2, start in ((left, top, left + 2*radius, top + 2*radius, 90),
                                              (right - 2*radius, top, right, top + 2*radius, 0),
                                              (right - 2*radius, bottom - 2*radius, right, bottom, 270),
                                              (left, bottom - 2*radius, left + 2*radius, bottom, 180)):
                    button.create_arc(x1, y1, x2, y2, start=start, extent=90,
                                      style='arc', outline=color, dash=(2, 2))


class SidebarPill(tk.Canvas):
    """Rounded, keyboard-friendly navigation control for the fixed SERVIX rail."""
    def __init__(self, parent, label, icon, command, **kwargs):
        super().__init__(parent, height=52, bg='#063765', highlightthickness=0,
                         takefocus=True, cursor='hand2', **kwargs)
        self.label, self.icon, self.command = label, icon, command
        self.active = False
        self.hover = False
        self._surface_image = None
        self._icon_image = None
        self.bind('<Configure>', self._draw)
        self.bind('<Button-1>', self._activate)
        self.bind('<Return>', self._activate)
        self.bind('<space>', self._activate)
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<FocusIn>', self._draw)
        self.bind('<FocusOut>', self._draw)
        self._draw()

    def set_active(self, active):
        self.active = bool(active)
        self._draw()

    def _activate(self, _event=None):
        self.command()
        return 'break'

    def _on_enter(self, _event=None):
        self.hover = True
        self._draw()

    def _on_leave(self, _event=None):
        self.hover = False
        self._draw()

    def _draw(self, _event=None):
        self.delete('all')
        # Tk can call this before pack assigns the sidebar's real width. Keep
        # the temporary first paint wide enough for valid rounded rectangles;
        # the following Configure event redraws it at the actual width.
        width = max(64, self.winfo_width())
        scale = 3
        surface = Image.new('RGBA', (width * scale, 52 * scale), (0, 0, 0, 0))
        painter = ImageDraw.Draw(surface)
        def rounded(top, bottom, color):
            painter.rounded_rectangle((2*scale, top*scale, (width-2)*scale, bottom*scale),
                                      radius=22*scale, fill=color)
        if self.active:
            # Supersampling removes the stair-stepped edges visible on native Tk ovals.
            rounded(6, 52, '#04294E')
            rounded(3, 49, '#0876D1')
            painter.line((24*scale, 4*scale, (width-24)*scale, 4*scale),
                         fill='#3B9CEF', width=scale)
        elif self.hover:
            rounded(3, 49, '#104879')
        badge_color = {
            'Dashboard': '#149CF3', 'Service Calls': '#10AFA5',
            'Clients': '#8068D9', 'Equipment': '#2587D7',
            'Warranty & AMC': '#D99A27', 'Engineers': '#35A96D',
            'Parts / Inventory': '#E07842', 'Commercial & Payments': '#268FAF',
            'Documents': '#A75CC1', 'Reports & Analytics': '#347BD0',
            'Data Export / Import': '#159B86', 'Administration': '#7085A2',
        }.get(self.label, '#2587D7')
        painter.ellipse((12*scale, 11*scale, 42*scale, 41*scale), fill=badge_color)
        self._surface_image = ImageTk.PhotoImage(
            surface.resize((width, 52), Image.Resampling.LANCZOS), master=self)
        self.create_image(0, 0, anchor='nw', image=self._surface_image)
        self._icon_image = self._draw_icon()
        self.create_image(27, 26, image=self._icon_image)
        self.create_text(54, 26, text=self.label, anchor='w', fill='white' if self.active else '#DDE9F7',
                         font=('Segoe UI', 11, 'bold' if self.active else 'normal'))
        if self.focus_get() == self:
            self.create_rectangle(7, 5, width - 7, 48,
                                  outline='#B9E2FF', dash=(2, 2))

    def _pill(self, left, top, right, bottom, radius, color):
        self.create_rectangle(left + radius, top, right - radius, bottom, fill=color, outline='')
        self.create_oval(left, top, left + radius * 2, bottom, fill=color, outline='')
        self.create_oval(right - radius * 2, top, right, bottom, fill=color, outline='')

    def _draw_icon(self):
        """Render a consistent, antialiased outline icon for the sidebar badge."""
        icon = {
            'Dashboard': 'home', 'Service Calls': 'wrench', 'Clients': 'users',
            'Equipment': 'box', 'Warranty & AMC': 'shield', 'Engineers': 'user',
            'Parts / Inventory': 'layers', 'Commercial & Payments': 'coin',
            'Documents': 'file', 'Reports & Analytics': 'chart',
            'Data Export / Import': 'transfer', 'Administration': 'settings',
        }.get(self.label, 'dot')
        scale, x, y = 4, 12, 12
        color, stroke = '#FFFFFF', 7
        image = Image.new('RGBA', (24 * scale, 24 * scale), (0, 0, 0, 0))
        painter = ImageDraw.Draw(image)
        def xy(points):
            return [(int(round(a * scale)), int(round(b * scale))) for a, b in points]
        def line(points):
            painter.line(xy(points), fill=color, width=stroke, joint='curve')
        def ellipse(box, fill=None):
            coords = tuple(int(round(v * scale)) for v in box)
            painter.ellipse(coords, fill=fill, outline=None if fill else color,
                            width=stroke)
        if icon == 'home':
            line(((x-8,y-1),(x,y-8),(x+8,y-1))); line(((x-6,y-2),(x-6,y+7),(x+6,y+7),(x+6,y-2)))
            line(((x-2,y+7),(x-2,y+2),(x+2,y+2),(x+2,y+7)))
        elif icon == 'wrench':
            line(((x-5,y+6),(x+4,y-3))); ellipse((x-7,y+4,x-3,y+8))
            line(((x+2,y-5),(x+5,y-7),(x+8,y-4),(x+6,y-1),(x+3,y-2)))
        elif icon in ('users','user'):
            ellipse((x-3,y-8,x+3,y-2))
            line(((x-7,y+7),(x-7,y+4),(x-5,y+1),(x-2,y),(x+2,y),(x+5,y+1),(x+7,y+4),(x+7,y+7)))
            if icon == 'users':
                ellipse((x-10,y-6,x-6,y-2)); ellipse((x+6,y-6,x+10,y-2))
                line(((x-10,y+6),(x-10,y+4),(x-8,y+2))); line(((x+10,y+6),(x+10,y+4),(x+8,y+2)))
        elif icon == 'box':
            line(((x-8,y-5),(x,y-9),(x+8,y-5),(x+8,y+5),(x,y+9),(x-8,y+5),(x-8,y-5)))
            line(((x-8,y-5),(x,y-1),(x+8,y-5))); line(((x,y-1),(x,y+9)))
        elif icon == 'shield':
            line(((x,y-9),(x+7,y-6),(x+6,y+1),(x+3,y+6),(x,y+9),(x-3,y+6),(x-6,y+1),(x-7,y-6),(x,y-9)))
            line(((x-3,y),(x-1,y+2),(x+4,y-3)))
        elif icon == 'layers':
            line(((x,y-8),(x+8,y-4),(x,y),(x-8,y-4),(x,y-8))); line(((x-8,y),(x,y+4),(x+8,y)))
            line(((x-8,y+4),(x,y+8),(x+8,y+4)))
        elif icon == 'coin':
            ellipse((x-8,y-8,x+8,y+8))
            line(((x+3,y-4),(x-2,y-4),(x-4,y-2),(x+3,y+1),(x+2,y+4),(x-3,y+4))); line(((x,y-6),(x,y+6)))
        elif icon == 'file':
            line(((x-6,y-8),(x+2,y-8),(x+7,y-3),(x+7,y+8),(x-6,y+8),(x-6,y-8)))
            line(((x+2,y-8),(x+2,y-3),(x+7,y-3))); line(((x-3,y+1),(x+4,y+1))); line(((x-3,y+4),(x+4,y+4)))
        elif icon == 'chart':
            line(((x-8,y+7),(x-8,y-7))); line(((x-8,y+7),(x+8,y+7))); line(((x-5,y+3),(x-1,y-1),(x+2,y+2),(x+7,y-5)))
        elif icon == 'transfer':
            line(((x-7,y-4),(x+7,y-4),(x+4,y-7))); line(((x+7,y-4),(x+4,y-1)))
            line(((x+7,y+4),(x-7,y+4),(x-4,y+1))); line(((x-7,y+4),(x-4,y+7)))
        elif icon == 'settings':
            ellipse((x-7,y-7,x+7,y+7)); ellipse((x-2,y-2,x+2,y+2))
            for dx,dy in ((0,-9),(0,9),(-9,0),(9,0),(-6,-6),(6,-6),(-6,6),(6,6)):
                line(((x+dx*.78,y+dy*.78),(x+dx,y+dy)))
        else:
            ellipse((x-3,y-3,x+3,y+3), fill=color)
        return ImageTk.PhotoImage(image.resize((24, 24), Image.Resampling.LANCZOS), master=self)


class PremiumCombobox(tk.Canvas):
    """Rounded selector with a floating, keyboard-operable option list.

    The app currently uses read-only comboboxes throughout. This keeps their small
    get/set/bind surface while allowing the field and popup to follow the pill UI.
    """
    def __init__(self, parent, values=(), width=20, state='readonly', textvariable=None, **kwargs):
        self.values = list(values)
        self.char_width = width
        self.state = state
        self.variable = textvariable or tk.StringVar(master=parent)
        self.popup = None
        self._surface_image = None
        self._trace = self.variable.trace_add('write', self._draw)
        # Match the host surface. A BG-colored canvas on white filter cards was
        # the pale rectangular patch visible around each capsule in the screenshots.
        try:
            parent_bg = parent.cget('bg')
        except (tk.TclError, AttributeError):
            try:
                parent_bg = parent.cget('background')
            except (tk.TclError, AttributeError):
                parent_bg = BG
        super().__init__(parent, height=44, width=max(160, width * 7 + 60),
                         bg=parent_bg or BG, highlightthickness=0, takefocus=True,
                         cursor='hand2', **kwargs)
        self.bind('<Configure>', self._draw)
        self.bind('<Button-1>', self._toggle)
        self.bind('<Return>', self._toggle)
        self.bind('<space>', self._toggle)
        self.bind('<Down>', self._open)
        self.bind('<FocusIn>', self._draw)
        self.bind('<FocusOut>', self._draw)
        self.bind('<Destroy>', self._on_destroy, add='+')
        self._draw()

    def get(self):
        return self.variable.get()

    def set(self, value):
        self.variable.set(value)

    def current(self, index=None):
        if index is None:
            try:
                return self.values.index(self.get())
            except ValueError:
                return -1
        if 0 <= index < len(self.values):
            self.set(self.values[index])
        return None

    def configure(self, cnf=None, **kwargs):
        if isinstance(cnf, dict):
            kwargs = {**cnf, **kwargs}
            cnf = None
        if 'values' in kwargs:
            self.values = list(kwargs.pop('values') or ())
        if 'state' in kwargs:
            self.state = kwargs.pop('state')
        if 'width' in kwargs:
            self.char_width = kwargs.pop('width')
        result = super().configure(cnf, **kwargs)
        self._draw()
        return result

    config = configure

    def __getitem__(self, key):
        if key == 'values':
            return tuple(self.values)
        if key == 'state':
            return self.state
        if key == 'width':
            return self.char_width
        return super().__getitem__(key)

    def __setitem__(self, key, value):
        if key in ('values', 'state', 'width'):
            self.configure(**{key: value})
        else:
            super().__setitem__(key, value)

    def _draw(self, *_):
        if not self.winfo_exists():
            return
        self.delete('all')
        width = max(90, self.winfo_width())
        height = max(38, self.winfo_height())
        scale=3
        surface=Image.new('RGBA',(width*scale,height*scale),(0,0,0,0))
        painter=ImageDraw.Draw(surface)
        focused=self.focus_get()==self
        edge='#79B9EE' if focused else '#D5E1ED'
        painter.rounded_rectangle((2*scale,4*scale,(width-3)*scale,(height-2)*scale),
                                  radius=(height//2)*scale,fill='#E8EEF5')
        painter.rounded_rectangle((2*scale,2*scale,(width-3)*scale,(height-5)*scale),
                                  radius=(height//2)*scale,fill='white',outline=edge,
                                  width=(2 if focused else 1)*scale)
        arrow_x=width-25
        painter.rounded_rectangle(((arrow_x-14)*scale,(height//2-12)*scale,
                                   (arrow_x+11)*scale,(height//2+12)*scale),
                                  radius=8*scale,fill='#EEF5FC')
        self._surface_image=ImageTk.PhotoImage(
            surface.resize((width,height),Image.Resampling.LANCZOS),master=self)
        self.create_image(0,0,anchor='nw',image=self._surface_image)
        self.create_line(arrow_x-4,height//2-1,arrow_x,height//2+3,
                         arrow_x+4,height//2-1,fill=BLUE,width=2,capstyle='round',joinstyle='round')
        selected = self.get()
        label = selected if selected else 'Select an option'
        font_obj = font.Font(family='Segoe UI', size=11)
        max_width = max(30, arrow_x - 25)
        while label and font_obj.measure(label) > max_width:
            label = label[:-2] + '…' if len(label) > 2 else '…'
        self.create_text(18, height // 2, text=label, anchor='w',
                         fill=TEXT if selected else MUTED, font=('Segoe UI', 11))

    def _pill(self, left, top, right, bottom, radius, fill, outline=None):
        if right <= left or bottom <= top:
            return
        color = fill or ''
        self.create_rectangle(left + radius, top, right - radius, bottom,
                              fill=color, outline=outline or '', width=1 if outline else 0)
        self.create_oval(left, top, left + radius * 2, bottom,
                         fill=color, outline=outline or '', width=1 if outline else 0)
        self.create_oval(right - radius * 2, top, right, bottom,
                         fill=color, outline=outline or '', width=1 if outline else 0)

    def _open(self, _event=None):
        if self.state != 'disabled' and not self.popup and self.values:
            self._show_popup()
        return 'break'

    def _toggle(self, _event=None):
        if self.state == 'disabled':
            return 'break'
        if self.popup:
            self._close_popup()
        elif self.values:
            self._show_popup()
        return 'break'

    def _show_popup(self):
        self.focus_set()
        self.popup = tk.Toplevel(self)
        popup = self.popup
        popup.withdraw()
        popup.overrideredirect(True)
        popup.transient(self.winfo_toplevel())
        popup.configure(bg='#E8EEF5')
        visible = min(8, max(1, len(self.values)))
        row_height=36; font_obj=font.Font(family='Segoe UI',size=10)
        longest=max((font_obj.measure(str(value)) for value in self.values),default=150)
        desired_width=max(self.winfo_width(),min(480,max(190,longest+48)))
        desired_height=visible*row_height+18
        shell=tk.Frame(popup,bg='#E8EEF5'); shell.pack(fill='both',expand=True,padx=1,pady=1)
        self._popup_canvas=tk.Canvas(shell,width=desired_width-2,height=desired_height-2,
                                     bg='white',highlightthickness=0,takefocus=True)
        self._popup_canvas.pack(side='left',fill='both',expand=True)
        # Supersampled rounded popup surface with a soft lift shadow.
        scale=3; surface=Image.new('RGBA',(desired_width*scale,desired_height*scale),(0,0,0,0)); painter=ImageDraw.Draw(surface)
        painter.rounded_rectangle((3*scale,5*scale,(desired_width-3)*scale,(desired_height-2)*scale),radius=13*scale,fill='#D3DFEB')
        painter.rounded_rectangle((2*scale,2*scale,(desired_width-4)*scale,(desired_height-6)*scale),radius=13*scale,fill='white',outline='#D8E4F0',width=scale)
        self._popup_surface=ImageTk.PhotoImage(surface.resize((desired_width,desired_height),Image.Resampling.LANCZOS),master=self)
        self._popup_canvas.create_image(0,0,anchor='nw',image=self._popup_surface,tags=('surface',))
        self._popup_canvas.configure(scrollregion=(0,0,desired_width-12,len(self.values)*row_height+18))
        self._popup_index=self.values.index(self.get()) if self.get() in self.values else 0
        self._popup_draw_options()
        if len(self.values)>visible:
            scrollbar=ttk.Scrollbar(shell,orient='vertical',command=self._popup_canvas.yview)
            scrollbar.pack(side='right',fill='y',padx=(1,3),pady=6)
            self._popup_canvas.configure(yscrollcommand=scrollbar.set)
        self._popup_canvas.bind('<Button-1>',self._popup_click)
        self._popup_canvas.bind('<Motion>',self._popup_motion)
        self._popup_canvas.bind('<Leave>',lambda _e:self._popup_draw_options())
        self._popup_canvas.bind('<MouseWheel>',self._popup_wheel)
        self._popup_canvas.bind('<Button-4>',lambda _e:self._popup_scroll(-1))
        self._popup_canvas.bind('<Button-5>',lambda _e:self._popup_scroll(1))
        self._popup_canvas.bind('<Up>',lambda _e:self._popup_move(-1))
        self._popup_canvas.bind('<Down>',lambda _e:self._popup_move(1))
        self._popup_canvas.bind('<Return>',lambda _e:self._choose())
        self._popup_canvas.bind('<Escape>',lambda _e:self._close_popup())
        self._popup_canvas.bind('<FocusOut>',self._popup_focus_out)
        popup.update_idletasks()
        x = min(self.winfo_rootx(), self.winfo_screenwidth() - desired_width - 8)
        y = self.winfo_rooty() + self.winfo_height() - 2
        screen_bottom = self.winfo_screenheight()
        if y + desired_height > screen_bottom - 12:
            y = max(0, self.winfo_rooty() - desired_height + 2)
        popup.geometry(f'{desired_width}x{desired_height}+{x}+{y}')
        popup.deiconify()
        popup.lift()
        self._popup_canvas.focus_set()
        self._popup_canvas.yview_moveto(max(0,self._popup_index-visible+1)/max(1,len(self.values)))
        self._draw()

    def _popup_draw_options(self):
        if not self.popup or not getattr(self,'_popup_canvas',None):return
        canvas=self._popup_canvas; canvas.delete('option')
        width=max(100,canvas.winfo_width()-18); hover=getattr(self,'_popup_hover',-1)
        for index,value in enumerate(self.values):
            top=9+index*36; bottom=top+31
            if index==self._popup_index or index==hover:
                fill='#EAF4FE' if index==self._popup_index else '#F4F8FC'
                canvas.create_rectangle(22,top,width-14,bottom,fill=fill,outline='',tags=('option',))
                canvas.create_oval(7,top,37,bottom,fill=fill,outline='',tags=('option',))
                canvas.create_oval(width-29,top,width+1,bottom,fill=fill,outline='',tags=('option',))
            text=str(value); max_width=width-34; f=font.Font(family='Segoe UI',size=10)
            while text and f.measure(text)>max_width:text=text[:-2]+'…' if len(text)>2 else '…'
            canvas.create_text(20,top+15,text=text,anchor='w',fill=NAVY if index==self._popup_index else TEXT,
                              font=('Segoe UI',10,'bold' if index==self._popup_index else 'normal'),tags=('option',f'index:{index}'))

    def _popup_click(self,event):
        index=(int(self._popup_canvas.canvasy(event.y))-9)//36
        if 0<=index<len(self.values):self._popup_index=index;self._choose()
    def _popup_motion(self,event):
        index=(int(self._popup_canvas.canvasy(event.y))-9)//36
        self._popup_hover=index if 0<=index<len(self.values) else -1;self._popup_draw_options()
    def _popup_move(self,step):
        self._popup_index=max(0,min(len(self.values)-1,self._popup_index+step));self._popup_draw_options()
        self._popup_canvas.yview_moveto(max(0,self._popup_index-5)/max(1,len(self.values)));return 'break'
    def _popup_scroll(self,step):
        self._popup_canvas.yview_scroll(step,'units');return 'break'
    def _popup_wheel(self,event):
        self._popup_scroll(-1 if event.delta>0 else 1);return 'break'
    def _choose(self):
        if self.popup and self.values:
            self.variable.set(self.values[self._popup_index])
            self._close_popup()
            self.event_generate('<<ComboboxSelected>>')
        return 'break'

    def _popup_focus_out(self, _event=None):
        if self.popup:
            try:
                self.after_idle(self._close_if_focus_left)
            except tk.TclError:
                self._close_popup()

    def _close_if_focus_left(self):
        if not self.popup:
            return
        try:
            focus = self.popup.focus_get()
            if not focus or not str(focus).startswith(str(self.popup)):
                self._close_popup(restore_focus=False)
        except tk.TclError:
            self._close_popup()

    def _close_popup(self, restore_focus=True):
        popup, self.popup = self.popup, None
        if popup:
            try:
                popup.destroy()
            except tk.TclError:
                pass
        self._popup_listbox = None
        if restore_focus:
            try:
                self.focus_set()
            except tk.TclError:
                pass
        if self.winfo_exists():
            self._draw()

    def _on_destroy(self, event):
        if event.widget is self:
            self._close_popup(restore_focus=False)
            try:
                self.variable.trace_remove('write', self._trace)
            except (tk.TclError, AttributeError):
                pass

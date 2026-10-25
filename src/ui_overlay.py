import tkinter as tk
import tkinter.font as tkfont


class ResultOverlay:
    def __init__(self, master, text, x, y, width, height):
        self.master = master
        self.text = text
        self.top = tk.Toplevel(self.master)

        self.top.overrideredirect(True)
        self.top.attributes('-topmost', True)

        # Start hidden to avoid flickering during font calculation
        self.top.attributes('-alpha', 0.0)

        qt_x = int(x)
        qt_y = int(y)
        qt_w = int(max(width, 200))
        qt_h = int(max(height, 100))

        self.top.geometry(f"{qt_w}x{qt_h}+{qt_x}+{qt_y}")
        self.top.configure(bg='#202020')

        # Context menu (right-click)
        self.context_menu = tk.Menu(self.top, tearoff=0,
                                    bg='#303030', fg='white',
                                    activebackground='#505050', activeforeground='white')
        self.context_menu.add_command(label="Kopyala", command=self._copy_to_clipboard)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Kapat", command=self.close)

        # Left click to close
        self.top.bind("<Button-1>", lambda e: self.close())
        # Right click to open context menu
        self.top.bind("<Button-3>", self._show_context_menu)
        self.top.bind("<Escape>", lambda e: self.close())

        wrap_width = qt_w - 20
        self.label = tk.Label(
            self.top,
            text=text,
            fg='white',
            bg='#202020',
            justify="left",
            wraplength=wrap_width
        )
        self.label.pack(expand=True, fill='both', padx=10, pady=10)
        self.label.bind("<Button-1>", lambda e: self.close())
        self.label.bind("<Button-3>", self._show_context_menu)

        self.fit_font_size(text, qt_h, wrap_width)

        # Show window
        self.top.attributes('-alpha', 0.9)
        self.top.focus_force()

    def fit_font_size(self, text, window_height, wrap_width):
        max_size = 20
        min_size = 8
        current_size = max_size
        available_height = window_height - 20

        while current_size >= min_size:
            font = tkfont.Font(family="Arial", size=current_size)
            self.label.configure(font=font)
            self.label.update_idletasks()
            needed_height = self.label.winfo_reqheight()

            if needed_height <= available_height:
                return
            current_size -= 1

    def _show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _copy_to_clipboard(self):
        try:
            self.master.clipboard_clear()
            self.master.clipboard_append(self.text)
            self.master.update()  # Forces clipboard to persist after window closes
            print("Metin panoya kopyalandi.")
        except Exception as e:
            print(f"Kopyalama hatasi: {e}")

    def close(self):
        if self.top:
            self.top.destroy()
            self.top = None

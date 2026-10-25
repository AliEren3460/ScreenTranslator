import tkinter as tk
from PIL import ImageGrab


class Sniper:
    def __init__(self, master):
        self.master = master
        self.top = None
        self.start_x = None
        self.start_y = None
        self.current_rect = None
        self.screenshot = None
        self.selection_coords = None
        self.callback = None

    def start_selection(self, callback):
        """
        Opens a full screen overlay to select a region.
        callback: function(image, coords); called with (None, None) on cancel.
        """
        self.callback = callback
        self.screenshot = None
        self.selection_coords = None

        self.top = tk.Toplevel(self.master)

        self.top.attributes('-fullscreen', True)
        self.top.attributes('-alpha', 0.3)
        self.top.configure(background='black')
        self.top.attributes('-topmost', True)

        self.canvas = tk.Canvas(self.top, cursor="cross", bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        # Right click cancels too: Escape needs keyboard focus, which Windows
        # does not always give to a window opened from a global hotkey
        self.canvas.bind("<Button-3>", lambda e: self.cancel())
        # Escape binding on toplevel so it always receives keyboard events
        self.top.bind("<Escape>", lambda e: self.cancel())

        self.top.focus_force()

    def cancel(self):
        self.close()
        if self.callback:
            callback, self.callback = self.callback, None
            callback(None, None)

    def close(self):
        if self.top:
            self.top.destroy()
            self.top = None

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.current_rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline='red', width=2
        )

    def on_move_press(self, event):
        cur_x, cur_y = (event.x, event.y)
        self.canvas.coords(self.current_rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        if self.start_x is None or self.start_y is None:
            return

        end_x, end_y = (event.x, event.y)

        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)

        if (x2 - x1) > 10 and (y2 - y1) > 10:
            self.selection_coords = (x1, y1, x2, y2)
            self.top.withdraw()
            self.master.after(200, self._capture_and_callback, x1, y1, x2, y2)
        else:
            self.cancel()

    def _capture_and_callback(self, x1, y1, x2, y2):
        try:
            self.screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        except Exception as e:
            print(f"Ekran yakalama hatasi: {e}")
            self.cancel()
            return
        self.close()
        if self.callback:
            callback, self.callback = self.callback, None
            callback(self.screenshot, (x1, y1, x2, y2))


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    def cb(img, coords):
        print(f"Captured: {coords}")
        if img:
            img.show()
        root.destroy()
    s = Sniper(root)
    s.start_selection(cb)
    root.mainloop()

import tkinter as tk
from PIL import ImageGrab
import ctypes

import tkinter as tk
from PIL import ImageGrab
import ctypes

class Sniper:
    def __init__(self, master):
        self.master = master
        self.top = None
        self.start_x = None
        self.start_y = None
        self.current_rect = None
        self.screenshot = None
        self.selection_coords = None
        self.callback = None # Function to call with result

    def start_selection(self, callback):
        """
        Opens a full screen overlay to select a region.
        callback: function(image, coords)
        """
        self.callback = callback
        self.screenshot = None
        self.selection_coords = None

        self.top = tk.Toplevel(self.master)
        
        # Handle DPI awareness to get correct coordinates
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        self.top.attributes('-fullscreen', True)
        self.top.attributes('-alpha', 0.3)
        self.top.configure(background='black')
        self.top.attributes('-topmost', True)

        self.canvas = tk.Canvas(self.top, cursor="cross", bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.canvas.bind("<Escape>", lambda e: self.close())

        self.top.focus_force()
        # We do NOT run mainloop here because master is already running it

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
        end_x, end_y = (event.x, event.y)
        
        # Ensure coordinates are top-left to bottom-right
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)

        # Avoid zero-size selection
        if (x2 - x1) > 10 and (y2 - y1) > 10:
            self.selection_coords = (x1, y1, x2, y2)
            # Hide window briefly to take screenshot
            self.top.withdraw()
            # Wait a tiny bit for window to disappear
            self.master.after(200, self._capture_and_callback, x1, y1, x2, y2)
        else:
            self.close()

    def _capture_and_callback(self, x1, y1, x2, y2):
        try:
            # ImageGrab.grab accepts (bbox)
            self.screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            if self.callback:
                self.callback(self.screenshot, (x1, y1, x2, y2))
        except Exception as e:
            print(f"Error grabbing screen: {e}")
        finally:
            self.close()

if __name__ == "__main__":
    # Test stub
    root = tk.Tk()
    root.withdraw()
    def cb(img, coords):
        print(f"Captured: {coords}")
        img.show()
        root.destroy()
    s = Sniper(root)
    s.start_selection(cb)
    root.mainloop()

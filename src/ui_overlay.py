import tkinter as tk
import tkinter.font as tkfont
import ctypes

class ResultOverlay:
    def __init__(self, master, text, x, y, width, height):
        self.master = master
        self.top = tk.Toplevel(self.master)
        
        # Remove window borders
        self.top.overrideredirect(True)
        self.top.attributes('-topmost', True)
        
        # Start hidden to avoid flickering during font calculation
        self.top.attributes('-alpha', 0.0)
        
        # Determine geometry
        qt_x = int(x)
        qt_y = int(y)
        
        # Ensure minimum dimensions but respect user selection for max
        # Actually user wants to FIT into selection.
        # But if selection is tiny, we must enforce some min readability ??
        # Let's trust user selection mostly, but ensure at least we can see something.
        qt_w = int(max(width, 200)) 
        qt_h = int(max(height, 100))
        
        self.top.geometry(f"{qt_w}x{qt_h}+{qt_x}+{qt_y}")
        self.top.configure(bg='#202020') # Dark background

        # Close on click or Escape
        self.top.bind("<Button-1>", lambda e: self.close())
        self.top.bind("<Escape>", lambda e: self.close())
        
        # Create Label
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
        
        # Determine optimal font size
        self.fit_font_size(text, qt_h, wrap_width)

        # Show Window
        self.top.attributes('-alpha', 0.9)
        self.top.focus_force()

    def fit_font_size(self, text, window_height, wrap_width):
        # Start from a reasonable max size and go down
        max_size = 20
        min_size = 8
        current_size = max_size
        
        # Text area height limit (subtract padding)
        available_height = window_height - 20 

        while current_size >= min_size:
            font = tkfont.Font(family="Arial", size=current_size)
            self.label.configure(font=font)
            
            # Force update to calculate required height
            self.label.update_idletasks()
            needed_height = self.label.winfo_reqheight()
            
            if needed_height <= available_height:
                return # Fits!
            
            current_size -= 1
        
        # If we exit loop, we use min_size (already set in last iteration)
        print("Text too long for window even at min font size.")

    def close(self):
        if self.top:
            self.top.destroy()
            self.top = None

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    # Test with long text
    long_text = "Bu çok uzun bir test metnidir. " * 20
    ResultOverlay(root, long_text, 100, 100, 300, 200)
    root.mainloop()

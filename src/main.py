import tkinter as tk
from pynput import keyboard
import threading
import queue
import time
import sys
import os

print("Initializing libraries... (This may take a few seconds)")

from sniper import Sniper
from ui_overlay import ResultOverlay
from ocr_engine import OCREngine
from translator import Translator

def select_model_cli():
    """
    Displays a CLI menu to select the translation model.
    Returns: The selected model name (str) or None (for default/last used).
    """
    os.system('cls' if os.name == 'nt' else 'clear')
    print("==================================================")
    print("      SCREEN TRANSLATOR - MODEL SELECTION")
    print("==================================================")
    print("1. Helsinki-NLP/opus-mt-en-tr (Hızlı, Standart)")
    print("   [Önerilen: 'opus-mt-tc-big' zaten inmişse bunu seçer]")
    print("")
    print("2. facebook/nllb-200-distilled-600M (Daha İyi Kalite)")
    print("   [~1 GB indirme gerektirir]")
    print("")
    print("3. facebook/nllb-200-distilled-1.3B (En İyi Kalite - AÇIR)")
    print("   [~2.5 GB indirme gerektirir - Yüksek VRAM]")
    print("")
    print("4. Son Kullanılan / Varsayılan")
    print("==================================================")
    
    choice = input("Seçiminiz (1-4): ").strip()
    
    if choice == '1':
        # We can return the base name. logic in translator handles 'big' lookup via config usually
        # But if user WANTS to force base model? 
        # For now let's pass the standard name, if local config overrides it with big model, good.
        return "Helsinki-NLP/opus-mt-en-tr"
    elif choice == '2':
        return "facebook/nllb-200-distilled-600M"
    elif choice == '3':
        return "facebook/nllb-200-distilled-1.3B"
    else:
        return None # Let logic decide (load from config)

class ScreenTranslatorApp:
    def __init__(self, selected_model_name=None):
        self.selected_model_name = selected_model_name
        
        self.root = tk.Tk()
        self.root.withdraw() # Hide the root window
        self.root.title("Screen Translator")

        # Command Queue 
        self.queue = queue.Queue()

        self.ocr_engine = None
        self.translator = None
        
        print(f"Application Initializing... Model Selection: {self.selected_model_name}")
        threading.Thread(target=self.load_models, daemon=True).start()

        self.listener = keyboard.GlobalHotKeys({
            '<ctrl>+<shift>+t': self.on_hotkey
        })
        self.listener.start()
        print("Hotkey Listener Started: CTRL+SHIFT+T")

        # Periodically check queue
        self.root.after(100, self.process_queue)

    def load_models(self):
        print("Loading Models in background...")
        try:
            # Load OCR
            self.ocr_engine = OCREngine(gpu=True)
            
            # Load Translator with selection
            self.translator = Translator(model_name=self.selected_model_name)
            
            print("Models Loaded Successfully!")
            print("Hazır! CTRL+SHIFT+T ile çeviri yapabilirsiniz.")
        except Exception as e:
            print(f"Error loading models: {e}")

    def on_hotkey(self):
        self.queue.put("START_SELECTION")

    def process_queue(self):
        try:
            msg = self.queue.get_nowait()
            if msg == "START_SELECTION":
                self.start_snipping()
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

    def start_snipping(self):
        if not self.ocr_engine or not self.translator:
            print("Modeller yükleniyor, lütfen bekleyin...")
            return

        print("Starting selection...")
        sniper = Sniper(self.root)
        sniper.start_selection(self.handle_snipped_image)

    def handle_snipped_image(self, image, coords):
        if image is None:
            print("Selection cancelled.")
            return
        
        x1, y1, x2, y2 = coords
        print(f"Image Captured: {coords}")
        threading.Thread(target=self.process_image, args=(image, x1, y1, x2-x1, y2-y1)).start()

    def process_image(self, image, x, y, w, h):
        try:
            print("Extracting text...")
            text = self.ocr_engine.extract_text(image)
            print(f"Extracted: {text}")

            if not text.strip():
                print("No text found.")
                return

            print("Translating...")
            translated = self.translator.translate(text)
            print(f"Translated: {translated}")

            self.root.after(0, lambda: ResultOverlay(self.root, translated, x, y, w, h))

        except Exception as e:
            print(f"Error during processing: {e}")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    selected_model = select_model_cli()
    app = ScreenTranslatorApp(selected_model)
    app.run()

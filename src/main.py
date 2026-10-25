import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import queue
import os
import ctypes

# Use the Windows certificate store for HTTPS. Antivirus HTTPS scanning (e.g.
# Kaspersky) re-signs traffic with its own root, which Python's bundled
# certificates reject and which breaks model downloads halfway.
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

# Set DPI awareness once at startup (Windows only)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

from pynput import keyboard

print("Kutuphaneler yukleniyor... (Bu birkac saniye surebilir)")

from config import load_config, update_config
from sniper import Sniper
from ui_overlay import ResultOverlay
from ocr_engine import OCREngine
from translator import Translator, MODELS, DEFAULT_MODEL, find_local_model

DEFAULT_HOTKEY = "ctrl+shift+t"
KEY_ALIASES = {"control": "ctrl", "win": "cmd", "windows": "cmd", "escape": "esc", "return": "enter"}


def to_pynput_hotkey(hotkey):
    """Convert "ctrl+shift+t" / "alt+f5" to pynput format ("<ctrl>+<shift>+t").
    Raises ValueError for unknown keys."""
    parts = []
    for part in hotkey.lower().split("+"):
        part = part.strip()
        if not part:
            raise ValueError(hotkey)
        part = KEY_ALIASES.get(part, part)
        parts.append(part if len(part) == 1 else f"<{part}>")
    combo = "+".join(parts)
    keyboard.HotKey.parse(combo)
    return combo


def select_settings_cli():
    """
    Displays a CLI menu for model selection and settings.
    Returns: (model_name, ocr_languages, hotkey)
    """
    config = load_config()
    last_model = config.get("model", DEFAULT_MODEL)

    os.system('cls' if os.name == 'nt' else 'clear')
    print("==================================================")
    print("      SCREEN TRANSLATOR - AYARLAR")
    print("==================================================")
    print("")
    print("  Ceviri Modeli:")
    for i, (repo_id, description, size_gb) in enumerate(MODELS, 1):
        status = "indirilmis" if find_local_model(repo_id, deep=False) else f"ilk kullanimda ~{size_gb} GB indirilecek"
        print(f"  {i}. {repo_id} ({description}) [{status}]")
    print(f"  {len(MODELS) + 1}. Son Kullanilan: {last_model}")
    print("")
    print("==================================================")

    choice = input(f"Model seciminiz (1-{len(MODELS) + 1}) [{len(MODELS) + 1}]: ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(MODELS):
        model_name = MODELS[int(choice) - 1][0]
    else:
        model_name = last_model

    # OCR language selection
    default_ocr = ",".join(config.get("ocr_languages", ["en"]))
    ocr_input = input(f"OCR dilleri (virgul ile ayir, or: en,tr) [{default_ocr}]: ").strip()
    if ocr_input:
        ocr_languages = [lang.strip() for lang in ocr_input.split(",") if lang.strip()]
    else:
        ocr_languages = config.get("ocr_languages", ["en"])

    # Hotkey selection (only a valid hotkey is accepted and saved)
    default_hotkey = config.get("hotkey", DEFAULT_HOTKEY)
    try:
        to_pynput_hotkey(default_hotkey)
    except ValueError:
        default_hotkey = DEFAULT_HOTKEY
    while True:
        hotkey = input(f"Kisayol tusu (or: ctrl+shift+t, alt+f5) [{default_hotkey}]: ").strip() or default_hotkey
        try:
            to_pynput_hotkey(hotkey)
            break
        except ValueError:
            print(f"Gecersiz kisayol: {hotkey}. Ornek: ctrl+shift+t, alt+t, ctrl+f5")

    update_config(ocr_languages=ocr_languages, hotkey=hotkey)
    return model_name, ocr_languages, hotkey


class ScreenTranslatorApp:
    def __init__(self, selected_model_name=None, ocr_languages=None, hotkey=DEFAULT_HOTKEY):
        self.selected_model_name = selected_model_name or DEFAULT_MODEL
        self.ocr_languages = ocr_languages or ["en"]
        self.hotkey = hotkey
        self.current_overlay = None
        self.sniper = None

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Screen Translator")

        # Worker threads never touch Tk directly; they post messages here
        self.queue = queue.Queue()
        self.models_ready = threading.Event()
        self.load_error = None
        self.process_lock = threading.Lock()

        self.ocr_engine = None
        self.translator = None

        print(f"Uygulama baslatiliyor... Model: {self.selected_model_name}")
        print(f"OCR dilleri: {self.ocr_languages}")
        print(f"Kisayol: {self.hotkey}")
        self.start_loading(self.selected_model_name)

        self.listener = keyboard.GlobalHotKeys({
            to_pynput_hotkey(self.hotkey): self.on_hotkey
        })
        self.listener.start()
        print(f"Kisayol dinleniyor: {self.hotkey.upper()}")

        self.root.after(100, self.process_queue)

    def start_loading(self, model_name):
        self.load_error = None
        threading.Thread(target=self.load_models, args=(model_name,), daemon=True).start()

    def load_models(self, model_name):
        print("Modeller arka planda yukleniyor...")
        try:
            if self.ocr_engine is None:
                self.ocr_engine = OCREngine(languages=self.ocr_languages, gpu=True)
            self.translator = Translator(model_name=model_name)
            update_config(model=model_name)
            self.queue.put(("MODELS_READY",))
        except Exception as e:
            self.queue.put(("LOAD_FAILED", str(e)))

    def on_hotkey(self):
        self.queue.put(("START_SELECTION",))

    def process_queue(self):
        try:
            while True:
                msg, *args = self.queue.get_nowait()
                if msg == "START_SELECTION":
                    self.start_snipping()
                elif msg == "SHOW_RESULT":
                    self._show_overlay(*args)
                elif msg == "MODELS_READY":
                    self.models_ready.set()
                    print("Modeller basariyla yuklendi!")
                    print(f"Hazir! {self.hotkey.upper()} ile ceviri yapabilirsiniz.")
                elif msg == "LOAD_FAILED":
                    self.on_load_failed(*args)
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

    def on_load_failed(self, error):
        self.load_error = error
        print(f"Model yukleme hatasi: {error}")
        retry = messagebox.askyesno(
            "Model Yuklenemedi",
            f"{error}\n\nElle indirilmis bir model klasoru secmek ister misiniz?\n"
            "(config.json, tokenizer ve agirlik dosyalarini iceren klasor)",
            parent=self.root,
        )
        if retry:
            path = filedialog.askdirectory(title="Model Klasorunu Secin", parent=self.root)
            if path:
                self.start_loading(path)
                return
        print("Model yuklenemedi. Uygulamayi yeniden baslatip baska bir model secebilirsiniz.")

    def start_snipping(self):
        if self.load_error:
            self.on_load_failed(self.load_error)
            return
        if not self.models_ready.is_set():
            print("Modeller yukleniyor, lutfen bekleyin...")
            return
        if self.sniper:
            return

        print("Secim baslatiliyor...")
        self.sniper = Sniper(self.root)
        self.sniper.start_selection(self.handle_snipped_image)

    def handle_snipped_image(self, image, coords):
        self.sniper = None
        if image is None:
            print("Secim iptal edildi.")
            return

        x1, y1, x2, y2 = coords
        print(f"Goruntu yakalandi: {coords}")
        threading.Thread(target=self.process_image, args=(image, x1, y1, x2 - x1, y2 - y1), daemon=True).start()

    def process_image(self, image, x, y, w, h):
        try:
            with self.process_lock:
                print("Metin cikariliyor...")
                paragraphs = self.ocr_engine.extract_paragraphs(image)
                print(f"Cikarilan metin: {paragraphs}")

                if not any(p.strip() for p in paragraphs):
                    print("Metin bulunamadi.")
                    return

                print("Cevriliyor...")
                translated = self.translator.translate(paragraphs)
                print(f"Ceviri: {translated}")

            self.queue.put(("SHOW_RESULT", translated, x, y, w, h))

        except Exception as e:
            print(f"Islem hatasi: {e}")

    def _show_overlay(self, text, x, y, w, h):
        if self.current_overlay:
            self.current_overlay.close()
        self.current_overlay = ResultOverlay(self.root, text, x, y, w, h)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    model, ocr_langs, hk = select_settings_cli()
    app = ScreenTranslatorApp(model, ocr_langs, hk)
    app.run()

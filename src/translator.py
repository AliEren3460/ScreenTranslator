from transformers import MarianMTModel, MarianTokenizer, AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import json

CONFIG_FILE = "translator_config.json"

class Translator:
    def __init__(self, model_name=None):
        """
        model_name: "Helsinki-NLP/opus-mt-en-tr", "facebook/nllb-200-distilled-600M", etc.
        If None, tries to load from config.
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")
        
        self.tokenizer = None
        self.model = None
        self.is_nllb = False
        
        # 1. Check Config exists and user DID NOT provide a specific override?
        # Actually, if user picked from CLI, we should respect that.
        # But if user picked "Default/Last Used", then we look at config.
        # Let's say if model_name is passed, we try that. If it fails, we fallback.
        # If model_name is None, we look at config.
        
        if model_name:
            # User explicitly chose a model (CLI)
            print(f"Initializing with selected model: {model_name}")
            try:
                self.load_from_path(model_name)
            except Exception as e:
                print(f"Failed to load selected model: {e}")
                self.ask_user_for_model(model_name)
        else:
            # Auto-load last config
            if os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, 'r') as f:
                        config = json.load(f)
                        local_path = config.get("model_path")
                        if local_path and os.path.exists(local_path):
                            print(f"Loading from last used path: {local_path}")
                            self.load_from_path(local_path)
                except Exception as e:
                    print(f"Config load failed: {e}")

            if not self.model:
                # Fallback to default
                default = "Helsinki-NLP/opus-mt-en-tr"
                print(f"No config or selection. trying default: {default}")
                try:
                    self.load_from_path(default)
                except Exception as e:
                    self.ask_user_for_model(default)

    def load_from_path(self, path):
        # Detect NLLB
        # We can check string name if it contains 'nllb'
        # OR we can try loading as Auto and check config.
        
        path_str = str(path).lower()
        if "nllb" in path_str:
            self.is_nllb = True
            print("Detected NLLB model.")
            self.tokenizer = AutoTokenizer.from_pretrained(path, token=False)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(path, token=False).to(self.device)
        else:
            self.is_nllb = False
            print("Detected MarianMT (Opus) model.")
            # We can use Auto for everything usually, but let's be safe with previous working code for Marian
            # Actually, let's try strict Marian classes for Helsinki to avoid regression
            self.tokenizer = MarianTokenizer.from_pretrained(path, token=False)
            self.model = MarianMTModel.from_pretrained(path, token=False).to(self.device)
            
        print(f"Translation model loaded successfully: {path}")

    def ask_user_for_model(self, default_name):
        print("Asking user for manual model path...")
        root = tk.Tk()
        root.withdraw()
        
        msg = (
            f"Model yüklenemedi: {default_name}\n\n"
            "İnternet bağlantısı veya yetki sorunu olabilir.\n"
            "Lütfen manuel olarak indirilmiş model KLASÖRÜNÜ seçin."
        )
        messagebox.showerror("Model Hatası", msg)
        
        selected_path = filedialog.askdirectory(title="Model Klasörünü Seçin")
        root.destroy()
        
        if selected_path:
            self.load_from_path(selected_path)
            # Save to config
            with open(CONFIG_FILE, 'w') as f:
                json.dump({"model_path": selected_path}, f)
        else:
            raise RuntimeError("User cancelled model selection.")

    def translate(self, text):
        if not self.model:
             return "Model not loaded."
        if not text or not text.strip():
            return ""

        try:
            if self.is_nllb:
                # NLLB specific translation
                # src_lang is usually automatic if tokenizer was init with it, but safest is to specify
                # M2M100/NLLB tokens: 'eng_Latn', 'tur_Latn'
                # Note: NLLB 200 checks src_lang tokens
                
                # Check directly if we can use simple generation or need forced_bos_token_id
                # NLLB requires telling it the target language.
                
                # Ensure src lang provided (if needed)
                # tokenizer.src_lang = "eng_Latn"
                inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True).to(self.device)
                
                # Force target language token
                # tur_Latn is the code for Turkish
                forced_id = self.tokenizer.convert_tokens_to_ids("tur_Latn")
                
                translated_tokens = self.model.generate(
                    **inputs, 
                    forced_bos_token_id=forced_id, 
                    max_length=512
                )
                result = self.tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)
                return result[0]
            else:
                # MarianMT standard
                inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True).to(self.device)
                translated_tokens = self.model.generate(**inputs)
                result = self.tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)
                return result[0]

        except Exception as e:
            print(f"Translation Error: {e}")
            return f"[Error: {e}]"

if __name__ == "__main__":
    # Test
    pass

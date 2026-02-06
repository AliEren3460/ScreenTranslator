import sys
import time

print("Debug: Starting imports...")

start = time.time()
print("Importing os/sys/threading...", end="", flush=True)
import os
import threading
import queue
print(f" Done ({time.time()-start:.2f}s)")

start = time.time()
print("Importing tkinter...", end="", flush=True)
import tkinter as tk
print(f" Done ({time.time()-start:.2f}s)")

start = time.time()
print("Importing pynput...", end="", flush=True)
from pynput import keyboard
print(f" Done ({time.time()-start:.2f}s)")

start = time.time()
print("Importing Pillow...", end="", flush=True)
from PIL import ImageGrab
print(f" Done ({time.time()-start:.2f}s)")

try:
    start = time.time()
    print("Importing libraries from src...", end="", flush=True)
    sys.path.append(os.path.join(os.getcwd(), 'src'))
    print(" path added.", end="", flush=True)
except Exception as e:
    print(f"\nError adding path: {e}")

try:
    start = time.time()
    print("\nImporting easyocr (This can be slow)...", end="", flush=True)
    import easyocr
    print(f" Done ({time.time()-start:.2f}s)")
except Exception as e:
    print(f"\nError importing easyocr: {e}")

try:
    start = time.time()
    print("Importing torch (This can be slow)...", end="", flush=True)
    import torch
    print(f" Done ({time.time()-start:.2f}s)")
except Exception as e:
    print(f"\nError importing torch: {e}")

try:
    start = time.time()
    print("Importing transformers...", end="", flush=True)
    from transformers import MarianMTModel, MarianTokenizer
    print(f" Done ({time.time()-start:.2f}s)")
except Exception as e:
    print(f"\nError importing transformers: {e}")

print("\nImport check complete. If you saw all 'Done' messages, imports are fine.")

import json
import os

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(CONFIG_DIR, "translator_config.json")


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # Older versions stored the last manually selected folder as "model_path"
            if "model" not in config and config.get("model_path"):
                config["model"] = config.pop("model_path")
            return config
        except Exception as e:
            print(f"Config okunamadi ({e}), varsayilanlar kullaniliyor.")
    return {}


def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def update_config(**values):
    config = load_config()
    config.update(values)
    config.pop("model_path", None)
    save_config(config)

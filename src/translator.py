import json
import os
import re
import threading

import torch
from huggingface_hub import HfApi, snapshot_download
from huggingface_hub.constants import HF_HUB_CACHE
from huggingface_hub.utils import RepositoryNotFoundError
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

from config import CONFIG_DIR

# (repo id, description, approximate download size in GB)
MODELS = [
    ("Helsinki-NLP/opus-mt-tc-big-en-tr", "Hizli, Standart", 0.5),
    ("facebook/nllb-200-distilled-600M", "Daha Iyi Kalite", 2.5),
    ("facebook/nllb-200-distilled-1.3B", "Yuksek Kalite - AGIR", 5.5),
    ("facebook/nllb-200-3.3B", "En Iyi Kalite - COK AGIR", 17.6),
]
DEFAULT_MODEL = MODELS[0][0]

NLLB_SRC_LANG = "eng_Latn"
NLLB_TGT_LANG = "tur_Latn"

# Checked in the same order transformers picks weights: the first file present wins
WEIGHT_FILES = ("model.safetensors", "model.safetensors.index.json",
                "pytorch_model.bin", "pytorch_model.bin.index.json")
TOKENIZER_FILES = ("tokenizer.json", "sentencepiece.bpe.model", "source.spm", "spiece.model", "vocab.json")
# Everything except weights that a seq2seq model/tokenizer may need
SUPPORT_FILE_PATTERNS = ["*.json", "*.spm", "*.model", "*.txt"]
# Weight formats by preference, plus everything to skip when that format is used
WEIGHT_FORMATS = [
    (re.compile(r"^model(-\d+-of-\d+)?\.safetensors(\.index\.json)?$"),
     ["*.bin", "*.bin.index.json", "*.h5", "*.msgpack", "*.ot", "onnx/*"]),
    (re.compile(r"^pytorch_model(-\d+-of-\d+)?\.bin(\.index\.json)?$"),
     ["*.safetensors", "*.safetensors.index.json", "*.h5", "*.msgpack", "*.ot", "onnx/*"]),
]

SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")


class ModelLoadError(Exception):
    pass


def is_complete_model_dir(path):
    """True if `path` holds a config, a tokenizer and *all* weight files.
    Interrupted downloads leave config/tokenizer files behind without weights,
    so checking for config.json alone is not enough."""
    if not os.path.isfile(os.path.join(path, "config.json")):
        return False
    if not any(os.path.isfile(os.path.join(path, f)) for f in TOKENIZER_FILES):
        return False
    for name in WEIGHT_FILES:
        weight_path = os.path.join(path, name)
        if not os.path.isfile(weight_path):
            continue
        if not name.endswith(".index.json"):
            return True
        # Sharded weights: every shard listed in the index must exist
        try:
            with open(weight_path, 'r', encoding='utf-8') as f:
                shards = set(json.load(f)["weight_map"].values())
        except Exception:
            return False
        return bool(shards) and all(os.path.isfile(os.path.join(path, s)) for s in shards)
    return False


def _complete_snapshot(path):
    """Return `path` or one of its HF-cache snapshots if it is a complete model.
    The snapshot that refs/main points to is preferred."""
    if is_complete_model_dir(path):
        return path
    snapshots = os.path.join(path, "snapshots")
    if not os.path.isdir(snapshots):
        return None
    candidates = sorted(os.listdir(snapshots))
    ref_main = os.path.join(path, "refs", "main")
    if os.path.isfile(ref_main):
        with open(ref_main, 'r', encoding='utf-8') as f:
            main_hash = f.read().strip()
        if main_hash in candidates:
            candidates.remove(main_hash)
            candidates.insert(0, main_hash)
    for entry in candidates:
        snap = os.path.join(snapshots, entry)
        if is_complete_model_dir(snap):
            return snap
    return None


def _cache_folder_name(repo_id):
    return "models--" + repo_id.replace("/", "--")


def _extra_search_dirs():
    """Folders (besides the HF cache) that may hold a manually downloaded model."""
    home = os.path.expanduser("~")
    bases = [
        os.path.join(os.getcwd(), "model_cache"),
        os.path.join(CONFIG_DIR, "model_cache"),
        os.path.join(os.path.dirname(CONFIG_DIR), "model_cache"),
        os.path.join(home, "Downloads"),
        os.path.join(home, "Desktop"),
        os.path.join(home, "Documents"),
    ]
    seen, out = set(), []
    for b in bases:
        b = os.path.normcase(os.path.abspath(b))
        if b not in seen and os.path.isdir(b):
            seen.add(b)
            out.append(b)
    return out


def _scan_dir_for_model(base, repo_id, max_depth=4):
    """Find a folder under `base` named like the model (e.g. "nllb-200-distilled-600M"
    or "models--facebook--nllb-200-distilled-600M") that holds a complete model."""
    names = {repo_id.split("/")[-1].lower(), _cache_folder_name(repo_id).lower()}
    base_depth = base.rstrip(os.sep).count(os.sep)
    try:
        for root, dirs, _files in os.walk(base):
            if root.count(os.sep) - base_depth >= max_depth:
                dirs[:] = []
            for d in dirs:
                if d.lower() in names:
                    found = _complete_snapshot(os.path.join(root, d))
                    if found:
                        return found
    except Exception:
        pass
    return None


def find_local_model(name, deep=True):
    """Return a folder holding a complete copy of `name` (a local folder or a
    HuggingFace repo id), or None. `deep` also scans Downloads/Desktop/Documents."""
    if os.path.isdir(name):
        return _complete_snapshot(name)

    cached = _complete_snapshot(os.path.join(HF_HUB_CACHE, _cache_folder_name(name)))
    if cached:
        return cached

    if deep:
        for base in _extra_search_dirs():
            found = _scan_dir_for_model(base, name)
            if found:
                return found
    return None


def download_model(repo_id):
    """Download only the files needed to run `repo_id` into the HF cache and
    return the local folder. Interrupted downloads are resumed."""
    try:
        info = HfApi().model_info(repo_id, files_metadata=True, token=False)
    except RepositoryNotFoundError:
        raise ModelLoadError(
            f"'{repo_id}' HuggingFace'te bulunamadi (adi yanlis veya model kaldirilmis).")
    except Exception as e:
        raise ModelLoadError(f"HuggingFace'e baglanilamadi, internet baglantinizi kontrol edin. ({e})")

    files = {s.rfilename: (s.size or 0) for s in info.siblings}
    # Prefer safetensors; fall back to .bin. Never download both.
    for pattern, ignore in WEIGHT_FORMATS:
        weights = [f for f in files if pattern.match(f)]
        if weights:
            break
    else:
        raise ModelLoadError(f"'{repo_id}' icin PyTorch agirlik dosyasi bulunamadi.")

    size_gb = sum(files[f] for f in weights) / 1024 ** 3
    print(f"Model indiriliyor: {repo_id} (~{size_gb:.1f} GB). Yarim kalan indirmeler kaldigi yerden devam eder.")
    try:
        path = snapshot_download(
            repo_id,
            allow_patterns=SUPPORT_FILE_PATTERNS + weights,
            ignore_patterns=ignore,
            token=False,
        )
    except Exception as e:
        raise ModelLoadError(f"Indirme basarisiz: {e}")

    if not is_complete_model_dir(path):
        raise ModelLoadError(f"Indirme tamamlandi ama model dosyalari eksik: {path}")
    return path


def split_sentences(text):
    return [s for s in SENTENCE_SPLIT.split(text.strip()) if s]


class Translator:
    def __init__(self, model_name=None):
        """
        model_name: a HuggingFace repo id (see MODELS) or a local model folder.
        Raises ModelLoadError if the model can not be found, downloaded or loaded.
        """
        self.model_name = model_name or DEFAULT_MODEL
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # Half precision halves VRAM use (nllb-3.3B: ~13 GB -> ~6.6 GB)
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32
        self._lock = threading.Lock()
        print(f"Cihaz: {self.device}")

        path = find_local_model(self.model_name)
        if path:
            print(f"Yerel model bulundu: {path}")
        elif os.path.isdir(self.model_name):
            raise ModelLoadError(
                f"Secilen klasorde eksiksiz bir model yok: {self.model_name}\n"
                "(config.json, tokenizer ve agirlik dosyalari gerekli)")
        else:
            print(f"Yerel kopya bulunamadi: {self.model_name}")
            path = download_model(self.model_name)

        self._load(path)

    def _load(self, path):
        print(f"Model yukleniyor: {path}")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                path, local_files_only=True, dtype=self.dtype).to(self.device).eval()
        except Exception as e:
            raise ModelLoadError(f"Model dosyalari yuklenemedi ({path}): {e}")

        self.is_nllb = self.model.config.model_type == "m2m_100" and NLLB_TGT_LANG in self.tokenizer.get_vocab()
        if self.is_nllb:
            self.tokenizer.src_lang = NLLB_SRC_LANG
            self.forced_bos_token_id = self.tokenizer.convert_tokens_to_ids(NLLB_TGT_LANG)
        print(f"Ceviri modeli yuklendi ({'NLLB' if self.is_nllb else self.model.config.model_type}).")

    def translate(self, text, batch_size=16):
        """Translate a string or a list of paragraphs. Each paragraph is split
        into sentences (long inputs make the models skip sentences) and the
        result keeps one line per paragraph."""
        paragraphs = [text] if isinstance(text, str) else list(text)
        paragraphs = [p for p in paragraphs if p and p.strip()]
        if not paragraphs:
            return ""

        sentences, counts = [], []
        for p in paragraphs:
            parts = split_sentences(p)
            sentences.extend(parts)
            counts.append(len(parts))

        try:
            with self._lock:
                translated = []
                for i in range(0, len(sentences), batch_size):
                    translated.extend(self._generate(sentences[i:i + batch_size]))
        except Exception as e:
            print(f"Ceviri hatasi: {e}")
            return f"[Hata: {e}]"

        lines, pos = [], 0
        for n in counts:
            lines.append(" ".join(translated[pos:pos + n]))
            pos += n
        return "\n".join(lines)

    @torch.inference_mode()
    def _generate(self, batch):
        inputs = self.tokenizer(batch, return_tensors="pt", padding=True, truncation=True).to(self.device)
        kwargs = {"max_new_tokens": 256, "num_beams": 4}
        if self.is_nllb:
            kwargs["forced_bos_token_id"] = self.forced_bos_token_id
        tokens = self.model.generate(**inputs, **kwargs)
        return self.tokenizer.batch_decode(tokens, skip_special_tokens=True)

import hashlib
import json
import os
import re
import shutil
import site
import threading

from huggingface_hub import HfApi, snapshot_download
from huggingface_hub.constants import HF_HUB_CACHE
from huggingface_hub.utils import RepositoryNotFoundError

from config import CONFIG_DIR

OPUS_MODEL = "Helsinki-NLP/opus-mt-tc-big-en-tr"
TOZ_MODEL = "TozAI/Toz-Cevir-1"

# (repo id, description, approximate download size in GB)
MODELS = [
    (OPUS_MODEL, "Hizli - GPU varsa GPU, yoksa CPU", 0.5),
    (TOZ_MODEL, "En Iyi Kalite - GPU varsa GPU, yoksa CPU", 0.3),
]
DEFAULT_MODEL = OPUS_MODEL

TOZ_FILES = ["toz-cevir.pt", "tokenizer.model"]
CT2_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "screentranslator", "ct2")

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
    """Find a folder under `base` named like the model (e.g. "opus-mt-tc-big-en-tr"
    or "models--Helsinki-NLP--opus-mt-tc-big-en-tr") that holds a complete model."""
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


def find_local_toz():
    try:
        path = snapshot_download(TOZ_MODEL, allow_patterns=TOZ_FILES, local_files_only=True)
    except Exception:
        return None
    return path if all(os.path.isfile(os.path.join(path, f)) for f in TOZ_FILES) else None


def is_downloaded(name):
    """Fast check for the settings menu (no folder scanning)."""
    return bool(find_local_toz() if name == TOZ_MODEL else find_local_model(name, deep=False))


def _repo_info(repo_id):
    try:
        return HfApi().model_info(repo_id, files_metadata=True, token=False)
    except RepositoryNotFoundError:
        raise ModelLoadError(
            f"'{repo_id}' HuggingFace'te bulunamadi (adi yanlis veya model kaldirilmis).")
    except Exception as e:
        raise ModelLoadError(f"HuggingFace'e baglanilamadi, internet baglantinizi kontrol edin. ({e})")


def download_model(repo_id):
    """Download only the files needed to run `repo_id` into the HF cache and
    return the local folder. Interrupted downloads are resumed."""
    files = {s.rfilename: (s.size or 0) for s in _repo_info(repo_id).siblings}
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


def download_toz():
    _repo_info(TOZ_MODEL)
    print(f"Model indiriliyor: {TOZ_MODEL} (~0.3 GB)")
    try:
        path = snapshot_download(TOZ_MODEL, allow_patterns=TOZ_FILES, token=False)
    except Exception as e:
        raise ModelLoadError(f"Indirme basarisiz: {e}")
    if not all(os.path.isfile(os.path.join(path, f)) for f in TOZ_FILES):
        raise ModelLoadError(f"Indirme tamamlandi ama model dosyalari eksik: {path}")
    return path


def ensure_ct2_model(hf_path):
    """Convert a HuggingFace model folder to CTranslate2 int8 once and return
    the converted folder. Conversion takes a few seconds and needs torch."""
    key = hashlib.sha1(os.path.abspath(hf_path).lower().encode()).hexdigest()[:12]
    out = os.path.join(CT2_CACHE, f"{os.path.basename(hf_path.rstrip(os.sep))}-{key}")
    if os.path.isfile(os.path.join(out, "model.bin")):
        return out

    print("Model hizli calisma bicimine (CTranslate2 int8) donusturuluyor, bu bir kez yapilir...")
    from ctranslate2.converters import TransformersConverter
    tmp = out + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    try:
        TransformersConverter(hf_path).convert(tmp, quantization="int8", force=True)
    except Exception as e:
        shutil.rmtree(tmp, ignore_errors=True)
        raise ModelLoadError(f"Model donusturulemedi ({hf_path}): {e}")
    os.replace(tmp, out)
    return out


def _add_cuda_dll_dirs():
    """CTranslate2 needs cuBLAS 12. On Windows it comes from the nvidia-cublas-cu12
    package or a CUDA 12 build of torch; make both findable."""
    if os.name != "nt":
        return
    dirs = [os.path.join(p, "nvidia", "cublas", "bin") for p in site.getsitepackages()]
    try:
        import torch
        dirs.append(os.path.join(os.path.dirname(torch.__file__), "lib"))
    except ImportError:
        pass
    for d in dirs:
        if os.path.isdir(d):
            os.add_dll_directory(d)
            os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]


def split_sentences(text):
    return [s for s in SENTENCE_SPLIT.split(text.strip()) if s]


class Translator:
    def __init__(self, model_name=None, device="auto"):
        """
        model_name: TOZ_MODEL, a HuggingFace seq2seq repo id or a local model folder.
        device: "auto" (GPU if it works, else CPU), "cuda" or "cpu".
        Raises ModelLoadError if the model can not be found, downloaded or loaded.
        """
        self.model_name = model_name or DEFAULT_MODEL
        self._lock = threading.Lock()

        if self.model_name == TOZ_MODEL:
            self._load_toz(device)
        else:
            self._load_ct2(self._resolve_hf_model(), device)

    def _resolve_hf_model(self):
        path = find_local_model(self.model_name)
        if path:
            print(f"Yerel model bulundu: {path}")
            return path
        if os.path.isdir(self.model_name):
            raise ModelLoadError(
                f"Secilen klasorde eksiksiz bir model yok: {self.model_name}\n"
                "(config.json, tokenizer ve agirlik dosyalari gerekli)")
        print(f"Yerel kopya bulunamadi: {self.model_name}")
        return download_model(self.model_name)

    def _load_toz(self, device):
        import torch
        import tozcevir

        path = find_local_toz() or download_toz()
        print(f"Model yukleniyor: {path}")
        self.backend = "toz"

        if device in ("auto", "cuda"):
            if torch.cuda.is_available():
                try:
                    self.toz = tozcevir.load(path, device="cuda")
                    self._generate(["Test."])
                    print("Ceviri modeli yuklendi (Toz-Cevir-1, GPU).")
                    return
                except Exception as e:
                    if device == "cuda":
                        raise ModelLoadError(f"Toz-Cevir GPU'da calistirilamadi: {e}")
                    print(f"GPU kullanilamadi, CPU'ya geciliyor: {e}")
            elif device == "cuda":
                raise ModelLoadError("CUDA destekli GPU bulunamadi.")

        try:
            self.toz = tozcevir.load(path, device="cpu")
        except Exception as e:
            raise ModelLoadError(f"Toz-Cevir yuklenemedi: {e}")
        print("Ceviri modeli yuklendi (Toz-Cevir-1, CPU).")

    def _load_ct2(self, hf_path, device):
        import ctranslate2
        from transformers import AutoConfig, AutoTokenizer

        try:
            model_type = AutoConfig.from_pretrained(hf_path, local_files_only=True).model_type
            self.tokenizer = AutoTokenizer.from_pretrained(hf_path, local_files_only=True)
        except Exception as e:
            raise ModelLoadError(f"Model dosyalari yuklenemedi ({hf_path}): {e}")
        self.is_nllb = model_type == "m2m_100" and NLLB_TGT_LANG in self.tokenizer.get_vocab()
        if self.is_nllb:
            self.tokenizer.src_lang = NLLB_SRC_LANG
        ct2_path = ensure_ct2_model(hf_path)
        self.backend = "ct2"

        if device in ("auto", "cuda"):
            _add_cuda_dll_dirs()
            if ctranslate2.get_cuda_device_count() > 0:
                try:
                    self.model = ctranslate2.Translator(ct2_path, device="cuda", compute_type="int8_float16")
                    self._generate(["Test."])  # cuBLAS is only loaded on first use
                    print(f"Ceviri modeli yuklendi ({model_type}, GPU).")
                    return
                except Exception as e:
                    if device == "cuda":
                        raise ModelLoadError(f"Model GPU'da calistirilamadi: {e}")
                    print(f"GPU kullanilamadi, CPU'ya geciliyor: {e}")
            elif device == "cuda":
                raise ModelLoadError("CUDA destekli GPU bulunamadi.")

        self.model = ctranslate2.Translator(ct2_path, device="cpu", compute_type="int8",
                                            intra_threads=os.cpu_count() or 4)
        print(f"Ceviri modeli yuklendi ({model_type}, CPU).")

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

    def _generate(self, batch):
        if self.backend == "toz":
            return [self.toz.translate(s, to="tr", beam=4, split=False) for s in batch]

        source = [self.tokenizer.convert_ids_to_tokens(self.tokenizer.encode(s)) for s in batch]
        prefix = [[NLLB_TGT_LANG]] * len(source) if self.is_nllb else None
        results = self.model.translate_batch(source, target_prefix=prefix, beam_size=4,
                                             max_decoding_length=256)
        out = []
        for r in results:
            tokens = r.hypotheses[0][1:] if self.is_nllb else r.hypotheses[0]
            out.append(self.tokenizer.decode(self.tokenizer.convert_tokens_to_ids(tokens),
                                             skip_special_tokens=True))
        return out

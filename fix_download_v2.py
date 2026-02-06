import os
from huggingface_hub import snapshot_download

# Explicitly clear environment variables inside this script
if "HF_TOKEN" in os.environ:
    del os.environ["HF_TOKEN"]
if "HUGGING_FACE_HUB_TOKEN" in os.environ:
    del os.environ["HUGGING_FACE_HUB_TOKEN"]

print("Environment variables cleared.")

# Use a local cache dir to avoid global config issues
local_cache = os.path.join(os.getcwd(), "model_cache")

print(f"Downloading to local cache: {local_cache}")

try:
    model_id = "Helsinki-NLP/opus-mt-en-tr"
    path = snapshot_download(
        repo_id=model_id, 
        token=False, 
        cache_dir=local_cache,
        local_files_only=False
    )
    print(f"SUCCESS: Model downloaded to {path}")
except Exception as e:
    print(f"FAILURE: {e}")

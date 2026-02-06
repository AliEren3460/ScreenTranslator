import os
import shutil
from pathlib import Path
from huggingface_hub import snapshot_download

def fix_huggingface_auth():
    print("--- Hugging Face Auth Fixer ---")
    
    # 1. Locate and remove the token file
    home = Path.home()
    token_path = home / ".cache" / "huggingface" / "token"
    stored_token_path = home / ".huggingface" / "token"
    
    deleted = False
    for p in [token_path, stored_token_path]:
        if p.exists():
            print(f"Found token file at: {p}")
            try:
                os.remove(p)
                print("Token file deleted.")
                deleted = True
            except Exception as e:
                print(f"Could not delete token file: {e}")
    
    if not deleted:
        print("No token file found (this is good if we want anonymous access).")

    # 2. Force Anonymous Download
    print("\nAttempting to download model anonymously...")
    try:
        model_id = "Helsinki-NLP/opus-mt-en-tr"
        snapshot_download(repo_id=model_id, token=False)
        print("\nSUCCESS: Model downloaded to cache!")
    except Exception as e:
        print(f"\nFAILURE: Could not download model: {e}")
        print("\nTrying alternative method (renaming cache folder)...")

if __name__ == "__main__":
    fix_huggingface_auth()

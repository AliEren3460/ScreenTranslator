import requests
import os

def debug_env():
    print("--- Environment Variables (Filtered) ---")
    for k, v in os.environ.items():
        if "TOKEN" in k.upper() or "AUTH" in k.upper() or "HUGGING" in k.upper():
            print(f"{k}: [REDACTED]")

def test_google():
    try:
        r = requests.get("https://google.com", timeout=5)
        print(f"Google Status: {r.status_code}")
    except Exception as e:
        print(f"Google Failed: {e}")

def test_hf_explicit():
    url = "https://huggingface.co/api/models/Helsinki-NLP/opus-mt-en-tr/revision/main"
    try:
        # Explicitly disable auth via auth=None (though it is default)
        # And empty headers
        r = requests.get(url, auth=None, headers={}) 
        print(f"HF Explicit Status: {r.status_code}")
        print(f"Response: {r.text[:100]}")
    except Exception as e:
        print(f"HF Explicit Failed: {e}")

if __name__ == "__main__":
    debug_env()
    test_google()
    test_hf_explicit()

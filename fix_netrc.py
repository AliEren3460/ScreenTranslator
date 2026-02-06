import os
from pathlib import Path

def find_and_disable_netrc():
    home = Path.home()
    candidates = [home / ".netrc", home / "_netrc"]
    
    found = False
    for p in candidates:
        if p.exists():
            print(f"Found netrc file at: {p}")
            new_name = p.with_name(p.name + ".bak")
            try:
                p.rename(new_name)
                print(f"Renamed to: {new_name}")
                found = True
            except Exception as e:
                print(f"Failed to rename {p}: {e}")
    
    if not found:
        print("No .netrc file found.")

if __name__ == "__main__":
    find_and_disable_netrc()

#!/usr/bin/env python3
import os
import sys
from pathlib import Path

def setup_symlink():
    # Workspace source directory
    src_dir = Path("/Users/moritzmuss/Programmieren/Ankicity").resolve()
    
    # Anki addons directory on macOS
    addons_dir = Path("~/Library/Application Support/Anki2/addons21").expanduser()
    
    if not addons_dir.exists():
        print(f"Error: Anki add-ons directory not found at {addons_dir}")
        print("Please make sure Anki is installed and has been run at least once.")
        sys.exit(1)
        
    dest_link = addons_dir / "ankicity"
    
    if dest_link.exists() or dest_link.is_symlink():
        print(f"Removing existing link/folder at {dest_link}...")
        if dest_link.is_symlink():
            dest_link.unlink()
        elif dest_link.is_dir():
            import shutil
            shutil.rmtree(dest_link)
        else:
            dest_link.unlink()
            
    try:
        os.symlink(src_dir, dest_link)
        print(f"Successfully symlinked {src_dir} to {dest_link}")
        print("Now you can restart Anki to load the add-on!")
    except Exception as e:
        print(f"Failed to create symlink: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_symlink()

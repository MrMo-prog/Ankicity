#!/usr/bin/env python3
import os
import zipfile

def main():
    addon_filename = "/Users/moritzmuss/Programmieren/Ankicity/ankicity.ankiaddon"
    source_dir = "/Users/moritzmuss/Programmieren/Ankicity"
    
    # Files to include in the root
    root_files = [
        "__init__.py",
        "config.json",
        "db.py",
        "engine.py",
        "exporter.py",
        "manifest.json",
        "patch_notes.md",
        "webview.py"
    ]
    
    print(f"Creating {addon_filename}...")
    with zipfile.ZipFile(addon_filename, "w", zipfile.ZIP_DEFLATED) as z:
        # 1. Add root files
        for filename in root_files:
            filepath = os.path.join(source_dir, filename)
            if os.path.exists(filepath):
                z.write(filepath, filename)
                print(f"Added: {filename}")
                
        # 2. Add web folder contents recursively
        web_dir = os.path.join(source_dir, "web")
        for root, dirs, files in os.walk(web_dir):
            for file in files:
                if file == ".DS_Store" or "__pycache__" in root:
                    continue
                filepath = os.path.join(root, file)
                # Compute relative path inside the zip
                relpath = os.path.relpath(filepath, source_dir)
                z.write(filepath, relpath)
                
    print(f"Add-on package created successfully at: {addon_filename}")

if __name__ == "__main__":
    main()

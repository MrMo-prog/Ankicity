#!/usr/bin/env python3
import os
from PIL import Image

def process_file(filepath):
    print(f"Processing: {filepath}")
    img = Image.open(filepath).convert("RGBA")
    w, h = img.size
    pixels = img.load()
    
    # Chroma key green definition
    def is_green_bg(r, g, b, a):
        if a == 0:
            return True
        return g > 180 and g - r > 100 and g - b > 100

    # Flood-fill from borders
    visited = [[False for _ in range(h)] for _ in range(w)]
    queue = []
    
    # Add edges
    for x in range(w):
        queue.append((x, 0))
        queue.append((x, h - 1))
        visited[x][0] = True
        visited[x][h - 1] = True
    for y in range(h):
        queue.append((0, y))
        queue.append((w - 1, y))
        visited[0][y] = True
        visited[w - 1][y] = True
        
    head = 0
    while head < len(queue):
        cx, cy = queue[head]
        head += 1
        
        r, g, b, a = pixels[cx, cy]
        if is_green_bg(r, g, b, a):
            pixels[cx, cy] = (0, 0, 0, 0)
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < w and 0 <= ny < h:
                    if not visited[nx][ny]:
                        visited[nx][ny] = True
                        queue.append((nx, ny))
                        
    # Check if this is tavern level 1 or 2
    filename = os.path.basename(filepath)
    if "TAVERN_lvl1" in filename or "TAVERN_lvl2" in filename or "tavern_t1" in filename or "tavern_t2" in filename or "lvl1 tavern" in filename or "lvl2 tavern" in filename:
        print(f"Cutting {filename} vertically in half...")
        for y in range(h // 2):
            for x in range(w):
                pixels[x, y] = (0, 0, 0, 0)
                
    img.save(filepath, "PNG")
    print(f"Saved: {filepath}")

def main():
    dirs = [
        "/Users/moritzmuss/Programmieren/Ankicity/images",
        "/Users/moritzmuss/Programmieren/Ankicity/web/images"
    ]
    
    for d in dirs:
        if not os.path.exists(d):
            continue
        for filename in os.listdir(d):
            if filename.endswith(".png") and filename != "background.png":
                filepath = os.path.join(d, filename)
                process_file(filepath)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import os
import sys
from PIL import Image

def slice_expansion():
    # Source generated expansion sheet path
    src_sheet = "/Users/moritzmuss/.gemini/antigravity-ide/brain/fe894d79-e438-4045-8fdd-e26aa839a426/pixel_expansion_1781616736942.png"
    
    # Target images folder
    dest_dir = "/Users/moritzmuss/Programmieren/Ankicity/web/images"
    os.makedirs(dest_dir, exist_ok=True)
    
    if not os.path.exists(src_sheet):
        print(f"Error: Spritesheet not found at {src_sheet}")
        sys.exit(1)
        
    print(f"Loading expansion spritesheet from {src_sheet}...")
    img = Image.open(src_sheet)
    
    # 5 columns, 4 rows
    width, height = img.size
    cell_w = width / 5
    cell_h = height / 4
    
    print(f"Image size: {width}x{height}, cell size: {cell_w}x{cell_h}")
    
    sprite_map = {
        "straw_field_t1": (0, 0),
        "straw_field_t2": (1, 0),
        "straw_field_t3": (2, 0),
        "straw_field_t4": (3, 0),
        "sawmill_t4": (4, 0),
        "quarry_t4": (0, 1),
        "gold_mine_t1": (1, 1),
        "gold_mine_t2": (2, 1),
        "gold_mine_t3": (3, 1),
        "gold_mine_t4": (4, 1),
        "town_hall_t4": (0, 2),
        "city_wall_single": (1, 2),
        "city_wall_h": (2, 2),
        "city_wall_v": (3, 2),
        "city_wall_cross": (4, 2),
        "garden_flowers": (0, 3),
        "garden_hedge": (1, 3),
        "garden_pond": (2, 3)
    }
    
    import collections
    def clean_background(img_to_clean):
        img_rgba = img_to_clean.convert("RGBA")
        w, h = img_rgba.size
        pxs = img_rgba.load()
        
        visited = [[False for _ in range(h)] for _ in range(w)]
        queue = collections.deque()
        
        # Add all border pixels of this crop to queue
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
            
        def is_bg(x, y):
            r, g, b, a = pxs[x, y]
            if a == 0:
                return True
            if max(r, g, b) - min(r, g, b) > 15:
                return False
            avg = (r + g + b) / 3.0
            if (60 <= avg <= 95) or (190 <= avg <= 250):
                return True
            return False

        bg_pxs = set()
        while queue:
            cx, cy = queue.popleft()
            if is_bg(cx, cy):
                bg_pxs.add((cx, cy))
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        if not visited[nx][ny]:
                            visited[nx][ny] = True
                            queue.append((nx, ny))
                            
        for x, y in bg_pxs:
            pxs[x, y] = (0, 0, 0, 0)
            
        return img_rgba
    
    for name, (col, row) in sprite_map.items():
        # Define crop box
        left = int(col * cell_w)
        top = int(row * cell_h)
        right = int(left + cell_w)
        bottom = int(top + cell_h)
        
        # Crop
        cropped = img.crop((left, top, right, bottom))
        
        # Resize to standard square (256x256)
        cropped = cropped.resize((256, 256), Image.Resampling.LANCZOS)
        
        # Clean background checkerboard
        cropped = clean_background(cropped)
        
        dest_path = os.path.join(dest_dir, f"{name}.png")
        cropped.save(dest_path, "PNG")
        print(f"Saved {name}.png to {dest_path}")
        
    print("Expansion slicing complete!")

if __name__ == "__main__":
    slice_expansion()

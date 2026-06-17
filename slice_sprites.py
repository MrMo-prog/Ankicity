#!/usr/bin/env python3
import os
import sys
import shutil
from PIL import Image

def slice_sprites():
    # Source generated spritesheet path
    src_sheet = "/Users/moritzmuss/.gemini/antigravity-ide/brain/fe894d79-e438-4045-8fdd-e26aa839a426/pixel_spritesheet_1781615064606.png"
    
    # Target images folder
    dest_dir = "/Users/moritzmuss/Programmieren/Ankicity/web/images"
    os.makedirs(dest_dir, exist_ok=True)
    
    if not os.path.exists(src_sheet):
        print(f"Error: Spritesheet not found at {src_sheet}")
        sys.exit(1)
        
    print(f"Loading spritesheet from {src_sheet}...")
    img = Image.open(src_sheet)
    
    # Verify dimensions (expecting 1024x1024)
    width, height = img.size
    print(f"Image dimensions: {width}x{height}")
    
    # Slicing config
    # 4x4 grid, each cell is 256x256 pixels
    cell_w = width // 4
    cell_h = height // 4
    
    sprite_map = {
        "grass": (0, 0, 1, 1),
        "straw_hut": (1, 0, 1, 1),
        "timber_house": (2, 0, 1, 1),
        "stone_villa": (3, 0, 1, 1),
        "marketplace": (0, 1, 1, 1),
        "sawmill_t1": (1, 1, 1, 1),
        "sawmill_t2": (2, 1, 1, 1),
        "sawmill_t3": (3, 1, 1, 1),
        "quarry_t1": (0, 2, 1, 1),
        "quarry_t2": (1, 2, 1, 1),
        "quarry_t3": (2, 2, 1, 1),
        "town_hall_t1": (3, 2, 1, 1),
        # Town Hall T2 and T3 span 2 columns, we'll crop and scale them to a square
        "town_hall_t2": (0, 3, 2, 1),
        "town_hall_t3": (2, 3, 2, 1),
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
    
    for name, (col, row, col_span, row_span) in sprite_map.items():
        # Define crop box
        left = col * cell_w
        top = row * cell_h
        right = left + col_span * cell_w
        bottom = top + row_span * cell_h
        
        # Crop
        cropped = img.crop((left, top, right, bottom))
        
        # Resize to square (256x256) if it spans multiple columns to fit our 1:1 grid cells
        if col_span > 1 or row_span > 1:
            cropped = cropped.resize((256, 256), Image.Resampling.LANCZOS)
        else:
            cropped = cropped.resize((256, 256), Image.Resampling.LANCZOS)
            
        # Clean background checkerboard for all sprites
        cropped = clean_background(cropped)
            
        dest_path = os.path.join(dest_dir, f"{name}.png")
        cropped.save(dest_path, "PNG")
        print(f"Saved {name}.png to {dest_path}")
        
    # Copy the main spritesheet to the workspace just in case
    shutil.copy(src_sheet, os.path.join(dest_dir, "spritesheet.png"))
    print("Slicing complete!")

if __name__ == "__main__":
    slice_sprites()

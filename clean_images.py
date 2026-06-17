import os
import glob
from PIL import Image

src_dir = '/Users/moritzmuss/.gemini/antigravity-ide/brain/fe894d79-e438-4045-8fdd-e26aa839a426'
dest_dir = 'web/images'

buildings = ['straw_hut', 'timber_house', 'stone_villa', 'sawmill', 'quarry', 'gold_mine', 'town_hall_t1', 'town_hall_t2', 'town_hall_t3', 'town_hall_t4']

for b in buildings:
    files = glob.glob(os.path.join(src_dir, b + '_*.png'))
    if not files:
        print('No generated image found for ' + b)
        continue
    
    latest_file = max(files, key=os.path.getmtime)
    print('Processing ' + latest_file)
    
    img = Image.open(latest_file).convert('RGBA')
    pixels = img.load()
    width, height = img.size
    
    for y in range(height):
        for x in range(width):
            r, g, b_color, a = pixels[x, y]
            if (abs(r-204)<15 and abs(g-204)<15 and abs(b_color-204)<15) or (r>230 and g>230 and b_color>230):
                pixels[x, y] = (0, 0, 0, 0)
            elif (abs(r-102)<15 and abs(g-102)<15 and abs(b_color-102)<15):
                pixels[x, y] = (0, 0, 0, 0)
                
    dest_path = os.path.join(dest_dir, b + '.png')
    img.save(dest_path)
    print('Saved to ' + dest_path)

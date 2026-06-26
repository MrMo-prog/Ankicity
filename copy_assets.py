import os
import shutil

src_dir = '/Users/moritzmuss/Programmieren/Ankicity/new_images'
dest_dir = '/Users/moritzmuss/Programmieren/Ankicity/web/images'

mapping = {
    'house': 'HOUSE',
    'quarry': 'QUARRY',
    'sawmill': 'SAWMILL',
    'townhall': 'TOWNHALL',
    'tavern': 'TAVERN',
    'windmill': 'STRAW_MILL',
    'goldmine': 'GOLD_MINE'
}

for filename in os.listdir(src_dir):
    if filename.endswith('.png'):
        if filename == 'background.png':
            shutil.copy(os.path.join(src_dir, filename), os.path.join(dest_dir, filename))
            continue
        
        # Parse 'lvlX name.png'
        parts = filename.replace('.png', '').split(' ')
        if len(parts) == 2 and parts[0].startswith('lvl'):
            lvl = parts[0]
            name = parts[1]
            if name in mapping:
                new_name = f"{mapping[name]}_{lvl}.png"
                shutil.copy(os.path.join(src_dir, filename), os.path.join(dest_dir, new_name))
                print(f"Copied {filename} to {new_name}")
            else:
                print(f"Warning: unknown building name {name} in {filename}")

import os
from PIL import Image
import numpy as np

def is_white_image(image_path):
    try:
        with Image.open(image_path) as img:
            img_array = np.array(img)
            if img_array.ndim == 3 and np.all(img_array == 255):
                return True
            elif img_array.ndim == 4 and np.all(img_array[:, :, :3] == 255) and np.all(img_array[:, :, 3] == 255):
                return True
            else:
                return False
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return False

def process_png_files(directory):
    deleted_files = []

    for filename in os.listdir(directory):
        if filename.endswith('.png'):
            filepath = os.path.join(directory, filename)
            if is_white_image(filepath):
                os.remove(filepath)
                deleted_files.append(filename)
                print(f"Deleted: {filename}")

    if not deleted_files:
        print("No white images found.")
    else:
        print("\nDeleted files:")
        for file in deleted_files:
            print(file)

directory_path = r'inference_png'
process_png_files(directory_path)

import os
import re
from tqdm import tqdm

def round_floats_in_path(path_data):
    def round_match(match):
        number = float(match.group(0))
        return str(round(number))
    rounded_path = re.sub(r'-?\d+\.\d+', round_match, path_data)
    return rounded_path

def process_svg(svg_content):
    path_pattern = re.compile(r'<path[^>]* d="([^"]+)"[^>]*>')
    def replace_path(match):
        original_path_tag = match.group(0)
        path_data = match.group(1)
        rounded_path_data = round_floats_in_path(path_data)
        return original_path_tag.replace(path_data, rounded_path_data)

    processed_svg = re.sub(path_pattern, replace_path, svg_content)
    return processed_svg

def batch_process_svgs(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    try:
        files = os.listdir(input_dir)

        svg_files = [f for f in files if f.lower().endswith('.svg')]
        if not svg_files:
            print(f"Warning: no SVG files found in folder '{input_dir}'.")
            return
    except FileNotFoundError:
        print(f"Error: input folder '{input_dir}' not found. Please check the path.")
        return

    print(f"Found {len(svg_files)} SVG files, starting processing...")

    for filename in tqdm(svg_files, desc="Progress"):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f_in:
                content = f_in.read()
            
            processed_content = process_svg(content)
            
            with open(output_path, 'w', encoding='utf-8') as f_out:
                f_out.write(processed_content)
        
        except Exception as e:
            print(f"\n--- Failed processing file: {filename} ---")
            print(f"Error: {e}")

    print(f"\nAll files processed. Results saved to '{output_dir}'")

if __name__ == "__main__":
    input_folder = r'omnisvgs'
    output_folder = r'omnisvgs_int'
    
    if 'FILL_ME' in input_folder or 'FILL_ME' in output_folder:
        print("="*50)
        print("Please update 'input_folder' and 'output_folder' paths in the code before running.")
        print("="*50)
    else:
        batch_process_svgs(input_folder, output_folder)


import os
import re
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import tostring, register_namespace
from tqdm import tqdm  # show progress bar

def scale_svg(svg_content, original_viewbox_str, new_viewbox_size):
    try:
        root = ET.fromstring(svg_content.encode('utf-8'))

        namespace = "http://www.w3.org/2000/svg"
        register_namespace('', namespace)
        
        root.set('viewBox', f"0 0 {new_viewbox_size} {new_viewbox_size}")

        original_size = float(original_viewbox_str.split()[2]) 
        new_size = float(new_viewbox_size)
        
        if original_size == new_size:
            return tostring(root, encoding='unicode')

        scale_factor = original_size / new_size

        path_regex = re.compile(r'([MLHVCSQTAZmlhvcsqtaz])|([+-]?\d*\.?\d+)')

        for path in root.findall(f'.//{{{namespace}}}path'):
            d = path.attrib.get('d', '')
            if not d:
                continue

            new_d_parts = []
            
            for match in path_regex.finditer(d):
                command, number_str = match.groups()

                if command:
                    new_d_parts.append(command)
                elif number_str:
                    scaled_number = round(float(number_str) / scale_factor)
                    new_d_parts.append(str(scaled_number))

            path.set('d', ' '.join(new_d_parts))
        return tostring(root, encoding='unicode')

    except ET.ParseError as e:
        print(f"XML parse error: {e}")
        return None 

def batch_process_svgs(input_folder, output_folder, original_viewbox, new_viewbox):
    """
    Batch process all SVG files in a folder.
    """
    os.makedirs(output_folder, exist_ok=True)
    
    try:
        svg_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.svg')]
        if not svg_files:
            print(f"Warning: no SVG files found in folder '{input_folder}'.")
            return
    except FileNotFoundError:
        print(f"Error: input folder '{input_folder}' not found. Please check the path.")
        return
    
    print(f"Found {len(svg_files)} SVG files, starting processing...")

    for filename in tqdm(svg_files, desc="Progress"):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, filename)

        try:
            with open(input_path, 'r', encoding='utf-8') as file:
                svg_content = file.read()
            
            scaled_svg = scale_svg(svg_content, original_viewbox, new_viewbox)
            
            if scaled_svg:
                with open(output_path, 'w', encoding='utf-8') as file:
                    file.write(scaled_svg)
            else:
                print(f"\nFile {filename} failed to process, skipped.")

        except Exception as e:
            print(f"\nUnexpected error while processing file {filename}: {e}")
    
    print(f"\nProcessing complete! All files saved to folder '{output_folder}'.")


if __name__ == "__main__":
    input_folder = r"svgs"
    output_folder = r"svgen_200"

    original_viewbox = "0 0 1024 1024"
    new_viewbox = "200"
    
    if 'FILL_ME' in input_folder or 'FILL_ME' in output_folder:
        print("="*60)
        print(">> Please update 'input_folder' and 'output_folder' paths in the code <<")
        print("="*60)
    else:
        batch_process_svgs(input_folder, output_folder, original_viewbox, new_viewbox)

    print("\nTip: If you see 'ModuleNotFoundError' indicating 'tqdm' is missing,")
    print("please run this command in your terminal to install it: pip install tqdm")
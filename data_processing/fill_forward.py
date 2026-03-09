import os
import xml.etree.ElementTree as ET
from tqdm import tqdm

def reorder_attributes_in_place(file_path):
    try:
        ET.register_namespace('', "http://www.w3.org/2000/svg")
        tree = ET.parse(file_path)
        root = tree.getroot()
        was_modified = False

        for elem in root.iter():
            if 'd' in elem.attrib and 'fill' in elem.attrib:
                
                original_attrs = elem.attrib
                keys = list(original_attrs.keys())
                try:
                    d_index = keys.index('d')
                    fill_index = keys.index('fill')
                    if fill_index < d_index:
                        continue
                except ValueError:
                    continue

                new_attrs_corrected = {}
                new_attrs_corrected['fill'] = original_attrs.pop('fill')
                new_attrs_corrected['d'] = original_attrs.pop('d')
                new_attrs_corrected.update(original_attrs)

                elem.attrib = new_attrs_corrected
                was_modified = True

        if was_modified:
            tree.write(file_path, encoding='utf-8', xml_declaration=False)
        
        return was_modified

    except (ET.ParseError, Exception) as e:
        print(f"\nError processing file {os.path.basename(file_path)}: {e}")
        return False


def process_folder_in_place(target_folder):
    if not os.path.isdir(target_folder):
        print(f"Error: folder '{target_folder}' does not exist.")
        return

    svg_files = [f for f in os.listdir(target_folder) if f.lower().endswith('.svg')]
    
    if not svg_files:
        print(f"No SVG files found in folder '{target_folder}'.")
        return

    print(f"--- Target folder: {target_folder}")
    print(f"--- Ready to modify {len(svg_files)} SVG files in place ---")
    
    modified_count = 0
    progress_bar = tqdm(svg_files, desc="In-place processing", unit="files")
    
    for filename in progress_bar:
        file_path = os.path.join(target_folder, filename)
        progress_bar.set_postfix_str(filename, refresh=True)
        
        if reorder_attributes_in_place(file_path):
            modified_count += 1
            
    print("\n--- Processing complete ---")
    print(f"Total files checked: {len(svg_files)}")
    print(f"Modified and saved: {modified_count}")


if __name__ == "__main__":
    target_folder = r"omnisvgs_int"
    process_folder_in_place(target_folder)
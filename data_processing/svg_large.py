import os
import re
from xml.etree import ElementTree as ET
from tqdm import tqdm
ET.register_namespace('', "http://www.w3.org/2000/svg")

def scale_svg(svg_content, new_size):
    """
    Automatically detect the SVG viewBox, scale it proportionally to a new viewBox,
    round all coordinates to integers, and update the SVG header.
    """
    try:
        root = ET.fromstring(svg_content)
    except ET.ParseError as e:
        print(f"XML parse error: {e}")
        return None

    original_viewbox_str = root.get('viewBox')
    if not original_viewbox_str:
        width = root.get('width')
        height = root.get('height')
        if width and height:
            original_viewbox_str = f"0 0 {width} {height}"
        else:
            return None
    
    try:
        min_x, min_y, old_width, old_height = map(float, re.split(r'[ ,]+', original_viewbox_str))
    except (ValueError, IndexError):
        return None

    if old_width <= 0 or old_height <= 0:
        return None

    scale_x = new_size / old_width
    scale_y = new_size / old_height
    scale_factor = min(scale_x, scale_y)
    
    trans_x = (new_size - old_width * scale_factor) / 2
    trans_y = (new_size - old_height * scale_factor) / 2
    
    root.attrib.clear()
    root.set('viewBox', f"0 0 {new_size} {new_size}")

    attrs_to_scale = {
        'rect': ['x', 'y', 'width', 'height', 'rx', 'ry'],
        'circle': ['cx', 'cy', 'r'],
        'ellipse': ['cx', 'cy', 'rx', 'ry'],
        'line': ['x1', 'y1', 'x2', 'y2'],
    }

    for tag, attrs in attrs_to_scale.items():
        for elem in root.findall(f".//{{http://www.w3.org/2000/svg}}{tag}"):
            for attr in attrs:
                if elem.get(attr) is not None:
                    original_val = float(elem.get(attr))
                    if 'x' in attr or 'y' in attr or 'c' in attr:
                        if 'x' in attr or 'cx' in attr:
                            scaled_val = (original_val - min_x) * scale_factor + trans_x
                        else:
                            scaled_val = (original_val - min_y) * scale_factor + trans_y
                    else:
                        scaled_val = original_val * scale_factor
                    
                    elem.set(attr, str(round(scaled_val)))
    
    path_regex = re.compile(r'([MLHVCSQTAZmlhvcsqtaz])|([-]?\d*\.?\d+(?:[eE][-+]?\d+)?)')
    
    for path in root.findall(f".//{{http://www.w3.org/2000/svg}}path"):
        d = path.get('d', '')
        if not d: continue
        new_d = []
        is_x = True
        command = ''
        
        for match in path_regex.finditer(d):
            cmd, num_str = match.groups()
            if cmd:
                new_d.append(cmd)
                command = cmd.upper()
                is_x = False if command == 'V' else True
            elif num_str:
                num = float(num_str)
                if command.isupper():
                    if is_x:
                        scaled_num = (num - min_x) * scale_factor + trans_x
                    else:
                        scaled_num = (num - min_y) * scale_factor + trans_y
                else:
                    scaled_num = num * scale_factor
                
                new_d.append(str(round(scaled_num)))

                if command not in ['H', 'V']:
                    is_x = not is_x

        path.set('d', ' '.join(new_d))

    for poly in root.findall(f".//{{http://www.w3.org/2000/svg}}polyline") + root.findall(f".//{{http://www.w3.org/2000/svg}}polygon"):
        points_str = poly.get('points', '')
        points = re.split(r'[ ,]+', points_str.strip())
        new_points = []
        for i in range(0, len(points), 2):
            if i + 1 < len(points) and points[i] and points[i+1]:
                x = float(points[i])
                y = float(points[i+1])
                new_x = (x - min_x) * scale_factor + trans_x
                new_y = (y - min_y) * scale_factor + trans_y
                new_points.extend([str(round(new_x)), str(round(new_y))])
        poly.set('points', ' '.join(new_points))

    return ET.tostring(root, encoding='unicode', xml_declaration=False)

def process_svgs_in_folder(input_folder, output_folder, new_viewbox_size):
    os.makedirs(output_folder, exist_ok=True)
    
    filenames = [f for f in os.listdir(input_folder) if f.lower().endswith('.svg')]
    
    if not filenames:
        print(f"No SVG files found in folder '{input_folder}'.")
        return

    for filename in tqdm(filenames, desc="Processing SVG files"):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, filename)

        try:
            with open(input_path, 'r', encoding='utf-8') as file:
                svg_content = file.read()
            
            scaled_svg = scale_svg(svg_content, new_viewbox_size)
            
            if scaled_svg:
                with open(output_path, 'w', encoding='utf-8') as file:
                    file.write(scaled_svg)
            else:
                tqdm.write(f"Skipped {filename} (cannot process or missing viewBox)")
        except Exception as e:
            tqdm.write(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    input_folder = r"llm4svg_files_color_changed"
    output_folder = r"llm4svg_files_color_changed_200_int"
    new_viewbox_size = 200

    process_svgs_in_folder(input_folder, output_folder, new_viewbox_size)
    print("\nProcessing complete!")

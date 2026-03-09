import os
from xml.dom.minidom import parse
from deepsvg.svglib.svg import SVG
from tqdm import tqdm
from deepsvg.svglib.svg_command import SVGCommandMove, SVGCommandLine, SVGCommandBezier, SVGCommandArc
from deepsvg.svglib.svg_path import SVGPath
import numpy as np
import pdb
def arc_to_bezier(arc):
    return arc.to_beziers()

def circle_to_path(cx, cy, r):
    d = 2 * (np.sqrt(2) - 1) / 3 

    beziers = [
        f"M {cx + r} {cy}",
        f"C {cx + r} {cy + d * r} {cx + d * r} {cy + r} {cx} {cy + r}",
        f"C {cx - d * r} {cy + r} {cx - r} {cy + d * r} {cx - r} {cy}",
        f"C {cx - r} {cy - d * r} {cx - d * r} {cy - r} {cx} {cy - r}",
        f"C {cx + d * r} {cy - r} {cx + r} {cy - d * r} {cx + r} {cy}",
    ]
    
    return " ".join(beziers)

def create_svg_path_data(svg, doc):
    path_data_list = []
    # Process path elements
    for path_group in svg.svg_path_groups:
        path_data = []
        for path in path_group.paths:
            for i, command in enumerate(path.all_commands()):
                if isinstance(command, SVGCommandMove):
                    if i == 0 or not path_data or not path_data[-1].startswith("M"):
                        path_data.append(f"M {command.end_pos.x} {command.end_pos.y}")
                elif isinstance(command, SVGCommandLine):
                    path_data.append(f"L {command.end_pos.x} {command.end_pos.y}")
                elif isinstance(command, SVGCommandBezier):
                    c1 = command.control1
                    c2 = command.control2
                    end = command.end_pos
                    path_data.append(f"C {c1.x} {c1.y} {c2.x} {c2.y} {end.x} {end.y}")
                elif isinstance(command, SVGCommandArc):
                    beziers = arc_to_bezier(command)
                    for bezier in beziers:
                        c1 = bezier.control1
                        c2 = bezier.control2
                        end = bezier.end_pos
                        path_data.append(f"C {c1.x} {c1.y} {c2.x} {c2.y} {end.x} {end.y}")
        path_data_list.append(" ".join(path_data))
    
    circle_elements = doc.getElementsByTagName("circle")
    for circle in circle_elements:
        cx = float(circle.getAttribute("cx"))
        cy = float(circle.getAttribute("cy"))
        r = float(circle.getAttribute("r"))
        path_data = circle_to_path(cx, cy, r)
        path_data_list.append(path_data)

    return path_data_list

def replace_svg_path_data(original_svg_file, path_data_list, output_file, doc):
    path_elements = doc.getElementsByTagName("path")
    circle_elements = doc.getElementsByTagName("circle")

    total_elements = len(path_elements) + len(circle_elements)
    
    if len(path_data_list) != total_elements:
        raise ValueError("Length of path data list does not match the number of <path> and <circle> elements in the SVG file.")

    for i, path_element in enumerate(path_elements):
        path_element.setAttribute("d", path_data_list[i])

    # Process converted path data for circles
    for i, circle_element in enumerate(circle_elements, start=len(path_elements)):
        new_path = doc.createElement("path")
        new_path.setAttribute("d", path_data_list[i])
        circle_element.parentNode.replaceChild(new_path, circle_element)

    with open(output_file, "w") as f:
        f.write(doc.documentElement.toxml())

def process_svg_files(input_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder, exist_ok=True)

    svg_files = [f for f in os.listdir(input_folder) if f.endswith('.svg')]

    for svg_file in tqdm(svg_files, desc="Processing SVG files"):
        input_file = os.path.join(input_folder, svg_file)
        output_file = os.path.join(output_folder, svg_file)

        if os.path.getsize(input_file) == 0:
            print(f"File {input_file} is empty, skipping.")
            continue

        try:
            doc = parse(input_file)
            svg = SVG.load_svg(input_file)
            path_data_list = create_svg_path_data(svg, doc)

            replace_svg_path_data(input_file, path_data_list, output_file, doc)
        except Exception as e:
            print(f"Error processing file {input_file}: {e}")

if __name__ == "__main__":
    input_folder = r"llm4svg_files_color_final"
    output_folder = r"llm4svg_files_color_changed"
    process_svg_files(input_folder, output_folder)
    print("All files processed.")

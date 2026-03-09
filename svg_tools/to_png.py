import os
import cairosvg

def convert_svg_to_png(input_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    for filename in os.listdir(input_folder):
        if filename.endswith('.svg'):
            svg_path = os.path.join(input_folder, filename)
            png_filename = filename.replace('.svg', '.png')
            png_path = os.path.join(output_folder, png_filename)

            try:
                cairosvg.svg2png(url=svg_path, write_to=png_path, output_width=200, output_height=200,background_color="white")
                print(f'Converted {svg_path} to {png_path}')
            except Exception as e:
                print(f'Error converting {svg_path}: {e}')
                print(f'Skipping {svg_path}')

input_folder = r'your_svg_folder'
output_folder = r'your_png_folder'
convert_svg_to_png(input_folder, output_folder)
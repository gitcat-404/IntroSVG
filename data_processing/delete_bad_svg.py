import os

def sync_png_with_svg(svg_folder, png_folder):
    svg_files = {os.path.splitext(f)[0] for f in os.listdir(svg_folder) if f.endswith('.png')}
    
    for png_file in os.listdir(png_folder):
        if png_file.endswith('.svg'):
            png_name = os.path.splitext(png_file)[0]
            if png_name not in svg_files:
                os.remove(os.path.join(png_folder, png_file))
                print(f"Deleted: {png_file}")

# Example usage
svg_folder_path = r'PNG'
png_folder_path = r'SVG'

sync_png_with_svg(svg_folder_path, png_folder_path)

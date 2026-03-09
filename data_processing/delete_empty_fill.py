import os

def delete_svgs_with_empty_fill(folder_path):
    """
    Scan the specified folder and delete all SVG files that contain fill="".
    """
    if not os.path.isdir(folder_path):
        print(f"Error: folder '{folder_path}' does not exist.")
        return

    deleted_count = 0

    print("Starting scan...")
    for filename in os.listdir(folder_path):
        if filename.lower().endswith('.svg'):
            file_path = os.path.join(folder_path, filename)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 'fill=""' in content:
                    print(f"Detected empty fill: {filename}")
                    
                    os.remove(file_path)
                    
                    print(f" -> Deleted: {filename}")
                    deleted_count += 1

            except Exception as e:
                print(f"Error processing file {filename}: {e}")
    
    print("\nScan complete.")
    if deleted_count > 0:
        print(f"Total deleted files: {deleted_count}.")
    else:
        print("No files to delete were found.")

if __name__ == "__main__":
    SVG_FOLDER_PATH = r'omnisvgs_int'  
    
    print(f"Target folder: {SVG_FOLDER_PATH}")
    delete_svgs_with_empty_fill(SVG_FOLDER_PATH)
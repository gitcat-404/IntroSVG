import os

def remove_xml_tag_from_svgs(folder_path):
    tag_to_remove = "<?xml version='1.0' encoding='utf-8'?>"
    
    if not os.path.isdir(folder_path):
        print(f"Error: folder '{folder_path}' does not exist.")
        return

    print(f"Start processing folder: {folder_path}")

    for filename in os.listdir(folder_path):
        if filename.endswith(".svg"):
            file_path = os.path.join(folder_path, filename)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                if content.strip().startswith(tag_to_remove):
                    new_content = content.replace(tag_to_remove, '', 1).lstrip()
                    
                    with open(file_path, 'w', encoding='utf-8') as file:
                        file.write(new_content)
                        
                else:
                    print(f"No matching tag found at start of file {filename}, skipped.")

            except Exception as e:
                print(f"Error processing file {filename}: {e}")

    print("Processing complete!")

target_folder = r'omnisvgs_int'
remove_xml_tag_from_svgs(target_folder)
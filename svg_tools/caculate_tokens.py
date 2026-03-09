import os
from transformers import AutoTokenizer

model_name_or_path = 'Qwen2.5-3B-Instruct'

tokenizer = AutoTokenizer.from_pretrained(model_name_or_path)

svg_folder_path = 'SVG/test/omnisvg'


token_counts = []


for filename in os.listdir(svg_folder_path):
    if filename.endswith('.svg'):
        file_path = os.path.join(svg_folder_path, filename)
        
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        tokens = tokenizer.encode(content, truncation=False, add_special_tokens=False)
        token_counts.append(len(tokens))

average_tokens = sum(token_counts) / len(token_counts) if token_counts else 0
print(svg_folder_path)
print(f"The average number of tokens in the SVG files: {average_tokens:.2f}")

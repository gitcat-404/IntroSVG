import json
import os
import pandas as pd
from tqdm import tqdm
import ast  # To safely evaluate string representation of lists

def format_suggestions(suggestions_str):
    """
    Formats the suggestions string into a readable numbered list.
    Attempts to parse it if it's a string representation of a list.
    """
    try:
        # Attempt to parse the string as a Python list literal
        suggestions_list = ast.literal_eval(suggestions_str)
        if isinstance(suggestions_list, list):
            # Format as a numbered list
            return "\n".join(f"{i+1}. {item}" for i, item in enumerate(suggestions_list))
        else:
            # If it's not a list after evaluation, return the original string
            return suggestions_str
    except (ValueError, SyntaxError, TypeError):
        # If it's not a valid list literal or None/NaN, return the original string
        # Handle potential NaN values by converting to string first
        return str(suggestions_str)

def create_json_from_csv(csv_path, svg_folder_path, output_json_path, s_gold_folder_path):
    """
    Create a JSON dataset from CSV and SVG files for training an SVG refinement model.

    Args:
        csv_path (str): Path to a CSV containing columns 'id', 'critique', 'suggestions', 'desc'.
        svg_folder_path (str): Folder containing draft SVG files named {id}.svg.
        output_json_path (str): Output JSON file path.
        s_gold_folder_path (str): Folder containing high-quality SVG files.
    """
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"Error: CSV file not found at '{csv_path}'")
        return
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    # Check required columns
    required_columns = ['id', 'critique', 'suggestions', 'desc']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"Error: CSV file is missing required columns: {', '.join(missing_columns)}")
        return

    data = []
    print(f"Start processing CSV: {csv_path}")
    print(f"Looking for SVG files at: {svg_folder_path}")
    print(f"Looking for high-quality SVG files at: {s_gold_folder_path}")

    # Use tqdm to create a progress bar
    for index, row in tqdm(df.iterrows(), total=df.shape[0], desc="Processing SVG files"):
        svg_id = str(row['id'])  # Ensure ID is a string
        origin_prompt = str(row['desc'])
        critique = str(row['critique'])
        # Handle NaN/None values to ensure suggestions is a string
        suggestions_raw = row['suggestions']
        suggestions_str = str(suggestions_raw) if pd.notna(suggestions_raw) else ""

        svg_file_path = os.path.join(svg_folder_path, f"{svg_id}.svg")
        s_gold_file_path = os.path.join(s_gold_folder_path, f"{svg_id}.svg")

        # Check that the corresponding SVG files exist
        if os.path.exists(svg_file_path) and os.path.exists(s_gold_file_path):
            try:
                with open(svg_file_path, 'r', encoding='utf-8') as svg_file:
                    svg_draft_content = svg_file.read().strip()

                # Skip this entry if SVG content is empty
                if not svg_draft_content:
                    continue

                # Read the high-quality SVG content
                with open(s_gold_file_path, 'r', encoding='utf-8') as s_gold_file:
                    s_gold_content = s_gold_file.read().strip()

                # Format suggestions
                formatted_suggestions = format_suggestions(suggestions_str)

                # Build user prompt
                user_prompt = f"""Please analyze all the information provided below and generate a final, high-quality SVG code. The original design goal was: "{origin_prompt}"; a draft SVG code that needs improvement is as follows: ```xml
{svg_draft_content}
```; an expert critique of this draft is: "{critique}"; and the specific modification suggestions are: {formatted_suggestions}. Please strictly follow these suggestions to improve the draft and directly output the final, refined SVG code."""

                # Build JSON entry
                message_entry = {
                    "messages": [
                        {
                            "content": user_prompt,
                            "role": "user"
                        },
                        {
                            "content": s_gold_content,  # Use high-quality SVG code
                            "role": "assistant"
                        }
                    ],
                    "images": []  # Keep as empty list
                }

                data.append(message_entry)

            except Exception as e:
                print(f"\nError processing file '{svg_file_path}' or '{s_gold_file_path}': {e}")

    # Check if any data was generated
    if not data:
        print("\nError: failed to generate any valid JSON data. Please check the CSV contents and SVG file paths.")
        return

    # Write the entire list to the output JSON file
    try:
        with open(output_json_path, 'w', encoding='utf-8') as json_file:
            # indent=2 for readability
            json.dump(data, json_file, ensure_ascii=False, indent=2)
        print(f"\nDone! Processed {len(data)} valid records. JSON saved to: {output_json_path}")
    except Exception as e:
        print(f"\nError writing JSON file: {e}")

# --- Example usage ---
# Ensure the paths below are correct
csv_path = r'merged_inference_file.csv'
svg_folder_path = r'all-test'
s_gold_folder_path = r'inference_svg'
output_json_path = r'train.json'

# --- Generate data ---
create_json_from_csv(csv_path, svg_folder_path, output_json_path, s_gold_folder_path)

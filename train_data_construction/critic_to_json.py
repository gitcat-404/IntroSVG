import json
import os
import pandas as pd
from tqdm import tqdm
import base64 # Keep if your VLM framework requires base64-encoded images; otherwise remove

# --- Prompt template for critic model (updated) ---
CRITIC_USER_PROMPT_TEMPLATE ="""You are a professional SVG design critic. Please analyze the input AI-generated SVG draft<image> according to the "Original Design Prompt".

**Original Design Prompt**: "{origin_prompt}"

Your task is to output a structured critique report, strictly following the JSON format below. The JSON object must contain three fields:
1. "score": A float between 0.0 and 10.0, for a comprehensive evaluation of the draft's quality and alignment.
2. "critique": A comprehensive evaluation explaining the extent to which the draft meets the original prompt, and pointing out its main differences and shortcomings in aesthetics, color, and geometric construction compared to an ideal version.
3. "suggestions": A single string. If the draft's quality is high, this string should be an affirmative statement, such as "The overall quality is excellent, no changes are needed." Otherwise, it should contain 2 to 4 specific, actionable SVG modification suggestions, presented as a numbered list within this string (e.g., "1. Suggestion A\n2. Suggestion B")."""
def create_critique_training_data(csv_path_prompts, csv_path_results, draft_image_folder, output_json_path, use_base64=False):
    try:
        df_prompts = pd.read_csv(csv_path_prompts)
        df_results = pd.read_csv(csv_path_results)
    except FileNotFoundError as e:
        print(f"Error: CSV file not found: {e}")
        return
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    if 'id' not in df_prompts.columns or 'desc' not in df_prompts.columns:
        print(f"Error: prompt CSV '{csv_path_prompts}' is missing 'id' or 'desc'.")
        return
    if 'id' not in df_results.columns or 'result' not in df_results.columns:
        print(f"Error: result CSV '{csv_path_results}' is missing 'id' or 'result'.")
        return

    try:
        df_prompts['id'] = df_prompts['id'].astype(str)
        df_results['id'] = df_results['id'].astype(str)
        df_merged = pd.merge(df_prompts[['id', 'desc']], df_results[['id', 'result']], on='id', how='inner')
    except Exception as e:
        print(f"Error merging CSV files: {e}")
        return

    if df_merged.empty:
        print("Error: merged DataFrame is empty. Please check 'id' column alignment between CSV files.")
        return

    data = []
    print(f"Successfully merged {len(df_merged)} records.")
    print(f"Start processing merged data...")
    print(f"Looking for draft SVG renders at: {draft_image_folder}")

    for index, row in tqdm(df_merged.iterrows(), total=df_merged.shape[0], desc="Generating training data"):
        svg_id = str(row['id']) # Ensure ID is a string
        origin_prompt = str(row['desc'])
        # Get target JSON string directly
        target_result_json_str = str(row['result']).strip() # Read and strip whitespace

        # Clean potential markdown code block markers
        if target_result_json_str.startswith("```json"):
            target_result_json_str = target_result_json_str[7:]
        if target_result_json_str.endswith("```"):
            target_result_json_str = target_result_json_str[:-3]
        target_result_json_str = target_result_json_str.strip() # Strip after removing markers

        # Basic validation: looks like JSON (starts with '{' and ends with '}')
        if not (target_result_json_str.startswith('{') and target_result_json_str.endswith('}')):
             print(f"\nWarning: skip ID '{svg_id}'. 'result' does not look like valid JSON: {target_result_json_str[:100]}...")
             continue

        actual_image_path = None
        expected_image_relative_path = f"draft_image/{svg_id}.png"

        for ext in ['.png', '.jpg', '.jpeg']:
            potential_actual_path = os.path.join(draft_image_folder, f"{svg_id}{ext}")
            if os.path.exists(potential_actual_path):
                actual_image_path = potential_actual_path
                break

        if actual_image_path:
            try:
                # Build user prompt
                user_prompt_for_critic = CRITIC_USER_PROMPT_TEMPLATE.format(origin_prompt=origin_prompt)

                # Prepare image data (path or base64)
                image_data_field = {}
                if use_base64:
                    with open(actual_image_path, "rb") as image_file:
                        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                    image_data_field = {"images": [base64_image]}
                else:
                    # Put image path into a list named "images"
                    image_data_field = {"images": [expected_image_relative_path]}

                # Build final JSON entry for training
                message_entry = {
                    "messages": [
                        {
                            "content": user_prompt_for_critic,
                            "role": "user"
                        },
                        {
                            "content": target_result_json_str, 
                            "role": "assistant"
                        }
                    ],
                    **image_data_field 
                }

                data.append(message_entry)

            except Exception as e:
                print(f"\nError processing entry with ID '{svg_id}': {e}")

    if not data:
        print("\nError: failed to generate any valid JSON training data. Please check paths, CSV contents, and image existence.")
        return

    try:
        with open(output_json_path, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=2)
        print(f"\nDone! Processed {len(data)} valid records. Critic training JSON saved to: {output_json_path}")
    except Exception as e:
        print(f"\nError writing JSON file: {e}")


csv_path_prompts = os.path.join('.', 'data', 'merged_inference_file.csv')
csv_path_results = os.path.join('.', 'data', 'inference_results.csv')
draft_image_folder = os.path.join('.', 'data', 'draft_image')
output_json_path = 'critic_training_data.json'
INCLUDE_BASE64_IMAGE = False

create_critique_training_data(csv_path_prompts, csv_path_results, draft_image_folder, output_json_path, use_base64=INCLUDE_BASE64_IMAGE)

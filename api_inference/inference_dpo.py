import os
import base64
from openai import AzureOpenAI
import time
import csv
import json

api_base = "" 
api_key = ""
deployment_name = 'gpt-4o'
api_version = ''

client = AzureOpenAI(
    api_key=api_key,
    api_version=api_version,
    base_url=f"{api_base}/openai/deployments/{deployment_name}"
)

PROMPT_TEMPLATE = """
Task: I used this prompt: {original_prompt}

Rate the 5 SVG images I'm uploading from 1-100 based on that prompt. Ensure the scores are differentiated.

Evaluate based on:

Prompt Adherence: How well the image matches the prompt's elements and mood.

Visual Aesthetics: Color, composition, and visual impact.

Execution Quality: Creativity and technical quality (clean SVG, no flaws).

Output Format: Provide only JSON in this exact format. No other text.

JSON

{
"image_1_score": [Score],
  "image_2_score": [Score],
  "image_3_score": [Score],
  "image_4_score": [Score],
  "image_5_score": [Score]
}
"""

def analyze_image_set(image_paths_list, original_prompt):
    """
    Process a set of 5 images (in order) and return scores.
    
    :param image_paths_list: List of 5 PNG image file paths
    :param original_prompt: Original prompt
    :return: API returned JSON string
    """
    
    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    final_prompt = PROMPT_TEMPLATE.format(original_prompt=original_prompt)

    messages_content = [
        {"type": "text", "text": final_prompt}
    ]

    for img_path in image_paths_list:
        try:
            base64_image = encode_image(img_path)
            mime_type = "image/jpeg" if img_path.lower().endswith((".jpg", ".jpeg")) else "image/png"
            data_url = f"data:{mime_type};base64,{base64_image}"
            
            messages_content.append({
                "type": "image_url",
                "image_url": {"url": data_url}
            })
        except FileNotFoundError:
            print(f"File not found during encoding: {img_path}")
            raise

    response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {"role": "system", "content": "You are a rigorous SVG design reviewer and evaluator."},
            {"role": "user", "content": messages_content}
        ],
        max_tokens=1000,
        temperature=0.2
    )

    return response.choices[0].message.content

if __name__ == "__main__":
    start_time = time.time()

    png_folder = os.path.join('.', 'data', 'png') 
    csv_name = os.path.join('.', 'data', 'merged_all_infer.csv')
    output_json = "inference_scores.json"

    try:
        id2prompt = {row['id']: row['desc'] for row in csv.DictReader(open(csv_name, 'r', newline='', encoding='utf-8'))}
        print(f"Loaded {len(id2prompt)} IDs from {csv_name}.")
    except Exception as e:
        print(f"Fatal error: cannot read CSV {csv_name}. Error: {e}")
        exit()

    results = []

    for base_id, original_prompt in id2prompt.items():
        print(f"Processing ID: {base_id}")
        
        image_paths_to_process = []
        all_files_found = True

        for i in range(1, 6):
            png_filename = f"{base_id}-{i}.png"
            full_path = os.path.join(png_folder, png_filename)
            
            if not os.path.exists(full_path):
                print(f"Missing file: {png_filename}. Skipping ID {base_id}.")
                all_files_found = False
                break
            
            image_paths_to_process.append(full_path)

        if not all_files_found:
            results.append({
                "id": base_id,
                "status": "Skipped - Missing files",
                "scores": None
            })
            continue

        try:
            print(f"Submitting {len(image_paths_to_process)} images to API...")
            report_str = analyze_image_set(image_paths_to_process, original_prompt)
            
            print(f"Received response for {base_id}.")
            
            try:
                scores_data = json.loads(report_str)
                results.append({
                    "id": base_id,
                    "status": "Success",
                    "scores": scores_data
                })
            except json.JSONDecodeError:
                print(f"Warning: API did not return valid JSON. Will save raw string.")
                results.append({
                    "id": base_id,
                    "status": "Error - Invalid JSON response",
                    "raw_response": report_str
                })

        except Exception as e:
            print(f"API error while processing {base_id}: {e}")
            results.append({
                "id": base_id,
                "status": f"Error - {e}",
                "scores": None
            })

    with open(output_json, "w", encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nAll files processed. Results saved to {output_json}")
    print(f"Total time: {time.time() - start_time:.2f}s")
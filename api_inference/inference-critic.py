import os
import base64
from openai import AzureOpenAI
import time
import csv
import json
api_base = ""
deployment_name = "gpt-4o"
api_key = ""
api_version = ""

client = AzureOpenAI(
    api_key=api_key,
    api_version=api_version,
    base_url=f"{api_base}/openai/deployments/{deployment_name}"
)

PROMPT_TEMPLATE = """
Role Play
You are a world-class SVG design master and code engineer, possessing exceptional design aesthetics and a profound understanding of SVG code structure. Your task is to act as a mentor reviewing an SVG work. Your core expertise lies in the ability to reverse-engineer the underlying SVG paths, shapes, and layer structure from a rendered image and provide code-level optimization advice.

Task Context
A draft has been generated based on an original design requirement, and a high-quality reference version designed by a human expert is also provided. Both images are rendered from SVG code. Your task is to compare these two works and generate a professional review report for the draft. The report should guide on how to modify the SVG code to learn from and improve towards the reference version, while also considering the draft's consistency with the original design prompt.

Contextual Information

1. Original Prompt
{original_prompt}

2. The draft image is the first input image, used to present the generated design draft.

3. The high-quality reference image is the second input image, used to present the visual effect of the reference design.

Your Core Task & Scoring Guide
Please carefully observe and compare the first image (the draft) with the second image (the high-quality reference version), while also considering the requirements of the original design prompt. Output a detailed review report in JSON format. Your sole task is to generate this report; do not generate any SVG code.

Important Scoring Instructions
- When the draft is highly similar to the reference version and meets the requirements of the original design prompt, please give a high score (e.g., 9.0-10.0). In the suggestions, do not provide modification guidance, only an affirmative output.
- When there are significant differences between the draft and the reference version, or deviations from the original design prompt, please give a reasonable mid-to-low score based on the severity of the differences and the visual quality. Provide 2 to 4 specific, actionable SVG modification suggestions.

JSON Output Format
The JSON object must contain the following three fields:
- "score": A float, ranging from 0.0 to 10.0, for the overall rating of the draft.
- "critique": A comprehensive evaluation explaining the draft's adherence to the original design prompt and pointing out the main differences and shortcomings in aesthetics, color, and geometric construction compared to the reference version.
- "suggestions": If the draft is very close to the reference version and aligns with the original prompt, use an affirmative statement such as "The overall quality is excellent, no changes needed." Otherwise, provide specific SVG modification suggestions.
"""

def analyze_images_seq(image_path1, image_path2, original_prompt):
    """Process two images (draft + high-quality reference) and generate a review report."""
    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    base64_image1 = encode_image(image_path1)
    base64_image2 = encode_image(image_path2)

    mime_type1 = "image/jpeg" if image_path1.lower().endswith((".jpg", ".jpeg")) else "image/png"
    mime_type2 = "image/jpeg" if image_path2.lower().endswith((".jpg", ".jpeg")) else "image/png"

    data_url1 = f"data:{mime_type1};base64,{base64_image1}"
    data_url2 = f"data:{mime_type2};base64,{base64_image2}"

    final_prompt = PROMPT_TEMPLATE.format(original_prompt=original_prompt)

    response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {"role": "system", "content": "You are a rigorous SVG design reviewer and evaluator."},
            {"role": "user", "content": [
                {"type": "text", "text": final_prompt},
                {"type": "image_url", "image_url": {"url": data_url1}},
                {"type": "image_url", "image_url": {"url": data_url2}}
            ]}
        ],
        max_tokens=3600,
        temperature=0.2
    )

    return response.choices[0].message.content

if __name__ == "__main__":
    start_time = time.time()

    draft_folder = os.path.join('.', 'data', 'draft_png')
    reference_folder = os.path.join('.', 'data', 'reference_png')
    csv_name = os.path.join('.', 'data', 'merged_all_infer.csv')

    id2prompt = {row['id']: row['desc'] for row in csv.DictReader(open(csv_name, 'r', newline='', encoding='utf-8'))}

    results = []

    for file_name in os.listdir(draft_folder):
        if not file_name.lower().endswith((".png", ".jpg", ".jpeg")):
            continue
        file_id = os.path.splitext(file_name)[0]

        draft_path = os.path.join(draft_folder, file_name)
        reference_path = os.path.join(reference_folder, file_name)
        original_prompt = id2prompt.get(file_id)

        print(f"Processing {file_id} ...")
        try:
            report = analyze_images_seq(draft_path, reference_path, original_prompt)
            results.append({
                "file_id": file_id,
                "report": report
            })
        except Exception as e:
            print(f"Error while processing {file_id}: {e}")

    output_json = r"inference_results.json"
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nAll files processed. Results saved to {output_json}")
    print(f"Total time: {time.time() - start_time:.2f}s")

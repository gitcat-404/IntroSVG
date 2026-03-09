import csv
import re
import json
import os

score_csv_path = "SVG/dpo/inference_dpo_score.csv"        
svg_folder = "SVG/dpo/dpo-svg"          
output_json_path = "dpo.json"   
desc_csv_path = "SVG/dpo/dpo_all.csv"
pattern = re.compile(r'"image_(\d+)_score"\s*:\s*(\d+)')
id2desc = {}

# Read description CSV
with open(desc_csv_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        _id = row["id"].strip()
        id2desc[_id] = row["desc"].strip()

results = []

# Read score CSV and process
with open(score_csv_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        _id = row["id"].strip()
        inference_result = row["inference_result"]

        scores = [(int(idx), int(score)) for idx, score in pattern.findall(inference_result)]
        if not scores:
            print(f"ID={_id}: inference_result format error, skipping.")
            continue

        min_img, min_score = min(scores, key=lambda x: x[1])
        max_img, max_score = max(scores, key=lambda x: x[1])

        chosen_file = os.path.join(svg_folder, f"{_id}-{max_img}.svg")
        rejected_file = os.path.join(svg_folder, f"{_id}-{min_img}.svg")

        try:
            with open(chosen_file, "r", encoding="utf-8") as cf:
                chosen_svg = cf.read()
            with open(rejected_file, "r", encoding="utf-8") as rf:
                rejected_svg = rf.read()
        except FileNotFoundError as e:
            print(f"Corresponding SVG file not found: {e}")
            continue

        desc = id2desc.get(_id, "(No description available)")

        entry = {
            "conversations": [
                {
                    "from": "human",
                    "value": f"Please generate an SVG icon that meets the following description: {desc}"
                }
            ],
            "chosen": {
                "from": "gpt",
                "value": chosen_svg
            },
            "rejected": {
                "from": "gpt",
                "value": rejected_svg
            }
        }

        results.append(entry)

with open(output_json_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=4)
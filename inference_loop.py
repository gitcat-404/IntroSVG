import os
import time
import pandas as pd
from openai import OpenAI, APIStatusError, InternalServerError, RateLimitError
import requests
import json
import base64
import io
import re
import argparse
import sys
try:
    import cairosvg
except ImportError:
    print("ERROR: Library 'cairosvg' not found.")
    print("Please run 'pip install cairosvg' to install it.")
    exit(1)


openai_api_key = "EMPTY"
openai_api_base = "http://127.0.0.1:23333/v1" 
print(f"INFO: Initializing program; target server: {openai_api_base}")
client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_api_base,
)


def extract_json_block(text: str) -> str:
    """Extract the first JSON block from text that may contain markdown fences."""
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    
    start_index = text.find('{')
    end_index = text.rfind('}')
    if start_index != -1 and end_index != -1 and end_index > start_index:
        return text[start_index : end_index + 1]
    
    raise ValueError(f"Could not find a valid JSON block in the response. Content: {text}")


def call_openai_with_retry(api_client, max_retries=3, initial_delay=5, **kwargs):
    """Call the OpenAI API with retry logic for transient errors (503/500/429) using exponential backoff."""
    retries = 0
    delay = initial_delay
    while retries < max_retries:
        try:
            return api_client.chat_completions.create(**kwargs)
        except (InternalServerError, RateLimitError) as e:
            print(f"    WARNING: Temporary API error: {e}. Retrying in {delay} seconds... (attempt {retries + 1}/{max_retries})")
            time.sleep(delay)
            retries += 1
            delay *= 2 
        except APIStatusError as e:
            print(f"    ERROR: API call failed with non-retryable status error: {e}")
            raise  
        except requests.exceptions.ConnectionError as e:
            print(f"    ERROR: API connection error: {e}. Please ensure the server is running.")
            raise  
    
    print(f"    ERROR: API call failed after {max_retries} retries.")
    raise Exception(f"Failed to get response from API after {max_retries} retries.")


def convert_svg_to_png(svg_content: str, output_path: str, width: int = 200, height: int = 200):
    """Convert an SVG string into a PNG file with the specified size and a white background."""
    try:
        if not isinstance(svg_content, str) or not svg_content.strip():
            raise ValueError("SVG content is empty or invalid.")
            
        cairosvg.svg2png(
            bytestring=svg_content.encode('utf-8'),
            write_to=output_path,
            output_width=width,
            output_height=height,
            background_color="white" 
        )
    except Exception as e:
        print(f"ERROR: SVG to PNG conversion failed. Error: {e}")
        raise

def encode_image_to_base64(image_path: str) -> str:
    """Read a PNG file and encode it as a base64 string."""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"ERROR: Failed to encode PNG file: {e}")
        raise

def batch_svg_generation(
    api_client, 
    model_name: str, 
    csv_file_path: str, 
    output_folder: str,
    max_iterations: int = 3
):
    """Execute a multi-iteration SVG generation pipeline."""
    
    # Critic prompt template
    CRITIC_USER_PROMPT_TEMPLATE ="""You are a professional SVG design critic. Please analyze the input AI-generated SVG draft<image> according to the "Original Design Prompt".

**Original Design Prompt**: "{origin_prompt}"

Your task is to output a structured critique report, strictly following the JSON format below. The JSON object must contain three fields:
1. "score": A float between 0.0 and 10.0, for a comprehensive evaluation of the draft's quality and alignment.
2. "critique": A comprehensive evaluation explaining the extent to which the draft meets the original prompt, and pointing out its main differences and shortcomings in aesthetics, color, and geometric construction compared to an ideal version.
3. "suggestions": A single string. If the draft's quality is high, this string should be an affirmative statement, such as "The overall quality is excellent, no changes are needed." Otherwise, it should contain 2 to 4 specific, actionable SVG modification suggestions, presented as a numbered list within this string (e.g., "1. Suggestion A\n2. Suggestion B")."""

    print(f"INFO: Starting batch process. Data source: {csv_file_path}")
    print(f"INFO: Each item will run {max_iterations} refinement iterations.")
    start_time = time.time()
    
    os.makedirs(output_folder, exist_ok=True)
    

    final_svg_dir = os.path.join(output_folder, "final_svgs")
    final_png_dir = os.path.join(output_folder, "final_pngs")
    os.makedirs(final_svg_dir, exist_ok=True)
    os.makedirs(final_png_dir, exist_ok=True)
    
    intermediate_dir = os.path.join(output_folder, "intermediate_files")
    os.makedirs(intermediate_dir, exist_ok=True)
    
    initial_draft_dir = os.path.join(intermediate_dir, "00_initial_drafts")
    os.makedirs(initial_draft_dir, exist_ok=True)

    print(f"INFO: Creating intermediate folders for {max_iterations} iterations...")
    for i in range(max_iterations):
        iter_num_str = f"{i + 1:02d}" 
        iter_dir = os.path.join(intermediate_dir, f"{iter_num_str}_iteration")
        
        png_critique_dir = os.path.join(iter_dir, "critique_pngs")
        refined_svg_dir = os.path.join(iter_dir, "refined_svgs")
        
        os.makedirs(png_critique_dir, exist_ok=True)
        os.makedirs(refined_svg_dir, exist_ok=True)
    
    print(f"INFO: Final SVGs and reports will be saved to: {final_svg_dir}")
    print(f"INFO: Final PNGs will be saved to: {final_png_dir}")
    print(f"INFO: All intermediate files will be saved to: {intermediate_dir}")

    try:
        df = pd.read_csv(csv_file_path)
        if 'desc' not in df.columns or 'id' not in df.columns:
            print(f"ERROR: CSV file is missing 'desc' and/or 'id' columns")
            return
    except Exception as e:
        print(f"ERROR: Failed to read CSV file {csv_file_path}. Error: {e}")
        return

    descriptions = df['desc'].tolist()
    ids = df['id'].tolist()
    total_items = len(descriptions)
    
    print(f"INFO: Found {total_items} descriptions. Starting processing...")

    for i, origin_prompt in enumerate(descriptions):
        current_id = ids[i]
        print(f"\n -> Processing [{i+1}/{total_items}] ID: {current_id}")
        
        final_svg_path = os.path.join(final_svg_dir, f"{current_id}.svg") 
        final_png_path = os.path.join(final_png_dir, f"{current_id}.png") 
        final_report_path = os.path.join(final_svg_dir, f"{current_id}.json") 

        
        try:

            print(f"    [Iter 0] Generating initial SVG draft...")
            generation_prompt = f"Please generate an SVG icon that meets the following description: {origin_prompt}"
            
            draft_response = call_openai_with_retry(
                api_client,
                model=model_name,
                messages=[
                    {"role": "user", "content": generation_prompt}
                ],
                max_tokens=6000,
                temperature=0.5,
                top_p=1
            )
            current_svg_content = draft_response.choices[0].message.content
            
            draft_svg_path = os.path.join(initial_draft_dir, f"{current_id}.svg")
            with open(draft_svg_path, 'w', encoding='utf-8') as file:
                file.write(current_svg_content)
            print(f"    [Iter 0] Initial draft saved: {draft_svg_path}")

            for iter_num in range(max_iterations):
                print(f"\n    --- Iteration {iter_num + 1}/{max_iterations} ---")
                
                iter_num_str = f"{iter_num + 1:02d}" # "01", "02", ...
                iter_dir = os.path.join(intermediate_dir, f"{iter_num_str}_iteration")
                png_critique_dir = os.path.join(iter_dir, "critique_pngs")
                refined_svg_dir = os.path.join(iter_dir, "refined_svgs")
                
                # --- A. Critique ---
                print(f"    [Iter {iter_num + 1}] Stage A: Evaluating current SVG...")
                png_path = os.path.join(png_critique_dir, f"{current_id}.png")
                
                convert_svg_to_png(current_svg_content, png_path, width=200, height=200)
                
                base64_image = encode_image_to_base64(png_path)
                critique_prompt_text = CRITIC_USER_PROMPT_TEMPLATE.format(origin_prompt=origin_prompt)
                critique_messages = [
                    {"role": "user", "content": [
                        {"type": "text", "text": critique_prompt_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                    ]}
                ]
                
                critique_response = call_openai_with_retry(
                    api_client, model=model_name, messages=critique_messages,
                    max_tokens=2048, temperature=0.1,
                )
                
                response_content = critique_response.choices[0].message.content
                json_string = extract_json_block(response_content) 
                critique_data = json.loads(json_string) 
                
                score = critique_data.get("score")
                critique = critique_data.get("critique")
                suggestions = critique_data.get("suggestions")
                
                if not all([score is not None, critique, suggestions]):
                    raise ValueError("Critique JSON response is missing 'score', 'critique', or 'suggestions'.")
                
                print(f"    [Iter {iter_num + 1}] Critique complete. Score: {score}")

                print(f"    [Iter {iter_num + 1}] Stage B: Refining SVG...")
                refine_prompt = f"""Please analyze all the information provided below and generate a final, high-quality SVG code. The original design goal was: "{origin_prompt}"; a draft SVG code that needs improvement is as follows: ```xml
{current_svg_content}
```; an expert critique of this draft is: "{critique}"; and the specific modification suggestions are: {suggestions}. Please strictly follow these suggestions to improve the draft and directly output the final, refined SVG code."""

                final_response = call_openai_with_retry(
                    api_client, model=model_name,
                    messages=[{"role": "user", "content": refine_prompt}],
                    max_tokens=6000, temperature=0.2, top_p=1
                )
                
                refined_svg_code = final_response.choices[0].message.content

                current_svg_content = refined_svg_code # <-- Key: update SVG content for the next iteration
                
                refined_svg_path = os.path.join(refined_svg_dir, f"{current_id}.svg")
                with open(refined_svg_path, 'w', encoding='utf-8') as file:
                    file.write(current_svg_content)
                print(f"    [Iter {iter_num + 1}] Refined SVG saved: {refined_svg_path}")

            print(f"\n    --- Finalizing ID: {current_id} ---")
            
            with open(final_svg_path, 'w', encoding='utf-8') as file:
                file.write(current_svg_content)
            print(f"    [Final] Final SVG saved: {final_svg_path}")
            
            convert_svg_to_png(current_svg_content, final_png_path, width=200, height=200)
            print(f"    [Final] Final PNG rendered: {final_png_path}")

            print(f"    [Final] Performing final critique...")
            
            base64_image = encode_image_to_base64(final_png_path) 
            critique_prompt_text = CRITIC_USER_PROMPT_TEMPLATE.format(origin_prompt=origin_prompt)
            
            critique_messages = [
                {"role": "user", "content": [
                    {"type": "text", "text": critique_prompt_text},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                ]}
            ]
            
            critique_response = call_openai_with_retry(
                api_client, model=model_name, messages=critique_messages,
                max_tokens=2048, temperature=0,
            )
            
            response_content = critique_response.choices[0].message.content
            json_string = extract_json_block(response_content)
            final_critique_data = json.loads(json_string) # <-- Final critique data
            
            final_score = final_critique_data.get("score")
            print(f"    [Final] SUCCESS: Final critique score = {final_score}")
            
            with open(final_report_path, 'w', encoding='utf-8') as f:
                json.dump(final_critique_data, f, indent=4, ensure_ascii=False)
            print(f"    [Final] Final critique report saved: {final_report_path}")

        except (requests.exceptions.ConnectionError, APIStatusError) as e:
            print(f"ERROR: [ID: {current_id}] Non-retryable API or connection error; skipped. Error: {e}")
            continue
        except json.JSONDecodeError as e:
            print(f"WARNING: [ID: {current_id}] JSON parsing failed during critique stage. Check if model response is valid JSON. Error: {e}. Response: {response_content}")
            continue
        except (ValueError, KeyError, TypeError) as e:
            print(f"WARNING: [ID: {current_id}] Critique data processing failed (e.g., JSON block missing, missing fields, or SVG conversion failure). Error: {e}. Skipping.")
            continue
        except Exception as e:
            print(f"WARNING: [ID: {current_id}] Unknown error occurred during processing; skipped. Error: {e}")
            continue

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"\nINFO: Batch processing complete. Total time: {elapsed_time:.2f}s)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch SVG generation pipeline")

    parser.add_argument("--MODEL_NAME", required=True, help="Model name")
    parser.add_argument("--CSV_FILE", required=True, help="Input CSV file")
    parser.add_argument("--OUTPUT_DIR", required=True, help="Output directory")

    args = parser.parse_args()

    MODEL_NAME = args.MODEL_NAME
    CSV_FILE = args.CSV_FILE
    OUTPUT_DIR = args.OUTPUT_DIR

    MAX_ITERATIONS = 3

    print(f"INFO: MODEL_NAME = {MODEL_NAME}")
    print(f"INFO: CSV_FILE = {CSV_FILE}")
    print(f"INFO: OUTPUT_DIR = {OUTPUT_DIR}")

    if not os.path.exists(CSV_FILE):
        print(f"FATAL ERROR: CSV file not found: {CSV_FILE}")
        sys.exit(1)

    batch_svg_generation(
        api_client=client,
        model_name=MODEL_NAME,
        csv_file_path=CSV_FILE,
        output_folder=OUTPUT_DIR,
        max_iterations=MAX_ITERATIONS
    )

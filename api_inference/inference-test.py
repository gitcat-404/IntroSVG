import csv
import os
import asyncio
import re
from openai import AsyncAzureOpenAI
from tqdm.asyncio import tqdm

api_base = "" 
api_key = ""
deployment_name = 'DeepSeek-R1-0528'
api_version = ''

aclient = AsyncAzureOpenAI(
    api_key=api_key,
    api_version=api_version,
    base_url=f"{api_base}/openai/deployments/{deployment_name}"
)

semaphore = asyncio.Semaphore(10)

async def generate_svg_from_csv(csv_file_path, output_folder):
    """Read rows from CSV and generate SVG files into the specified folder."""

    os.makedirs(output_folder, exist_ok=True)
    
    with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)

    with tqdm(total=len(rows), desc="Processing Rows") as progress_bar:
        tasks = [process_row(row, output_folder, progress_bar) for row in rows]
        await asyncio.gather(*tasks)

async def process_row(row, output_folder, progress_bar):
    """Process one CSV row, generate an SVG, and update the progress bar."""
    desc = row['desc']
    file_id = row['id']
    
    prompt = f"Please generate an SVG icon that meets the following description: {desc}"
    
    async with semaphore:
        try:
            svg_content = await generate_svg(prompt)

            svg_pattern = re.compile(r'<svg[^>]*>(.*?)</svg>', re.DOTALL)
            match = svg_pattern.search(svg_content)
            
            if match:
                svg_data = match.group(0)
                svg_file_path = os.path.join(output_folder, f"{file_id}.svg")
                with open(svg_file_path, 'w', encoding='utf-8') as svg_file:
                    svg_file.write(svg_data)
            else:
                print(f"No SVG content found for ID {file_id}.")
        
        except Exception as e:
            print(f"Failed to generate SVG for ID {file_id}: {e}")

        progress_bar.update(1)

async def generate_svg(prompt):
    """Generate SVG content via OpenAI."""
    
    response = await aclient.chat.completions.create(
        model=deployment_name,
        messages=[
            {"role": "system", "content": "You are an SVG design assistant."},
            {"role": "user", "content": prompt}
        ],
        max_completion_tokens=4000
    )
    
    return response.choices[0].message.content

if __name__ == "__main__":
    csv_file_path = os.path.join('.', 'data', 'input.csv')
    output_folder = os.path.join('.', 'data', 'outputs', 'deepseekr1')
    asyncio.run(generate_svg_from_csv(csv_file_path, output_folder))

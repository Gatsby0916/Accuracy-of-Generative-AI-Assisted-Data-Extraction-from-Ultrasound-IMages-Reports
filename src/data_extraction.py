# src/extraction_data.py

import pandas as pd
import json
import os
import sys
import argparse
import config # Import our new, flexible config

def extract_and_create_template(dataset_name):
    """
    Reads the ground truth Excel for a specific dataset, cleans it,
    and creates a JSON template from its headers.
    """
    print(f"\n--- Starting Template Generation for Dataset: {dataset_name} ---")

    # 1. Get the correct paths from our new config structure
    try:
        dataset_config = config.DATASET_CONFIGS[dataset_name]
        # We will read directly from the final ground truth file
        input_excel_path = dataset_config["ground_truth_xlsx"]
        # The output path will also be fetched from the config
        output_json_path = dataset_config["template_json"]
    except KeyError:
        print(f"❌ FATAL: Dataset '{dataset_name}' is not defined in config.py.", file=sys.stderr)
        return False

    print(f"Reading headers from: {input_excel_path}")
    if not os.path.exists(input_excel_path):
        print(f"❌ Error: Input ground truth Excel file not found at '{input_excel_path}'")
        return False

    # 2. Read headers from the specified Excel file
    try:
        # We only need the headers, so we read just the first row to be efficient.
        df = pd.read_excel(input_excel_path, nrows=0)
        headers = df.columns.tolist()
        print(f"Successfully extracted {len(headers)} headers.")

    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")
        return False

    # 3. Create the JSON template from the headers
    # The cleaning logic you wrote is great, but for a simple template generation,
    # we can directly use the headers from the final, clean ground truth file.
    print("Creating JSON template...")
    json_template = {header: "" for header in headers}

    # 4. Save the new JSON template
    print(f"Saving JSON template to: {output_json_path}")
    try:
        # Ensure the template directory exists
        os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as f:
            # Use formatting from config file
            json.dump(json_template, f, indent=config.JSON_INDENT, ensure_ascii=config.ENSURE_ASCII)
        
        print(f"\n✅ Success!")
        print(f"JSON template saved to: {output_json_path}")
        return True
    except Exception as e:
       print(f"❌ Error saving JSON template: {e}")
       return False


if __name__ == "__main__":
    # Use argparse to let the user specify which dataset to process
    parser = argparse.ArgumentParser(
        description="Create a JSON template from the headers of a dataset's ground truth Excel file."
    )
    parser.add_argument(
        '--dataset',
        required=True,
        choices=list(config.DATASET_CONFIGS.keys()),
        help="The name of the dataset (e.g., 'sugo', 'benson') to generate a template for."
    )
    args = parser.parse_args()
    
    # Run the main function with the selected dataset
    success = extract_and_create_template(args.dataset)
    
    if not success:
        sys.exit(1)
# src/json_to_excel.py

import json
import pandas as pd
import os
import sys
import config # Import our updated config

def convert_json_to_excel(json_path, excel_path):
    """
    Converts a single JSON file to a single row in an Excel file.
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found at {json_path}", file=sys.stderr)
        return False
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {json_path}", file=sys.stderr)
        return False

    # Convert the flat JSON object into a DataFrame with a single row
    df = pd.DataFrame([data])
    
    # Ensure the output directory exists
    try:
        os.makedirs(os.path.dirname(excel_path), exist_ok=True)
        df.to_excel(excel_path, index=False)
        print(f"Successfully converted JSON to Excel: {excel_path}")
        return True
    except Exception as e:
        print(f"Error saving Excel file to {excel_path}: {e}", file=sys.stderr)
        return False

def main(dataset_name, report_id, provider_name, model_name_slug):
    """
    Main function to orchestrate the JSON to Excel conversion.
    """
    print(f"\n--- Starting JSON to Excel Conversion for Report: {report_id}, Dataset: {dataset_name} ---")

    # Get paths dynamically using the new config functions
    try:
        checked_json_dir = config.get_extracted_json_checked_dir(provider_name, model_name_slug, dataset_name)
        excel_dir = config.get_extracted_excel_dir(provider_name, model_name_slug, dataset_name)
    except KeyError:
        print(f"FATAL: Dataset '{dataset_name}' not found in config.py.", file=sys.stderr)
        sys.exit(1)

    # Define the full input and output file paths
    # The filename format should be consistent, e.g., "RRI002_validated_data.json"
    json_input_path = os.path.join(checked_json_dir, f"{report_id}_validated_data.json")
    excel_output_path = os.path.join(excel_dir, f"{report_id}_output.xlsx")

    print(f"Input validated JSON: {json_input_path}")
    print(f"Output Excel file: {excel_output_path}")

    # Run the conversion
    success = convert_json_to_excel(json_input_path, excel_output_path)
    if not success:
        raise RuntimeError(f"Failed to convert JSON to Excel for report {report_id}.")

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(f"Usage: python {os.path.basename(__file__)} <dataset_name> <report_id> <provider_name> <model_name_slug>", file=sys.stderr)
        sys.exit(1)

    dataset_name_arg = sys.argv[1]
    report_id_arg = sys.argv[2]
    provider_name_arg = sys.argv[3]
    model_name_slug_arg = sys.argv[4]

    try:
        main(dataset_name_arg, report_id_arg, provider_name_arg, model_name_slug_arg)
    except Exception as e:
        print(f"\nAn error occurred during JSON to Excel conversion: {e}", file=sys.stderr)
        sys.exit(1)
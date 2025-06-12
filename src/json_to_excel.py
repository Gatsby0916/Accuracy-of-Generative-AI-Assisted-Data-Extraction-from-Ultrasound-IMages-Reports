import sys
import json
import pandas as pd
import os
import config # Import the config module

# project_root is defined in config, no need to redefine here

def main(report_id, provider_name, model_name_slug):
    """
    Converts a validated JSON file to an Excel file for a given report, provider, and model.
    Args:
        report_id (str): The report ID (e.g., "RRI002").
        provider_name (str): The LLM provider name (e.g., "openai").
        model_name_slug (str): The model name slug for directory naming (e.g., "gpt-4o").
    """
    report_id_formatted = report_id[:3] + " " + report_id[3:] # Format for filenames "RRI XXX"

    # --- Determine Paths using config functions ---
    # Input JSON comes from the 'json_checked' directory for the specific provider and model
    json_checked_folder = config.get_extracted_json_checked_dir(provider_name, model_name_slug)
    json_path = os.path.join(json_checked_folder, f"{report_id_formatted}_extracted_data.json")

    # Output Excel goes into the 'excel' directory for the specific provider and model
    excel_folder = config.get_extracted_excel_dir(provider_name, model_name_slug)
    excel_path = os.path.join(excel_folder, f"{report_id_formatted}_extracted_data.xlsx")

    print(f"\nStarting JSON to Excel conversion for report {report_id} (Provider: {provider_name}, Model: {model_name_slug})")
    print(f"Input JSON file path: {json_path}")
    print(f"Output Excel file path: {excel_path}")

    # Ensure the output directory for Excel files exists
    try:
        os.makedirs(excel_folder, exist_ok=True)
    except Exception as e:
        print(f"Error: Failed to create Excel output directory '{excel_folder}': {e}")
        raise IOError(f"Error creating Excel output directory: {e}") # Re-raise to be caught

    # --- Read JSON ---
    print(f"Reading JSON file: {json_path}")
    if not os.path.exists(json_path):
        print(f"Error: Input JSON file not found: {json_path}")
        raise FileNotFoundError(f"Input JSON file for Excel conversion not found: {json_path}")

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON file '{json_path}': {e}")
        raise IOError(f"Error decoding JSON file: {e}")
    except Exception as e:
        print(f"An unknown error occurred while reading JSON file '{json_path}': {e}")
        raise IOError(f"Error reading JSON file: {e}")

    # --- Convert and Save Excel ---
    try:
        # The JSON contains a single object, which needs to be wrapped in a list for DataFrame
        df = pd.DataFrame([data])
        df.to_excel(excel_path, index=False)
        print(f"JSON file successfully converted to Excel: {excel_path}")
    except Exception as e:
        print(f"Error converting JSON to Excel or saving file '{excel_path}': {e}")
        raise IOError(f"Error converting JSON to Excel or saving: {e}")

if __name__ == "__main__":
    # This script expects three arguments: report_id, provider_name, model_name_slug
    if len(sys.argv) != 4:
        print(f"Usage: python {os.path.basename(__file__)} <report_id> <provider_name> <model_name_slug>")
        print("Example: python json_to_excel.py RRI002 openai gpt-4o")
        sys.exit(1)

    report_id_arg = sys.argv[1]
    provider_name_arg = sys.argv[2]
    model_name_slug_arg = sys.argv[3] # This is the fs-safe slug

    try:
        main(report_id_arg, provider_name_arg, model_name_slug_arg)
        print(f"\nJSON to Excel conversion completed for report {report_id_arg} (Provider: {provider_name_arg}, Model: {model_name_slug_arg}).")
    except Exception as e:
        # Error messages from main() should be informative
        print(f"\nAn error occurred while converting JSON to Excel for report {report_id_arg} (Provider: {provider_name_arg}, Model: {model_name_slug_arg}), aborted.")
        sys.exit(1) # Exit with a non-zero code to indicate failure

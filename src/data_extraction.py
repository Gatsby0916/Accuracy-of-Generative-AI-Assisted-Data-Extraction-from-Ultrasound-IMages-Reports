import pandas as pd
import json
import os
import sys
import config # <--- Import the config module

# project_root defined in config, no need to redefine here

# --- Use Paths from config ---
input_file_path = config.ORIGINAL_GROUND_TRUTH_XLSX # <--- Use config
output_excel_path = config.CLEANED_GROUND_TRUTH_XLSX # <--- Use config
output_json_path = config.TEMPLATE_JSON_PATH # <--- Use config

def extract_and_clean():
    """Reads the specified sheet from the original ground truth (defined in config),
    cleans it, saves the cleaned version, and saves a template JSON."""

    # --- Read file paths and sheet name from config ---
    input_file = config.ORIGINAL_GROUND_TRUTH_XLSX
    output_excel = config.CLEANED_GROUND_TRUTH_XLSX
    output_json = config.TEMPLATE_JSON_PATH
    sheet_to_read = config.GROUND_TRUTH_SHEET_NAME # <--- Get sheet name from config
    # ------------------------------------------

    if not os.path.exists(input_file):
        print(f"Error: Input Excel file not found: {input_file}")
        return False

    print(f"Reading sheet '{sheet_to_read}' from file {input_file}...")
    try:
        # --- Modification Point ---
        # Use the sheet name read from config
        MRI = pd.read_excel(input_file, sheet_name=sheet_to_read)
        # -------------
    except ValueError as ve:
        if f"Worksheet named '{sheet_to_read}' not found" in str(ve):
            print(f"Error: Worksheet named '{sheet_to_read}' not found in file {input_file} (please check the GROUND_TRUTH_SHEET_NAME setting in config.py).")
        else:
            print(f"Error reading Excel file: {ve}")
        return False
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return False

    print("Cleaning data...")
    try:
        # --- Cleaning logic remains unchanged ---
        columns_to_keep = [col for col in MRI.columns if not str(col).startswith('Unnamed:')]
        MRI_cleaned = MRI[columns_to_keep].copy()
        MRI_cleaned.dropna(axis=1, how='all', inplace=True)
        columns = MRI_cleaned.columns.tolist()
        print(f"Cleaning complete, {len(columns)} columns remaining.")
        # -----------------------
    except Exception as e:
        print(f"Error cleaning data: {e}")
        return False

    # --- Save the cleaned Excel ---
    print(f"Saving cleaned Excel file to: {output_excel}")
    try:
        os.makedirs(os.path.dirname(output_excel), exist_ok=True)
        MRI_cleaned.to_excel(output_excel, index=False)
    except Exception as e:
        print(f"Error saving cleaned Excel file: {e}")
        # return False

    # --- Create and save JSON template ---
    print("Creating JSON template...")
    json_template = {col: "" for col in columns}

    print(f"Saving JSON template to: {output_json}")
    try:
        os.makedirs(os.path.dirname(output_json), exist_ok=True)
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(json_template, f, indent=config.JSON_INDENT, ensure_ascii=config.ENSURE_ASCII)
    except Exception as e:
       print(f"Error saving JSON template: {e}")
       return False

    print(f"\nSuccess:")
    print(f"- Cleaned Excel file saved to: {output_excel}")
    print(f"- JSON template saved to: {output_json}")
    return True


if __name__ == "__main__":
    success = extract_and_clean()
    if not success:
        sys.exit(1)

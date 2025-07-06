# src/data_validation.py

import sys
import json
import difflib
import os
import config # Import our updated config

# --- Helper Functions (Your functions - no changes needed) ---
def load_json(file_path):
    """Loads a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not load JSON file, not found: {file_path}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Error parsing JSON file: {file_path} - {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"An unknown error occurred while loading JSON file {file_path}: {e}", file=sys.stderr)
        return None

def get_keys(data):
    """Gets all keys from the first level of a dictionary."""
    if data is None:
        return set()
    return set(data.keys())

def find_similar_keys(template_keys, extracted_keys):
    """Finds keys in extracted_keys that are similar to keys in template_keys."""
    similar = {}
    for key in extracted_keys:
        matches = difflib.get_close_matches(key, template_keys, n=1, cutoff=config.SIMILARITY_CUTOFF)
        if matches:
            if key != matches[0]:
                similar[key] = matches[0]
    return similar

# --- Main Check and Fix Logic (Your function - no changes needed) ---
def check_and_fix(template_path, input_json_path, output_json_path):
    """
    Checks extracted JSON data against a template, fixes discrepancies, and saves the corrected data.
    """
    print(f"\nValidating file: {os.path.basename(input_json_path)}")
    print(f"Using template: {os.path.basename(template_path)}")

    template_data = load_json(template_path)
    extracted_data = load_json(input_json_path)

    if template_data is None or extracted_data is None:
        print(f"Error: Could not load JSON files, validation aborted.", file=sys.stderr)
        return False

    template_keys = get_keys(template_data)
    extracted_keys = get_keys(extracted_data)
    
    missing_in_extracted = template_keys - extracted_keys
    extra_in_extracted = extracted_keys - template_keys
    
    similar_keys_to_rename = find_similar_keys(template_keys, extra_in_extracted)
    keys_to_delete = extra_in_extracted - set(similar_keys_to_rename.keys())

    corrected_data = extracted_data.copy()

    if missing_in_extracted:
        print("Info: Adding missing keys with template's default value...")
        for key in sorted(list(missing_in_extracted)):
            corrected_data[key] = template_data.get(key, "") # Use template's default

    if similar_keys_to_rename:
        print("Info: Correcting misspelled keys...")
        for wrong_key, correct_key in sorted(similar_keys_to_rename.items()):
            print(f"  - Renaming '{wrong_key}' -> '{correct_key}'")
            if wrong_key in corrected_data:
                corrected_data[correct_key] = corrected_data.pop(wrong_key)

    if keys_to_delete:
        print("Info: Removing extra keys...")
        for key in sorted(list(keys_to_delete)):
            print(f"  - Deleting '{key}'")
            if key in corrected_data:
                del corrected_data[key]
    
    try:
        os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(corrected_data, f, indent=config.JSON_INDENT, ensure_ascii=config.ENSURE_ASCII)
        print(f"\nValidation complete. Corrected file saved to: {output_json_path}")
        return True
    except Exception as e:
        print(f"Error saving the corrected JSON file '{output_json_path}': {e}", file=sys.stderr)
        return False

# --- Main Function ---
# --- MODIFIED: Reworked to use the new config and argument structure ---
def main(dataset_name, report_id, provider_name, model_name_slug):
    """
    Main function to orchestrate the validation and fixing of a JSON file.
    """
    print(f"\n--- Starting Validation for Report: {report_id}, Dataset: {dataset_name} ---")

    # 1. Get all paths dynamically from the config module
    try:
        dataset_config = config.DATASET_CONFIGS[dataset_name]
        template_path = dataset_config["template_json"]
        
        raw_json_dir = config.get_extracted_json_raw_dir(provider_name, model_name_slug, dataset_name)
        checked_json_dir = config.get_extracted_json_checked_dir(provider_name, model_name_slug, dataset_name)
    except KeyError:
        print(f"FATAL: Dataset '{dataset_name}' is not defined in config.py.", file=sys.stderr)
        sys.exit(1)

    # 2. Define the full input and output file paths
    # The filename format is now consistent across all scripts: {report_id}_...
    input_json_path = os.path.join(raw_json_dir, f"{report_id}_extracted_data.json")
    output_json_path = os.path.join(checked_json_dir, f"{report_id}_validated_data.json")

    print(f"Input raw JSON path: {input_json_path}")
    print(f"Output validated JSON path: {output_json_path}")

    # 3. Run the validation and fixing process
    if not os.path.exists(input_json_path):
       print(f"FATAL: Input JSON file for validation not found at {input_json_path}", file=sys.stderr)
       raise FileNotFoundError(f"Input JSON file not found: {input_json_path}")

    success = check_and_fix(template_path, input_json_path, output_json_path)
    
    if not success:
        raise RuntimeError("The check_and_fix process failed.")

# --- Script Execution Block ---
# --- MODIFIED: Updated to handle the new arguments from main.py ---
if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(f"Usage: python {os.path.basename(__file__)} <dataset_name> <report_id> <provider_name> <model_name_slug>", file=sys.stderr)
        print("Example: python data_validation.py benson RRI002 openai gpt-4-turbo", file=sys.stderr)
        sys.exit(1)

    dataset_name_arg = sys.argv[1]
    report_id_arg = sys.argv[2]
    provider_name_arg = sys.argv[3]
    model_name_slug_arg = sys.argv[4]

    try:
        main(dataset_name_arg, report_id_arg, provider_name_arg, model_name_slug_arg)
        print(f"\nJSON data validation completed for report {report_id_arg}.")
    except Exception as e:
        print(f"\nAn error occurred during data validation for report {report_id_arg}: {e}", file=sys.stderr)
        sys.exit(1) # Exit with a non-zero code to indicate failure
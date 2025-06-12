import sys
import json
import difflib
import os
import config # Import the config module

# project_root is defined in config, no need to redefine here

# --- Helper Functions (load_json, get_keys - remain largely the same) ---
def load_json(file_path):
    """
    Loads a JSON file.
    Args:
        file_path (str): The path to the JSON file.
    Returns:
        dict: The loaded JSON data as a dictionary, or None if an error occurs.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not load JSON file, not found: {file_path}")
        return None
    except json.JSONDecodeError as e: # Corrected typo from JSONDecodeErrorr
        print(f"Error: Error parsing JSON file: {file_path} - {e}")
        return None
    except Exception as e:
        print(f"An unknown error occurred while loading JSON file {file_path}: {e}")
        return None

def get_keys(data):
    """
    Gets all keys from the first level of a dictionary.
    Args:
        data (dict): The dictionary to extract keys from.
    Returns:
        set: A set of keys, or an empty set if data is None.
    """
    if data is None:
        return set()
    return set(data.keys())

def find_similar_keys(template_keys, extracted_keys):
    """
    Finds keys in extracted_keys that are similar to keys in template_keys.
    Args:
        template_keys (set): A set of keys from the template.
        extracted_keys (set): A set of keys from the extracted data.
    Returns:
        dict: A dictionary mapping misspelled keys to their correct counterparts.
    """
    similar = {}
    for key in extracted_keys:
        # Use similarity cutoff from config
        matches = difflib.get_close_matches(key, template_keys, n=1, cutoff=config.SIMILARITY_CUTOFF)
        if matches:
            if key != matches[0]: # If a close match is found and it's not an exact match
                similar[key] = matches[0]
    return similar

# --- Main Check and Fix Logic ---
def check_and_fix(template_path, input_json_path, output_json_path):
    """
    Checks extracted JSON data against a template, fixes discrepancies, and saves the corrected data.
    Args:
        template_path (str): Path to the JSON template file.
        input_json_path (str): Path to the raw extracted JSON file.
        output_json_path (str): Path to save the corrected JSON file.
    Returns:
        bool: True if successful, False otherwise.
    """
    print(f"\nValidating file: {os.path.basename(input_json_path)}")
    print(f"Using template: {os.path.basename(template_path)}")

    template_data = load_json(template_path)
    extracted_data = load_json(input_json_path)

    if template_data is None:
        print(f"Error: Could not load template JSON file '{template_path}', validation aborted.")
        return False
    if extracted_data is None:
        print(f"Error: Could not load extracted JSON file '{input_json_path}', validation aborted.")
        # It might be an empty file or truly missing, either way, can't proceed.
        return False # Or raise an error if this should be fatal

    template_keys = get_keys(template_data)
    extracted_keys = get_keys(extracted_data)

    missing_in_extracted = template_keys - extracted_keys
    extra_in_extracted = extracted_keys - template_keys # Keys in extracted but not in template

    # Find keys that are in extra_in_extracted but are just misspellings of template_keys
    similar_keys_to_rename = find_similar_keys(template_keys, extra_in_extracted)

    # Keys that are truly extra (not similar to any template key) and should be deleted
    keys_to_delete = extra_in_extracted - set(similar_keys_to_rename.keys())

    corrected_data = extracted_data.copy() # Start with a copy of the extracted data

    # 1. Add missing keys (present in template, missing in extracted)
    if missing_in_extracted:
        print("Info: The following field names are missing in the extracted file (will be added with the template's default value ''):")
        for key in sorted(list(missing_in_extracted)): # Sort for consistent output
            print(f"  - {key}")
            corrected_data[key] = template_data.get(key, "") # Use template's default or ""

    # 2. Rename similar keys (misspelled in extracted, correct in template)
    if similar_keys_to_rename:
        print("Info: The following extracted field names may be misspelled and have been corrected (extracted file -> template):")
        for wrong_key, correct_key in sorted(similar_keys_to_rename.items()): # Sort for consistency
            print(f"  - '{wrong_key}' -> '{correct_key}'")
            if wrong_key in corrected_data: # Ensure the key still exists before popping
                corrected_data[correct_key] = corrected_data.pop(wrong_key)

    # 3. Delete extra keys (present in extracted, not in template and not similar)
    if keys_to_delete:
        print("Info: The following extra field names were found in the extracted file (will be removed):")
        for key in sorted(list(keys_to_delete)): # Sort for consistent output
            print(f"  - {key}")
            if key in corrected_data: # Ensure the key still exists before deleting
                del corrected_data[key]
    
    # Ensure the output directory exists
    try:
        os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    except Exception as e:
        print(f"Error: Failed to create output directory '{os.path.dirname(output_json_path)}': {e}")
        return False

    # Save the corrected data
    try:
        with open(output_json_path, 'w', encoding='utf-8') as f:
            # Use formatting constants from config
            json.dump(corrected_data, f, indent=config.JSON_INDENT, ensure_ascii=config.ENSURE_ASCII)
        print(f"\nValidation complete. Corrected file has been saved to: {output_json_path}")
        return True
    except Exception as e:
        print(f"Error saving the corrected JSON file '{output_json_path}': {e}")
        return False

def main(report_id, provider_name, model_name_slug):
    """
    Main function to validate and fix JSON data for a given report, provider, and model.
    Args:
        report_id (str): The report ID (e.g., "RRI002").
        provider_name (str): The LLM provider name (e.g., "openai").
        model_name_slug (str): The model name slug for directory naming (e.g., "gpt-4o").
    """
    report_id_formatted = report_id[:3] + " " + report_id[3:] # Format for filenames "RRI XXX"

    # Template path is general
    template_path = config.TEMPLATE_JSON_PATH

    # Input and output paths are specific to provider and model
    input_json_path = os.path.join(
        config.get_extracted_json_raw_dir(provider_name, model_name_slug),
        f"{report_id_formatted}_extracted_data.json"
    )
    output_json_path = os.path.join(
        config.get_extracted_json_checked_dir(provider_name, model_name_slug),
        f"{report_id_formatted}_extracted_data.json"
    )

    print(f"\nStarting validation for report {report_id} (Provider: {provider_name}, Model: {model_name_slug})")
    print(f"Input raw JSON path: {input_json_path}")
    print(f"Output validated JSON path: {output_json_path}")


    if not os.path.exists(input_json_path):
       print(f"Error: Input JSON file for validation not found: {input_json_path}")
       # This error will be caught by the main.py's subprocess handling if raised
       raise FileNotFoundError(f"Input JSON file for validation not found: {input_json_path}")

    success = check_and_fix(template_path, input_json_path, output_json_path)
    if not success:
        # This error will be caught by the main.py's subprocess handling if raised
        raise RuntimeError(f"Failed to validate and fix the JSON file for report {report_id} (Provider: {provider_name}, Model: {model_name_slug})")

if __name__ == "__main__":
    # This script expects three arguments: report_id, provider_name, model_name_slug
    if len(sys.argv) != 4:
        print(f"Usage: python {os.path.basename(__file__)} <report_id> <provider_name> <model_name_slug>")
        print("Example: python data_validation.py RRI002 openai gpt-4o")
        sys.exit(1)

    report_id_arg = sys.argv[1]
    provider_name_arg = sys.argv[2]
    model_name_slug_arg = sys.argv[3] # This is the fs-safe slug

    try:
        main(report_id_arg, provider_name_arg, model_name_slug_arg)
        print(f"\nJSON data validation completed for report {report_id_arg} (Provider: {provider_name_arg}, Model: {model_name_slug_arg}).")
    except Exception as e:
        # Error messages from main() or check_and_fix() should be informative
        print(f"\nAn error occurred while validating JSON data for report {report_id_arg} (Provider: {provider_name_arg}, Model: {model_name_slug_arg}), aborted.")
        sys.exit(1) # Exit with a non-zero code to indicate failure

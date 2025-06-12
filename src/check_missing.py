import os
import re
import sys
import pandas as pd # For reading Excel
import argparse # For command-line arguments

# Attempt to import config, with a fallback
try:
    import config # Try importing project config
except ImportError:
    try:
        from src import config # If running as a module from project root
    except ImportError:
        print("Error: Could not import config.py. Please ensure the relative path to config.py is correct, or add the directory containing it to the Python path.")
        sys.exit(1)

def get_expected_ids_from_pdfs(pdf_directory):
    """
    Scans the specified PDF directory for filenames and extracts expected report IDs (format RRIXXX).
    """
    expected_ids = set()
    # Regex to find RRIXXX.pdf or RRI XXX.pdf (case insensitive)
    pattern = re.compile(r'^RRI\s?(\d{3})\.pdf$', re.IGNORECASE)

    print(f"Scanning PDF directory for a list of expected reports: {pdf_directory}")
    if not os.path.isdir(pdf_directory):
        print(f"Error: The specified PDF directory does not exist: {pdf_directory}")
        return None # Return None to indicate failure

    try:
        count = 0
        for filename in os.listdir(pdf_directory):
            match = pattern.match(filename)
            if match:
                report_num = match.group(1)
                report_id = f"RRI{report_num}" # Standardize to RRIXXX
                expected_ids.add(report_id)
                count += 1
        print(f"Found {count} expected report IDs from PDF filenames.")
        return expected_ids
    except Exception as e:
        print(f"Error while scanning PDF directory '{pdf_directory}': {e}")
        return None

def get_successful_ids_from_accuracy_reports(accuracy_dir_for_llm):
    """
    Scans the specified accuracy reports directory for filenames and extracts successfully processed report IDs.
    Assumes accuracy filenames are like "RRI XXX_accuracy.txt".
    Args:
        accuracy_dir_for_llm (str): The path to the accuracy reports directory for a specific LLM.
    """
    successful_ids = set()
    # Regex to capture "RRI XXX" from "RRI XXX_accuracy.txt"
    pattern = re.compile(r'^(RRI\s\d{3})_accuracy\.txt$', re.IGNORECASE)

    print(f"Scanning accuracy report directory: {accuracy_dir_for_llm}")
    if not os.path.isdir(accuracy_dir_for_llm):
        print(f"Error: The specified accuracy report directory does not exist: {accuracy_dir_for_llm}")
        return None # Return None to indicate failure

    try:
        count = 0
        for filename in os.listdir(accuracy_dir_for_llm):
            match = pattern.match(filename)
            if match:
                report_id_with_space = match.group(1) # This is "RRI XXX"
                report_id = report_id_with_space.replace(' ', '') # Standardize to RRIXXX
                successful_ids.add(report_id)
                count += 1
        print(f"Found {count} successfully processed report IDs from accuracy report filenames.")
        return successful_ids
    except Exception as e:
        print(f"Error scanning accuracy report directory '{accuracy_dir_for_llm}': {e}")
        return None

def get_ids_from_ground_truth(excel_path, id_column_names_list):
    """
    Reads report ID column from the Ground Truth Excel file and returns a set of standardized IDs (RRIXXX).
    """
    print(f"Reading Ground Truth Excel file to get a list of IDs: {excel_path}")
    if not os.path.exists(excel_path):
        print(f"Error: Ground Truth Excel file not found: {excel_path}")
        return None

    try:
        df_true = pd.read_excel(excel_path, dtype=str) # Read all columns as strings
        
        id_col_name_found = None
        for col_name in id_column_names_list:
            if col_name in df_true.columns:
                id_col_name_found = col_name
                break
        
        if not id_col_name_found:
            print(f"Error: Could not find the specified report ID column in the Excel file '{excel_path}' (checked for: {id_column_names_list}).")
            return None

        print(f"Found report ID column: '{id_col_name_found}'")
        
        # Extract IDs, convert to string, remove all whitespace, get unique, remove NAs/empty strings
        ground_truth_ids = set(
            df_true[id_col_name_found]
            .dropna() # Remove NA values
            .astype(str) # Ensure all are strings
            .str.replace(r'\s+', '', regex=True) # Remove all whitespace (e.g. "RRI 002" -> "RRI002")
            .str.upper() # Standardize to uppercase e.g. rri002 -> RRI002
            .unique() # Get unique values
        )
        ground_truth_ids.discard('') # Remove any empty string ID that might result
        
        print(f"Found {len(ground_truth_ids)} valid report IDs from the Ground Truth Excel.")
        return ground_truth_ids

    except Exception as e:
        print(f"Error reading or processing the Ground Truth Excel file '{excel_path}': {e}")
        return None

def find_missing_reports_for_provider_model(provider_name, model_name_slug):
    """
    Compares expected reports (from PDFs), successfully processed reports (from accuracy files
    for the given provider/model), and Ground Truth reports to find discrepancies.
    Args:
        provider_name (str): The LLM provider name.
        model_name_slug (str): The model name slug (filesystem-safe).
    """
    print(f"\n--- Checking for missing reports for provider '{provider_name}', model '{model_name_slug}' ---")

    # Get general paths from config (not LLM specific)
    pdf_dir = config.DEFAULT_PDF_SCAN_DIR
    ground_truth_excel = config.CLEANED_GROUND_TRUTH_XLSX
    id_columns_in_gt = config.REPORT_ID_COLUMN_NAMES

    # Get LLM-specific accuracy reports directory
    accuracy_dir_for_llm = config.get_accuracy_reports_dir(provider_name, model_name_slug)

    # --- Fetch ID sets ---
    expected_ids_from_pdf = get_expected_ids_from_pdfs(pdf_dir)
    # Pass the specific accuracy directory to the function
    successful_ids_for_llm = get_successful_ids_from_accuracy_reports(accuracy_dir_for_llm)
    ground_truth_ids_from_excel = get_ids_from_ground_truth(ground_truth_excel, id_columns_in_gt)

    # --- Handle cases where fetching any ID set failed ---
    if expected_ids_from_pdf is None:
        print("Since expected IDs could not be fetched from PDF files, some comparisons will be skipped.")
        expected_ids_from_pdf = set() # Use empty set to allow other comparisons
    if successful_ids_for_llm is None:
        print(f"Since successful IDs could not be fetched from the accuracy report directory '{accuracy_dir_for_llm}', some comparisons will be skipped.")
        successful_ids_for_llm = set()
    if ground_truth_ids_from_excel is None:
        print("Since IDs could not be fetched from the Ground Truth Excel, some comparisons will be skipped.")
        ground_truth_ids_from_excel = set()
    
    # --- Perform Comparisons ---
    print(f"\n--- Report Processing Status Cross-Check Results ({provider_name} / {model_name_slug}) ---")
    print(f"Total expected reports (from PDF files): {len(expected_ids_from_pdf)}")
    print(f"Total reports in Ground Truth Excel: {len(ground_truth_ids_from_excel)}")
    print(f"Number of accuracy reports generated for this provider/model: {len(successful_ids_for_llm)}")

    # Check 1: PDFs that are in Ground Truth but no accuracy report for this LLM/model
    gt_ids_not_in_successful_llm = ground_truth_ids_from_excel - successful_ids_for_llm
    if gt_ids_not_in_successful_llm:
        print(f"\n[Check 1] **NOTE**: The following {len(gt_ids_not_in_successful_llm)} report IDs exist in the Ground Truth, but a corresponding accuracy report was not found ({provider_name}/{model_name_slug}):")
        for report_id in sorted(list(gt_ids_not_in_successful_llm)):
            print(f"  - {report_id}")
    else:
        print(f"\n[Check 1] Pass: All report IDs in the Ground Truth have an accuracy report generated for this provider/model (or the Ground Truth is empty).")

    # Check 2: PDFs found in scan, but no accuracy report for this LLM/model
    # This is particularly relevant if processing is done for all PDFs.
    pdf_ids_not_in_successful_llm = expected_ids_from_pdf - successful_ids_for_llm
    if pdf_ids_not_in_successful_llm:
        print(f"\n[Check 2] **NOTE**: The following {len(pdf_ids_not_in_successful_llm)} report IDs exist in the PDF scan directory, but a corresponding accuracy report was not found ({provider_name}/{model_name_slug}):")
        for report_id in sorted(list(pdf_ids_not_in_successful_llm)):
            print(f"  - {report_id}")
    else:
        print(f"\n[Check 2] Pass: All report IDs scanned from the PDF directory have an accuracy report generated for this provider/model (or the PDF scan list is empty).")

    # --- Additional Optional Checks (can be expanded) ---
    # Check 3: IDs in PDF scan but not in Ground Truth
    pdf_ids_not_in_gt = expected_ids_from_pdf - ground_truth_ids_from_excel
    if pdf_ids_not_in_gt:
        print(f"\n[Additional Info 1] The following {len(pdf_ids_not_in_gt)} report IDs exist in the PDF scan directory but were not found in the Ground Truth Excel:")
        for report_id in sorted(list(pdf_ids_not_in_gt)):
            print(f"  - {report_id}")

    # Check 4: IDs in Ground Truth but not in PDF scan
    gt_ids_not_in_pdf = ground_truth_ids_from_excel - expected_ids_from_pdf
    if gt_ids_not_in_pdf:
        print(f"\n[Additional Info 2] The following {len(gt_ids_not_in_pdf)} report IDs exist in the Ground Truth Excel, but a corresponding PDF file was not found in the PDF scan directory:")
        for report_id in sorted(list(gt_ids_not_in_pdf)):
            print(f"  - {report_id}")
            
    # Check 5: Accuracy reports present for this LLM/model but corresponding ID not in Ground Truth
    successful_llm_ids_not_in_gt = successful_ids_for_llm - ground_truth_ids_from_excel
    if successful_llm_ids_not_in_gt:
        print(f"\n[Additional Info 3] Accuracy reports for the following {len(successful_llm_ids_not_in_gt)} IDs exist ({provider_name}/{model_name_slug}), but their IDs were not found in the Ground Truth Excel:")
        for report_id in sorted(list(successful_llm_ids_not_in_gt)):
            print(f"  - {report_id}")

    print(f"\n--- Check completed ({provider_name} / {model_name_slug}) ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check for missing reports for a specified LLM provider and model by comparing PDFs, Ground Truth, and accuracy reports."
    )
    parser.add_argument("provider_name", help="The name of the LLM provider (e.g., openai, gemini, claude).")
    parser.add_argument("model_name_slug", help="The identifier for the LLM model (filesystem-safe version, e.g., gpt-4o, gemini-1.5-pro-latest).")
    
    args = parser.parse_args()

    # Basic validation of inputs
    if args.provider_name not in config.LLM_PROVIDERS:
        print(f"Error: Unknown provider '{args.provider_name}'. Options are: {list(config.LLM_PROVIDERS.keys())}")
        sys.exit(1)
    if not args.model_name_slug.strip(): # Check if slug is not empty or just whitespace
        print(f"Error: model_name_slug cannot be empty.")
        sys.exit(1)
    
    # It's also good practice to ensure the model_name_slug is somewhat valid for the provider,
    # though main.py should ideally pass valid slugs.
    # For example, check if a directory for this slug could exist or matches a known pattern.

    find_missing_reports_for_provider_model(args.provider_name, args.model_name_slug)
    print("Done.")
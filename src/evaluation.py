import sys
import pandas as pd
import numpy as np
import os
# Optional: Use tabulate for better diff printing if installed
try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False
import config # Import the config module

# --- Helper Functions (No changes needed in these helpers) ---

def standardize_columns(df):
    """Applies column name standardization based on config mapping."""
    # Use mapping from config
    df.rename(columns=config.COLUMN_NAME_MAPPING, inplace=True, errors='ignore') # ignore if a column doesn't exist
    return df

def preprocess(df):
    """Applies general preprocessing: converts to string, strips whitespace, normalizes NA values."""
    # Convert all to string first to handle mixed types before stripping/replacing
    df = df.astype(str)
    # Strip leading/trailing whitespace from all string cells
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x) # More robust stripping for pandas Series
    # Define multiple NA representations to replace (case-insensitive using regex)
    # Ensure the regex matches whole cell content using anchors ^$
    na_patterns = [r'^\s*$', r'^(nan|none|na|n/a|nat|unspecified|not specified|null)\s*$'] # Added 'null'
    for pattern in na_patterns:
        df.replace(pattern, pd.NA, inplace=True, regex=True)
    return df

def cells_equal(val1, val2):
    """
    Compares two cell values with added tolerances:
    1. NA vs NA -> True
    2. NA vs common 'unspecified'/'empty' strings / '0' -> True (case-insensitive)
    3. Boolean mapping: '1'/'0' vs. common true/false strings -> True if match
    4. Float comparison using np.isclose for tolerance.
    5. String comparison ignoring case.
    """
    # 1. Handle NA vs NA
    isna1 = pd.isna(val1)
    isna2 = pd.isna(val2)
    if isna1 and isna2:
        return True

    # Define sets for common strings (lowercase) for faster lookups
    unspecified_strings = {'unspecified', 'not specified', 'n/a', 'na', '', 'null'} # Added 'null'
    true_strings = {'yes', 'present', 'true', 'active', 'positive', 'complete', 'conventional'}
    false_strings = {'no', 'absent', 'false', 'inactive', 'negative', 'normal'} # 'normal' often implies absence of pathology

    # Convert to comparable string representations (lowercase, stripped) AFTER initial NA checks
    s1 = str(val1).strip().lower() if not isna1 else None
    s2 = str(val2).strip().lower() if not isna2 else None

    # 2. Handle NA vs Unspecified String / Zero / Empty
    if isna1 or isna2:
        non_na_val_str = s2 if isna1 else s1
        # If one is NA and the other is considered an "empty" or "zero" equivalent
        if non_na_val_str in unspecified_strings or non_na_val_str == '0':
              return True
        return False # One is NA, the other is something meaningful -> Not equal

    # --- At this point, neither val1 nor val2 is NA ---

    # 3. Handle Boolean Mapping (e.g., "1" vs "yes", "0" vs "no")
    # Check if s1 represents a "true" value (either '1' or in true_strings)
    is_s1_true_type = (s1 == '1') or (s1 in true_strings)
    # Check if s1 represents a "false" value (either '0' or in false_strings)
    is_s1_false_type = (s1 == '0') or (s1 in false_strings)

    # Check if s2 represents a "true" value
    is_s2_true_type = (s2 == '1') or (s2 in true_strings)
    # Check if s2 represents a "false" value
    is_s2_false_type = (s2 == '0') or (s2 in false_strings)

    # If both are "true" type or both are "false" type, they are considered equal
    if (is_s1_true_type and is_s2_true_type) or \
       (is_s1_false_type and is_s2_false_type):
        return True
    # If one is "true" type and the other is "false" type, they are not equal
    # This also covers cases where one is boolean-like and the other is not recognized as such.
    if (is_s1_true_type and is_s2_false_type) or \
       (is_s1_false_type and is_s2_true_type):
        return False

    # 4. Handle Numeric Comparison (Floats with tolerance)
    try:
        f1 = float(val1) # Attempt to convert val1 to float
        f2 = float(val2) # Attempt to convert val2 to float
        return np.isclose(f1, f2, equal_nan=False) # equal_nan=False because NAs handled above
    except (ValueError, TypeError):
        # If conversion to float fails, proceed to string comparison
        pass

    # 5. Handle String Comparison (Case-Insensitive) as final fallback
    return s1 == s2


# --- Main Evaluation Logic ---
def main(report_id, provider_name, model_name_slug):
    """
    Loads data, preprocesses, compares, and saves accuracy for a given report ID,
    LLM provider, and model.
    Args:
        report_id (str): The report ID (e.g., "RRI002").
        provider_name (str): The LLM provider name (e.g., "openai").
        model_name_slug (str): The model name slug for directory naming (e.g., "gpt-4o").
    """
    report_id_formatted = report_id[:3] + " " + report_id[3:] # "RRI XXX" for filenames

    print(f"\nStarting evaluation for report {report_id} (Provider: {provider_name}, Model: {model_name_slug})")
    # print(f"Original report_id: {report_id}")
    # print(f"Formatted report_id_formatted (for filenames): {report_id_formatted}")

    # --- Get Paths from Config ---
    true_data_path = config.CLEANED_GROUND_TRUTH_XLSX # Ground truth path is general

    # Extracted data path is specific to provider and model
    extracted_excel_folder = config.get_extracted_excel_dir(provider_name, model_name_slug)
    extracted_data_path = os.path.join(extracted_excel_folder, f"{report_id_formatted}_extracted_data.xlsx")

    # Accuracy report output path is specific to provider and model
    accuracy_folder = config.get_accuracy_reports_dir(provider_name, model_name_slug)
    accuracy_file = os.path.join(accuracy_folder, f"{report_id_formatted}_accuracy.txt")

    # Ensure the output directory for accuracy files exists
    try:
        os.makedirs(accuracy_folder, exist_ok=True)
    except Exception as e:
        print(f"Error: Failed to create accuracy report output directory '{accuracy_folder}': {e}")
        raise IOError(f"Error creating accuracy report output directory: {e}")

    # --- Check Input Files ---
    print(f"Ground Truth Path: {true_data_path}")
    print(f"Extracted Excel Path: {extracted_data_path}")
    print(f"Accuracy Report Output Path: {accuracy_file}")

    if not os.path.exists(true_data_path):
        print(f"❌ Error: Ground truth file not found: {true_data_path}")
        raise FileNotFoundError(f"Ground truth file not found: {true_data_path}")
    if not os.path.exists(extracted_data_path):
        print(f"❌ Error: Extracted data Excel file not found: {extracted_data_path}")
        raise FileNotFoundError(f"Extracted data Excel file not found for {provider_name}/{model_name_slug}: {extracted_data_path}")

    # --- Read Data (Read all as string initially to preserve original formatting for diffs) ---
    try:
        df_true_orig = pd.read_excel(true_data_path, dtype=str)
        df_extracted_orig = pd.read_excel(extracted_data_path, dtype=str)
    except Exception as e:
       print(f"❌ Error reading Excel files: {e}")
       raise IOError(f"Error reading Excel files: {e}")

    # --- Find Report ID Column in both dataframes ---
    # Use the list of possible ID column names from config
    id_col_true = next((col for col in config.REPORT_ID_COLUMN_NAMES if col in df_true_orig.columns), None)
    id_col_extracted = next((col for col in config.REPORT_ID_COLUMN_NAMES if col in df_extracted_orig.columns), None)

    if not id_col_true:
        raise ValueError(f"Error: Could not find report ID column in ground truth file '{true_data_path}' (checked for: {config.REPORT_ID_COLUMN_NAMES}).")
    if not id_col_extracted:
        raise ValueError(f"Error: Could not find report ID column in extracted data file '{extracted_data_path}' (checked for: {config.REPORT_ID_COLUMN_NAMES}).")

    # --- Filter Data for the specific report_id ---
    # Clean ID columns first for reliable filtering
    df_true_orig[id_col_true] = df_true_orig[id_col_true].astype(str).str.strip().str.replace(r'\s+', '', regex=True)
    df_extracted_orig[id_col_extracted] = df_extracted_orig[id_col_extracted].astype(str).str.strip().str.replace(r'\s+', '', regex=True)
    
    # Filter using the non-formatted report_id (e.g., "RRI002") as IDs in sheets should be clean
    df_true_filtered = df_true_orig[df_true_orig[id_col_true] == report_id].copy()
    # Extracted data's "Report ID" field might have the space, but we added it consistently in api_interaction.
    # However, if it was manually edited or comes from a different source, it might vary.
    # For comparison, we ensure the ID column in df_extracted_orig is also cleaned.
    df_extracted_filtered = df_extracted_orig[df_extracted_orig[id_col_extracted] == report_id].copy()


    if df_true_filtered.empty:
        raise ValueError(f"Could not find record with ID = '{report_id}' in ground truth data. Please check the Ground Truth file.")
    if df_extracted_filtered.empty:
        # Try with formatted ID as a fallback if the extracted file used that in its ID column
        df_extracted_filtered_fallback = df_extracted_orig[df_extracted_orig[id_col_extracted] == report_id_formatted.replace(" ","")].copy()
        if df_extracted_filtered_fallback.empty:
            raise ValueError(f"Could not find record with ID = '{report_id}' (or '{report_id_formatted.replace(' ','')}') in extracted data. Please check the extracted Excel file.")
        else:
            df_extracted_filtered = df_extracted_filtered_fallback
            print(f"Info: Found record in extracted data using fallback ID '{report_id_formatted.replace(' ','')}'.")


    # --- Standardize Column Names ---
    df_true_std = standardize_columns(df_true_filtered.copy()) # Use .copy() to avoid SettingWithCopyWarning
    df_extracted_std = standardize_columns(df_extracted_filtered.copy())

    # --- Align Columns (use only common columns for fair comparison) ---
    common_cols = sorted(list(set(df_true_std.columns) & set(df_extracted_std.columns)))
    
    # Attempt to find the standardized version of the ID column to ensure it's in common_cols
    # This assumes REPORT_ID_COLUMN_NAMES in config contains the *original* names,
    # and COLUMN_NAME_MAPPING might standardize them.
    # For simplicity, we'll assume the ID column name is consistent after standardization if present.
    # A more robust way would be to track the ID column name through standardization.
    
    # Re-check for ID column in common_cols (it might have been standardized)
    # Use the first name from config.REPORT_ID_COLUMN_NAMES that exists in common_cols
    id_col_in_common = next((col for col in config.REPORT_ID_COLUMN_NAMES if col in common_cols), None)
    if not id_col_in_common: # If original names not found, check standardized names
        standardized_id_names = [config.COLUMN_NAME_MAPPING.get(name, name) for name in config.REPORT_ID_COLUMN_NAMES]
        id_col_in_common = next((col for col in standardized_id_names if col in common_cols), None)

    if id_col_in_common and id_col_in_common not in common_cols: # Should not happen if logic is right
         common_cols.insert(0, id_col_in_common) # Add ID col if somehow missing but found
    elif not id_col_in_common and common_cols : # If no ID column in common, pick first common as placeholder for ordering
        print(f"Warning: Report ID column not found in common columns. It will not be explicitly ordered in the comparison columns. Common columns: {common_cols[:3]}...")


    if not common_cols:
        raise ValueError("Error: No common column names between ground truth and extracted data, cannot compare.")

    df_true_aligned = df_true_std[common_cols].reset_index(drop=True)
    df_extracted_aligned = df_extracted_std[common_cols].reset_index(drop=True)

    # --- Preprocess data for comparison (convert to string, normalize NA, etc.) ---
    # The df_true_processed and df_extracted_processed will be used for the actual comparison
    df_true_processed = preprocess(df_true_aligned.copy())
    df_extracted_processed = preprocess(df_extracted_aligned.copy())

    # Final shape check after alignment and preprocessing
    if df_true_processed.shape != df_extracted_processed.shape:
        raise ValueError(f"Error: DataFrame shapes do not match after alignment and preprocessing. True: {df_true_processed.shape}, Extracted: {df_extracted_processed.shape}. Columns: {common_cols}")
    if df_true_processed.empty: # Should be caught by earlier checks if no rows were found
        raise ValueError("Error: Processed DataFrame is empty, cannot compare.")

    # --- Compare DataFrames Cell by Cell and Calculate Accuracy ---
    true_values_for_comparison = df_true_processed.values
    extracted_values_for_comparison = df_extracted_processed.values
    
    try:
        # Apply the enhanced cells_equal function element-wise
        correct_mask = np.vectorize(cells_equal)(true_values_for_comparison, extracted_values_for_comparison)
    except Exception as e:
        print(f"Internal error during cell comparison: {e}")
        # Detailed debugging for cell-wise comparison errors:
        # for r_idx in range(true_values_for_comparison.shape[0]):
        #     for c_idx in range(true_values_for_comparison.shape[1]):
        #         try:
        #             cells_equal(true_values_for_comparison[r_idx, c_idx], extracted_values_for_comparison[r_idx, c_idx])
        #         except Exception as cell_e:
        #             print(f"Error at row {r_idx}, col {c_idx} ('{common_cols[c_idx]}'):")
        #             print(f"  True Val: '{true_values_for_comparison[r_idx, c_idx]}', Type: {type(true_values_for_comparison[r_idx, c_idx])}")
        #             print(f"  Extracted Val: '{extracted_values_for_comparison[r_idx, c_idx]}', Type: {type(extracted_values_for_comparison[r_idx, c_idx])}")
        #             print(f"  Cell-specific error: {cell_e}")
        raise RuntimeError(f"Error during cell comparison: {e}")

    total_cells = correct_mask.size
    correct_cells = np.sum(correct_mask)
    incorrect_cells = total_cells - correct_cells
    accuracy = (correct_cells / total_cells) if total_cells > 0 else 0.0 # Ensure float division and handle empty case

    # --- Print and Save Results ---
    print(f"\n📊 Cell-Level Comparison Results (ID={report_id_formatted}, Provider={provider_name}, Model={model_name_slug})")
    print(f"Total Comparable Cells : {total_cells}")
    print(f"Correct Cells          : {correct_cells}")
    print(f"Incorrect Cells        : {incorrect_cells}")
    print(f"✅ Overall Accuracy     : {accuracy:.4f}")

    try:
        with open(accuracy_file, "w", encoding="utf-8") as f:
            f.write(f"Report ID: {report_id_formatted}\n") # Report ID for this file
            f.write(f"LLM Provider: {provider_name}\n")
            f.write(f"LLM Model: {model_name_slug}\n") # Using slug for consistency in report
            f.write(f"Compared Columns ({len(common_cols)}):\n")
            f.write(f"{', '.join(common_cols)}\n\n") # List common columns compared
            f.write(f"Total comparable cells: {total_cells}\n")
            f.write(f"Correct cells: {correct_cells}\n")
            f.write(f"Incorrect cells: {incorrect_cells}\n")
            f.write(f"Overall accuracy: {accuracy:.4f}\n")

        if incorrect_cells > 0 and true_values_for_comparison.shape[0] > 0: # Ensure there are rows to compare
            diff_list = []
            # Iterate through the mask to find differing cells
            for r_idx in range(correct_mask.shape[0]): # Should only be one row after filtering
                for c_idx in range(correct_mask.shape[1]):
                    if not correct_mask[r_idx, c_idx]:
                        # For displaying differences, use the values from df_true_aligned and df_extracted_aligned
                        # These are standardized but not fully preprocessed (e.g., NA normalization)
                        # which might give a clearer view of the original-like differing values.
                        true_val_display = df_true_aligned.iloc[r_idx, c_idx]
                        extracted_val_display = df_extracted_aligned.iloc[r_idx, c_idx]
                        diff_list.append({
                            'Column': common_cols[c_idx],
                            'True Value': true_val_display,
                            'Extracted Value': extracted_val_display
                        })
            
            if diff_list: # If any differences were actually recorded
                diff_df = pd.DataFrame(diff_list)
                diff_output = ""
                if HAS_TABULATE:
                    diff_output = tabulate(diff_df, headers='keys', tablefmt='psql', showindex=False, missingval="<NA>")
                else:
                    diff_output = diff_df.to_string(index=False, na_rep="<NA>")

                with open(accuracy_file, "a", encoding="utf-8") as f:
                    f.write("\n--- Differences ---\n")
                    f.write(diff_output)
            else:
                 print("Info: Incorrect cells were reported, but failed to generate a difference list. Please check the comparison logic.")


        print(f"\nAccuracy and difference details have been saved to: {accuracy_file}")

    except Exception as e:
        print(f"❌ Error saving accuracy file or differences: {e}")
        # Do not re-raise here if main processing was successful, just log the save error.
        # However, if saving the accuracy is critical, then re-raise.
        # For now, let's consider it a non-fatal error for the script's exit code.
        # raise IOError(f"Error saving accuracy file: {e}")


# --- Main Execution Block ---
if __name__ == "__main__":
    # This script expects three arguments: report_id, provider_name, model_name_slug
    if len(sys.argv) != 4:
        print(f"Usage: python {os.path.basename(__file__)} <report_id> <provider_name> <model_name_slug>")
        print("Example: python evaluation.py RRI002 openai gpt-4o")
        sys.exit(1)

    report_id_arg = sys.argv[1]
    provider_name_arg = sys.argv[2]
    model_name_slug_arg = sys.argv[3] # This is the fs-safe slug

    try:
        main(report_id_arg, provider_name_arg, model_name_slug_arg)
        print(f"\nEvaluation completed for report {report_id_arg} (Provider: {provider_name_arg}, Model: {model_name_slug_arg}).")
    except (FileNotFoundError, ValueError, IOError, RuntimeError) as e:
        # Catch specific errors raised from main() for cleaner exit message
        print(f"\nAn error occurred while evaluating report {report_id_arg} (Provider: {provider_name_arg}, Model: {model_name_slug_arg}): {e}")
        sys.exit(1) # Exit with a non-zero code to indicate failure
    except Exception as e:
        # Catch any other unexpected errors
        print(f"\nAn unexpected critical error occurred while evaluating report {report_id_arg} (Provider: {provider_name_arg}, Model: {model_name_slug_arg}): {e}")
        # import traceback # For debugging
        # traceback.print_exc() # For debugging
        sys.exit(1)

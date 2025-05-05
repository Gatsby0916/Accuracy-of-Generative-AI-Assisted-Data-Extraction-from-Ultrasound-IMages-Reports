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
import config # <--- 导入 config 模块

# --- Helper Functions ---

def standardize_columns(df):
    """Applies column name standardization based on config mapping."""
    # Use mapping from config
    df.rename(columns=config.COLUMN_NAME_MAPPING, inplace=True, errors='ignore') # ignore errors if a column doesn't exist
    return df

def preprocess(df):
    """Applies general preprocessing: converts to string, strips whitespace, normalizes NA values."""
    # Convert all to string first to handle mixed types before stripping/replacing
    df = df.astype(str)
    # Strip leading/trailing whitespace from all string cells
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    # Define multiple NA representations to replace (case-insensitive using regex)
    # Ensure the regex matches whole cell content using anchors ^$
    na_patterns = [r'^\s*$', r'^(nan|none|na|n/a|nat|unspecified|not specified)\s*$']
    for pattern in na_patterns:
        df.replace(pattern, pd.NA, inplace=True, regex=True)
    return df

def cells_equal(val1, val2):
    """
    Compares two cell values with added tolerances:
    1. NA vs NA -> True
    2. NA vs common 'unspecified'/'empty' strings -> True (case-insensitive)
    3. NA vs 0/'0' -> True
    4. Boolean mapping: 1 == Yes/Present/True/Active/Positive/Complete (case-insensitive)
    5. Boolean mapping: 0 == No/Absent/False/Inactive/Negative/Normal (case-insensitive)
    6. Float comparison using np.isclose for tolerance.
    7. String comparison ignoring case and leading/trailing whitespace.
    """
    # 1. Handle NA vs NA
    isna1 = pd.isna(val1)
    isna2 = pd.isna(val2)
    if isna1 and isna2:
        return True

    # Define sets for common strings (lowercase) for faster lookups
    unspecified_strings = {'unspecified', 'not specified', 'n/a', 'na', ''}
    true_strings = {'yes', 'present', 'true', 'active', 'positive', 'complete', 'conventional'}
    false_strings = {'no', 'absent', 'false', 'inactive', 'negative', 'normal'}

    # Convert to comparable string representations (lowercase, stripped) AFTER initial NA checks
    s1 = str(val1).strip().lower() if not isna1 else None
    s2 = str(val2).strip().lower() if not isna2 else None

    # 2. Handle NA vs Unspecified String / Zero / Empty
    if isna1 or isna2:
        non_na_val_str = s2 if isna1 else s1
        if non_na_val_str in unspecified_strings or non_na_val_str == '0':
             return True
        return False # One is NA, the other is something meaningful -> Not equal

    # --- At this point, neither val1 nor val2 is NA ---

    # 3. Handle Boolean Mapping (1/0 vs. String and String vs String)
    is_s1_true_type = (s1 == '1') or (s1 in true_strings)
    is_s1_false_type = (s1 == '0') or (s1 in false_strings)
    is_s2_true_type = (s2 == '1') or (s2 in true_strings)
    is_s2_false_type = (s2 == '0') or (s2 in false_strings)

    if (is_s1_true_type and is_s2_true_type) or \
       (is_s1_false_type and is_s2_false_type):
        return True
    if (is_s1_true_type and is_s2_false_type) or \
       (is_s1_false_type and is_s2_true_type):
        return False

    # 4. Handle Numeric Comparison (Floats)
    try:
        f1 = float(val1)
        f2 = float(val2)
        return np.isclose(f1, f2)
    except (ValueError, TypeError):
        # 5. Handle String Comparison (Case-Insensitive) as final fallback
        return s1 == s2

# --- Main Evaluation Logic ---

def main(report_id):
    """Loads data, preprocesses, compares, and saves accuracy for a given report ID."""
    # report_id comes in as "RRIXXX"
    report_id_formatted = report_id[:3] + " " + report_id[3:] # "RRI XXX" for filenames etc.
    print(f"原始 report_id: {report_id}")
    print(f"格式化 report_id_formatted: {report_id_formatted}")

    # --- Get Paths from Config ---
    true_data_path = config.CLEANED_GROUND_TRUTH_XLSX
    extracted_data_path = os.path.join(config.EXTRACTED_EXCEL_DIR, f"{report_id_formatted}_extracted_data.xlsx")
    accuracy_folder = config.ACCURACY_REPORTS_DIR
    os.makedirs(accuracy_folder, exist_ok=True)
    accuracy_file = os.path.join(accuracy_folder, f"{report_id_formatted}_accuracy.txt")

    # --- Check Input Files ---
    if not os.path.exists(true_data_path):
        print(f"❌ 错误：真实数据文件未找到: {true_data_path}")
        raise FileNotFoundError(f"Ground truth file not found: {true_data_path}")
    if not os.path.exists(extracted_data_path):
        print(f"❌ 错误：提取的数据 Excel 文件未找到: {extracted_data_path}")
        raise FileNotFoundError(f"Extracted data Excel file not found: {extracted_data_path}")

    print(f"正在加载真实数据: {true_data_path}")
    print(f"正在加载提取数据: {extracted_data_path}")

    # --- Read Data (Read as string initially) ---
    try:
        df_true = pd.read_excel(true_data_path, dtype=str)
        df_extracted = pd.read_excel(extracted_data_path, dtype=str)
    except Exception as e:
         print(f"❌ 读取 Excel 文件时出错: {e}")
         raise IOError(f"Error reading Excel files: {e}")

    # --- Find Report ID Column ---
    id_col_true = next((col for col in config.REPORT_ID_COLUMN_NAMES if col in df_true.columns), None)
    id_col_extracted = next((col for col in config.REPORT_ID_COLUMN_NAMES if col in df_extracted.columns), None)

    if not id_col_true: raise ValueError(f"错误：在真实数据中找不到报告 ID 列 (检查 {config.REPORT_ID_COLUMN_NAMES})。")
    if not id_col_extracted: raise ValueError(f"错误：在提取数据中找不到报告 ID 列 (检查 {config.REPORT_ID_COLUMN_NAMES})。")

    # --- Filter Data based on Correct ID Format ---
    # Clean ID columns first
    df_true[id_col_true] = df_true[id_col_true].astype(str).str.strip()
    df_extracted[id_col_extracted] = df_extracted[id_col_extracted].astype(str).str.strip()
    
    # Filter using appropriate ID format for each dataframe
    df_true_filtered = df_true[df_true[id_col_true] == report_id].copy() # Use original ID (no space) for true data
    df_extracted_filtered = df_extracted[df_extracted[id_col_extracted] == report_id_formatted].copy() # Use formatted ID (with space) for extracted data

    # Check if filtering was successful
    if df_true_filtered.empty:
        raise ValueError(f"在真实数据中找不到 ID = {report_id} 的记录。请检查 Ground Truth 文件。")
    if df_extracted_filtered.empty:
        raise ValueError(f"在提取数据中找不到 ID = {report_id_formatted} 的记录。请检查提取的 Excel 文件。")

    # --- Standardize Columns ---
    df_true_std = standardize_columns(df_true_filtered)
    df_extracted_std = standardize_columns(df_extracted_filtered)

    # --- Align Columns ---
    common_cols = sorted(list(set(df_true_std.columns) & set(df_extracted_std.columns)))
    
    # Ensure ID column is included if possible (use the name present in common_cols)
    id_col_to_use_in_common = None
    if id_col_true in common_cols:
        id_col_to_use_in_common = id_col_true
    elif id_col_extracted in common_cols:
         id_col_to_use_in_common = id_col_extracted # Should have the same name after standardization if mapping exists

    if id_col_to_use_in_common and id_col_to_use_in_common not in common_cols:
         common_cols.insert(0, id_col_to_use_in_common) # Add ID col if missing but found

    # Keep only common columns
    df_true_aligned = df_true_std[common_cols].reset_index(drop=True)
    df_extracted_aligned = df_extracted_std[common_cols].reset_index(drop=True)

    # --- Preprocess Report ID Column for Comparison ---
    # Standardize the Report ID format *before* general preprocessing and comparison
    if id_col_true in df_true_aligned.columns:
        df_true_aligned[id_col_true] = df_true_aligned[id_col_true].astype(str).str.replace(r'\s+', '', regex=True)
    if id_col_extracted in df_extracted_aligned.columns:
        df_extracted_aligned[id_col_extracted] = df_extracted_aligned[id_col_extracted].astype(str).str.replace(r'\s+', '', regex=True)

    # --- Apply General Preprocessing ---
    df_true_processed = preprocess(df_true_aligned)
    df_extracted_processed = preprocess(df_extracted_aligned)

    # Final shape check
    if df_true_processed.shape != df_extracted_processed.shape:
        raise ValueError(f"错误：对齐和预处理后，数据框形状不匹配。 True: {df_true_processed.shape}, Extracted: {df_extracted_processed.shape}")
    if df_true_processed.empty:
        raise ValueError("错误：处理后的数据框为空，无法比较。")

    # --- Compare DataFrames and Calculate Accuracy ---
    true_values = df_true_processed.values
    extracted_values = df_extracted_processed.values
    try:
        # Apply the enhanced cells_equal function element-wise
        correct_mask = np.vectorize(cells_equal)(true_values, extracted_values)
    except Exception as e:
        print(f"比较单元格时发生内部错误: {e}")
        # Optionally print problematic values for debugging
        # for r in range(true_values.shape[0]):
        #     for c in range(true_values.shape[1]):
        #         try:
        #             cells_equal(true_values[r,c], extracted_values[r,c])
        #         except Exception as cell_e:
        #             print(f"Error comparing row {r}, col {c} ('{common_cols[c]}'): val1='{true_values[r,c]}', val2='{extracted_values[r,c]}', error='{cell_e}'")
        raise RuntimeError(f"比较单元格时出错: {e}")

    total_cells = correct_mask.size
    correct_cells = np.sum(correct_mask)
    incorrect_cells = total_cells - correct_cells
    accuracy = correct_cells / total_cells if total_cells > 0 else 0

    # --- Print and Save Results ---
    print(f"\n📊 Cell-level comparison results (ID={report_id_formatted})")
    print(f"Total comparable cells : {total_cells}")
    print(f"Correct cells        : {correct_cells}")
    print(f"Incorrect cells      : {incorrect_cells}")
    print(f"✅ Overall accuracy  : {accuracy:.4f}")

    try:
        with open(accuracy_file, "w", encoding="utf-8") as f:
            f.write(f"Report ID: {report_id_formatted}\n") # Report uses formatted ID
            f.write(f"Compared Columns ({len(common_cols)}):\n")
            f.write(f"{', '.join(common_cols)}\n\n")
            f.write(f"Total comparable cells: {total_cells}\n")
            f.write(f"Correct cells: {correct_cells}\n")
            f.write(f"Incorrect cells: {incorrect_cells}\n")
            f.write(f"Overall accuracy: {accuracy:.4f}\n")

        if incorrect_cells > 0 and true_values.shape[0] > 0:
            # Create DataFrame for differences using original aligned (but not preprocessed) values for clarity
            diff_indices = np.where(~correct_mask)
            diff_list = []
            for r, c in zip(diff_indices[0], diff_indices[1]):
                 # Use iloc on the aligned dataframes before general preprocessing
                 # but after Report ID normalization for consistency there
                 true_val_orig = df_true_aligned.iloc[r, c]
                 extracted_val_orig = df_extracted_aligned.iloc[r, c]
                 diff_list.append({
                      'Column': common_cols[c],
                      'True Value': true_val_orig,
                      'Extracted Value': extracted_val_orig
                 })
            diff_df = pd.DataFrame(diff_list)


            diff_output = ""
            if HAS_TABULATE:
                # Use tabulate for better formatting if available
                diff_output = tabulate(diff_df, headers='keys', tablefmt='psql', showindex=False, missingval="<NA>")
            else:
                diff_output = diff_df.to_string(index=False, na_rep="<NA>")


            # Append differences to the accuracy file
            with open(accuracy_file, "a", encoding="utf-8") as f:
                f.write("\n--- Differences ---\n")
                f.write(diff_output)

        print(f"\nAccuracy and difference details have been saved to: {accuracy_file}")

    except Exception as e:
        print(f"❌ 保存准确率文件或差异时出错: {e}")
        raise IOError(f"Error saving accuracy file: {e}")


# --- Main Execution Block ---
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {os.path.basename(__file__)} <report_id>")
        sys.exit(1)
    report_id_arg = sys.argv[1]
    try:
        main(report_id_arg)
    except (FileNotFoundError, ValueError, IOError, RuntimeError) as e:
        # Catch specific errors raised from main() for cleaner exit message
        print(f"\n处理报告 {report_id_arg} 时发生错误: {e}")
        sys.exit(1)
    except Exception as e:
        # Catch any other unexpected errors
        print(f"\n处理报告 {report_id_arg} 时发生未预料的严重错误: {e}")
        # Optionally print traceback for debugging
        # import traceback
        # traceback.print_exc()
        sys.exit(1)


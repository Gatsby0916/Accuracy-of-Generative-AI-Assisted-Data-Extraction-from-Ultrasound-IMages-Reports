import sys
import os
import re

import pandas as pd
import numpy as np

# Optional: Use tabulate for prettier diff printing if installed
try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

import config  # your config module

def standardize_columns(df):
    """Apply column name corrections based on config mapping."""
    df.rename(columns=config.COLUMN_NAME_MAPPING, inplace=True, errors='ignore')
    return df

def preprocess(df):
    """
    1. Strip whitespace
    2. Convert common NA patterns (including 'nr') to pd.NA
    3. Normalize dimension strings (e.g., '48 x 33 x 37' -> '48x33x37')
    4. Strip time component from datetime strings (e.g., '2023-03-24 00:00:00' -> '2023-03-24')
    """
    # 1) to string and strip
    df = df.astype(str)
    df = df.apply(lambda col: col.str.strip() if col.dtype == object else col)

    # 2) NA patterns (case-insensitive)
    na_patterns = [
        r'^\s*$',
        r'^(nan|none|na|n/a|nat|unspecified|not specified|null|nr)\s*$'
    ]
    for pat in na_patterns:
        df.replace(pat, pd.NA, inplace=True, regex=True)

    # helper: normalize dims
    def normalize_dims(val):
        if isinstance(val, str):
            return re.sub(r'(\d+)\s*[xX]\s*(\d+)\s*[xX]\s*(\d+)', r'\1x\2x\3', val)
        return val

    # helper: strip time
    def strip_time(val):
        if isinstance(val, str) and re.match(r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$', val):
            try:
                return pd.to_datetime(val).strftime('%Y-%m-%d')
            except:
                return val
        return val

    # apply to each object column
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].map(normalize_dims)
            df[col] = df[col].map(strip_time)

    return df

def cells_equal(val1, val2):
    """
    Compare two cell values with tolerances:
    - NA vs NA -> True
    - NA vs { '', '0', 'not detected' } -> True
    - Boolean mapping: '1'/'0' vs yes/no/present/absent/... -> True
    - Numeric close match -> True
    - Fallback: case-insensitive string equality
    """
    isna1, isna2 = pd.isna(val1), pd.isna(val2)
    if isna1 and isna2:
        return True

    # Strings for mapping
    unspecified = {'unspecified', 'not specified', 'n/a', 'na', '', 'null', 'nr'}
    true_strs  = {'yes', 'present', 'true', 'active', 'positive', 'complete', 'conventional'}
    false_strs = {'no', 'absent', 'false', 'inactive', 'negative', 'normal', 'not detected'}

    s1 = str(val1).strip().lower() if not isna1 else None
    s2 = str(val2).strip().lower() if not isna2 else None

    # NA vs unspecified or zero
    if isna1 or isna2:
        other = s2 if isna1 else s1
        if other in unspecified or other == '0':
            return True
        return False

    # Boolean mapping
    is1_true  = (s1 == '1') or (s1 in true_strs)
    is1_false = (s1 == '0') or (s1 in false_strs)
    is2_true  = (s2 == '1') or (s2 in true_strs)
    is2_false = (s2 == '0') or (s2 in false_strs)

    if (is1_true and is2_true) or (is1_false and is2_false):
        return True
    if (is1_true and is2_false) or (is1_false and is2_true):
        return False

    # Numeric comparison
    try:
        return np.isclose(float(val1), float(val2), equal_nan=False)
    except:
        pass

    # Fallback: case-insensitive string match
    return s1 == s2

def main(dataset_name, report_id, provider_name, model_name_slug):
    print(f"\n--- Starting Evaluation for Report: {report_id}, Dataset: {dataset_name} ---")

    # 1. Paths
    try:
        cfg = config.DATASET_CONFIGS[dataset_name]
        gt_path = cfg["ground_truth_xlsx"]
        excel_dir = config.get_extracted_excel_dir(provider_name, model_name_slug, dataset_name)
        out_dir = config.get_accuracy_reports_dir(provider_name, model_name_slug, dataset_name)
        os.makedirs(out_dir, exist_ok=True)
    except KeyError:
        print(f"FATAL: Dataset '{dataset_name}' not found.", file=sys.stderr)
        sys.exit(1)

    extracted_path = os.path.join(excel_dir, f"{report_id}_output.xlsx")
    report_path    = os.path.join(out_dir, f"{report_id}_accuracy_report.txt")

    print(f"Ground Truth: {gt_path}")
    print(f"Extracted Excel: {extracted_path}")
    print(f"Accuracy Report: {report_path}")

    # 2. Load
    try:
        df_true      = pd.read_excel(gt_path, dtype=str)
        df_extracted = pd.read_excel(extracted_path, dtype=str)
    except Exception as e:
        print(f"Error loading Excel: {e}", file=sys.stderr)
        sys.exit(1)

    # 3. Filter by Report ID
    id_col = next((c for c in config.REPORT_ID_COLUMN_NAMES if c in df_true.columns), None)
    if not id_col:
        raise ValueError("Report ID column not found in ground truth.")
    df_true[id_col] = df_true[id_col].astype(str).str.strip()
    extr_id = str(df_extracted["Report ID"].iloc[0]).strip()

    # Numeric vs string matching
    gt_row = pd.DataFrame()
    try:
        gt_num = pd.to_numeric(df_true[id_col], errors='coerce')
        ex_num = pd.to_numeric(extr_id, errors='coerce')
        if not pd.isna(ex_num):
            gt_row = df_true[gt_num == ex_num]
            if not gt_row.empty:
                print(f"Matched ID '{extr_id}' numerically.")
    except:
        pass
    if gt_row.empty:
        print(f"Falling back to string match for ID '{extr_id}'.")
        gt_row = df_true[df_true[id_col] == extr_id]

    if gt_row.empty:
        raise ValueError(f"ID '{extr_id}' not found in ground truth.")

    # 4. Align columns
    df_true_std     = standardize_columns(gt_row.copy())
    df_extracted_std= standardize_columns(df_extracted.copy())
    common = sorted(set(df_true_std.columns) & set(df_extracted_std.columns))
    if not common:
        raise ValueError("No common columns to compare.")

    df_true_al = preprocess(df_true_std[common].reset_index(drop=True))
    df_ext_al  = preprocess(df_extracted_std[common].reset_index(drop=True))

    # 5. Compare
    mask    = np.vectorize(cells_equal)(df_true_al.values, df_ext_al.values)
    total   = mask.size
    correct = mask.sum()
    acc     = correct / total if total > 0 else 0.0
    print(f"✅ Overall Accuracy: {acc:.4f}")

    # 6. Report
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"Evaluation Report for: {report_id}\n")
        f.write(f"Accuracy: {acc:.4f} ({correct}/{total})\n\n")
        if correct < total:
            rows = []
            for i in range(mask.shape[0]):
                for j in range(mask.shape[1]):
                    if not mask[i, j]:
                        rows.append({
                            "Column": common[j],
                            "True Value": df_true_al.iloc[i, j],
                            "Extracted Value": df_ext_al.iloc[i, j]
                        })
            diff_df = pd.DataFrame(rows)
            diff_out = (tabulate(diff_df, headers="keys", tablefmt="psql", showindex=False)
                        if HAS_TABULATE else diff_df.to_string(index=False))
            f.write("--- Differences ---\n")
            f.write(diff_out)

    print(f"\nSaved accuracy report to: {report_path}")

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(f"Usage: python {os.path.basename(__file__)} <dataset> <report_id> <provider> <model>", file=sys.stderr)
        sys.exit(1)
    main(*sys.argv[1:5])

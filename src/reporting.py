import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker # For formatting ticks
import seaborn as sns
import sys
import re
import json # For loading the JSON template
from collections import Counter, defaultdict
import argparse # For command-line arguments

# Attempt to import config, with a fallback for running from different locations
try:
    import config
except ImportError:
    try:
        from src import config # If running as a module from project root
    except ImportError:
        print("Error: Could not import config.py. Please ensure the relative path to config.py is correct, or add the directory containing it to the Python path.")
        sys.exit(1)

# --- Matplotlib and Seaborn Configuration ---
plt.rcParams['axes.unicode_minus'] = False # Ensure minus sign displays correctly
sns.set_style("whitegrid", {'axes.edgecolor': '.8'}) # Use a slightly lighter edge color for axes
plt.rcParams['font.family'] = 'sans-serif' # Use a common sans-serif font
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans', 'Bitstream Vera Sans', 'sans-serif']


# --- Helper Functions ---

def load_template_fields(json_path):
    """Loads all standard field names from the JSON template."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        return list(template_data.keys())
    except FileNotFoundError:
        print(f"Error: JSON template file not found: {json_path}")
        return []
    except Exception as e:
        print(f"Error loading JSON template: {e}")
        return []

STANDARD_FIELD_NAMES = load_template_fields(config.TEMPLATE_JSON_PATH)
if not STANDARD_FIELD_NAMES:
    print("Warning: Failed to load standard field names from JSON template. Field name parsing and statistics may be inaccurate.")

def reconstruct_split_field_names(split_parts, canonical_fields):
    """
    Attempts to reconstruct field name parts that were split by commas,
    based on a list of standard field names. This is a heuristic approach.
    """
    if not canonical_fields: 
        return [part.strip() for part in split_parts]

    reconstructed_fields = []
    current_accumulated_parts = [] 
    original_part_idx = 0

    while original_part_idx < len(split_parts):
        current_accumulated_parts.append(split_parts[original_part_idx].strip())
        
        best_match_found = None
        num_parts_in_best_match = 0

        for j in range(len(current_accumulated_parts)):
            candidate_name_parts = current_accumulated_parts[:j+1]
            candidate_name = ", ".join(candidate_name_parts) 

            if candidate_name in canonical_fields:
                best_match_found = candidate_name
                num_parts_in_best_match = j + 1
        
        if best_match_found:
            temp_extended_name = best_match_found
            temp_num_parts_consumed_for_extended_match = num_parts_in_best_match
            
            lookahead_original_idx = original_part_idx + 1 
            
            can_extend_further = True
            while can_extend_further and lookahead_original_idx < len(split_parts):
                next_original_part = split_parts[lookahead_original_idx].strip()
                potential_extended_candidate = temp_extended_name + ", " + next_original_part
                
                if potential_extended_candidate in canonical_fields:
                    temp_extended_name = potential_extended_candidate
                    temp_num_parts_consumed_for_extended_match += 1 
                    lookahead_original_idx += 1 
                else:
                    can_extend_further = False 
            
            reconstructed_fields.append(temp_extended_name)
            original_part_idx += temp_num_parts_consumed_for_extended_match
            current_accumulated_parts = [] 
        else:
            if current_accumulated_parts: 
                reconstructed_fields.append(current_accumulated_parts[0])
            original_part_idx += 1 
            current_accumulated_parts = [] 

    return [rf.strip() for rf in reconstructed_fields if rf.strip()]


def parse_difference_columns_from_table(lines, compared_cols_for_report):
    """
    Parses column names from the '--- Differences ---' section of an accuracy file.
    It tries to match extracted names with the report's 'compared_cols_for_report'
    to get the canonical field names.
    """
    error_cols_found = []
    in_difference_section = False
    header_line_index = -1
    
    COLUMN_HEADER = "Column"
    TRUE_VALUE_HEADER = "True Value" 
    EXTRACTED_VALUE_HEADER = "Extracted Value" 

    for i, line in enumerate(lines):
        if line.strip() == '--- Differences ---':
            in_difference_section = True
            header_line_index = i + 1 
            break
    
    if not in_difference_section:
        return []

    actual_column_names_in_table_header = []
    data_start_line_idx = -1
    col_idx_in_table_header = -1


    for i in range(header_line_index, min(header_line_index + 3, len(lines))): 
        line_stripped = lines[i].strip()
        if not line_stripped: continue

        if COLUMN_HEADER in line_stripped and TRUE_VALUE_HEADER in line_stripped: 
            if line_stripped.startswith("|") and line_stripped.endswith("|"): 
                parts = [p.strip() for p in line_stripped.split('|')]
                actual_column_names_in_table_header = [p for p in parts if p] 
            else: 
                actual_column_names_in_table_header = line_stripped.split() 

            try:
                col_idx_in_table_header = actual_column_names_in_table_header.index(COLUMN_HEADER)
            except ValueError:
                col_idx_in_table_header = -1 

            if col_idx_in_table_header != -1:
                data_start_line_idx = i + 1
                if data_start_line_idx < len(lines):
                    next_line_s = lines[data_start_line_idx].strip()
                    if next_line_s.startswith("|-") or next_line_s.startswith("+-"):
                        data_start_line_idx += 1
                break 
    
    if data_start_line_idx == -1 or col_idx_in_table_header == -1:
        return [] 

    for i in range(data_start_line_idx, len(lines)):
        line_content = lines[i]
        line_content_stripped = line_content.strip()

        if not line_content_stripped: continue 
        if (line_content_stripped.startswith("---") and line_content_stripped != '--- Differences ---') or \
           (line_content_stripped.startswith("+-") and line_content_stripped.endswith("--+")):
            break 
        
        extracted_name_from_row = None
        if line_content_stripped.startswith("|") and line_content_stripped.endswith("|"): 
            parts = [p.strip() for p in line_content.split('|')]
            row_data_values = [p for p in parts if p] 
            if col_idx_in_table_header < len(row_data_values):
                extracted_name_from_row = row_data_values[col_idx_in_table_header]
        elif actual_column_names_in_table_header and not line_content_stripped.startswith("|"): 
            if col_idx_in_table_header == 0:
                split_by_multiple_spaces = re.split(r'\s{2,}', line_content_stripped) 
                if split_by_multiple_spaces:
                    extracted_name_from_row = split_by_multiple_spaces[0]

        if extracted_name_from_row and extracted_name_from_row != COLUMN_HEADER :
            best_match_for_error_col = extracted_name_from_row 
            if compared_cols_for_report:
                if extracted_name_from_row in compared_cols_for_report:
                    best_match_for_error_col = extracted_name_from_row
                else:
                    possible_matches = [
                        known_field for known_field in compared_cols_for_report 
                        if extracted_name_from_row in known_field 
                    ]
                    if possible_matches:
                        best_match_for_error_col = max(possible_matches, key=len)
            error_cols_found.append(best_match_for_error_col)
            
    return error_cols_found


def extract_accuracy_details_from_file(filepath, canonical_field_names):
    """
    Extracts overall accuracy, report ID, list of compared columns, and list of error columns
    from a single accuracy file. Attempts to reconstruct split 'Compared Columns' names.
    """
    report_id_from_file = None
    llm_provider_from_file = None 
    llm_model_from_file = None      
    overall_accuracy = None
    compared_columns_list_reconstructed = []
    error_columns_list_reconstructed = [] 
    
    reading_compared_columns_line = False 
    raw_compared_columns_str = "" 

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line_raw in enumerate(lines):
            line = line_raw.strip()

            if line.startswith("Report ID:"):
                report_id_from_file = line.split(":", 1)[1].strip()
            elif line.startswith("LLM Provider:"): 
                llm_provider_from_file = line.split(":", 1)[1].strip()
            elif line.startswith("LLM Model:"): 
                llm_model_from_file = line.split(":", 1)[1].strip()
            elif line.startswith("Overall accuracy:") or line.startswith("Overall Accuracy"): 
                accuracy_str = line.split(":", 1)[1].strip()
                try:
                    overall_accuracy = float(accuracy_str)
                except ValueError:
                    print(f"Warning: Could not convert accuracy '{accuracy_str}' to float (file: {os.path.basename(filepath)})")
            elif line.startswith("Compared Columns ("): 
                reading_compared_columns_line = True 
            elif reading_compared_columns_line and line: 
                raw_compared_columns_str = line 
                raw_split_parts = [part.strip() for part in raw_compared_columns_str.split(',') if part.strip()]
                compared_columns_list_reconstructed = reconstruct_split_field_names(raw_split_parts, canonical_field_names)
                reading_compared_columns_line = False 
        
        if report_id_from_file is None:
            base_name = os.path.basename(filepath)
            report_id_match = re.match(r"^(RRI\s?\d+)_accuracy\.txt$", base_name, re.IGNORECASE)
            if report_id_match:
                report_id_from_file = report_id_match.group(1) 

        error_columns_list_raw = parse_difference_columns_from_table(lines, compared_columns_list_reconstructed)
        error_columns_list_reconstructed = [col for col in error_columns_list_raw if col in compared_columns_list_reconstructed]

    except FileNotFoundError:
        print(f"Warning: Accuracy file not found: {filepath}")
        return None, None, None, None, [], [] 
    except Exception as e:
        print(f"Error reading or parsing file {os.path.basename(filepath)}: {e}")
        return None, None, None, None, [], []

    if overall_accuracy is None and report_id_from_file is not None:
         print(f"Warning: No valid 'Overall accuracy' line found in file {os.path.basename(filepath)} (Report ID {report_id_from_file}).")
    if not compared_columns_list_reconstructed and report_id_from_file is not None:
         print(f"Warning: 'Compared Columns' list not found or empty in file {os.path.basename(filepath)} (Report ID {report_id_from_file}).")

    return report_id_from_file, llm_provider_from_file, llm_model_from_file, overall_accuracy, compared_columns_list_reconstructed, error_columns_list_reconstructed


def generate_report(provider_name_filter, model_name_slug_filter):
    """
    Reads all relevant accuracy files, calculates summary statistics, generates plots and reports
    for the specified LLM provider and model.
    """
    current_accuracy_folder = config.get_accuracy_reports_dir(provider_name_filter, model_name_slug_filter)
    current_analysis_folder = config.get_overall_analysis_dir(provider_name_filter, model_name_slug_filter)
    
    current_summary_filepath = config.get_summary_report_txt_path(provider_name_filter, model_name_slug_filter)
    current_overall_accuracy_plot_filepath = config.get_accuracy_plot_png_path(provider_name_filter, model_name_slug_filter)
    
    current_overall_accuracy_boxplot_filepath = os.path.join(current_analysis_folder, "overall_accuracy_boxplot.png")
    current_field_accuracy_barchart_filepath = os.path.join(current_analysis_folder, "field_accuracy_barchart.png")
    current_field_performance_stacked_bar_filepath = os.path.join(current_analysis_folder, "field_performance_stacked_bar.png")
    current_field_accuracy_vs_frequency_scatter_filepath = os.path.join(current_analysis_folder, "field_accuracy_vs_frequency_scatter.png")

    try:
        os.makedirs(current_analysis_folder, exist_ok=True)
    except Exception as e:
        print(f"Error: Failed to create analysis directory '{current_analysis_folder}': {e}")
        sys.exit(1)

    print(f"\n--- Generating Report for Provider: '{provider_name_filter}', Model: '{model_name_slug_filter}' ---")
    print(f"Reading accuracy reports from: {current_accuracy_folder}")

    overall_accuracies = []
    all_report_ids_with_overall_acc = [] 
    
    field_comparison_counts = Counter() 
    field_correct_counts = Counter()    
    field_error_details = defaultdict(lambda: Counter()) 
    
    all_parsed_reports_data = [] 

    if not os.path.isdir(current_accuracy_folder):
        print(f"Error: Accuracy reports directory not found: {current_accuracy_folder}")
        print("Please ensure the evaluation process has been run for the specified provider and model.")
        return 

    filenames = sorted([f for f in os.listdir(current_accuracy_folder) if f.endswith(".txt")])
    if not filenames:
        print(f"Info: No .txt files found in the accuracy reports directory '{current_accuracy_folder}'.")
        return 

    print(f"Found {len(filenames)} .txt files.")

    for filename in filenames:
        filepath = os.path.join(current_accuracy_folder, filename)
        report_id, provider, model, overall_acc, compared_cols, error_cols = \
            extract_accuracy_details_from_file(filepath, STANDARD_FIELD_NAMES)
        
        if provider and provider != provider_name_filter:
            print(f"Warning: Provider '{provider}' in file {filename} does not match expected '{provider_name_filter}'. Skipping file.")
            continue
        if model and model != model_name_slug_filter: 
            print(f"Warning: Model '{model}' in file {filename} does not match expected '{model_name_slug_filter}'. Skipping file.")
            continue

        if report_id:
            all_parsed_reports_data.append({
                "report_id": report_id, 
                "overall_accuracy": overall_acc,
                "compared_columns": compared_cols, 
                "error_columns": error_cols,      
                "filepath": filepath 
            })
            if overall_acc is not None:
                overall_accuracies.append(overall_acc)
                all_report_ids_with_overall_acc.append(report_id) 
        else:
            print(f"Skipping file {filename} as report ID could not be determined.")
    
    if not all_parsed_reports_data:
        print(f"Error: No valid data could be parsed from any files in '{current_accuracy_folder}'. Cannot generate report.")
        return

    accuracies_np = np.array(overall_accuracies) if overall_accuracies else np.array([])
    num_reports_with_acc = len(overall_accuracies)

    average_accuracy = np.mean(accuracies_np) if num_reports_with_acc > 0 else 0.0
    median_accuracy = np.median(accuracies_np) if num_reports_with_acc > 0 else 0.0
    std_dev = np.std(accuracies_np) if num_reports_with_acc > 0 else 0.0
    min_accuracy = np.min(accuracies_np) if num_reports_with_acc > 0 else 0.0
    max_accuracy = np.max(accuracies_np) if num_reports_with_acc > 0 else 0.0
    
    min_report_id_overall = 'N/A'
    max_report_id_overall = 'N/A'
    if num_reports_with_acc > 0:
        min_idx = np.argmin(accuracies_np)
        max_idx = np.argmax(accuracies_np)
        if min_idx < len(all_report_ids_with_overall_acc):
            min_report_id_overall = all_report_ids_with_overall_acc[min_idx]
        if max_idx < len(all_report_ids_with_overall_acc):
            max_report_id_overall = all_report_ids_with_overall_acc[max_idx]

    print("\n--- Overall Accuracy Statistics ---")
    print(f"Provider: {provider_name_filter}, Model: {model_name_slug_filter}")
    print(f"Number of reports processed with valid overall accuracy: {num_reports_with_acc}")
    print(f"Mean Overall Accuracy   : {average_accuracy:.4f}")
    print(f"Median Overall Accuracy : {median_accuracy:.4f}")
    print(f"Standard Deviation      : {std_dev:.4f}")
    print(f"Minimum Overall Accuracy: {min_accuracy:.4f} (Report: {min_report_id_overall})")
    print(f"Maximum Overall Accuracy: {max_accuracy:.4f} (Report: {max_report_id_overall})")

    print("\n--- Calculating Field-Level Accuracies ---")
    for report_data in all_parsed_reports_data:
        if not report_data["compared_columns"]: 
            continue
        for field_name in report_data["compared_columns"]:
            field_comparison_counts[field_name] += 1
            if field_name not in report_data["error_columns"]:
                field_correct_counts[field_name] += 1
            else:
                try:
                    with open(report_data["filepath"], 'r', encoding='utf-8') as f_err_detail:
                        lines_for_detail = f_err_detail.readlines()
                    
                    in_diff_section_detail = False
                    header_found_detail = False
                    col_name_idx_detail, true_val_idx_detail, extr_val_idx_detail = -1, -1, -1
                    data_start_idx_detail = -1

                    for line_idx, line_content in enumerate(lines_for_detail):
                        if line_content.strip() == "--- Differences ---":
                            in_diff_section_detail = True
                            for h_search_idx in range(line_idx + 1, min(line_idx + 4, len(lines_for_detail))):
                                header_l_detail = lines_for_detail[h_search_idx].strip()
                                if "Column" in header_l_detail and "True Value" in header_l_detail and "Extracted Value" in header_l_detail:
                                    parts_detail = [p.strip() for p in header_l_detail.split('|') if p.strip()]
                                    try:
                                        col_name_idx_detail = parts_detail.index("Column")
                                        true_val_idx_detail = parts_detail.index("True Value")
                                        extr_val_idx_detail = parts_detail.index("Extracted Value")
                                        header_found_detail = True
                                        data_start_idx_detail = h_search_idx + 1
                                        if data_start_idx_detail < len(lines_for_detail) and \
                                           (lines_for_detail[data_start_idx_detail].strip().startswith("+-") or \
                                            lines_for_detail[data_start_idx_detail].strip().startswith("|--")):
                                            data_start_idx_detail += 1
                                        break 
                                    except ValueError: pass 
                            if header_found_detail: break 
                    
                    if header_found_detail:
                        for data_l_idx in range(data_start_idx_detail, len(lines_for_detail)):
                            data_l_s = lines_for_detail[data_l_idx].strip()
                            if not data_l_s or (data_l_s.startswith("---") and data_l_s != "--- Differences ---") or \
                               (data_l_s.startswith("+-") and data_l_s.endswith("--+")):
                                break 

                            row_parts_raw_detail = [p.strip() for p in lines_for_detail[data_l_idx].strip().split('|')]
                            row_parts_detail = [p for p in row_parts_raw_detail if p]
                            
                            current_col_name_in_diff_detail, true_val_detail, extr_val_detail = None, None, None
                            if col_name_idx_detail < len(row_parts_detail): current_col_name_in_diff_detail = row_parts_detail[col_name_idx_detail]
                            if true_val_idx_detail < len(row_parts_detail): true_val_detail = row_parts_detail[true_val_idx_detail]
                            if extr_val_idx_detail < len(row_parts_detail): extr_val_detail = row_parts_detail[extr_val_idx_detail]
                            
                            matched_field_for_error_detail = None
                            if current_col_name_in_diff_detail:
                                if current_col_name_in_diff_detail == field_name: 
                                    matched_field_for_error_detail = field_name
                                else: 
                                    if current_col_name_in_diff_detail in field_name:
                                        matched_field_for_error_detail = field_name

                            if matched_field_for_error_detail == field_name and true_val_detail is not None and extr_val_detail is not None:
                                field_error_details[field_name][(true_val_detail, extr_val_detail)] += 1
                except Exception as e_detail_parse:
                    print(f"Error parsing error details from file {report_data['filepath']} for field {field_name}: {e_detail_parse}")

    field_accuracy_data = []
    if field_comparison_counts: 
        for field, compared_count in field_comparison_counts.items():
            correct_count = field_correct_counts.get(field, 0)
            accuracy = (correct_count / compared_count) if compared_count > 0 else 0.0
            field_accuracy_data.append({
                "Field_Name": field,
                "Times_Correct": correct_count,
                "Times_Compared": compared_count,
                "Times_Incorrect": compared_count - correct_count, 
                "Field_Accuracy": accuracy
            })
        
        field_accuracy_df = pd.DataFrame(field_accuracy_data)
        if not field_accuracy_df.empty:
            field_accuracy_df = field_accuracy_df.sort_values(by="Field_Accuracy", ascending=True).reset_index(drop=True) 
            print("\n--- Field-Level Accuracy Summary (Bottom 10 by Accuracy) ---")
            print(field_accuracy_df.head(10).to_string(index=False))
            if len(field_accuracy_df) > 10:
                print(f"\n--- Field-Level Accuracy Summary (Top 10 by Accuracy) ---")
                print(field_accuracy_df.tail(10).sort_values(by="Field_Accuracy", ascending=False).to_string(index=False))
        else:
            print("Field accuracy DataFrame is empty after processing.")
            field_accuracy_df = pd.DataFrame() 
    else:
        print("No field-level comparison data found to calculate field accuracies (field_comparison_counts is empty).")
        field_accuracy_df = pd.DataFrame() 

    try:
        with open(current_summary_filepath, "w", encoding="utf-8") as f:
            f.write(f"--- Overall Accuracy Summary ({provider_name_filter} / {model_name_slug_filter}) ---\n")
            f.write(f"Number of reports processed with valid overall accuracy: {num_reports_with_acc}\n")
            f.write(f"Mean Overall Accuracy   : {average_accuracy:.4f}\n")
            f.write(f"Median Overall Accuracy : {median_accuracy:.4f}\n")
            f.write(f"Standard Deviation      : {std_dev:.4f}\n")
            f.write(f"Minimum Overall Accuracy: {min_accuracy:.4f} (Report: {min_report_id_overall})\n")
            f.write(f"Maximum Overall Accuracy: {max_accuracy:.4f} (Report: {max_report_id_overall})\n\n")
            
            f.write(f"--- Individual Report Overall Accuracies ({provider_name_filter} / {model_name_slug_filter}) ---\n")
            valid_report_acc_pairs = sorted([
                (pid, acc) for pid, acc in zip(all_report_ids_with_overall_acc, overall_accuracies)
            ])
            for r_id, acc_val in valid_report_acc_pairs:
                f.write(f"{r_id}: {acc_val:.4f}\n")

            if not field_accuracy_df.empty:
                f.write(f"\n\n--- Field-Level Accuracy Summary ({provider_name_filter} / {model_name_slug_filter}) ---\n")
                cols_to_show_in_report = ["Field_Name", "Times_Correct", "Times_Incorrect", "Times_Compared", "Field_Accuracy"]
                f.write(field_accuracy_df[cols_to_show_in_report].to_string(index=False))

                f.write(f"\n\n--- Top 3 Common Error Details per Field ({provider_name_filter} / {model_name_slug_filter}) ---\n")
                sorted_field_names_for_detail = field_accuracy_df.sort_values(by="Field_Accuracy")["Field_Name"]
                for field_name_detail in sorted_field_names_for_detail:
                    if field_error_details[field_name_detail]: 
                        f.write(f"\nField: {field_name_detail}\n")
                        top_3_errors = field_error_details[field_name_detail].most_common(3)
                        for (true_v, extr_v), count_err in top_3_errors:
                            f.write(f"  - Count: {count_err}, GT Value: '{true_v}', LLM Extracted: '{extr_v}'\n")
            else:
                f.write(f"\n\n--- Field-Level Accuracy Summary ({provider_name_filter} / {model_name_slug_filter}) ---\n")
                f.write("No field-level accuracy data available.\n")

        print(f"\nSummary statistics saved to: {current_summary_filepath}")
    except Exception as e:
        print(f"Error saving summary statistics file '{current_summary_filepath}': {e}")

    # --- Plotting Section with English Labels and Enhancements ---
    plot_title_suffix = f"({provider_name_filter} / {model_name_slug_filter})"
    
    # Overall Accuracy Histogram
    if accuracies_np.size > 0:
        try:
            plt.figure(figsize=(12, 7))
            # Use a slightly more distinct color and ensure good contrast
            sns.histplot(accuracies_np, bins=np.arange(0, 1.1, 0.1), kde=False, color="steelblue", edgecolor='black', linewidth=0.8, alpha=0.75)
            
            # Add data labels on top of bars more robustly
            ax = plt.gca()
            for p in ax.patches:
                height = p.get_height()
                if height > 0:
                    ax.text(p.get_x() + p.get_width()/2.,
                            height + 0.01 * accuracies_np.size, # Dynamic offset
                            f'{int(height)}',
                            ha="center", va="bottom", fontsize=9, color='dimgray')

            plt.axvline(average_accuracy, color='crimson', linestyle='--', linewidth=1.5,
                        label=f'Mean: {average_accuracy:.4f}')
            plt.axvline(median_accuracy, color='forestgreen', linestyle=':', linewidth=1.5,
                        label=f'Median: {median_accuracy:.4f}')
            
            plt.title(f"Distribution of Overall Report Accuracy Scores {plot_title_suffix}", fontsize=15, pad=15, weight='bold')
            plt.xlabel("Overall Accuracy Score", fontsize=12, labelpad=10)
            plt.ylabel("Number of Reports", fontsize=12, labelpad=10)
            plt.xticks(np.arange(0, 1.1, 0.1), fontsize=10)
            plt.yticks(fontsize=10)
            plt.ylim(bottom=0)
            plt.legend(fontsize=10, frameon=True, facecolor='white', edgecolor='gray')
            sns.despine(trim=True) 
            plt.tight_layout()
            plt.savefig(current_overall_accuracy_plot_filepath, dpi=150)
            print(f"Overall accuracy histogram saved to: {current_overall_accuracy_plot_filepath}")
            plt.close()
        except Exception as e:
            print(f"\nError generating or saving overall accuracy histogram: {e}")
    else:
        print(f"\nSkipping overall accuracy histogram {plot_title_suffix}: No valid overall accuracy data.")

    # Overall Accuracy Boxplot
    if accuracies_np.size > 0:
        try:
            plt.figure(figsize=(7, 7)) # Adjusted for better aspect ratio for a single box
            sns.boxplot(y=accuracies_np, color="skyblue", width=0.4, 
                        medianprops={'color':'orange', 'linewidth':2},
                        boxprops={'edgecolor':'black'}, whiskerprops={'color':'black'}, capprops={'color':'black'})
            
            plt.scatter([0], [average_accuracy], marker='o', color='red', s=60, zorder=5, label=f'Mean: {average_accuracy:.4f}', edgecolors='black')
            
            plt.title(f"Boxplot of Overall Report Accuracy Scores", fontsize=15, pad=15, weight='bold')
            plt.ylabel("Overall Accuracy Score", fontsize=12, labelpad=10)
            plt.xticks([]) 
            plt.yticks(np.arange(0, 1.1, 0.1), fontsize=10)
            plt.ylim(min(0, np.min(accuracies_np)-0.05) if accuracies_np.size >0 else 0, max(1, np.max(accuracies_np)+0.05) if accuracies_np.size > 0 else 1)
            plt.legend(fontsize=10, loc='lower center', frameon=True, facecolor='white', edgecolor='gray')
            sns.despine(left=False, bottom=True) 
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            plt.tight_layout()
            plt.savefig(current_overall_accuracy_boxplot_filepath, dpi=150)
            print(f"Overall accuracy boxplot saved to: {current_overall_accuracy_boxplot_filepath}")
            plt.close()
        except Exception as e:
            print(f"\nError generating or saving overall accuracy boxplot: {e}")
    else:
        print(f"\nSkipping overall accuracy boxplot {plot_title_suffix}: No valid overall accuracy data.")

    # Field-Level Accuracy Bar Chart
    if not field_accuracy_df.empty:
        try:
            num_fields_to_plot_bar = min(len(field_accuracy_df), 30) 
            plot_df_field_accuracy_bar = field_accuracy_df.sort_values(by="Field_Accuracy", ascending=False).head(num_fields_to_plot_bar)
            plot_df_field_accuracy_bar = plot_df_field_accuracy_bar.sort_values(by="Field_Accuracy", ascending=True)

            plt.figure(figsize=(12, max(8, len(plot_df_field_accuracy_bar) * 0.35))) 
            bar_plot = sns.barplot(x="Field_Accuracy", y="Field_Name", data=plot_df_field_accuracy_bar, 
                                   palette="coolwarm_r", hue="Field_Name", legend=False, dodge=False) 
            
            plt.title(f"Top {num_fields_to_plot_bar} Fields by Accuracy Score {plot_title_suffix}", fontsize=15, pad=15, weight='bold')
            plt.xlabel("Average Field Accuracy", fontsize=12, labelpad=10)
            plt.ylabel("Field Name", fontsize=12, labelpad=10)
            plt.xlim(0, 1.0) 
            plt.gca().xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0))


            for patch_bar in bar_plot.patches:
                accuracy_val_bar = patch_bar.get_width()
                y_pos_bar = patch_bar.get_y() + patch_bar.get_height() / 2.
                
                text_x_pos = accuracy_val_bar - 0.05 if accuracy_val_bar > 0.1 else accuracy_val_bar + 0.01
                text_color = 'white' if accuracy_val_bar > 0.5 else 'black'

                plt.text(text_x_pos, y_pos_bar, f"{accuracy_val_bar:.1%}", 
                         color=text_color, ha='center', 
                         va='center', fontsize=8, weight='bold')

            plt.yticks(fontsize=9) 
            plt.xticks(fontsize=10)
            plt.grid(axis='x', linestyle=':', alpha=0.6)
            sns.despine(trim=True)
            plt.tight_layout()
            plt.savefig(current_field_accuracy_barchart_filepath, dpi=150)
            print(f"Field-level accuracy bar chart saved to: {current_field_accuracy_barchart_filepath}")
            plt.close()
        except Exception as e:
            print(f"\nError generating or saving field-level accuracy bar chart: {e}")
    else:
        print(f"\nSkipping field-level accuracy bar chart {plot_title_suffix}: No field accuracy data.")

    # Field Performance Stacked Bar Chart
    if not field_accuracy_df.empty and 'Times_Correct' in field_accuracy_df.columns and 'Times_Incorrect' in field_accuracy_df.columns:
        try:
            num_fields_stacked_bar = min(len(field_accuracy_df), 30)
            df_for_stacked_plot = field_accuracy_df.sort_values(by="Times_Compared", ascending=False).head(num_fields_stacked_bar)
            df_for_stacked_plot = df_for_stacked_plot.sort_values(by="Times_Compared", ascending=True) 
            
            df_for_stacked_plot_subset = df_for_stacked_plot[["Times_Correct", "Times_Incorrect"]].set_index(df_for_stacked_plot["Field_Name"])

            ax_stacked = df_for_stacked_plot_subset.plot(kind='barh', stacked=True, 
                                      figsize=(14, max(10, len(df_for_stacked_plot_subset) * 0.35)),
                                      color=['#5cb85c', '#d9534f'], width=0.8) # Green for correct, Red for incorrect

            plt.title(f"Field Performance (Top {num_fields_stacked_bar} by Comparison Count) {plot_title_suffix}", fontsize=15, pad=15, weight='bold')
            plt.xlabel("Number of Occurrences", fontsize=12, labelpad=10)
            plt.ylabel("Field Name", fontsize=12, labelpad=10)
            plt.legend(title="Outcome", labels=["Correct", "Incorrect"], fontsize=10, title_fontsize=11)
            plt.yticks(fontsize=9)
            plt.xticks(fontsize=10)
            plt.grid(axis='x', linestyle=':', alpha=0.5)
            sns.despine(trim=True)
            
            # Add text labels for total count at the end of each bar
            for i, (idx, row) in enumerate(df_for_stacked_plot.iterrows()):
                total_compared = row["Times_Compared"]
                ax_stacked.text(total_compared + 0.5, i, str(total_compared), va='center', ha='left', fontsize=8, color='dimgray')

            plt.tight_layout(rect=[0, 0, 0.95, 1]) # Adjust layout to make space for legend if needed
            plt.savefig(current_field_performance_stacked_bar_filepath, dpi=150)
            print(f"Field performance stacked bar chart saved to: {current_field_performance_stacked_bar_filepath}")
            plt.close()
        except Exception as e:
            print(f"\nError generating or saving field performance stacked bar chart: {e}")
    else:
        print(f"\nSkipping field performance stacked bar chart {plot_title_suffix}: Insufficient data.")

    # Field Accuracy vs. Comparison Frequency Scatter Plot
    if not field_accuracy_df.empty and 'Times_Compared' in field_accuracy_df.columns and 'Field_Accuracy' in field_accuracy_df.columns:
        try:
            plt.figure(figsize=(12, 8))
            x_values_scatter = np.log1p(field_accuracy_df["Times_Compared"]) # Log scale for better spread
            y_values_scatter = field_accuracy_df["Field_Accuracy"]
            
            # Use 'Times_Incorrect' for point size to highlight problematic fields
            sizes = 20 + (field_accuracy_df["Times_Incorrect"] * 5) # Base size + scaled by number of incorrect
            sizes = np.clip(sizes, 20, 500) # Clip sizes to a reasonable range

            scatter_plot = plt.scatter(x_values_scatter, y_values_scatter, 
                                       s=sizes,
                                       alpha=0.6, 
                                       c=field_accuracy_df["Field_Accuracy"], # Color by accuracy
                                       cmap="RdYlGn", # Red-Yellow-Green colormap
                                       edgecolors='gray', 
                                       linewidth=0.5)
            
            plt.title(f"Field Accuracy vs. Comparison Frequency {plot_title_suffix}", fontsize=15, pad=15, weight='bold')
            plt.xlabel("Log(Times Compared + 1)", fontsize=12, labelpad=10)
            plt.ylabel("Field Accuracy", fontsize=12, labelpad=10)
            plt.ylim(-0.05, 1.05) 
            plt.gca().yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0))
            plt.grid(True, linestyle=':', alpha=0.5)
            
            # Add a colorbar
            cbar = plt.colorbar(scatter_plot, label='Field Accuracy')
            cbar.ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0))

            # Optional: Annotate some points (e.g., very low accuracy or very high frequency)
            # for i, row_scatter in field_accuracy_df.iterrows():
            #     if row_scatter["Field_Accuracy"] < 0.5 or np.log1p(row_scatter["Times_Compared"]) > x_values_scatter.quantile(0.95):
            #         plt.text(np.log1p(row_scatter["Times_Compared"]), row_scatter["Field_Accuracy"], 
            #                  row_scatter["Field_Name"], fontsize=6, alpha=0.85, ha='left', va='bottom',
            #                  bbox=dict(boxstyle='round,pad=0.2', fc='yellow', alpha=0.3))
            
            sns.despine(trim=True)
            plt.tight_layout()
            plt.savefig(current_field_accuracy_vs_frequency_scatter_filepath, dpi=150)
            print(f"Field accuracy vs. comparison frequency scatter plot saved to: {current_field_accuracy_vs_frequency_scatter_filepath}")
            plt.close()
        except Exception as e:
            print(f"\nError generating or saving field accuracy vs. comparison frequency scatter plot: {e}")
    else:
        print(f"\nSkipping field accuracy vs. comparison frequency scatter plot {plot_title_suffix}: Insufficient data.")

    try:
        print(f"\n--- Generating Error Distribution Analysis for {provider_name_filter}/{model_name_slug_filter} ---")
        import analyze_error_distribution 
        if hasattr(analyze_error_distribution, 'analyze_error_distribution_for_provider_model'):
              analyze_error_distribution.analyze_error_distribution_for_provider_model(provider_name_filter, model_name_slug_filter)
              print("Error distribution analysis (CSV and plot) successfully generated for the current provider/model.")
        else:
            print("Warning: 'analyze_error_distribution.py' does not have the expected 'analyze_error_distribution_for_provider_model' function.")
            print("If 'analyze_error_distribution.py' is intended to be run standalone with command-line arguments, please run it separately.")
    except ImportError:
        print("Could not import 'analyze_error_distribution'. Please ensure it is in the 'src' directory and accessible.")
    except Exception as e:
        print(f"An error occurred while running error distribution analysis: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate summary accuracy reports and plots for a specified LLM provider and model.")
    parser.add_argument("provider_name", help="Name of the LLM provider (e.g., openai, gemini, claude).")
    parser.add_argument("model_name_slug", help="Identifier for the LLM model (filesystem-safe version, e.g., gpt-4o, gemini-1.5-pro-latest).")
    
    args = parser.parse_args()
    
    if args.provider_name not in config.LLM_PROVIDERS:
        print(f"Error: Unknown provider '{args.provider_name}'. Choices are: {list(config.LLM_PROVIDERS.keys())}")
        sys.exit(1)
    if not args.model_name_slug.strip():
        print(f"Error: model_name_slug cannot be empty.")
        sys.exit(1)

    generate_report(args.provider_name, args.model_name_slug)

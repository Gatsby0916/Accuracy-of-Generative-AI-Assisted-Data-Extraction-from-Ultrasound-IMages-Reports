import os
import re
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import argparse # For command-line arguments

# Attempt to import config, with a fallback
try:
    import config # Import project configuration
except ImportError:
    try:
        from src import config # If running as a module from project root
    except ImportError:
        print("Error: Could not import config.py. Please ensure the relative path to config.py is correct, or add the directory containing it to the Python path.")
        sys.exit(1)

# Matplotlib font setup for Chinese characters (from your script)
from matplotlib import rcParams
try:
    rcParams['font.sans-serif'] = ['SimHei']
    rcParams['axes.unicode_minus'] = False
    print("Attempted to set Chinese font to 'SimHei'.")
except Exception as e:
    print(f"Failed to set Chinese font: {e}")
    print("Please ensure SimHei or another Chinese font is installed, and try modifying the font name in the script.")


# --- Function to Parse Errors from a Single File ---
def parse_error_columns_from_file(filepath, compared_cols_for_report=None):
    """
    Parses an _accuracy.txt file to extract column names listed under '--- Differences ---'.
    Handles both tabulate (psql format) and basic to_string table formats.
    Args:
        filepath (str): Path to the _accuracy.txt file.
        compared_cols_for_report (list, optional): A list of canonical column names that were
                                                     actually compared for this specific report.
                                                     Used to normalize parsed error column names.
    Returns:
        list: A list of (potentially normalized) column names where errors occurred.
    """
    error_columns = []
    in_difference_section = False
    header_line_index = -1
    
    COLUMN_HEADER_NAME = "Column" # The exact header name for the column field in the diff table

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Find the start of the "--- Differences ---" section
        for i, line in enumerate(lines):
            if line.strip() == '--- Differences ---':
                in_difference_section = True
                header_line_index = i + 1 # Header should be on the next lines
                break
        
        if not in_difference_section:
            return [] # No differences section found

        # Try to find the header row of the differences table and the index of "Column"
        col_idx_in_table_header = -1
        data_start_line_idx = -1

        for i in range(header_line_index, min(header_line_index + 4, len(lines))): # Search a few lines
            line_stripped = lines[i].strip()
            if not line_stripped: continue

            if COLUMN_HEADER_NAME in line_stripped:
                current_line_headers = []
                if line_stripped.startswith("|") and line_stripped.endswith("|"): # Tabulate format
                    parts = [p.strip() for p in line_stripped.split('|')]
                    current_line_headers = [p for p in parts if p]
                else: # Simple text format (assume space-separated)
                    current_line_headers = line_stripped.split() 

                try:
                    col_idx_in_table_header = current_line_headers.index(COLUMN_HEADER_NAME)
                    data_start_line_idx = i + 1
                    if data_start_line_idx < len(lines):
                        next_line_s = lines[data_start_line_idx].strip()
                        if next_line_s.startswith("|-") or next_line_s.startswith("+-"):
                            data_start_line_idx += 1
                    break 
                except ValueError:
                    col_idx_in_table_header = -1 
            
        if data_start_line_idx == -1 or col_idx_in_table_header == -1:
            # print(f"Warning: Could not find or parse 'Differences' table header in file {os.path.basename(filepath)}.")
            return []

        # Parse data rows for error column names
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
            elif col_idx_in_table_header == 0 and not line_content_stripped.startswith("|"): 
                possible_col_name_parts = re.split(r'\s{2,}', line_content_stripped) 
                if possible_col_name_parts:
                    extracted_name_from_row = possible_col_name_parts[0]

            if extracted_name_from_row and extracted_name_from_row != COLUMN_HEADER_NAME:
                best_match_for_error_col = extracted_name_from_row 
                if compared_cols_for_report: 
                    if extracted_name_from_row in compared_cols_for_report:
                        best_match_for_error_col = extracted_name_from_row
                    else:
                        possible_canonical_matches = [
                            known_field for known_field in compared_cols_for_report 
                            if extracted_name_from_row in known_field 
                        ]
                        if possible_canonical_matches:
                            best_match_for_error_col = max(possible_canonical_matches, key=len)
                error_columns.append(best_match_for_error_col)

    except FileNotFoundError:
        print(f"Warning: Accuracy file not found: {filepath}")
    except Exception as e:
        print(f"Error while parsing file {os.path.basename(filepath)}: {e}")

    return error_columns

# --- Main Analysis Function (now parameterized) ---
def analyze_error_distribution_for_provider_model(provider_name, model_name_slug, dataset_name):
    """
    Analyzes the distribution of errors across columns from accuracy reports
    for a specific LLM provider and model.
    Args:
        provider_name (str): The LLM provider name.
        model_name_slug (str): The model name slug (filesystem-safe).
    """
    print(f"\n--- Analyzing Error Distribution for Provider '{provider_name}', Model '{model_name_slug}' ---")

    current_accuracy_dir = config.get_accuracy_reports_dir(provider_name, model_name_slug, dataset_name)
    current_analysis_dir = config.get_overall_analysis_dir(provider_name, model_name_slug, dataset_name)
    
    error_plot_file = os.path.join(current_analysis_dir, f"error_column_distribution_{provider_name}_{model_name_slug}.png")
    error_csv_file = os.path.join(current_analysis_dir, f"error_column_counts_{provider_name}_{model_name_slug}.csv")

    try:
        os.makedirs(current_analysis_dir, exist_ok=True)
    except Exception as e:
        print(f"Error: Failed to create analysis directory '{current_analysis_dir}': {e}")
        return

    all_error_columns_aggregated = []
    report_files_processed_count = 0

    print(f"Reading accuracy reports from: {current_accuracy_dir}")
    if not os.path.isdir(current_accuracy_dir):
        print(f"Error: Accuracy report directory not found: {current_accuracy_dir}")
        print("Please ensure the evaluation process has been run for the specified provider and model.")
        return

    filenames = [f for f in os.listdir(current_accuracy_dir) if f.endswith(".txt")]
    if not filenames:
        print(f"Info: No .txt files found in the accuracy report directory '{current_accuracy_dir}'.")
        return
        
    print(f"Found {len(filenames)} accuracy report files. Parsing errors...")

    for filename in filenames:
        filepath = os.path.join(current_accuracy_dir, filename)
        
        temp_compared_cols = [] # Initialize for each file
        try:
            with open(filepath, 'r', encoding='utf-8') as f_temp:
                lines_temp = f_temp.readlines()
            reading_comp_cols = False
            for line_t in lines_temp:
                line_t_s = line_t.strip()
                if line_t_s.startswith("Compared Columns ("):
                    reading_comp_cols = True
                    continue
                if reading_comp_cols and line_t_s: # This should be the line with column names
                    raw_parts = [p.strip() for p in line_t_s.split(',') if p.strip()]
                    # MODIFICATION: Assume raw_parts are the usable field names
                    # This removes the dependency on the missing config.reconstruct_split_field_names
                    # and config.STANDARD_FIELD_NAMES
                    temp_compared_cols = raw_parts
                    break 
        except Exception as e_pre_parse:
            print(f"Warning: Error during pre-parsing of file {filename} to get compared_columns: {e_pre_parse}")
            # Continue with temp_compared_cols as empty if pre-parsing failed,
            # parse_error_columns_from_file will handle it.

        errors_in_file = parse_error_columns_from_file(filepath, temp_compared_cols)
        all_error_columns_aggregated.extend(errors_in_file)
        report_files_processed_count += 1

    if not all_error_columns_aggregated:
        print("\nNo errors were found in any report files, or the errors could not be parsed.")
        return

    print(f"\nParsed errors from {report_files_processed_count} reports. Found a total of {len(all_error_columns_aggregated)} error records across fields.")

    error_counts = Counter(all_error_columns_aggregated)
    error_df = pd.DataFrame(error_counts.items(), columns=['Column', 'Error_Frequency'])
    error_df = error_df.sort_values(by='Error_Frequency', ascending=False).reset_index(drop=True)

    if error_df.empty:
        print("Error count DataFrame is empty, cannot generate report.")
        return

    print(f"\nTop {min(10, len(error_df))} most frequent error fields:")
    print(error_df.head(10).to_string(index=False))

    try:
        error_df.to_csv(error_csv_file, index=False, encoding='utf-8-sig')
        print(f"\nError frequency counts have been saved to: {error_csv_file}")
    except Exception as e:
        print(f"Error saving error counts to CSV file '{error_csv_file}': {e}")

    try:
        num_cols_to_plot = min(30, len(error_df)) 
        plot_df = error_df.head(num_cols_to_plot).sort_values(by='Error_Frequency', ascending=True)

        plt.figure(figsize=(15, max(8, num_cols_to_plot * 0.4))) 

        sns.barplot(x='Error_Frequency', y='Column', data=plot_df,
                      palette='plasma', 
                      orient='h',
                      hue='Column', 
                      legend=False) 
        
        plt.title(f'Top {num_cols_to_plot} Most Frequent Error Fields ({provider_name} / {model_name_slug})', fontsize=16, pad=20)
        plt.xlabel('Number of Reports with Error in this Field', fontsize=12, labelpad=10)
        plt.ylabel('Field Name', fontsize=12, labelpad=10)
        plt.yticks(fontsize=8) 
        plt.xticks(fontsize=8)

        for patch in plt.gca().patches:
            plt.text(patch.get_width() + 0.1, patch.get_y() + patch.get_height() / 2.,
                     f'{int(patch.get_width())}',
                     va='center', ha='left', fontsize=7)

        plt.tight_layout() 
        plt.grid(axis='x', linestyle='--', alpha=0.6) 
        sns.despine()

        plt.savefig(error_plot_file, dpi=150, bbox_inches='tight')
        print(f"Error distribution plot saved to: {error_plot_file}")
        plt.close() 
    except Exception as e:
        print(f"\nError generating or saving the error distribution plot: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze error distribution from accuracy reports for a specified LLM provider and model.")
    parser.add_argument("provider_name", help="The name of the LLM provider (e.g., openai, gemini, claude).")
    parser.add_argument("model_name_slug", help="The identifier for the LLM model (filesystem-safe version, e.g., gpt-4o, gemini-1.5-pro-latest).")
    
    args = parser.parse_args()

    if args.provider_name not in config.LLM_PROVIDERS:
        print(f"Error: Unknown provider '{args.provider_name}'. Options are: {list(config.LLM_PROVIDERS.keys())}")
        sys.exit(1)
    if not args.model_name_slug.strip():
        print(f"Error: model_name_slug cannot be empty.")
        sys.exit(1)
    
    analyze_error_distribution_for_provider_model(args.provider_name, args.model_name_slug, dataset_name="sugo")

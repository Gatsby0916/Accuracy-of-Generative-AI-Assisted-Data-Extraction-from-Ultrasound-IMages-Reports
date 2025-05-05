import os
import re
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
try:
    import config # Import project configuration
except ImportError:
    print("错误：无法导入 config.py。请确保此脚本与 config.py 在同一 src 目录下，或者 config.py 在 Python 路径中。")
    sys.exit(1)

# --- Configuration ---
# Use paths defined in config.py
ACCURACY_DIR = config.ACCURACY_REPORTS_DIR
ANALYSIS_DIR = config.OVERALL_ANALYSIS_DIR
ERROR_PLOT_FILE = os.path.join(ANALYSIS_DIR, "error_column_distribution.png")
ERROR_CSV_FILE = os.path.join(ANALYSIS_DIR, "error_column_counts.csv")

# Ensure analysis output directory exists
os.makedirs(ANALYSIS_DIR, exist_ok=True)

# --- Function to Parse Errors from a Single File ---
def parse_error_columns_from_file(filepath):
    """
    Parses an _accuracy.txt file to extract column names listed under '--- Differences ---'.
    Handles both tabulate (psql format) and basic to_string table formats.
    """
    error_columns = []
    in_difference_section = False
    header_found = False
    column_header_index = -1 # Index of the 'Column' header

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

            for line in lines:
                line_stripped = line.strip()

                if line_stripped == '--- Differences ---':
                    in_difference_section = True
                    header_found = False # Reset header flag for each diff section
                    column_header_index = -1
                    continue # Move to the next line

                if in_difference_section:
                    # Detect header separator line (like +---... or | Column | ...)
                    if (line_stripped.startswith('+--') and line_stripped.endswith('--+')) or \
                       (line_stripped.startswith('|') and 'Column' in line and '|' in line[1:]): # Check for tabulate headers
                        header_found = True
                        # Find the starting position of the 'Column' header
                        try:
                            # Find index based on '| Column' pattern
                            col_header_start = line.find('| Column') 
                            if col_header_start != -1:
                                # Find the end of the 'Column' header section
                                next_pipe = line.find('|', col_header_start + 1)
                                if next_pipe != -1:
                                     # We will extract text between these pipe indices later
                                     column_header_index = (col_header_start, next_pipe)
                            else: # Fallback for simple header like "Column True Value ..."
                                 column_header_index = line_stripped.find('Column')

                        except ValueError:
                             column_header_index = -1 # Header format not recognized or 'Column' missing
                        continue # Move to the next line after header/separator

                    # If header was found and this line looks like data (starts with '|' or not a separator)
                    if header_found and not (line_stripped.startswith('+--') and line_stripped.endswith('--+')):
                         # Try extracting based on pipe indices if found (tabulate format)
                         if isinstance(column_header_index, tuple):
                              start_idx, end_idx = column_header_index
                              # Ensure indices are valid and line is long enough
                              if start_idx != -1 and end_idx != -1 and len(line) > end_idx:
                                   # Extract text between the pipes for the 'Column' section
                                   col_name = line[start_idx+1:end_idx].strip()
                                   # Basic check to avoid empty strings or separators
                                   if col_name and not col_name.startswith('--'):
                                        error_columns.append(col_name)
                         # Fallback for simple space-separated format (less reliable)
                         elif column_header_index == 0: # Assumes 'Column' is the very first word
                              parts = line_stripped.split(maxsplit=1) # Split only on first space
                              if parts:
                                   col_name = parts[0]
                                   # Add more checks if needed to ensure it's a valid column name
                                   if len(col_name) > 1: # Avoid single characters etc.
                                        error_columns.append(col_name)
                         # If line doesn't match expected table format, stop parsing diffs for this file
                         # else:
                         #    in_difference_section = False # Or just continue to next line

    except FileNotFoundError:
        print(f"Warning: Accuracy file not found: {filepath}")
    except Exception as e:
        print(f"Error parsing file {os.path.basename(filepath)}: {e}")

    return error_columns

# --- Main Analysis Function ---
def analyze_error_distribution():
    """
    Analyzes the distribution of errors across columns from all accuracy reports.
    """
    all_error_columns = []
    report_count = 0

    print(f"Reading accuracy reports from: {ACCURACY_DIR}")
    if not os.path.isdir(ACCURACY_DIR):
        print(f"Error: Accuracy reports directory not found: {ACCURACY_DIR}")
        sys.exit(1)

    # Iterate through all .txt files in the accuracy directory
    filenames = [f for f in os.listdir(ACCURACY_DIR) if f.endswith(".txt")]
    if not filenames:
        print("Error: No .txt files found in the accuracy reports directory.")
        sys.exit(1)
        
    print(f"Found {len(filenames)} accuracy report files. Parsing errors...")

    for filename in filenames:
        filepath = os.path.join(ACCURACY_DIR, filename)
        errors_in_file = parse_error_columns_from_file(filepath)
        all_error_columns.extend(errors_in_file)
        report_count += 1

    if not all_error_columns:
        print("\nNo errors found in any report files, or errors could not be parsed.")
        return

    print(f"\nParsed errors from {report_count} reports. Found {len(all_error_columns)} total errors across all columns.")

    # Count the frequency of each column name appearing in the errors
    error_counts = Counter(all_error_columns)

    # Convert to DataFrame for easier handling and sorting
    error_df = pd.DataFrame(error_counts.items(), columns=['Column', 'Error Frequency'])
    error_df = error_df.sort_values(by='Error Frequency', ascending=False).reset_index(drop=True)

    print(f"\nTop {min(10, len(error_df))} most frequent error columns:")
    print(error_df.head(10).to_string(index=False))

    # --- Save Error Counts to CSV ---
    try:
        error_df.to_csv(ERROR_CSV_FILE, index=False, encoding='utf-8-sig') # Use utf-8-sig for Excel compatibility
        print(f"\nError frequency counts saved to: {ERROR_CSV_FILE}")
    except Exception as e:
        print(f"Error saving error counts to CSV: {e}")

    # --- Generate and Save Histogram (Bar Chart) ---
# ... (脚本的其他部分保持不变) ...

    # --- Generate and Save Histogram (Bar Chart) ---
    try:
        # Determine how many columns to plot (e.g., top 30 or all if fewer)
        num_cols_to_plot = min(30, len(error_df))
        plot_df = error_df.head(num_cols_to_plot)

        plt.figure(figsize=(15, 8)) # Adjust figure size for potentially many bars

        # --- FIX: Address FutureWarning & Change Palette ---
        # Assign the y variable ('Column') to hue
        # Change palette to 'magma'
        # Set legend=False because we don't need a legend for the hue here
        sns.barplot(x='Error Frequency', y='Column', data=plot_df,
                    palette='magma', # <--- Change palette here
                    orient='h',      # Keep orientation horizontal
                    hue='Column',    # Assign y-variable to hue
                    legend=False)    # Disable the legend for hue
        # --- End FIX ---

        plt.title(f'Top {num_cols_to_plot} Columns with Highest Error Frequency', fontsize=16, pad=20)
        plt.xlabel('Number of Reports with Error in this Column', fontsize=12, labelpad=10)
        plt.ylabel('Column Name', fontsize=12, labelpad=10)

        # Adjust y-axis tick label size if needed
        plt.yticks(fontsize=8)

        plt.tight_layout() # Adjust layout
        plt.grid(axis='x', linestyle='--', alpha=0.6) # Add horizontal grid lines

        # Save the plot
        plt.savefig(ERROR_PLOT_FILE, dpi=150, bbox_inches='tight') # Use bbox_inches='tight'
        print(f"Error distribution plot saved to: {ERROR_PLOT_FILE}")
        plt.close()

    except Exception as e:
        print(f"\nError generating or saving error distribution plot: {e}")

# --- Main Execution Block ---
if __name__ == "__main__":
    analyze_error_distribution()
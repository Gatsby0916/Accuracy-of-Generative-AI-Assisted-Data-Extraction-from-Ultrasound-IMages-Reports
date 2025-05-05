import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns # Seaborn for better styling
import sys
try:
    import config # Try importing project config
except ImportError:
    print("错误：无法导入 config.py。请确保此脚本与 config.py 在同一 src 目录下，或者 config.py 在 Python 路径中。")
    sys.exit(1)

# --- Configuration ---
# Keep setting for unicode minus, it's generally good practice
plt.rcParams['axes.unicode_minus'] = False
# Set a clean seaborn style
sns.set_style("whitegrid") # Or try "darkgrid", "ticks"

# --- Use Paths from config ---
accuracy_folder = config.ACCURACY_REPORTS_DIR
analysis_folder = config.OVERALL_ANALYSIS_DIR
summary_filepath = config.SUMMARY_REPORT_TXT
plot_filepath = config.ACCURACY_PLOT_PNG

# Ensure analysis output directory exists
os.makedirs(analysis_folder, exist_ok=True)

# --- extract_accuracy_from_file function (Unchanged) ---
def extract_accuracy_from_file(filepath):
    """Extracts accuracy value and report ID from a single accuracy file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
            accuracy = None
            report_id = None
            for line in lines:
                if line.startswith("Report ID:"):
                     report_id = line.split(":")[1].strip()
                # Check for English or previously used Chinese key
                if line.startswith("Overall accuracy:") or line.startswith("总体准确率:"):
                    accuracy_str = line.split(":")[1].strip()
                    try:
                        accuracy = float(accuracy_str)
                    except ValueError:
                        print(f"Warning: Could not convert '{accuracy_str}' to float (File: {os.path.basename(filepath)})")
                        accuracy = None
            if accuracy is not None and report_id is not None:
                 return report_id, accuracy
            else:
                 if report_id:
                      print(f"Warning: Valid 'Overall accuracy' line not found in {os.path.basename(filepath)}.")
                 return report_id, None # Return ID even if accuracy is missing/invalid
    except FileNotFoundError:
         print(f"Warning: Accuracy file not found: {filepath}")
         return None, None
    except Exception as e:
        print(f"Error reading or parsing file {os.path.basename(filepath)}: {e}")
        return None, None

# --- generate_report function (Plotting section modified) ---
def generate_report():
    """Reads all accuracy files, calculates summary stats, generates histogram and report."""
    accuracies = []
    report_ids = []

    print(f"Reading accuracy reports from: {accuracy_folder}")

    if not os.path.isdir(accuracy_folder):
        print(f"Error: Accuracy reports directory not found: {accuracy_folder}")
        sys.exit(1)

    filenames = sorted([f for f in os.listdir(accuracy_folder) if f.endswith(".txt")])
    if not filenames:
         print("Error: No .txt files found in the accuracy reports directory.")
         sys.exit(1)
    print(f"Found {len(filenames)} .txt files.")

    for filename in filenames:
        filepath = os.path.join(accuracy_folder, filename)
        report_id, accuracy = extract_accuracy_from_file(filepath)
        if accuracy is not None: # Only include valid accuracies
            accuracies.append(accuracy)
            # Use the report ID found in the file, or derive from filename if missing in file
            report_ids.append(report_id if report_id else filename.replace('_accuracy.txt', '').replace(' ', ''))
        elif report_id: # If ID exists but accuracy is invalid/missing
             print(f"Skipping report {report_id} due to missing or invalid accuracy value.")

    if not accuracies:
        print("\nError: No valid accuracy data extracted. Cannot generate report.")
        sys.exit(1)

    # --- Calculate Statistics (Unchanged) ---
    accuracies_np = np.array(accuracies)
    average_accuracy = np.mean(accuracies_np)
    median_accuracy = np.median(accuracies_np)
    std_dev = np.std(accuracies_np)
    min_accuracy = np.min(accuracies_np)
    max_accuracy = np.max(accuracies_np)
    min_idx = np.argmin(accuracies_np)
    max_idx = np.argmax(accuracies_np)
    
    # Ensure indices are valid before accessing report_ids list
    min_report_id = report_ids[min_idx] if min_idx < len(report_ids) else 'N/A'
    max_report_id = report_ids[max_idx] if max_idx < len(report_ids) else 'N/A'


    print("\n--- Accuracy Summary Statistics ---")
    print(f"Number of Reports Processed: {len(accuracies)}")
    print(f"Average Accuracy         : {average_accuracy:.4f}")
    print(f"Median Accuracy          : {median_accuracy:.4f}")
    print(f"Standard Deviation       : {std_dev:.4f}")
    print(f"Minimum Accuracy         : {min_accuracy:.4f} (Report: {min_report_id})")
    print(f"Maximum Accuracy         : {max_accuracy:.4f} (Report: {max_report_id})")

    # --- Save Summary Statistics to File (Unchanged logic, uses English keys now potentially) ---
    try:
        with open(summary_filepath, "w", encoding="utf-8") as f:
            f.write("--- Accuracy Summary ---\n")
            f.write(f"Processed Reports : {len(accuracies)}\n")
            f.write(f"Average Accuracy  : {average_accuracy:.4f}\n")
            f.write(f"Median Accuracy   : {median_accuracy:.4f}\n")
            f.write(f"Std Deviation     : {std_dev:.4f}\n")
            f.write(f"Minimum Accuracy  : {min_accuracy:.4f} (Report: {min_report_id})\n")
            f.write(f"Maximum Accuracy  : {max_accuracy:.4f} (Report: {max_report_id})\n\n")
            f.write("--- Individual Report Accuracies ---\n")
            # Sort by report ID before writing individual accuracies
            report_acc_pairs = sorted(zip(report_ids, accuracies))
            for r_id, acc in report_acc_pairs:
                f.write(f"{r_id}: {acc:.4f}\n")
        print(f"\nSummary statistics saved to: {summary_filepath}")
    except Exception as e:
         print(f"Error saving summary statistics file: {e}")

    # --- !!! Generate and Save Beautified Histogram with English Labels !!! ---
    try:
        plt.figure(figsize=(12, 7)) # Slightly adjusted size

        # Define histogram bins (0 to 1.0 with 0.1 steps)
        bins = np.arange(0, 1.1, 0.1)

        # Plot histogram with adjusted aesthetics
        n, bins, patches = plt.hist(accuracies_np, bins=bins, edgecolor='black', # Black edges for bins
                                     linewidth=0.8, alpha=0.75, color='#3498db') # Nicer blue color

        # Add data labels on top of bars
        for i in range(len(patches)):
             height = n[i]
             if height > 0:
                  plt.text(patches[i].get_x() + patches[i].get_width() / 2., height + 0.15, # Adjust vertical offset
                           f'{int(height)}', # Display integer count
                           ha='center', va='bottom', fontsize=9, color='dimgray') # Slightly dimmer color

        # Add vertical lines for average and median with English labels
        plt.axvline(average_accuracy, color='#e74c3c', linestyle='--', linewidth=1.5, # Reddish color
                    label=f'Average: {average_accuracy:.4f}')
        plt.axvline(median_accuracy, color='#2ecc71', linestyle=':', linewidth=1.5, # Greenish color
                    label=f'Median: {median_accuracy:.4f}')

        # Set English title and labels with slightly larger font size
        plt.title("Distribution of Report Accuracy Scores", fontsize=16, pad=20)
        plt.xlabel("Accuracy Score", fontsize=12, labelpad=10)
        plt.ylabel("Number of Reports", fontsize=12, labelpad=10)

        # Set x-axis ticks to match bin edges
        plt.xticks(bins)
        # Ensure y-axis starts at 0
        plt.ylim(bottom=0)

        # Add legend for the vertical lines
        plt.legend(fontsize=10)

        # Remove top and right spines for a cleaner look
        sns.despine()

        # Adjust layout
        plt.tight_layout()

        # Save the plot
        plt.savefig(plot_filepath, dpi=150) # Increase DPI for better resolution
        print(f"Accuracy histogram plot saved to: {plot_filepath}")

        # Close the plot figure
        plt.close()

    except Exception as e:
        # Catch potential plotting errors
        print(f"\nError generating or saving accuracy histogram: {e}")
        print("This might be due to missing graphical backend or permissions.")
    # --- !!! Plotting modification ends !!! ---


if __name__ == "__main__":
    generate_report()

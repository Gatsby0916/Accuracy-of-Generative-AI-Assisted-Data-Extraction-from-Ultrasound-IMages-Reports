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
        print("错误：无法导入 config.py。请确保此脚本与 config.py 的相对路径正确，或者将包含 config.py 的目录添加到 Python 路径中。")
        sys.exit(1)

# Matplotlib font setup for Chinese characters (from your script)
from matplotlib import rcParams
try:
    rcParams['font.sans-serif'] = ['SimHei']
    rcParams['axes.unicode_minus'] = False
    print("已尝试设置中文字体为 'SimHei'。")
except Exception as e:
    print(f"设置中文字体失败: {e}")
    print("请确保已安装 SimHei 或其他中文字体，并尝试修改脚本中的字体名称。")


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
            # print(f"警告：在文件 {os.path.basename(filepath)} 中未能找到或解析 'Differences' 表的表头。")
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
        print(f"警告：准确率文件未找到: {filepath}")
    except Exception as e:
        print(f"解析文件 {os.path.basename(filepath)} 时出错: {e}")

    return error_columns

# --- Main Analysis Function (now parameterized) ---
def analyze_error_distribution_for_provider_model(provider_name, model_name_slug):
    """
    Analyzes the distribution of errors across columns from accuracy reports
    for a specific LLM provider and model.
    Args:
        provider_name (str): The LLM provider name.
        model_name_slug (str): The model name slug (filesystem-safe).
    """
    print(f"\n--- 为提供商 '{provider_name}', 模型 '{model_name_slug}' 分析错误分布 ---")

    current_accuracy_dir = config.get_accuracy_reports_dir(provider_name, model_name_slug)
    current_analysis_dir = config.get_overall_analysis_dir(provider_name, model_name_slug)
    
    error_plot_file = os.path.join(current_analysis_dir, f"error_column_distribution_{provider_name}_{model_name_slug}.png")
    error_csv_file = os.path.join(current_analysis_dir, f"error_column_counts_{provider_name}_{model_name_slug}.csv")

    try:
        os.makedirs(current_analysis_dir, exist_ok=True)
    except Exception as e:
        print(f"错误：创建分析目录 '{current_analysis_dir}' 时失败: {e}")
        return

    all_error_columns_aggregated = []
    report_files_processed_count = 0

    print(f"从以下路径读取准确率报告: {current_accuracy_dir}")
    if not os.path.isdir(current_accuracy_dir):
        print(f"错误：准确率报告目录未找到: {current_accuracy_dir}")
        print("请确保已为指定的提供商和模型运行评估流程。")
        return

    filenames = [f for f in os.listdir(current_accuracy_dir) if f.endswith(".txt")]
    if not filenames:
        print(f"信息：在准确率报告目录 '{current_accuracy_dir}' 中未找到 .txt 文件。")
        return
        
    print(f"找到 {len(filenames)} 个准确率报告文件。正在解析错误...")

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
            print(f"警告: 预解析文件 {filename} 以获取 compared_columns 时出错: {e_pre_parse}")
            # Continue with temp_compared_cols as empty if pre-parsing failed,
            # parse_error_columns_from_file will handle it.

        errors_in_file = parse_error_columns_from_file(filepath, temp_compared_cols)
        all_error_columns_aggregated.extend(errors_in_file)
        report_files_processed_count += 1

    if not all_error_columns_aggregated:
        print("\n在任何报告文件中均未发现错误，或错误无法被解析。")
        return

    print(f"\n从 {report_files_processed_count} 个报告中解析了错误。总共发现 {len(all_error_columns_aggregated)} 个跨字段的错误记录。")

    error_counts = Counter(all_error_columns_aggregated)
    error_df = pd.DataFrame(error_counts.items(), columns=['Column', 'Error_Frequency'])
    error_df = error_df.sort_values(by='Error_Frequency', ascending=False).reset_index(drop=True)

    if error_df.empty:
        print("错误计数DataFrame为空，无法生成报告。")
        return

    print(f"\n出现频率最高的 {min(10, len(error_df))} 个错误字段:")
    print(error_df.head(10).to_string(index=False))

    try:
        error_df.to_csv(error_csv_file, index=False, encoding='utf-8-sig')
        print(f"\n错误频率计数已保存至: {error_csv_file}")
    except Exception as e:
        print(f"保存错误计数到CSV文件 '{error_csv_file}' 时出错: {e}")

    try:
        num_cols_to_plot = min(30, len(error_df)) 
        plot_df = error_df.head(num_cols_to_plot).sort_values(by='Error_Frequency', ascending=True)

        plt.figure(figsize=(15, max(8, num_cols_to_plot * 0.4))) 

        sns.barplot(x='Error_Frequency', y='Column', data=plot_df,
                    palette='plasma', 
                    orient='h',
                    hue='Column', 
                    legend=False) 
        
        plt.title(f'错误频率最高的 {num_cols_to_plot} 个字段 ({provider_name} / {model_name_slug})', fontsize=16, pad=20)
        plt.xlabel('报告中该字段出错的次数', fontsize=12, labelpad=10)
        plt.ylabel('字段名称', fontsize=12, labelpad=10)
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
        print(f"错误分布图已保存至: {error_plot_file}")
        plt.close() 
    except Exception as e:
        print(f"\n生成或保存错误分布图时出错: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="为指定的LLM提供商和模型分析准确率报告中的错误分布。")
    parser.add_argument("provider_name", help="LLM提供商的名称 (例如: openai, gemini, claude)。")
    parser.add_argument("model_name_slug", help="LLM模型的标识符 (文件系统安全版本，例如: gpt-4o, gemini-1.5-pro-latest)。")
    
    args = parser.parse_args()

    if args.provider_name not in config.LLM_PROVIDERS:
        print(f"错误: 未知的提供商 '{args.provider_name}'. 可选项: {list(config.LLM_PROVIDERS.keys())}")
        sys.exit(1)
    if not args.model_name_slug.strip():
        print(f"错误: model_name_slug不能为空。")
        sys.exit(1)
    
    analyze_error_distribution_for_provider_model(args.provider_name, args.model_name_slug)
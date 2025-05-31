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
        print("错误：无法导入 config.py。请确保此脚本与 config.py 的相对路径正确，或者将包含 config.py 的目录添加到 Python 路径中。")
        sys.exit(1)

def get_expected_ids_from_pdfs(pdf_directory):
    """
    Scans the specified PDF directory for filenames and extracts expected report IDs (format RRIXXX).
    """
    expected_ids = set()
    # Regex to find RRIXXX.pdf or RRI XXX.pdf (case insensitive)
    pattern = re.compile(r'^RRI\s?(\d{3})\.pdf$', re.IGNORECASE)

    print(f"正在扫描 PDF 目录以获取预期报告列表: {pdf_directory}")
    if not os.path.isdir(pdf_directory):
        print(f"错误：指定的 PDF 目录不存在: {pdf_directory}")
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
        print(f"从 PDF 文件名中发现 {count} 个预期的报告 ID。")
        return expected_ids
    except Exception as e:
        print(f"扫描 PDF 目录 '{pdf_directory}' 时出错: {e}")
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

    print(f"正在扫描准确率报告目录: {accuracy_dir_for_llm}")
    if not os.path.isdir(accuracy_dir_for_llm):
        print(f"错误：指定的准确率报告目录不存在: {accuracy_dir_for_llm}")
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
        print(f"从准确率报告文件名中发现 {count} 个成功处理的报告 ID。")
        return successful_ids
    except Exception as e:
        print(f"扫描准确率报告目录 '{accuracy_dir_for_llm}' 时出错: {e}")
        return None

def get_ids_from_ground_truth(excel_path, id_column_names_list):
    """
    Reads report ID column from the Ground Truth Excel file and returns a set of standardized IDs (RRIXXX).
    """
    print(f"正在读取 Ground Truth Excel 文件以获取 ID 列表: {excel_path}")
    if not os.path.exists(excel_path):
        print(f"错误：Ground Truth Excel 文件未找到: {excel_path}")
        return None

    try:
        df_true = pd.read_excel(excel_path, dtype=str) # Read all columns as strings
        
        id_col_name_found = None
        for col_name in id_column_names_list:
            if col_name in df_true.columns:
                id_col_name_found = col_name
                break
        
        if not id_col_name_found:
            print(f"错误：在 Excel 文件 '{excel_path}' 中找不到指定的报告 ID 列 (已检查: {id_column_names_list})。")
            return None

        print(f"找到报告 ID 列: '{id_col_name_found}'")
        
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
        
        print(f"从 Ground Truth Excel 中发现 {len(ground_truth_ids)} 个有效的报告 ID。")
        return ground_truth_ids

    except Exception as e:
        print(f"读取或处理 Ground Truth Excel 文件 '{excel_path}' 时出错: {e}")
        return None

def find_missing_reports_for_provider_model(provider_name, model_name_slug):
    """
    Compares expected reports (from PDFs), successfully processed reports (from accuracy files
    for the given provider/model), and Ground Truth reports to find discrepancies.
    Args:
        provider_name (str): The LLM provider name.
        model_name_slug (str): The model name slug (filesystem-safe).
    """
    print(f"\n--- 为提供商 '{provider_name}', 模型 '{model_name_slug}' 检查缺失报告 ---")

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
        print("由于无法从PDF文件获取预期ID，部分比较将无法进行。")
        expected_ids_from_pdf = set() # Use empty set to allow other comparisons
    if successful_ids_for_llm is None:
        print(f"由于无法从准确率报告目录 '{accuracy_dir_for_llm}' 获取成功ID，部分比较将无法进行。")
        successful_ids_for_llm = set()
    if ground_truth_ids_from_excel is None:
        print("由于无法从Ground Truth Excel获取ID，部分比较将无法进行。")
        ground_truth_ids_from_excel = set()
    
    # --- Perform Comparisons ---
    print(f"\n--- 报告处理状态交叉检查结果 ({provider_name} / {model_name_slug}) ---")
    print(f"预期报告总数 (来自 PDF 文件): {len(expected_ids_from_pdf)}")
    print(f"Ground Truth Excel 中的报告总数: {len(ground_truth_ids_from_excel)}")
    print(f"已成功为此提供商/模型生成准确率报告的数量: {len(successful_ids_for_llm)}")

    # Check 1: PDFs that are in Ground Truth but no accuracy report for this LLM/model
    gt_ids_not_in_successful_llm = ground_truth_ids_from_excel - successful_ids_for_llm
    if gt_ids_not_in_successful_llm:
        print(f"\n[检查 1] **注意**: 以下 {len(gt_ids_not_in_successful_llm)} 个报告ID存在于Ground Truth中, 但未找到对应的准确率报告 ({provider_name}/{model_name_slug}):")
        for report_id in sorted(list(gt_ids_not_in_successful_llm)):
            print(f"  - {report_id}")
    else:
        print(f"\n[检查 1] 通过: 所有Ground Truth中的报告ID都已为此提供商/模型生成了准确率报告 (或Ground Truth为空)。")

    # Check 2: PDFs found in scan, but no accuracy report for this LLM/model
    # This is particularly relevant if processing is done for all PDFs.
    pdf_ids_not_in_successful_llm = expected_ids_from_pdf - successful_ids_for_llm
    if pdf_ids_not_in_successful_llm:
        print(f"\n[检查 2] **注意**: 以下 {len(pdf_ids_not_in_successful_llm)} 个报告ID存在于PDF扫描目录中, 但未找到对应的准确率报告 ({provider_name}/{model_name_slug}):")
        for report_id in sorted(list(pdf_ids_not_in_successful_llm)):
            print(f"  - {report_id}")
    else:
        print(f"\n[检查 2] 通过: 所有在PDF目录中扫描到的报告ID都已为此提供商/模型生成了准确率报告 (或PDF扫描列表为空)。")

    # --- Additional Optional Checks (can be expanded) ---
    # Check 3: IDs in PDF scan but not in Ground Truth
    pdf_ids_not_in_gt = expected_ids_from_pdf - ground_truth_ids_from_excel
    if pdf_ids_not_in_gt:
        print(f"\n[附加信息 1] 以下 {len(pdf_ids_not_in_gt)} 个报告ID存在于PDF扫描目录中, 但在Ground Truth Excel中未找到:")
        for report_id in sorted(list(pdf_ids_not_in_gt)):
            print(f"  - {report_id}")

    # Check 4: IDs in Ground Truth but not in PDF scan
    gt_ids_not_in_pdf = ground_truth_ids_from_excel - expected_ids_from_pdf
    if gt_ids_not_in_pdf:
        print(f"\n[附加信息 2] 以下 {len(gt_ids_not_in_pdf)} 个报告ID存在于Ground Truth Excel中, 但在PDF扫描目录中未找到对应PDF文件:")
        for report_id in sorted(list(gt_ids_not_in_pdf)):
            print(f"  - {report_id}")
            
    # Check 5: Accuracy reports present for this LLM/model but corresponding ID not in Ground Truth
    successful_llm_ids_not_in_gt = successful_ids_for_llm - ground_truth_ids_from_excel
    if successful_llm_ids_not_in_gt:
        print(f"\n[附加信息 3] 以下 {len(successful_llm_ids_not_in_gt)} 个报告ID的准确率报告存在 ({provider_name}/{model_name_slug}), 但其ID在Ground Truth Excel中未找到:")
        for report_id in sorted(list(successful_llm_ids_not_in_gt)):
            print(f"  - {report_id}")

    print(f"\n--- 检查完成 ({provider_name} / {model_name_slug}) ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="为指定的LLM提供商和模型检查缺失的报告，对比PDF、Ground Truth和准确率报告。"
    )
    parser.add_argument("provider_name", help="LLM提供商的名称 (例如: openai, gemini, claude)。")
    parser.add_argument("model_name_slug", help="LLM模型的标识符 (文件系统安全版本，例如: gpt-4o, gemini-1.5-pro-latest)。")
    
    args = parser.parse_args()

    # Basic validation of inputs
    if args.provider_name not in config.LLM_PROVIDERS:
        print(f"错误: 未知的提供商 '{args.provider_name}'. 可选项: {list(config.LLM_PROVIDERS.keys())}")
        sys.exit(1)
    if not args.model_name_slug.strip(): # Check if slug is not empty or just whitespace
        print(f"错误: model_name_slug不能为空。")
        sys.exit(1)
    
    # It's also good practice to ensure the model_name_slug is somewhat valid for the provider,
    # though main.py should ideally pass valid slugs.
    # For example, check if a directory for this slug could exist or matches a known pattern.

    find_missing_reports_for_provider_model(args.provider_name, args.model_name_slug)

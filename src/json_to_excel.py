import sys
import json
import pandas as pd
import os
import config # Import the config module

# project_root is defined in config, no need to redefine here

def main(report_id, provider_name, model_name_slug):
    """
    Converts a validated JSON file to an Excel file for a given report, provider, and model.
    Args:
        report_id (str): The report ID (e.g., "RRI002").
        provider_name (str): The LLM provider name (e.g., "openai").
        model_name_slug (str): The model name slug for directory naming (e.g., "gpt-4o").
    """
    report_id_formatted = report_id[:3] + " " + report_id[3:] # Format for filenames "RRI XXX"

    # --- Determine Paths using config functions ---
    # Input JSON comes from the 'json_checked' directory for the specific provider and model
    json_checked_folder = config.get_extracted_json_checked_dir(provider_name, model_name_slug)
    json_path = os.path.join(json_checked_folder, f"{report_id_formatted}_extracted_data.json")

    # Output Excel goes into the 'excel' directory for the specific provider and model
    excel_folder = config.get_extracted_excel_dir(provider_name, model_name_slug)
    excel_path = os.path.join(excel_folder, f"{report_id_formatted}_extracted_data.xlsx")

    print(f"\n开始转换JSON到Excel，报告 {report_id} (提供商: {provider_name}, 模型: {model_name_slug})")
    print(f"输入JSON文件路径: {json_path}")
    print(f"输出Excel文件路径: {excel_path}")

    # Ensure the output directory for Excel files exists
    try:
        os.makedirs(excel_folder, exist_ok=True)
    except Exception as e:
        print(f"错误：创建Excel输出目录 '{excel_folder}' 时失败: {e}")
        raise IOError(f"Error creating Excel output directory: {e}") # Re-raise to be caught

    # --- Read JSON ---
    print(f"正在读取 JSON 文件: {json_path}")
    if not os.path.exists(json_path):
        print(f"错误：输入 JSON 文件未找到: {json_path}")
        raise FileNotFoundError(f"Input JSON file for Excel conversion not found: {json_path}")

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"错误：解析 JSON 文件 '{json_path}' 时出错: {e}")
        raise IOError(f"Error decoding JSON file: {e}")
    except Exception as e:
        print(f"读取 JSON 文件 '{json_path}' 时发生未知错误: {e}")
        raise IOError(f"Error reading JSON file: {e}")

    # --- Convert and Save Excel ---
    try:
        # The JSON contains a single object, which needs to be wrapped in a list for DataFrame
        df = pd.DataFrame([data])
        df.to_excel(excel_path, index=False)
        print(f"JSON 文件已成功转换为 Excel: {excel_path}")
    except Exception as e:
        print(f"将 JSON 转换为 Excel 或保存文件 '{excel_path}' 时出错: {e}")
        raise IOError(f"Error converting JSON to Excel or saving: {e}")

if __name__ == "__main__":
    # This script expects three arguments: report_id, provider_name, model_name_slug
    if len(sys.argv) != 4:
        print(f"用法: python {os.path.basename(__file__)} <report_id> <provider_name> <model_name_slug>")
        print("示例: python json_to_excel.py RRI002 openai gpt-4o")
        sys.exit(1)

    report_id_arg = sys.argv[1]
    provider_name_arg = sys.argv[2]
    model_name_slug_arg = sys.argv[3] # This is the fs-safe slug

    try:
        main(report_id_arg, provider_name_arg, model_name_slug_arg)
        print(f"\n报告 {report_id_arg} (提供商: {provider_name_arg}, 模型: {model_name_slug_arg}) 的JSON到Excel转换完成。")
    except Exception as e:
        # Error messages from main() should be informative
        print(f"\n处理报告 {report_id_arg} (提供商: {provider_name_arg}, 模型: {model_name_slug_arg}) 的JSON到Excel转换时发生错误，已中止。")
        sys.exit(1) # Exit with a non-zero code to indicate failure

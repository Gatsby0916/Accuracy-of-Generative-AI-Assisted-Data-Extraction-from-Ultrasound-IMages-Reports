import sys
import json
import pandas as pd
import os
import config # <--- 导入 config 模块

# project_root defined in config, no need to redefine here

def main(report_id):
    report_id_formatted = report_id[:3] + " " + report_id[3:]

    # --- Use Paths from config ---
    json_folder = config.EXTRACTED_JSON_CHECKED_DIR # <--- 使用 config
    json_path = os.path.join(json_folder, f"{report_id_formatted}_extracted_data.json")
    excel_folder = config.EXTRACTED_EXCEL_DIR # <--- 使用 config
    os.makedirs(excel_folder, exist_ok=True)
    excel_path = os.path.join(excel_folder, f"{report_id_formatted}_extracted_data.xlsx")

    print(f"正在读取 JSON 文件: {json_path}")
    if not os.path.exists(json_path):
        print(f"错误：输入 JSON 文件未找到: {json_path}")
        raise FileNotFoundError(f"Input JSON file not found: {json_path}")

    # --- Read JSON ---
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"读取或解析 JSON 文件时出错: {e}")
        raise IOError(f"Error reading JSON file: {e}")

    # --- Convert and Save Excel ---
    try:
        df = pd.DataFrame([data]) # Create DataFrame from single JSON object
        df.to_excel(excel_path, index=False)
        print(f"JSON 文件已成功转换为 Excel: {excel_path}")
    except Exception as e:
        print(f"将 JSON 转换为 Excel 或保存时出错: {e}")
        raise IOError(f"Error converting/saving Excel: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"用法: python {os.path.basename(__file__)} <report_id>")
        sys.exit(1)
    report_id_arg = sys.argv[1]
    try:
        main(report_id_arg)
    except Exception as e:
        print(f"\n处理报告 {report_id_arg} 时发生错误: {e}")
        sys.exit(1) # Exit if run standalone and fails

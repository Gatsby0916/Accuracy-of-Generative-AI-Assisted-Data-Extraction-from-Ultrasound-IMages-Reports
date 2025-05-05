import pandas as pd
import json
import os
import sys
import config # <--- 导入 config 模块

# project_root defined in config, no need to redefine here

# --- Use Paths from config ---
input_file_path = config.ORIGINAL_GROUND_TRUTH_XLSX # <--- 使用 config
output_excel_path = config.CLEANED_GROUND_TRUTH_XLSX # <--- 使用 config
output_json_path = config.TEMPLATE_JSON_PATH # <--- 使用 config

def extract_and_clean():
    """Reads the specified sheet from the original ground truth (defined in config),
    cleans it, saves cleaned version, and saves template JSON."""

    # --- 从 config 读取文件路径和工作表名称 ---
    input_file = config.ORIGINAL_GROUND_TRUTH_XLSX
    output_excel = config.CLEANED_GROUND_TRUTH_XLSX
    output_json = config.TEMPLATE_JSON_PATH
    sheet_to_read = config.GROUND_TRUTH_SHEET_NAME # <--- 从 config 获取工作表名称
    # ------------------------------------------

    if not os.path.exists(input_file):
        print(f"错误：输入 Excel 文件未找到: {input_file}")
        return False

    print(f"正在从文件 {input_file} 读取工作表 '{sheet_to_read}'...")
    try:
        # --- 修改点 ---
        # 使用从 config 读取的工作表名称
        MRI = pd.read_excel(input_file, sheet_name=sheet_to_read)
        # -------------
    except ValueError as ve:
        if f"Worksheet named '{sheet_to_read}' not found" in str(ve):
             print(f"错误：在文件 {input_file} 中未找到名为 '{sheet_to_read}' 的工作表（请检查 config.py 中的 GROUND_TRUTH_SHEET_NAME 设置）。")
        else:
            print(f"读取 Excel 文件时出错: {ve}")
        return False
    except Exception as e:
        print(f"读取 Excel 文件时出错: {e}")
        return False

    print("正在清理数据...")
    try:
        # --- 清理逻辑保持不变 ---
        columns_to_keep = [col for col in MRI.columns if not str(col).startswith('Unnamed:')]
        MRI_cleaned = MRI[columns_to_keep].copy()
        MRI_cleaned.dropna(axis=1, how='all', inplace=True)
        columns = MRI_cleaned.columns.tolist()
        print(f"清理完成，剩余 {len(columns)} 列。")
        # -----------------------
    except Exception as e:
        print(f"清理数据时出错: {e}")
        return False

    # --- 保存清理后的 Excel ---
    print(f"正在保存清理后的 Excel 文件到: {output_excel}")
    try:
        os.makedirs(os.path.dirname(output_excel), exist_ok=True)
        MRI_cleaned.to_excel(output_excel, index=False)
    except Exception as e:
        print(f"保存清理后的 Excel 文件时出错: {e}")
        # return False

    # --- 创建和保存 JSON 模板 ---
    print("正在创建 JSON 模板...")
    json_template = {col: "" for col in columns}

    print(f"正在保存 JSON 模板到: {output_json}")
    try:
        os.makedirs(os.path.dirname(output_json), exist_ok=True)
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(json_template, f, indent=config.JSON_INDENT, ensure_ascii=config.ENSURE_ASCII)
    except Exception as e:
         print(f"保存 JSON 模板时出错: {e}")
         return False

    print(f"\n成功:")
    print(f"- 清理后的 Excel 文件已保存到: {output_excel}")
    print(f"- JSON 模板已保存到: {output_json}")
    return True


if __name__ == "__main__":
    success = extract_and_clean()
    if not success:
        sys.exit(1)
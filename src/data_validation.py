import sys
import json
import difflib
import os
import config # <--- 导入 config 模块

# project_root defined in config, no need to redefine here

# --- Helper Functions (load_json, get_keys - remain largely the same) ---
def load_json(file_path):
    # ... (keep the improved error handling from previous version) ...
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"错误：无法加载 JSON 文件，未找到: {file_path}")
        return None 
    except json.JSONDecodeError:
        print(f"错误：解析 JSON 文件时出错: {file_path}")
        return None
    except Exception as e:
        print(f"加载 JSON 文件 {file_path} 时发生未知错误: {e}")
        return None

def get_keys(data):
    if data is None: return set()
    return set(data.keys())

def find_similar_keys(template_keys, extracted_keys):
    similar = {}
    for key in extracted_keys:
        # Use cutoff from config
        matches = difflib.get_close_matches(key, template_keys, n=1, cutoff=config.SIMILARITY_CUTOFF) # <--- 使用 config
        if matches:
            if key != matches[0]:
                similar[key] = matches[0]
    return similar

# --- Main Check and Fix Logic ---
def check_and_fix(template_path, input_json_path, output_json_path):
    print(f"\n正在校验文件: {os.path.basename(input_json_path)}")
    print(f"使用模板: {os.path.basename(template_path)}")

    template_data = load_json(template_path)
    extracted_data = load_json(input_json_path)

    if template_data is None or extracted_data is None:
        print("错误：无法加载模板或提取的 JSON 文件，校验中止。")
        return False

    template_keys = get_keys(template_data)
    extracted_keys = get_keys(extracted_data)
    missing_in_extracted = template_keys - extracted_keys
    extra_in_extracted = extracted_keys - template_keys
    similar_keys = find_similar_keys(template_keys, extra_in_extracted)
    keys_to_delete = extra_in_extracted - set(similar_keys.keys())
    corrected_data = extracted_data.copy()

    # --- (Logic for adding missing, renaming similar, deleting extra remains the same) ---
    if missing_in_extracted:
        print("信息：提取文件中缺失以下字段名 (将使用模板默认值 '' 添加):")
        for key in missing_in_extracted:
            print(f"  - {key}")
            corrected_data[key] = template_data.get(key, "")
    if similar_keys:
        print("信息：以下提取字段名可能拼写错误，已尝试修正 (提取文件 -> 模板):")
        for wrong_key, correct_key in similar_keys.items():
            print(f"  - '{wrong_key}' -> '{correct_key}'")
            if wrong_key in corrected_data:
                corrected_data[correct_key] = corrected_data.pop(wrong_key)
    if keys_to_delete:
        print("信息：提取文件中发现以下多余字段名 (将被移除):")
        for key in keys_to_delete:
            print(f"  - {key}")
            if key in corrected_data:
                 del corrected_data[key]
    # --- End Logic ---

    try:
        os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
        with open(output_json_path, 'w', encoding='utf-8') as f:
             # Use formatting constants from config
            json.dump(corrected_data, f, indent=config.JSON_INDENT, ensure_ascii=config.ENSURE_ASCII) # <--- 使用 config
        print(f"\n校验完成。修正后的文件已保存至: {output_json_path}")
        return True
    except Exception as e:
        print(f"保存修正后的 JSON 文件时出错: {e}")
        return False


def main(report_id):
    report_id_formatted = report_id[:3] + " " + report_id[3:]

    # --- Use Paths from config ---
    template_path = config.TEMPLATE_JSON_PATH # <--- 使用 config
    input_json_path = os.path.join(config.EXTRACTED_JSON_RAW_DIR, f"{report_id_formatted}_extracted_data.json") # <--- 使用 config
    output_json_path = os.path.join(config.EXTRACTED_JSON_CHECKED_DIR, f"{report_id_formatted}_extracted_data.json") # <--- 使用 config

    if not os.path.exists(input_json_path):
         print(f"错误：需要校验的输入 JSON 文件未找到: {input_json_path}")
         # sys.exit(1) # Let the calling function handle failure
         raise FileNotFoundError(f"Input JSON not found: {input_json_path}") 

    success = check_and_fix(template_path, input_json_path, output_json_path)
    if not success:
        # sys.exit(1) # Let the calling function handle failure
        raise RuntimeError(f"Failed to check and fix JSON for report {report_id}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"用法: python {os.path.basename(__file__)} <report_id>")
        sys.exit(1)
    report_id_arg = sys.argv[1]
    try:
        main(report_id_arg)
    except Exception as e:
        print(f"处理报告 {report_id_arg} 时发生错误: {e}")
        sys.exit(1) # Exit if run standalone and fails

import sys
import json
import difflib
import os
import config # Import the config module

# project_root is defined in config, no need to redefine here

# --- Helper Functions (load_json, get_keys - remain largely the same) ---
def load_json(file_path):
    """
    Loads a JSON file.
    Args:
        file_path (str): The path to the JSON file.
    Returns:
        dict: The loaded JSON data as a dictionary, or None if an error occurs.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"错误：无法加载 JSON 文件，未找到: {file_path}")
        return None
    except json.JSONDecodeError as e: # Corrected typo from JSONDecodeErrorr
        print(f"错误：解析 JSON 文件时出错: {file_path} - {e}")
        return None
    except Exception as e:
        print(f"加载 JSON 文件 {file_path} 时发生未知错误: {e}")
        return None

def get_keys(data):
    """
    Gets all keys from the first level of a dictionary.
    Args:
        data (dict): The dictionary to extract keys from.
    Returns:
        set: A set of keys, or an empty set if data is None.
    """
    if data is None:
        return set()
    return set(data.keys())

def find_similar_keys(template_keys, extracted_keys):
    """
    Finds keys in extracted_keys that are similar to keys in template_keys.
    Args:
        template_keys (set): A set of keys from the template.
        extracted_keys (set): A set of keys from the extracted data.
    Returns:
        dict: A dictionary mapping misspelled keys to their correct counterparts.
    """
    similar = {}
    for key in extracted_keys:
        # Use similarity cutoff from config
        matches = difflib.get_close_matches(key, template_keys, n=1, cutoff=config.SIMILARITY_CUTOFF)
        if matches:
            if key != matches[0]: # If a close match is found and it's not an exact match
                similar[key] = matches[0]
    return similar

# --- Main Check and Fix Logic ---
def check_and_fix(template_path, input_json_path, output_json_path):
    """
    Checks extracted JSON data against a template, fixes discrepancies, and saves the corrected data.
    Args:
        template_path (str): Path to the JSON template file.
        input_json_path (str): Path to the raw extracted JSON file.
        output_json_path (str): Path to save the corrected JSON file.
    Returns:
        bool: True if successful, False otherwise.
    """
    print(f"\n正在校验文件: {os.path.basename(input_json_path)}")
    print(f"使用模板: {os.path.basename(template_path)}")

    template_data = load_json(template_path)
    extracted_data = load_json(input_json_path)

    if template_data is None:
        print(f"错误：无法加载模板JSON文件 '{template_path}'，校验中止。")
        return False
    if extracted_data is None:
        print(f"错误：无法加载提取的JSON文件 '{input_json_path}'，校验中止。")
        # It might be an empty file or truly missing, either way, can't proceed.
        return False # Or raise an error if this should be fatal

    template_keys = get_keys(template_data)
    extracted_keys = get_keys(extracted_data)

    missing_in_extracted = template_keys - extracted_keys
    extra_in_extracted = extracted_keys - template_keys # Keys in extracted but not in template

    # Find keys that are in extra_in_extracted but are just misspellings of template_keys
    similar_keys_to_rename = find_similar_keys(template_keys, extra_in_extracted)

    # Keys that are truly extra (not similar to any template key) and should be deleted
    keys_to_delete = extra_in_extracted - set(similar_keys_to_rename.keys())

    corrected_data = extracted_data.copy() # Start with a copy of the extracted data

    # 1. Add missing keys (present in template, missing in extracted)
    if missing_in_extracted:
        print("信息：提取文件中缺失以下字段名 (将使用模板默认值 '' 添加):")
        for key in sorted(list(missing_in_extracted)): # Sort for consistent output
            print(f"  - {key}")
            corrected_data[key] = template_data.get(key, "") # Use template's default or ""

    # 2. Rename similar keys (misspelled in extracted, correct in template)
    if similar_keys_to_rename:
        print("信息：以下提取字段名可能拼写错误，已尝试修正 (提取文件 -> 模板):")
        for wrong_key, correct_key in sorted(similar_keys_to_rename.items()): # Sort for consistency
            print(f"  - '{wrong_key}' -> '{correct_key}'")
            if wrong_key in corrected_data: # Ensure the key still exists before popping
                corrected_data[correct_key] = corrected_data.pop(wrong_key)

    # 3. Delete extra keys (present in extracted, not in template and not similar)
    if keys_to_delete:
        print("信息：提取文件中发现以下多余字段名 (将被移除):")
        for key in sorted(list(keys_to_delete)): # Sort for consistent output
            print(f"  - {key}")
            if key in corrected_data: # Ensure the key still exists before deleting
                 del corrected_data[key]
    
    # Ensure the output directory exists
    try:
        os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    except Exception as e:
        print(f"错误：创建输出目录 '{os.path.dirname(output_json_path)}' 时失败: {e}")
        return False

    # Save the corrected data
    try:
        with open(output_json_path, 'w', encoding='utf-8') as f:
            # Use formatting constants from config
            json.dump(corrected_data, f, indent=config.JSON_INDENT, ensure_ascii=config.ENSURE_ASCII)
        print(f"\n校验完成。修正后的文件已保存至: {output_json_path}")
        return True
    except Exception as e:
        print(f"保存修正后的 JSON 文件 '{output_json_path}' 时出错: {e}")
        return False

def main(report_id, provider_name, model_name_slug):
    """
    Main function to validate and fix JSON data for a given report, provider, and model.
    Args:
        report_id (str): The report ID (e.g., "RRI002").
        provider_name (str): The LLM provider name (e.g., "openai").
        model_name_slug (str): The model name slug for directory naming (e.g., "gpt-4o").
    """
    report_id_formatted = report_id[:3] + " " + report_id[3:] # Format for filenames "RRI XXX"

    # Template path is general
    template_path = config.TEMPLATE_JSON_PATH

    # Input and output paths are specific to provider and model
    input_json_path = os.path.join(
        config.get_extracted_json_raw_dir(provider_name, model_name_slug),
        f"{report_id_formatted}_extracted_data.json"
    )
    output_json_path = os.path.join(
        config.get_extracted_json_checked_dir(provider_name, model_name_slug),
        f"{report_id_formatted}_extracted_data.json"
    )

    print(f"\n开始校验报告 {report_id} (提供商: {provider_name}, 模型: {model_name_slug})")
    print(f"输入原始JSON路径: {input_json_path}")
    print(f"输出校验后JSON路径: {output_json_path}")


    if not os.path.exists(input_json_path):
         print(f"错误：需要校验的输入 JSON 文件未找到: {input_json_path}")
         # This error will be caught by the main.py's subprocess handling if raised
         raise FileNotFoundError(f"Input JSON file for validation not found: {input_json_path}")

    success = check_and_fix(template_path, input_json_path, output_json_path)
    if not success:
        # This error will be caught by the main.py's subprocess handling if raised
        raise RuntimeError(f"校验和修正JSON文件失败，报告 {report_id} (提供商: {provider_name}, 模型: {model_name_slug})")

if __name__ == "__main__":
    # This script expects three arguments: report_id, provider_name, model_name_slug
    if len(sys.argv) != 4:
        print(f"用法: python {os.path.basename(__file__)} <report_id> <provider_name> <model_name_slug>")
        print("示例: python data_validation.py RRI002 openai gpt-4o")
        sys.exit(1)

    report_id_arg = sys.argv[1]
    provider_name_arg = sys.argv[2]
    model_name_slug_arg = sys.argv[3] # This is the fs-safe slug

    try:
        main(report_id_arg, provider_name_arg, model_name_slug_arg)
        print(f"\n报告 {report_id_arg} (提供商: {provider_name_arg}, 模型: {model_name_slug_arg}) 的JSON数据校验完成。")
    except Exception as e:
        # Error messages from main() or check_and_fix() should be informative
        print(f"\n处理报告 {report_id_arg} (提供商: {provider_name_arg}, 模型: {model_name_slug_arg}) 的JSON数据校验时发生错误，已中止。")
        sys.exit(1) # Exit with a non-zero code to indicate failure

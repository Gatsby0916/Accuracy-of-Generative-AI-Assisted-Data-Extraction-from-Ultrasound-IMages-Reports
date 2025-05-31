import sys
import subprocess
import os
import re
import argparse
import config # Your config import

# This line should be after all top-level imports and before any function definitions
# It captures the Python interpreter path of the currently running script (main.py)
print(f"main.py is running with Python interpreter: {sys.executable}")
VENV_PYTHON_EXECUTABLE = sys.executable

def select_llm_provider_and_model():
    """
    Interactively prompts the user to select an LLM provider and then a model from that provider.
    Returns:
        tuple: (selected_provider_name, selected_model_display_name, selected_model_id)
               Returns (None, None, None) if selection is aborted or fails.
    """
    print("\n--- 选择LLM提供商 ---")
    providers = list(config.LLM_PROVIDERS.keys())
    for i, provider_name in enumerate(providers):
        print(f"{i+1}. {provider_name.capitalize()}")
    print(f"{len(providers)+1}. 退出选择")

    selected_provider_name = None
    while True:
        try:
            choice = int(input(f"请输入选项 (1-{len(providers)+1}): ")) - 1
            if 0 <= choice < len(providers):
                selected_provider_name = providers[choice]
                break
            elif choice == len(providers):
                print("用户选择退出。")
                return None, None, None
            else:
                print("无效选项，请重新输入。")
        except ValueError:
            print("无效输入，请输入数字。")

    print(f"\n--- 为 {selected_provider_name.capitalize()} 选择模型 ---")
    provider_config = config.LLM_PROVIDERS[selected_provider_name]
    models_dict = provider_config["models"]
    model_display_names = list(models_dict.keys())

    for i, display_name in enumerate(model_display_names):
        print(f"{i+1}. {display_name} ({models_dict[display_name]})")
    
    default_model_id = provider_config.get("default_model")
    default_model_display = ""
    option_offset = 0 # To handle numbering if default model option is available

    if default_model_id:
        option_offset = 1
        # Find display name for the default model ID
        for name, id_val in models_dict.items():
            if id_val == default_model_id:
                default_model_display = name
                break
        if default_model_display: # If a display name was found for the default_model_id
             print(f"{len(model_display_names)+option_offset}. 使用默认模型: {default_model_display} ({default_model_id})")
        else: 
            # This case means default_model_id in config.py doesn't match any model_id in the 'models' dict values.
            # It's better to ensure config.py is consistent.
            print(f"{len(model_display_names)+option_offset}. 使用默认模型 ID: {default_model_id} (配置中的显示名称可能不匹配或default_model值不正确)")


    # Corrected numbering for "返回上一步" and "退出选择"
    print(f"{len(model_display_names)+option_offset+1}. 返回上一步")
    print(f"{len(model_display_names)+option_offset+2}. 退出选择")

    selected_model_id = None
    selected_model_display_name = None
    while True:
        try:
            # Max option number for the current menu
            current_max_option = len(model_display_names) + option_offset + 2 
            prompt_text = f"请输入选项 (1-{current_max_option}): "
            choice_input = int(input(prompt_text)) -1 # User input is 1-based, convert to 0-based

            if 0 <= choice_input < len(model_display_names): # Choice is one of the listed models
                selected_model_display_name = model_display_names[choice_input]
                selected_model_id = models_dict[selected_model_display_name]
                break
            # Choice is the default model (if it exists and option_offset is 1)
            elif default_model_id and option_offset == 1 and choice_input == len(model_display_names): 
                selected_model_id = default_model_id
                selected_model_display_name = default_model_display or selected_model_id # Fallback if display name wasn't found
                print(f"已选择默认模型: {selected_model_display_name} (ID: {selected_model_id})")
                break
            elif choice_input == len(model_display_names) + option_offset: # Choice is "返回上一步"
                return select_llm_provider_and_model() # Recursive call to re-select provider
            elif choice_input == len(model_display_names) + option_offset + 1: # Choice is "退出选择"
                print("用户选择退出。")
                return None, None, None
            else:
                print("无效选项，请重新输入。")
        except ValueError:
            print("无效输入，请输入数字。")
    
    print(f"已选择提供商: {selected_provider_name.capitalize()}, 模型: {selected_model_display_name} (ID: {selected_model_id})")
    return selected_provider_name, selected_model_display_name, selected_model_id


def run_script(script_name, report_id, script_specific_arg1=None, script_specific_arg2=None):
    """
    Helper function to run a script using the venv's Python interpreter,
    passing additional arguments if provided.
    """
    script_path = os.path.join(config.PROJECT_ROOT, 'src', script_name)
    
    # Use the Python interpreter from the virtual environment
    command = [VENV_PYTHON_EXECUTABLE, script_path, report_id] 

    if script_specific_arg1 is not None:
        command.append(str(script_specific_arg1))
    if script_specific_arg2 is not None:
        command.append(str(script_specific_arg2))

    print(f"\n{'='*10} Running: {' '.join(command)} {'='*10}")
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8' 
    try:
        process = subprocess.run(
            command,
            check=True,      
            capture_output=True, 
            text=True,        
            encoding='utf-8', 
            errors='replace', 
            cwd=config.PROJECT_ROOT, 
            env=env
        )
        print(f"--- Output from {script_name} ---")
        print(process.stdout)
        if process.stderr:
             print(f"--- Warnings/Errors from {script_name} ---", file=sys.stderr)
             print(process.stderr, file=sys.stderr)
        return True
    except FileNotFoundError:
         # This error could mean VENV_PYTHON_EXECUTABLE is incorrect or script_path is wrong
         print(f"错误：脚本或Python解释器未找到。命令: {' '.join(command)}", file=sys.stderr)
         return False
    except subprocess.CalledProcessError as e:
        print(f"!! 错误: {script_name} 执行失败 (返回码: {e.returncode})", file=sys.stderr)
        print(f"--- Error Output from {script_name} ---", file=sys.stderr)
        print(e.stdout if e.stdout else "[No stdout]", file=sys.stderr)
        print(e.stderr if e.stderr else "[No stderr]", file=sys.stderr)
        return False
    except Exception as e:
         print(f"!! 运行 {script_name} 时发生意外错误: {e}", file=sys.stderr)
         return False

def process_report(report_id, provider_name, model_id, model_name_slug):
    """
    Processes a single report through the entire pipeline using the specified LLM.
    """
    print(f"\n{'#'*20} 开始处理报告: {report_id} 使用 {provider_name.capitalize()}/{model_id} {'#'*20}")

    script_api = "api_interaction.py"
    script_validate = "data_validation.py"
    script_to_excel = "json_to_excel.py"
    script_evaluate = "evaluation.py"

    try:
        os.makedirs(config.get_extracted_json_raw_dir(provider_name, model_name_slug), exist_ok=True)
        os.makedirs(config.get_extracted_json_checked_dir(provider_name, model_name_slug), exist_ok=True)
        os.makedirs(config.get_extracted_excel_dir(provider_name, model_name_slug), exist_ok=True)
        os.makedirs(config.get_accuracy_reports_dir(provider_name, model_name_slug), exist_ok=True)
    except Exception as e:
        print(f"错误：为 {provider_name}/{model_name_slug} 创建输出目录时出错: {e}", file=sys.stderr)
        return False

    print(f"\n[步骤 1/4] 正在调用 {script_api} 提取数据...")
    if not run_script(script_api, report_id, provider_name, model_id): return False

    print(f"\n[步骤 2/4] 正在调用 {script_validate} 校验和修正提取的数据...")
    if not run_script(script_validate, report_id, provider_name, model_name_slug): return False

    print(f"\n[步骤 3/4] 正在调用 {script_to_excel} 转换 JSON 为 Excel...")
    if not run_script(script_to_excel, report_id, provider_name, model_name_slug): return False

    print(f"\n[步骤 4/4] 正在调用 {script_evaluate} 进行对比和评估...")
    if not run_script(script_evaluate, report_id, provider_name, model_name_slug): return False

    print(f"\n报告 {report_id} ({provider_name.capitalize()}/{model_id}) 处理成功完成。")
    return True

def find_report_ids_from_pdfs(pdf_directory):
    """
    Scans the specified directory for PDF files and extracts report IDs.
    """
    report_ids = set()
    pattern = re.compile(r'^RRI\s?(\d{3})\.pdf$', re.IGNORECASE)
    print(f"\n正在扫描 PDF 目录以查找报告 ID: {pdf_directory}")

    if not os.path.isdir(pdf_directory):
        print(f"警告：指定的 PDF 目录不存在: {pdf_directory}")
        return []
    try:
        for filename in os.listdir(pdf_directory):
            match = pattern.match(filename)
            if match:
                report_num = match.group(1)
                report_id = f"RRI{report_num}" 
                report_ids.add(report_id)
    except Exception as e:
        print(f"扫描 PDF 目录时出错: {e}")
        return [] 

    sorted_ids = sorted(list(report_ids))
    if sorted_ids:
        print(f"发现 {len(sorted_ids)} 个报告 ID: {', '.join(sorted_ids)}")
    else:
        print(f"在目录 '{pdf_directory}' 中未发现符合 'RRIXXX.pdf' 格式的 PDF 文件。")
    return sorted_ids


def run_main_workflow(report_ids_to_process, provider_name, model_id, model_name_slug):
    """
    Runs the main processing workflow for a list of report IDs using the specified LLM.
    """
    total_reports = len(report_ids_to_process)
    success_count = 0
    failure_count = 0

    if not report_ids_to_process:
        print("没有需要处理的报告 ID。")
        return

    print(f"\n准备使用 {provider_name.capitalize()}/{model_id} 处理 {total_reports} 个报告: {', '.join(report_ids_to_process)}")

    for i, report_id in enumerate(report_ids_to_process):
        print(f"\n--- 开始处理第 {i+1}/{total_reports} 个报告: {report_id} ---")
        success = process_report(report_id, provider_name, model_id, model_name_slug)
        if success:
            success_count += 1
        else:
            failure_count += 1
            print(f"!!! 报告 {report_id} ({provider_name.capitalize()}/{model_id}) 处理失败或中止 !!!", file=sys.stderr)

    print("\n" + "="*50)
    print(f"所有选定报告处理流程结束 (使用 {provider_name.capitalize()}/{model_id}).")
    print(f"总计: {total_reports} 个报告")
    print(f"成功: {success_count} 个")
    print(f"失败: {failure_count} 个")
    print("="*50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="处理MRI报告，允许选择LLM提供商和模型，自动从PDF发现ID或处理指定ID。"
    )
    parser.add_argument(
        '-i', '--report-id',
        nargs='+', 
        help="指定要处理的一个或多个报告 ID (例如: RRI002 RRI004)。如果提供此项，将覆盖自动发现。"
    )
    parser.add_argument(
        '--pdf-dir',
        default=config.DEFAULT_PDF_SCAN_DIR, 
        help=f"指定包含 PDF 报告的目录路径，用于自动发现报告 ID (默认: {config.DEFAULT_PDF_SCAN_DIR})"
    )
    parser.add_argument(
        '--provider',
        choices=list(config.LLM_PROVIDERS.keys()), 
        help="LLM提供商 (例如: openai, gemini, claude)。如果提供，将跳过交互式选择。"
    )
    parser.add_argument(
        '--model',
        help="LLM模型ID或显示名称 (例如: gpt-4o, gemini-1.5-pro)。需要与 --provider 一起使用。如果提供，将跳过交互式选择。"
    )
    args = parser.parse_args()

    selected_provider_name = args.provider
    cli_model_input = args.model 
    
    selected_model_id = None

    if selected_provider_name and cli_model_input:
        print(f"通过命令行参数选择LLM: 提供商='{selected_provider_name}', 模型输入='{cli_model_input}'")
        if selected_provider_name not in config.LLM_PROVIDERS:
            print(f"错误：无效的提供商 '{selected_provider_name}'. 可选项: {list(config.LLM_PROVIDERS.keys())}")
            sys.exit(1)
        
        provider_conf = config.LLM_PROVIDERS[selected_provider_name]
        if cli_model_input in provider_conf["models"]: # Check if it's a display name
            selected_model_id = provider_conf["models"][cli_model_input]
            print(f"模型 '{cli_model_input}' 被识别为显示名称，对应模型ID: '{selected_model_id}'.")
        elif cli_model_input in provider_conf["models"].values(): # Check if it's an actual model ID
            selected_model_id = cli_model_input
            print(f"模型 '{cli_model_input}' 被识别为有效的模型ID.")
        else:
            print(f"错误：提供商 '{selected_provider_name}' 的模型 '{cli_model_input}' 无效。")
            print(f"可用模型 (显示名称: ID): {provider_conf['models']}")
            sys.exit(1)
    else:
        # Interactive selection if provider and model are not fully specified via CLI
        _provider, _display_name, _model_id = select_llm_provider_and_model()
        if not _provider: # User exited selection
            print("未选择LLM，程序退出。")
            sys.exit(0)
        selected_provider_name = _provider
        selected_model_id = _model_id

    if not selected_model_id: 
        print("错误：未能确定有效的模型ID。程序退出。")
        sys.exit(1)
    # Create a filesystem-safe slug from the model_id for directory naming
    model_name_slug = selected_model_id.replace('/', '_').replace(':', '_') 

    if args.report_id:
        reports_to_run = args.report_id
        print(f"\n用户指定了处理报告 ID: {', '.join(reports_to_run)}")
    else:
        reports_to_run = find_report_ids_from_pdfs(args.pdf_dir)
        if not reports_to_run:
             print("\n未能自动发现任何报告 ID。如果期望处理报告，请检查 '--pdf-dir' 或使用 '-i' 指定ID。程序退出。")
             sys.exit(0) 

    # Ensure the general processed_images directory exists (it's not provider/model specific)
    try:
        os.makedirs(config.PROCESSED_IMAGES_DIR, exist_ok=True)
    except Exception as e:
        print(f"警告：创建通用图像目录 '{config.PROCESSED_IMAGES_DIR}' 时出错: {e}", file=sys.stderr)
        # This might not be fatal if images are already processed, but good to note.

    # Run the main workflow with the selected LLM provider and model details
    run_main_workflow(reports_to_run, selected_provider_name, selected_model_id, model_name_slug)
    print("\n处理完成。")

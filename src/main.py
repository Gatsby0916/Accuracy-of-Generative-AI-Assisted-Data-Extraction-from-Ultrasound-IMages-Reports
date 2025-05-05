import sys
import subprocess
import os
import re
import argparse
import config # <--- 导入 config 模块

# project_root and src_dir are implicitly handled via config and cwd

def run_script(script_name, report_id):
    """Helper function to run a script, assuming it's in the src directory."""
    # Construct script path relative to project root
    script_path = os.path.join(config.PROJECT_ROOT, 'src', script_name) # <--- 使用 config.PROJECT_ROOT
    command = ["python", script_path, report_id]
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
            cwd=config.PROJECT_ROOT, # <--- 使用 config.PROJECT_ROOT as cwd
            env=env
        )
        print(f"--- Output from {script_name} ---")
        print(process.stdout)
        print(f"--- End Output from {script_name} ---")
        if process.stderr:
             print(f"--- Warnings/Errors from {script_name} ---", file=sys.stderr)
             print(process.stderr, file=sys.stderr)
             print(f"--- End Warnings/Errors from {script_name} ---", file=sys.stderr)
        return True
    except FileNotFoundError:
         print(f"错误：脚本未找到: {script_path}", file=sys.stderr)
         return False
    except subprocess.CalledProcessError as e:
        print(f"!! 错误: {script_name} 执行失败 (返回码: {e.returncode})", file=sys.stderr)
        print(f"--- Error Output from {script_name} ---", file=sys.stderr)
        print(e.stdout if e.stdout else "[No stdout]", file=sys.stderr)
        print(e.stderr if e.stderr else "[No stderr]", file=sys.stderr)
        print(f"--- End Error Output from {script_name} ---", file=sys.stderr)
        return False
    except Exception as e:
         print(f"!! 运行 {script_name} 时发生意外错误: {e}", file=sys.stderr)
         return False

# --- process_report function remains the same ---
def process_report(report_id):
    """处理单个报告的完整流程。"""
    print(f"\n{'#'*20} 开始处理报告: {report_id} {'#'*20}")
    # Define script names (ensure these match actual filenames in src/)
    script_api = "api_interaction.py"
    script_validate = "data_validation.py"
    script_to_excel = "json_to_excel.py"
    script_evaluate = "evaluation.py"

    print(f"\n[步骤 1/4] 正在调用 {script_api} 提取数据...")
    if not run_script(script_api, report_id): return False

    print(f"\n[步骤 2/4] 正在调用 {script_validate} 校验和修正提取的数据...")
    if not run_script(script_validate, report_id): return False

    print(f"\n[步骤 3/4] 正在调用 {script_to_excel} 转换 JSON 为 Excel...")
    if not run_script(script_to_excel, report_id): return False

    print(f"\n[步骤 4/4] 正在调用 {script_evaluate} 进行对比和评估...")
    if not run_script(script_evaluate, report_id): return False

    print(f"\n报告 {report_id} 处理成功完成。")
    return True

# --- find_report_ids_from_pdfs function remains the same ---
def find_report_ids_from_pdfs(pdf_directory):
    """扫描指定目录，从 PDF 文件名中提取报告 ID。"""
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
    print(f"发现 {len(sorted_ids)} 个报告 ID: {', '.join(sorted_ids)}")
    return sorted_ids

# --- run_main_workflow function remains the same ---
def run_main_workflow(report_ids_to_process):
    """运行处理指定报告 ID 列表的主工作流。"""
    total_reports = len(report_ids_to_process)
    success_count = 0
    failure_count = 0
    if not report_ids_to_process:
        print("没有需要处理的报告 ID。")
        return
    print(f"\n准备处理 {total_reports} 个报告: {', '.join(report_ids_to_process)}")
    for i, report_id in enumerate(report_ids_to_process):
        print(f"\n--- 开始处理第 {i+1}/{total_reports} 个报告: {report_id} ---")
        success = process_report(report_id)
        if success:
            success_count += 1
            print(f"--- 报告 {report_id} 处理成功 ---")
        else:
            failure_count += 1
            print(f"!!! 报告 {report_id} 处理失败或中止 !!!", file=sys.stderr)
            # break # Optional: Stop on first failure
    print("\n" + "="*50)
    print("所有选定报告处理流程结束。")
    print(f"总计: {total_reports} 个报告")
    print(f"成功: {success_count} 个")
    print(f"失败: {failure_count} 个")
    print("="*50)


if __name__ == "__main__":
    # Setup argument parser
    parser = argparse.ArgumentParser(description="处理 MRI 报告，自动从 PDF 发现 ID 或处理指定 ID。")
    parser.add_argument(
        '-i', '--report-id',
        nargs='+',
        help="指定要处理的一个或多个报告 ID (例如: RRI002 RRI004)。如果提供此项，将覆盖自动发现。"
    )
    parser.add_argument(
        '--pdf-dir',
        default=config.DEFAULT_PDF_SCAN_DIR, # <--- 使用 config 设置默认值
        help=f"指定包含 PDF 报告的目录路径，用于自动发现报告 ID (默认: {config.DEFAULT_PDF_SCAN_DIR})"
    )
    args = parser.parse_args()

    # Determine which reports to process
    if args.report_id:
        reports_to_run = args.report_id
        print(f"\n用户指定了处理报告 ID: {', '.join(reports_to_run)}")
    else:
        # Use the directory specified by --pdf-dir argument (which defaults to config value)
        reports_to_run = find_report_ids_from_pdfs(args.pdf_dir)
        if not reports_to_run:
             print("\n未能自动发现任何报告 ID，程序退出。")
             sys.exit(0)

    # Run the main workflow
    run_main_workflow(reports_to_run)


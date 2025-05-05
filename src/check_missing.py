import os
import re
import sys
import pandas as pd # <--- 导入 pandas 用于读取 Excel
try:
    import config # 尝试导入项目配置文件
except ImportError:
    print("错误：无法导入 config.py。请确保此脚本与 config.py 在同一 src 目录下，或者 config.py 在 Python 路径中。")
    sys.exit(1)

def get_expected_ids_from_pdfs(pdf_directory):
    """
    从指定的 PDF 目录扫描文件名，提取预期的报告 ID (格式 RRIXXX)。
    """
    expected_ids = set()
    pattern = re.compile(r'^RRI\s?(\d{3})\.pdf$', re.IGNORECASE)

    print(f"正在扫描 PDF 目录以获取预期报告列表: {pdf_directory}")
    if not os.path.isdir(pdf_directory):
        print(f"错误：指定的 PDF 目录不存在: {pdf_directory}")
        return None

    try:
        count = 0
        for filename in os.listdir(pdf_directory):
            match = pattern.match(filename)
            if match:
                report_num = match.group(1)
                report_id = f"RRI{report_num}"
                expected_ids.add(report_id)
                count += 1
        print(f"从 PDF 文件名中发现 {count} 个预期的报告 ID。")
        return expected_ids
    except Exception as e:
        print(f"扫描 PDF 目录时出错: {e}")
        return None

def get_successful_ids_from_accuracy_reports(accuracy_dir):
    """
    从指定的准确率报告目录扫描文件名，提取成功处理的报告 ID (格式 RRIXXX)。
    """
    successful_ids = set()
    pattern = re.compile(r'^(RRI\s\d{3})_accuracy\.txt$', re.IGNORECASE)

    print(f"正在扫描准确率报告目录: {accuracy_dir}")
    if not os.path.isdir(accuracy_dir):
        print(f"错误：指定的准确率报告目录不存在: {accuracy_dir}")
        return None

    try:
        count = 0
        for filename in os.listdir(accuracy_dir):
            match = pattern.match(filename)
            if match:
                report_id_with_space = match.group(1)
                report_id = report_id_with_space.replace(' ', '')
                successful_ids.add(report_id)
                count += 1
        print(f"从准确率报告文件名中发现 {count} 个成功处理的报告 ID。")
        return successful_ids
    except Exception as e:
        print(f"扫描准确率报告目录时出错: {e}")
        return None

# --- 新增函数：从 Ground Truth Excel 读取 ID ---
def get_ids_from_ground_truth(excel_path, id_column_names):
    """
    从 Ground Truth Excel 文件读取报告 ID 列，并返回标准格式 (RRIXXX) 的 ID 集合。
    """
    print(f"正在读取 Ground Truth Excel 文件以获取 ID 列表: {excel_path}")
    if not os.path.exists(excel_path):
        print(f"错误：Ground Truth Excel 文件未找到: {excel_path}")
        return None

    try:
        df_true = pd.read_excel(excel_path, dtype=str) # 读取所有列为字符串
        
        # 查找报告 ID 列
        id_col_name = None
        for col_name in id_column_names:
            if col_name in df_true.columns:
                id_col_name = col_name
                break
        
        if not id_col_name:
            print(f"错误：在 Excel 文件中找不到指定的报告 ID 列 (检查了: {id_column_names})。")
            return None

        print(f"找到报告 ID 列: '{id_col_name}'")
        
        # 提取 ID，转换为字符串，移除空格，去重，移除空值/NA
        ground_truth_ids = set(
            df_true[id_col_name]
            .dropna() # 移除 NA 值
            .astype(str) # 确保是字符串
            .str.replace(r'\s+', '', regex=True) # 移除所有空格
            .unique() # 获取唯一值
        )
        # 移除可能的空字符串 ID
        ground_truth_ids.discard('') 
        
        print(f"从 Ground Truth Excel 中发现 {len(ground_truth_ids)} 个有效的报告 ID。")
        return ground_truth_ids

    except Exception as e:
        print(f"读取或处理 Ground Truth Excel 文件时出错: {e}")
        return None
# --- 新增函数结束 ---


def find_missing_reports():
    """
    比较预期报告、成功报告和 Ground Truth 报告，找出差异。
    """
    # 从 config 文件获取路径
    pdf_dir = config.DEFAULT_PDF_SCAN_DIR
    accuracy_dir = config.ACCURACY_REPORTS_DIR
    ground_truth_excel = config.CLEANED_GROUND_TRUTH_XLSX # <--- 从 config 获取 GT 路径
    id_columns = config.REPORT_ID_COLUMN_NAMES # <--- 从 config 获取 ID 列名

    expected_ids = get_expected_ids_from_pdfs(pdf_dir)
    successful_ids = get_successful_ids_from_accuracy_reports(accuracy_dir)
    ground_truth_ids = get_ids_from_ground_truth(ground_truth_excel, id_columns) # <--- 调用新函数

    # 检查是否有错误发生
    if expected_ids is None or successful_ids is None or ground_truth_ids is None:
        print("\n由于读取目录或文件出错，无法完成所有比较。")
        # 即使 GT 读取失败，仍然可以尝试比较 PDF 和 Accuracy
        if expected_ids is not None and successful_ids is not None:
             missing_from_accuracy = expected_ids - successful_ids
             print("\n--- 仅对比 PDF vs Accuracy Reports ---")
             print(f"预期处理的报告总数 (来自 PDF): {len(expected_ids)}")
             print(f"实际成功生成准确率报告的数量: {len(successful_ids)}")
             if not missing_from_accuracy:
                 print("所有根据 PDF 文件找到的报告都生成了准确率报告。")
             else:
                 print(f"以下 {len(missing_from_accuracy)} 个报告可能处理失败 (存在于 PDF 但无 accuracy.txt):")
                 for report_id in sorted(list(missing_from_accuracy)):
                     print(f"  - {report_id}")
        return # 提前退出

    # --- 执行所有比较 ---

    # 检查1: PDF 中有，但 Ground Truth 中没有的 ID
    missing_from_gt = expected_ids - ground_truth_ids

    # 检查2: PDF 中有，但 Accuracy Report 中没有的 ID (处理失败/跳过)
    missing_from_accuracy = expected_ids - successful_ids

    # (可选) 检查3: Ground Truth 中有，但 PDF 中没有的 ID
    missing_from_pdf = ground_truth_ids - expected_ids

    # (可选) 检查4: Ground Truth 中有，但 Accuracy Report 中没有的 ID
    gt_not_successful = ground_truth_ids - successful_ids


    print("\n--- 报告处理状态交叉检查结果 ---")
    print(f"预期报告总数 (来自 PDF 文件): {len(expected_ids)}")
    print(f"Ground Truth Excel 中的报告总数: {len(ground_truth_ids)}")
    print(f"成功生成 Accuracy Report 的数量: {len(successful_ids)}")

    # 报告检查结果
    if not missing_from_gt:
        print("\n[检查 1/2] 通过: 所有在 PDF 目录中找到的报告 ID 都能在 Ground Truth Excel 中找到对应记录。")
    else:
        print(f"\n[检查 1/2] **注意**: 以下 {len(missing_from_gt)} 个报告 ID 存在于 PDF 文件名中，但在 Ground Truth Excel 的 ID 列中未找到:")
        for report_id in sorted(list(missing_from_gt)):
            print(f"  - {report_id}")

    if not missing_from_accuracy:
        print("\n[检查 2/2] 通过: 所有在 PDF 目录中找到的报告 ID 都成功生成了对应的 Accuracy Report 文件。")
    else:
        print(f"\n[检查 2/2] **注意**: 以下 {len(missing_from_accuracy)} 个报告 ID 存在于 PDF 文件名中，但未能成功生成 Accuracy Report 文件 (可能处理失败或被跳过):")
        for report_id in sorted(list(missing_from_accuracy)):
            print(f"  - {report_id}")

    # (可选) 报告其他检查结果
    if missing_from_pdf:
        print(f"\n[附加信息] 以下 {len(missing_from_pdf)} 个报告 ID 存在于 Ground Truth Excel 中，但在扫描的 PDF 目录中未找到对应的 PDF 文件:")
        for report_id in sorted(list(missing_from_pdf)):
            print(f"  - {report_id}")

    # (可选) 打印成功列表
    # print("\n成功处理并生成 Accuracy Report 的报告列表:")
    # for report_id in sorted(list(successful_ids)):
    #     print(f"  - {report_id}")


if __name__ == "__main__":
    find_missing_reports()

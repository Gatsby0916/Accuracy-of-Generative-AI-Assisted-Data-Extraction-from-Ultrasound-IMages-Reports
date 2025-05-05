import os

# --- Project Root ---
# Dynamically calculate the project root directory (assuming config.py is in src/)
# 项目根目录 (src 文件夹的上级目录)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Base Directories ---
# 基础数据和结果目录路径
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")

# --- Data Sub-directories ---
# 数据子目录路径
GROUND_TRUTH_DIR = os.path.join(DATA_DIR, "ground_truth")
RAW_REPORTS_DIR = os.path.join(DATA_DIR, "raw_reports")
TEMPLATES_DIR = os.path.join(DATA_DIR, "templates")

# Default raw reports subdirectory to scan (可以根据需要修改)
DEFAULT_PDF_DIR_NAME = "BENSON DEID RRI REPORTS"
DEFAULT_PDF_SCAN_DIR = os.path.join(RAW_REPORTS_DIR, DEFAULT_PDF_DIR_NAME)

# --- Results Sub-directories ---
# 结果子目录路径
ACCURACY_REPORTS_DIR = os.path.join(RESULTS_DIR, "accuracy_reports")
EXTRACTED_DATA_DIR = os.path.join(RESULTS_DIR, "extracted_data")
OVERALL_ANALYSIS_DIR = os.path.join(RESULTS_DIR, "overall_analysis")
PROCESSED_IMAGES_DIR = os.path.join(RESULTS_DIR, "processed_images")

# Extracted Data Sub-directories
EXTRACTED_EXCEL_DIR = os.path.join(EXTRACTED_DATA_DIR, "excel")
EXTRACTED_JSON_CHECKED_DIR = os.path.join(EXTRACTED_DATA_DIR, "json_checked")
EXTRACTED_JSON_RAW_DIR = os.path.join(EXTRACTED_DATA_DIR, "json_raw")

# --- Specific File Paths ---
# 特定文件的完整路径
ORIGINAL_GROUND_TRUTH_XLSX = os.path.join(GROUND_TRUTH_DIR, "IMAGENDO_Project_Master___Truncated.xlsx")
# 指定要从原始 Ground Truth Excel 文件中读取的工作表名称
GROUND_TRUTH_SHEET_NAME = "MRI_Report Data Entry" # <--- 新增配置项
CLEANED_GROUND_TRUTH_XLSX = os.path.join(GROUND_TRUTH_DIR, "Stage 1A MRI Data Entry_cleaned.xlsx")
TEMPLATE_JSON_PATH = os.path.join(TEMPLATES_DIR, "json_template.json")
SUMMARY_REPORT_TXT = os.path.join(OVERALL_ANALYSIS_DIR, "accuracy_summary.txt")
ACCURACY_PLOT_PNG = os.path.join(OVERALL_ANALYSIS_DIR, "accuracy_plot.png")

# --- API Configuration ---
# API 相关配置 (密钥在 .env 文件中)
OPENAI_MODEL_NAME = "gpt-4-turbo"
MAX_TOKENS = 4000
# Number of pages to process per report (可以根据需要修改)
PAGES_PER_REPORT = 4 

# --- Script Parameters ---
# 脚本参数
# data_validation.py - difflib cutoff for finding similar keys
SIMILARITY_CUTOFF = 0.8
# data_conversion.py - PDF processing range (如果需要固定范围)
# PDF_PROCESSING_START_INDEX = 2
# PDF_PROCESSING_END_INDEX = 30

# --- Evaluation Configuration ---
# evaluation.py - Column name mappings for standardization
COLUMN_NAME_MAPPING = {
    'Right uteroscaral nodule size (mm)': 'Right uterosacral nodule size (mm)',
    'Endometrioal lesions Identified Comment': 'Endometrial lesions Identified Comment'
    # Add more mappings here if needed
}
# evaluation.py - Default report ID column names to check
REPORT_ID_COLUMN_NAMES = ["Report ID", "Report"]

# --- Output Formatting ---
# 输出格式配置
JSON_INDENT = 2
ENSURE_ASCII = False

# --- Logging Configuration (Optional Placeholder) ---
# 日志配置 (可选占位符)
LOG_FILE_PATH = os.path.join(PROJECT_ROOT, "project_log.log")
LOG_LEVEL = "INFO" # e.g., DEBUG, INFO, WARNING, ERROR


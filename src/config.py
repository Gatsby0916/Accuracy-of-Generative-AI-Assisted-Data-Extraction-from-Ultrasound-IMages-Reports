import os

# --- Project Root ---
# Dynamically calculate the project root directory (assuming config.py is in src/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Base Directories ---
# Base data and results directory paths
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")

# --- Data Sub-directories ---
# Data sub-directory paths
GROUND_TRUTH_DIR = os.path.join(DATA_DIR, "ground_truth")
RAW_REPORTS_DIR = os.path.join(DATA_DIR, "raw_reports")
TEMPLATES_DIR = os.path.join(DATA_DIR, "templates")

# Default raw reports subdirectory to scan (can be modified as needed)
DEFAULT_PDF_DIR_NAME = "BENSON DEID RRI REPORTS"
DEFAULT_PDF_SCAN_DIR = os.path.join(RAW_REPORTS_DIR, DEFAULT_PDF_DIR_NAME)


# --- LLM Provider and Model Configuration ---
LLM_PROVIDERS = {
    "openai": {
        "api_key_env": "OPENAI_API_KEY",
        "client_name": "openai", # Identifier for the client type
        "models": {
            # Display name: actual model ID
            "gpt-4-turbo": "gpt-4-turbo",
            "gpt-4o": "gpt-4o",
            "gpt-4o-mini": "gpt-4o-mini", # 假设 "gpt-4o-mini" 是一个有效的、支持图像的API模型ID
        },
        "max_tokens": 4096,
        "default_model": "gpt-4o" # 这个看起来是正确的，因为 "gpt-4o" 同时是显示名和模型ID
    },
    "gemini": {
        "api_key_env": "GEMINI_API_KEY",
        "client_name": "gemini",
        "models": {
            "gemini-1.5-pro": "gemini-1.5-pro-latest",
            "gemini-1.5-flash": "gemini-1.5-flash-latest",
        },
        "max_tokens": 8192,
        "default_model": "gemini-1.5-pro-latest" # <--- 修改这里
    },
    "claude": {
        "api_key_env": "CLAUDE_API_KEY",
        "client_name": "claude",
        "models": {
            "claude-3-opus": "claude-3-opus-20240229", # Opus 仍然是一个强大的模型
            # "claude-3-sonnet-old": "claude-3-sonnet-20240229", # 可以选择保留并重命名显示名称，或移除
            "claude-3-haiku": "claude-3-haiku-20240307",
            "claude-3.5-sonnet": "claude-3-5-sonnet-20240620", # 这是更新的 Sonnet
        },
        "max_tokens": 4096,
        "default_model": "claude-3-5-sonnet-20240620" # 将默认模型更新为最新的 Sonnet
    }
}


# --- Results Sub-directories (Dynamic Path Functions) ---
def get_provider_model_results_dir(provider_name, model_name_slug):
    """Base results directory for a specific provider and model."""
    # Use a "slugified" version of model_name for directory to avoid special characters
    return os.path.join(RESULTS_DIR, provider_name, model_name_slug.replace('/', '_'))

def get_accuracy_reports_dir(provider_name, model_name_slug):
    """Directory for accuracy reports of a specific provider and model."""
    return os.path.join(get_provider_model_results_dir(provider_name, model_name_slug), "accuracy_reports")

def get_extracted_data_dir(provider_name, model_name_slug):
    """Base directory for extracted data (JSON, Excel) of a specific provider and model."""
    return os.path.join(get_provider_model_results_dir(provider_name, model_name_slug), "extracted_data")

def get_overall_analysis_dir(provider_name, model_name_slug):
    """Directory for overall analysis (summary, plots) of a specific provider and model."""
    return os.path.join(get_provider_model_results_dir(provider_name, model_name_slug), "overall_analysis")

# Processed images are general, not provider/model specific
PROCESSED_IMAGES_DIR = os.path.join(RESULTS_DIR, "processed_images") # Kept as is

# --- Extracted Data Sub-directories (within provider/model specific extracted_data_dir) ---
def get_extracted_excel_dir(provider_name, model_name_slug):
    """Directory for extracted Excel files."""
    return os.path.join(get_extracted_data_dir(provider_name, model_name_slug), "excel")

def get_extracted_json_checked_dir(provider_name, model_name_slug):
    """Directory for validated/checked JSON files."""
    return os.path.join(get_extracted_data_dir(provider_name, model_name_slug), "json_checked")

def get_extracted_json_raw_dir(provider_name, model_name_slug):
    """Directory for raw JSON files from LLM."""
    return os.path.join(get_extracted_data_dir(provider_name, model_name_slug), "json_raw")


# --- Specific File Paths (Templates and Ground Truth are general) ---
# Full paths to specific files
ORIGINAL_GROUND_TRUTH_XLSX = os.path.join(GROUND_TRUTH_DIR, "IMAGENDO_Project_Master___Truncated.xlsx")
# Sheet name to read from the original Ground Truth Excel file
GROUND_TRUTH_SHEET_NAME = "MRI_Report Data Entry"
CLEANED_GROUND_TRUTH_XLSX = os.path.join(GROUND_TRUTH_DIR, "filtered_output.xlsx")
TEMPLATE_JSON_PATH = os.path.join(TEMPLATES_DIR, "json_template_edition.json")


# --- Paths for provider/model specific summary files ---
def get_summary_report_txt_path(provider_name, model_name_slug):
    """Path to the accuracy summary text file for a specific provider and model."""
    return os.path.join(get_overall_analysis_dir(provider_name, model_name_slug), "accuracy_summary.txt")

def get_accuracy_plot_png_path(provider_name, model_name_slug):
    """Path to the accuracy plot PNG file for a specific provider and model."""
    return os.path.join(get_overall_analysis_dir(provider_name, model_name_slug), "accuracy_plot.png")


# --- API Configuration (General script settings) ---
# Number of pages to process per report (can be modified as needed)
PAGES_PER_REPORT = 4

# --- Script Parameters ---
# data_validation.py - difflib cutoff for finding similar keys
SIMILARITY_CUTOFF = 0.8
# data_conversion.py - PDF processing range (if fixed range is needed)
# PDF_PROCESSING_START_INDEX = 2
# PDF_PROCESSING_END_INDEX = 30

# --- Evaluation Configuration ---
# evaluation.py - Column name mappings for standardization
COLUMN_NAME_MAPPING = {
    'Right uteroscaral nodule size (mm)': 'Right uterosacral nodule size (mm)',
    'Endometrioal lesions Identified Comment': 'Endometrial lesions Identified Comment'
    # Add more mappings here if needed
}
# evaluation.py - Default report ID column names to check in Excel files
REPORT_ID_COLUMN_NAMES = ["Report ID", "Report"]

# --- Output Formatting ---
# JSON output formatting
JSON_INDENT = 2
ENSURE_ASCII = False # Set to False to allow Unicode characters in JSON output

# --- Logging Configuration (Optional Placeholder) ---
# Logging settings
LOG_FILE_PATH = os.path.join(PROJECT_ROOT, "project_log.log")
LOG_LEVEL = "INFO" # e.g., DEBUG, INFO, WARNING, ERROR
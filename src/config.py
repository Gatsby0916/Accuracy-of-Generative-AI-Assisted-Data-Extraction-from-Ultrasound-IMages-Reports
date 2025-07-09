# src/config.py

import os

# --- Project Root ---
# Dynamically calculate the project root directory (assuming config.py is in src/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Base Directories ---
# Base data and results directory paths
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports") # For final analysis charts/reports

# --- Data Sub-directories ---
GROUND_TRUTH_DIR = os.path.join(DATA_DIR, "ground_truth")
RAW_REPORTS_DIR = os.path.join(DATA_DIR, "raw_reports")
TEMPLATES_DIR = os.path.join(DATA_DIR, "templates")

# ----------------------------------------------------------------------
# --- Master Dataset Configuration ---
# Central dictionary to manage all datasets and their specific properties.
# This is the single source of truth for dataset-specific paths and types.
# All other scripts will get their paths and data types from here.
# ----------------------------------------------------------------------
DATASET_CONFIGS = {
    "benson": {
        "display_name": "Benson Dataset",
        "data_type": "image",  # Used by the pipeline to select processing logic
        "pdf_dir": os.path.join(RAW_REPORTS_DIR, "BENSON DEID RRI REPORTS"),
        "ground_truth_xlsx": os.path.join(GROUND_TRUTH_DIR, "filtered_output.xlsx"),
        "template_json": os.path.join(TEMPLATES_DIR, "json_template_Benson.json")
    },
    "benson_text": {
        "display_name": "Benson Text-Based Reports",
        "data_type": "text",  # text_based
        "pdf_dir": os.path.join(RAW_REPORTS_DIR, "IMAGENDO ID REPORTS"),
        "ground_truth_xlsx": os.path.join(GROUND_TRUTH_DIR, "filtered_output.xlsx"),  
        "template_json": os.path.join(TEMPLATES_DIR, "json_template_Benson.json")
    },
    "sugo": {
        "display_name": "Sugo Dataset",
        "data_type": "text",   # Used by the pipeline to select processing logic
        "pdf_dir": os.path.join(RAW_REPORTS_DIR, "raw_sugo"),
        "ground_truth_xlsx": os.path.join(GROUND_TRUTH_DIR, "sugo_filtered_output.xlsx"),
        "template_json": os.path.join(TEMPLATES_DIR, "json_template_sugo.json")
    }
}


# --- LLM Provider and Model Configuration ---
# (Preserving your exact structure)
LLM_PROVIDERS = {
    "openai": {
        "api_key_env": "OPENAI_API_KEY",
        "client_name": "openai",
        "models": {
            "gpt-4-turbo": "gpt-4-turbo",
            "gpt-4o": "gpt-4o",
            "gpt-4o-mini": "gpt-4o-mini",
        },
        "max_tokens": 4096,
        "default_model": "gpt-4o"
    },
    "gemini": {
        "api_key_env": "GEMINI_API_KEY",
        "client_name": "gemini",
        "models": {
            "gemini-1.5-pro": "gemini-1.5-pro-latest",
            "gemini-1.5-flash": "gemini-1.5-flash-latest",
        },
        "max_tokens": 8192,
        "default_model": "gemini-1.5-pro-latest"
    },
    "claude": {
        "api_key_env": "CLAUDE_API_KEY",
        "client_name": "claude",
        "models": {
            "claude-3-opus": "claude-3-opus-20240229",
            "claude-3-haiku": "claude-3-haiku-20240307",
            "claude-3.5-sonnet": "claude-3-5-sonnet-20240620",
        },
        "max_tokens": 4096,
        "default_model": "claude-3-5-sonnet-20240620"
    }
}

# ----------------------------------------------------------------------
# --- Dynamic Path Generation Functions (Your Structure + Dataset Support) ---
# All functions now accept 'dataset_name' to ensure results are separated.
# ----------------------------------------------------------------------

def get_provider_model_dataset_dir(provider_name, model_name_slug, dataset_name):
    """Base results directory for a specific provider, model, AND dataset."""
    # Creates a path like: /results/openai/gpt-4o/sugo
    model_slug_safe = model_name_slug.replace('/', '_')
    return os.path.join(RESULTS_DIR, provider_name, model_slug_safe, dataset_name)

# In src/config.py
# This is the corrected version with proper spacing

def get_processed_data_dir(dataset_name):
    """
    Directory for pre-processed data (images or text), separated by dataset.
    """
    data_type = DATASET_CONFIGS[dataset_name]["data_type"]
    if data_type == "image":
        base = os.path.join(RESULTS_DIR, "processed_images")
    elif data_type == "text":
        base = os.path.join(RESULTS_DIR, "processed_text")
    else:
        return None
    # Put each dataset into its own subfolder
    return os.path.join(base, dataset_name)

# Add a line break before the next function
def get_extracted_data_dir(provider_name, model_name_slug, dataset_name):
    """Base directory for all extracted data (JSON, Excel)."""
    base_dir = get_provider_model_dataset_dir(provider_name, model_name_slug, dataset_name)
    return os.path.join(base_dir, "extracted_data")

def get_overall_analysis_dir(provider_name, model_name_slug, dataset_name):
    """Directory for overall analysis (summary, plots)."""
    base_dir = get_provider_model_dataset_dir(provider_name, model_name_slug, dataset_name)
    return os.path.join(base_dir, "overall_analysis")

# --- Specific Extracted Data Paths ---

def get_extracted_json_raw_dir(provider_name, model_name_slug, dataset_name):
    """Directory for raw JSON files from LLM."""
    return os.path.join(get_extracted_data_dir(provider_name, model_name_slug, dataset_name), "json_raw")

def get_extracted_json_checked_dir(provider_name, model_name_slug, dataset_name):
    """Directory for validated/checked JSON files."""
    return os.path.join(get_extracted_data_dir(provider_name, model_name_slug, dataset_name), "json_checked")

def get_extracted_excel_dir(provider_name, model_name_slug, dataset_name):
    """Directory for extracted Excel files."""
    return os.path.join(get_extracted_data_dir(provider_name, model_name_slug, dataset_name), "excel")

def get_accuracy_reports_dir(provider_name, model_name_slug, dataset_name):
    """Directory for accuracy reports, with fallback to dataset-root."""
    primary = os.path.join(
        get_overall_analysis_dir(provider_name, model_name_slug, dataset_name),
        "accuracy_reports"
    )
    if os.path.isdir(primary) and os.listdir(primary):
        return primary

    fallback = os.path.join(
        get_provider_model_dataset_dir(provider_name, model_name_slug, dataset_name),
        "accuracy_reports"
    )
    return fallback

# --- Paths for provider/model/dataset specific summary files ---

def get_summary_report_txt_path(provider_name, model_name_slug, dataset_name):
    """Path to the accuracy summary text file for a specific provider, model and dataset."""
    return os.path.join(get_overall_analysis_dir(provider_name, model_name_slug, dataset_name), "accuracy_summary.txt")

def get_accuracy_plot_png_path(provider_name, model_name_slug, dataset_name):
    """Path to the accuracy plot PNG file for a specific provider, model and dataset."""
    return os.path.join(get_overall_analysis_dir(provider_name, model_name_slug, dataset_name), "accuracy_plot.png")

# --- NOTE: The following static paths are now handled by DATASET_CONFIGS ---
# ORIGINAL_GROUND_TRUTH_XLSX -> use DATASET_CONFIGS[dataset_name]["ground_truth_xlsx"]
# CLEANED_GROUND_TRUTH_XLSX -> use DATASET_CONFIGS[dataset_name]["ground_truth_xlsx"]
# TEMPLATE_JSON_PATH -> use DATASET_CONFIGS[dataset_name]["template_json"]
# We do this so the pipeline can dynamically select the correct file for "benson" or "sugo".

# --- API & Script Parameters ---
PAGES_PER_REPORT = 4  # Number of pages to process per image-based report
SIMILARITY_CUTOFF = 0.8 # data_validation.py - difflib cutoff

# --- Evaluation Configuration ---
COLUMN_NAME_MAPPING = {
    'Right uteroscaral nodule size (mm)': 'Right uterosacral nodule size (mm)',
    'Endometrioal lesions Identified Comment': 'Endometrial lesions Identified Comment'
}
REPORT_ID_COLUMN_NAMES = ["Report ID", "Report"]

# --- Output Formatting ---
JSON_INDENT = 2
ENSURE_ASCII = False # Set to False to allow Unicode characters in JSON output

# --- Logging Configuration ---
LOG_FILE_PATH = os.path.join(PROJECT_ROOT, "project_log.log")
LOG_LEVEL = "INFO" # e.g., DEBUG, INFO, WARNING, ERROR
METADATA_PATH = os.path.join(TEMPLATES_DIR, 'fields_metadata_sugo.json')

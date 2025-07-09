# src/main.py

import sys
import subprocess
import os
import re
import time
import argparse
import config # Your new config import
import csv
# This captures the Python interpreter path of the currently running script (main.py)
print(f"main.py is running with Python interpreter: {sys.executable}")
VENV_PYTHON_EXECUTABLE = sys.executable

# --- NEW: Function to select the dataset ---
def select_dataset():
    """
    Interactively prompts the user to select a dataset defined in config.py.
    """
    print("\n--- Select Dataset ---")
    datasets = list(config.DATASET_CONFIGS.keys())
    for i, ds_name in enumerate(datasets):
        display_name = config.DATASET_CONFIGS[ds_name].get('display_name', ds_name)
        print(f"{i+1}. {display_name}")
    print(f"{len(datasets)+1}. Exit")

    while True:
        try:
            choice = int(input(f"Please enter an option (1-{len(datasets)+1}): ")) - 1
            if 0 <= choice < len(datasets):
                selected_dataset = datasets[choice]
                print(f"Selected Dataset: {config.DATASET_CONFIGS[selected_dataset]['display_name']}")
                return selected_dataset
            elif choice == len(datasets):
                return None
            else:
                print("Invalid option, please try again.")
        except ValueError:
            print("Invalid input, please enter a number.")

# --- MODIFIED: Added dataset_name parameter ---
def select_llm_provider_and_model(dataset_name):
    """
    Interactively prompts the user to select an LLM provider and then a model.
    """
    print(f"\n--- Select LLM Provider (for {dataset_name} dataset) ---")
    providers = list(config.LLM_PROVIDERS.keys())
    # ... (rest of the function is the same as your original)
    for i, provider_name in enumerate(providers):
        print(f"{i+1}. {provider_name.capitalize()}")
    print(f"{len(providers)+1}. Exit Selection")

    selected_provider_name = None
    while True:
        try:
            choice = int(input(f"Please enter an option (1-{len(providers)+1}): ")) - 1
            if 0 <= choice < len(providers):
                selected_provider_name = providers[choice]
                break
            elif choice == len(providers):
                print("User chose to exit.")
                return None, None, None
            else:
                print("Invalid option, please enter again.")
        except ValueError:
            print("Invalid input, please enter a number.")

    print(f"\n--- Select a Model for {selected_provider_name.capitalize()} ---")
    provider_config = config.LLM_PROVIDERS[selected_provider_name]
    models_dict = provider_config["models"]
    model_display_names = list(models_dict.keys())

    for i, display_name in enumerate(model_display_names):
        print(f"{i+1}. {display_name} ({models_dict[display_name]})")
    
    default_model_id = provider_config.get("default_model")
    default_model_display = ""
    option_offset = 0

    if default_model_id:
        option_offset = 1
        for name, id_val in models_dict.items():
            if id_val == default_model_id:
                default_model_display = name
                break
        if default_model_display:
            print(f"{len(model_display_names)+option_offset}. Use default model: {default_model_display} ({default_model_id})")
        else: 
            print(f"{len(model_display_names)+option_offset}. Use default model ID: {default_model_id} (Display name in config may not match)")

    print(f"{len(model_display_names)+option_offset+1}. Go Back")
    print(f"{len(model_display_names)+option_offset+2}. Exit Selection")

    selected_model_id = None
    selected_model_display_name = None
    while True:
        try:
            current_max_option = len(model_display_names) + option_offset + 2 
            prompt_text = f"Please enter an option (1-{current_max_option}): "
            choice_input = int(input(prompt_text)) - 1

            if 0 <= choice_input < len(model_display_names):
                selected_model_display_name = model_display_names[choice_input]
                selected_model_id = models_dict[selected_model_display_name]
                break
            elif default_model_id and option_offset == 1 and choice_input == len(model_display_names): 
                selected_model_id = default_model_id
                selected_model_display_name = default_model_display or selected_model_id
                print(f"Selected default model: {selected_model_display_name} (ID: {selected_model_id})")
                break
            elif choice_input == len(model_display_names) + option_offset:
                return select_llm_provider_and_model(dataset_name)
            elif choice_input == len(model_display_names) + option_offset + 1:
                print("User chose to exit.")
                return None, None, None
            else:
                print("Invalid option, please enter again.")
        except ValueError:
            print("Invalid input, please enter a number.")
    
    print(f"Selected Provider: {selected_provider_name.capitalize()}, Model: {selected_model_display_name} (ID: {selected_model_id})")
    return selected_provider_name, selected_model_display_name, selected_model_id


# --- MODIFIED: Now passes dataset_name as the first argument to the script ---
def run_script(script_name, dataset_name, report_id, arg1=None, arg2=None):
    """
    Helper function to run a script, passing dataset_name, report_id, and other optional args.
    """
    script_path = os.path.join(config.PROJECT_ROOT, 'src', script_name)
    command = [VENV_PYTHON_EXECUTABLE, script_path, dataset_name, report_id] 

    if arg1 is not None:
        command.append(str(arg1))
    if arg2 is not None:
        command.append(str(arg2))

    print(f"\n{'='*10} Running: {' '.join(command)} {'='*10}")
    # ... (rest of the function is the same, using the new command)
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
        print(f"Error: Script or Python interpreter not found. Command: {' '.join(command)}", file=sys.stderr)
        return False
    except subprocess.CalledProcessError as e:
        print(f"!! Error: {script_name} execution failed (return code: {e.returncode})", file=sys.stderr)
        print(f"--- Error Output from {script_name} ---", file=sys.stderr)
        print(e.stdout if e.stdout else "[No stdout]", file=sys.stderr)
        print(e.stderr if e.stderr else "[No stderr]", file=sys.stderr)
        return False
    except Exception as e:
        print(f"!! An unexpected error occurred while running {script_name}: {e}", file=sys.stderr)
        return False



def discover_processed_reports(dataset_name):
    """
    Scan the processed data directory and return a list of report IDs that have already
    been pre-processed.

    For image-based datasets, it will match filenames like:
      - '002_page_1.png'
      - 'RRI002_page_1.png'
    For text-based datasets, it will match:
      - '123.txt'

    Returns:
        A sorted list of report ID strings.
    """
    processed_dir = config.get_processed_data_dir(dataset_name)
    if not processed_dir or not os.path.exists(processed_dir):
        print(f"Error: Processed data directory not found for dataset '{dataset_name}': {processed_dir}", file=sys.stderr)
        print("Please run 'python src/preprocess.py --dataset <dataset_name>' first.", file=sys.stderr)
        return []

    report_ids = set()
    data_type = config.DATASET_CONFIGS[dataset_name]["data_type"]

    if data_type == "image":
        # Match '002_page_1.png' or 'RRI002_page_1.png'
        pattern = re.compile(r'^(?:RRI)?(\d+)_page_\d+\.png$', re.IGNORECASE)
    elif data_type == "text":
        # Match '123.txt'
        pattern = re.compile(r'^(\d+)\.txt$')
    else:
        return []

    print(f"\nScanning for processed reports in: {processed_dir}")
    for filename in os.listdir(processed_dir):
        match = pattern.match(filename)
        if match:
            report_ids.add(match.group(1))

    sorted_ids = sorted(report_ids)
    if sorted_ids:
        print(f"Found {len(sorted_ids)} processed report IDs to analyze: {sorted_ids}")
    else:
        print("No processed reports found in the directory.")
    return sorted_ids

def process_report(report_id, dataset_name, provider_name, model_id, model_name_slug, skip_eval=False):
    """
    Processes a single report, assuming pre-processing is already done.
    Records the time taken by the LLM extraction step in llm_timing_log.csv.
    """
    import time
    import csv

    print(f"\n{'#'*20} Starting process for report: {report_id} [Dataset: {dataset_name}] {'#'*20}")

    # 1. Create all necessary output directories for the run
    try:
        os.makedirs(config.get_extracted_json_raw_dir(provider_name, model_name_slug, dataset_name), exist_ok=True)
        os.makedirs(config.get_extracted_json_checked_dir(provider_name, model_name_slug, dataset_name), exist_ok=True)
        os.makedirs(config.get_extracted_excel_dir(provider_name, model_name_slug, dataset_name), exist_ok=True)
        os.makedirs(config.get_accuracy_reports_dir(provider_name, model_name_slug, dataset_name), exist_ok=True)
    except Exception as e:
        print(f"Error: Could not create output directories for the run: {e}", file=sys.stderr)
        return False

    # 2. Step 1/4: Call api_interaction.py and measure time
    print(f"\n[Step 1/4] Calling api_interaction.py to extract data…")
    start = time.time()
    success = run_script("api_interaction.py", dataset_name, report_id, provider_name, model_id)
    elapsed = time.time() - start
    if not success:
        return False

    # 2.1 Log the elapsed time
    log_path = os.path.join(config.PROJECT_ROOT, "llm_timing_log.csv")
    header = not os.path.exists(log_path)
    with open(log_path, "a", newline="", encoding="utf-8") as csvf:
        writer = csv.writer(csvf)
        if header:
            writer.writerow(["report_id", "provider", "model", "elapsed_sec"])
        writer.writerow([report_id, provider_name, model_id, f"{elapsed:.3f}"])

    # 3. Step 2/4: Data validation
    print(f"\n[Step 2/4] Calling data_validation.py to validate and fix…")
    if not run_script("data_validation.py", dataset_name, report_id, provider_name, model_name_slug):
        return False

    # 4. Step 3/4: Convert JSON to Excel
    print(f"\n[Step 3/4] Calling json_to_excel.py to convert JSON to Excel…")
    if not run_script("json_to_excel.py", dataset_name, report_id, provider_name, model_name_slug):
        return False

    # 5. Step 4/4: Evaluation
    if not skip_eval:
        print(f"\n[Step 4/4] Calling evaluation.py for evaluation…")
        if not run_script("evaluation.py", dataset_name, report_id, provider_name, model_name_slug):
            return False

    print(f"\nReport {report_id} [Dataset: {dataset_name}] processed successfully.")
    return True

# --- MODIFIED: Handles different filename patterns based on dataset ---
def find_report_ids_from_pdfs(pdf_directory, dataset_name):
    """
    Scans the specified directory for PDF files and extracts report IDs.
    Handles different naming conventions for different datasets.
    """
    report_ids = set()
    
    # Define regex patterns for each dataset
    patterns = {
        "benson": re.compile(r'^RRI\s?(\d{3,})\.pdf$', re.IGNORECASE),
        "sugo": re.compile(r'^(\d+)\.pdf$', re.IGNORECASE)
    }
    pattern = patterns.get(dataset_name)

    if not pattern:
        print(f"Error: No report ID pattern defined for dataset '{dataset_name}'.", file=sys.stderr)
        return []

    print(f"\nScanning for '{dataset_name}' PDFs in: {pdf_directory}")
    if not os.path.isdir(pdf_directory):
        print(f"Warning: PDF directory does not exist: {pdf_directory}", file=sys.stderr)
        return []
    
    for filename in os.listdir(pdf_directory):
        match = pattern.match(filename)
        if match:
            base_id = match.group(1)
            # Format the ID consistently
            report_id = f"RRI{base_id}" if dataset_name == "benson" else base_id
            report_ids.add(report_id)

    sorted_ids = sorted(list(report_ids))
    if sorted_ids:
        print(f"Found {len(sorted_ids)} report IDs.")
    else:
        print(f"No PDF files matching the pattern for '{dataset_name}' were found in '{pdf_directory}'.")
    return sorted_ids

# --- MODIFIED: Added dataset_name parameter ---
def run_main_workflow(report_ids, dataset_name, provider_name, model_id, model_name_slug, skip_eval=False):
    """
    Runs the main processing workflow for a list of report IDs.
    """
    total_reports = len(report_ids)
    if not total_reports:
        print("No report IDs to process.")
        return

    success_count, failure_count = 0, 0
    print(f"\nPreparing to process {total_reports} reports for dataset '{dataset_name}'...")

    for i, report_id in enumerate(report_ids):
        success = process_report(report_id, dataset_name, provider_name, model_id, model_name_slug, skip_eval=skip_eval)   
        if success:
            success_count += 1
        else:
            failure_count += 1
            print(f"!!! Processing failed for report {report_id} [Dataset: {dataset_name}] !!!", file=sys.stderr)

    print("\n" + "="*50)
    print("Main workflow finished.")
    print(f"Dataset: {dataset_name}")
    print(f"Provider/Model: {provider_name}/{model_id}")
    print(f"Total Reports: {total_reports} | Successful: {success_count} | Failed: {failure_count}")
    print("="*50)
# In src/main.py

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process medical reports using LLMs.")
    
    parser.add_argument(
        '--dataset',
        choices=list(config.DATASET_CONFIGS.keys()),
        help="Specify the dataset to process (e.g., 'benson', 'sugo')."
    )
    parser.add_argument(
        '-i', '--report-id',
        nargs='+', 
        help="Specify one or more report IDs to process. Overrides automatic discovery."
    )
    parser.add_argument(
        '--provider',
        choices=list(config.LLM_PROVIDERS.keys()), 
        help="LLM provider. Skips interactive selection."
    )
    parser.add_argument(
        '--model',
        help="LLM model ID or display name. Must be used with --provider."
    )
    parser.add_argument(
    '--skip-eval',
    action='store_true',
    help="Skip the evaluation (accuracy) step."
    )

    args = parser.parse_args()

    # --- Step 1: Determine the Dataset ---
    selected_dataset = args.dataset
    if not selected_dataset:
        selected_dataset = select_dataset()
        if not selected_dataset:
            print("No dataset selected. Exiting.")
            sys.exit(0)

    # --- Step 2: Determine the LLM Provider and Model ---
    # This logic remains the same...
    selected_provider_name = args.provider
    cli_model_input = args.model
    selected_model_id = None
    if selected_provider_name and cli_model_input:
        provider_conf = config.LLM_PROVIDERS.get(selected_provider_name)
        if not provider_conf:
             print(f"Error: Invalid provider '{selected_provider_name}'.", file=sys.stderr); sys.exit(1)
        if cli_model_input in provider_conf["models"]:
            selected_model_id = provider_conf["models"][cli_model_input]
        elif cli_model_input in provider_conf["models"].values():
            selected_model_id = cli_model_input
        else:
            print(f"Error: Model '{cli_model_input}' is invalid for provider '{selected_provider_name}'.", file=sys.stderr); sys.exit(1)
    else:
        _provider, _display_name, _model_id = select_llm_provider_and_model(selected_dataset)
        if not _provider:
            print("No LLM selected. Exiting."); sys.exit(0)
        selected_provider_name = _provider
        selected_model_id = _model_id
    if not selected_model_id:
        print("Error: Could not determine a valid model ID. Exiting.", file=sys.stderr); sys.exit(1)
    model_name_slug = selected_model_id.replace('/', '_').replace(':', '_') 

    # --- Step 3: Determine which reports to process ---
    # --- MODIFIED: Use the new discovery function ---
    reports_to_run = []
    if args.report_id:
        reports_to_run = args.report_id
        print(f"\nProcessing user-specified report IDs: {', '.join(reports_to_run)}")
    else:
        # Discover reports by looking for pre-processed files
        reports_to_run = discover_processed_reports(selected_dataset)
        if not reports_to_run:
            print("\nNo reports found to process. Exiting."); sys.exit(0)
    
    # --- Step 4: Run the main workflow (no changes here) ---

    run_main_workflow(
        reports_to_run,
        selected_dataset,
        selected_provider_name,
        selected_model_id,
        model_name_slug,
        skip_eval=args.skip_eval
    )
    print("\nMain script finished.")
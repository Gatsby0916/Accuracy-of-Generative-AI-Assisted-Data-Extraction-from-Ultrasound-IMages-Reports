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
    print("\n--- Select LLM Provider ---")
    providers = list(config.LLM_PROVIDERS.keys())
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
    option_offset = 0 # To handle numbering if default model option is available

    if default_model_id:
        option_offset = 1
        # Find display name for the default model ID
        for name, id_val in models_dict.items():
            if id_val == default_model_id:
                default_model_display = name
                break
        if default_model_display: # If a display name was found for the default_model_id
             print(f"{len(model_display_names)+option_offset}. Use default model: {default_model_display} ({default_model_id})")
        else: 
            # This case means default_model_id in config.py doesn't match any model_id in the 'models' dict values.
            # It's better to ensure config.py is consistent.
            print(f"{len(model_display_names)+option_offset}. Use default model ID: {default_model_id} (Display name in config may not match or default_model value is incorrect)")


    # Corrected numbering for "Go Back" and "Exit Selection"
    print(f"{len(model_display_names)+option_offset+1}. Go Back")
    print(f"{len(model_display_names)+option_offset+2}. Exit Selection")

    selected_model_id = None
    selected_model_display_name = None
    while True:
        try:
            # Max option number for the current menu
            current_max_option = len(model_display_names) + option_offset + 2 
            prompt_text = f"Please enter an option (1-{current_max_option}): "
            choice_input = int(input(prompt_text)) -1 # User input is 1-based, convert to 0-based

            if 0 <= choice_input < len(model_display_names): # Choice is one of the listed models
                selected_model_display_name = model_display_names[choice_input]
                selected_model_id = models_dict[selected_model_display_name]
                break
            # Choice is the default model (if it exists and option_offset is 1)
            elif default_model_id and option_offset == 1 and choice_input == len(model_display_names): 
                selected_model_id = default_model_id
                selected_model_display_name = default_model_display or selected_model_id # Fallback if display name wasn't found
                print(f"Selected default model: {selected_model_display_name} (ID: {selected_model_id})")
                break
            elif choice_input == len(model_display_names) + option_offset: # Choice is "Go Back"
                return select_llm_provider_and_model() # Recursive call to re-select provider
            elif choice_input == len(model_display_names) + option_offset + 1: # Choice is "Exit Selection"
                print("User chose to exit.")
                return None, None, None
            else:
                print("Invalid option, please enter again.")
        except ValueError:
            print("Invalid input, please enter a number.")
    
    print(f"Selected Provider: {selected_provider_name.capitalize()}, Model: {selected_model_display_name} (ID: {selected_model_id})")
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

def process_report(report_id, provider_name, model_id, model_name_slug):
    """
    Processes a single report through the entire pipeline using the specified LLM.
    """
    print(f"\n{'#'*20} Starting to process report: {report_id} using {provider_name.capitalize()}/{model_id} {'#'*20}")

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
        print(f"Error: Could not create output directories for {provider_name}/{model_name_slug}: {e}", file=sys.stderr)
        return False

    print(f"\n[Step 1/4] Calling {script_api} to extract data...")
    if not run_script(script_api, report_id, provider_name, model_id): return False

    print(f"\n[Step 2/4] Calling {script_validate} to validate and fix the extracted data...")
    if not run_script(script_validate, report_id, provider_name, model_name_slug): return False

    print(f"\n[Step 3/4] Calling {script_to_excel} to convert JSON to Excel...")
    if not run_script(script_to_excel, report_id, provider_name, model_name_slug): return False

    print(f"\n[Step 4/4] Calling {script_evaluate} for comparison and evaluation...")
    if not run_script(script_evaluate, report_id, provider_name, model_name_slug): return False

    print(f"\nReport {report_id} ({provider_name.capitalize()}/{model_id}) processed successfully.")
    return True

def find_report_ids_from_pdfs(pdf_directory):
    """
    Scans the specified directory for PDF files and extracts report IDs.
    """
    report_ids = set()
    pattern = re.compile(r'^RRI\s?(\d{3})\.pdf$', re.IGNORECASE)
    print(f"\nScanning PDF directory to find report IDs: {pdf_directory}")

    if not os.path.isdir(pdf_directory):
        print(f"Warning: The specified PDF directory does not exist: {pdf_directory}")
        return []
    try:
        for filename in os.listdir(pdf_directory):
            match = pattern.match(filename)
            if match:
                report_num = match.group(1)
                report_id = f"RRI{report_num}" 
                report_ids.add(report_id)
    except Exception as e:
        print(f"Error while scanning PDF directory: {e}")
        return [] 

    sorted_ids = sorted(list(report_ids))
    if sorted_ids:
        print(f"Found {len(sorted_ids)} report IDs: {', '.join(sorted_ids)}")
    else:
        print(f"No PDF files matching the 'RRIXXX.pdf' format were found in the directory '{pdf_directory}'.")
    return sorted_ids


def run_main_workflow(report_ids_to_process, provider_name, model_id, model_name_slug):
    """
    Runs the main processing workflow for a list of report IDs using the specified LLM.
    """
    total_reports = len(report_ids_to_process)
    success_count = 0
    failure_count = 0

    if not report_ids_to_process:
        print("No report IDs to process.")
        return

    print(f"\nPreparing to process {total_reports} reports with {provider_name.capitalize()}/{model_id}: {', '.join(report_ids_to_process)}")

    for i, report_id in enumerate(report_ids_to_process):
        print(f"\n--- Starting to process report {i+1}/{total_reports}: {report_id} ---")
        success = process_report(report_id, provider_name, model_id, model_name_slug)
        if success:
            success_count += 1
        else:
            failure_count += 1
            print(f"!!! Report {report_id} ({provider_name.capitalize()}/{model_id}) processing failed or was aborted !!!", file=sys.stderr)

    print("\n" + "="*50)
    print(f"Processing flow for all selected reports has finished (using {provider_name.capitalize()}/{model_id}).")
    print(f"Total: {total_reports} reports")
    print(f"Successful: {success_count}")
    print(f"Failed: {failure_count}")
    print("="*50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process MRI reports, allowing selection of LLM provider and model, and auto-discovery of IDs from PDFs or processing of specified IDs."
    )
    parser.add_argument(
        '-i', '--report-id',
        nargs='+', 
        help="Specify one or more report IDs to process (e.g., RRI002 RRI004). If provided, this will override auto-discovery."
    )
    parser.add_argument(
        '--pdf-dir',
        default=config.DEFAULT_PDF_SCAN_DIR, 
        help=f"Specify the directory path containing PDF reports for automatic discovery of report IDs (default: {config.DEFAULT_PDF_SCAN_DIR})"
    )
    parser.add_argument(
        '--provider',
        choices=list(config.LLM_PROVIDERS.keys()), 
        help="LLM provider (e.g., openai, gemini, claude). If provided, interactive selection will be skipped."
    )
    parser.add_argument(
        '--model',
        help="LLM model ID or display name (e.g., gpt-4o, gemini-1.5-pro). Must be used with --provider. If provided, interactive selection will be skipped."
    )
    args = parser.parse_args()

    selected_provider_name = args.provider
    cli_model_input = args.model 
    
    selected_model_id = None

    if selected_provider_name and cli_model_input:
        print(f"LLM selected via command-line arguments: Provider='{selected_provider_name}', Model Input='{cli_model_input}'")
        if selected_provider_name not in config.LLM_PROVIDERS:
            print(f"Error: Invalid provider '{selected_provider_name}'. Options are: {list(config.LLM_PROVIDERS.keys())}")
            sys.exit(1)
        
        provider_conf = config.LLM_PROVIDERS[selected_provider_name]
        if cli_model_input in provider_conf["models"]: # Check if it's a display name
            selected_model_id = provider_conf["models"][cli_model_input]
            print(f"Model '{cli_model_input}' was identified as a display name, corresponding model ID: '{selected_model_id}'.")
        elif cli_model_input in provider_conf["models"].values(): # Check if it's an actual model ID
            selected_model_id = cli_model_input
            print(f"Model '{cli_model_input}' was identified as a valid model ID.")
        else:
            print(f"Error: Model '{cli_model_input}' for provider '{selected_provider_name}' is invalid.")
            print(f"Available models (Display Name: ID): {provider_conf['models']}")
            sys.exit(1)
    else:
        # Interactive selection if provider and model are not fully specified via CLI
        _provider, _display_name, _model_id = select_llm_provider_and_model()
        if not _provider: # User exited selection
            print("No LLM selected, exiting program.")
            sys.exit(0)
        selected_provider_name = _provider
        selected_model_id = _model_id

    if not selected_model_id: 
        print("Error: Could not determine a valid model ID. Exiting program.")
        sys.exit(1)
    # Create a filesystem-safe slug from the model_id for directory naming
    model_name_slug = selected_model_id.replace('/', '_').replace(':', '_') 

    if args.report_id:
        reports_to_run = args.report_id
        print(f"\nUser specified processing report IDs: {', '.join(reports_to_run)}")
    else:
        reports_to_run = find_report_ids_from_pdfs(args.pdf_dir)
        if not reports_to_run:
             print("\nCould not automatically discover any report IDs. If you expect to process reports, check '--pdf-dir' or specify IDs with '-i'. Exiting program.")
             sys.exit(0) 

    # Ensure the general processed_images directory exists (it's not provider/model specific)
    try:
        os.makedirs(config.PROCESSED_IMAGES_DIR, exist_ok=True)
    except Exception as e:
        print(f"Warning: An error occurred while creating the general images directory '{config.PROCESSED_IMAGES_DIR}': {e}", file=sys.stderr)
        # This might not be fatal if images are already processed, but good to note.

    # Run the main workflow with the selected LLM provider and model details
    run_main_workflow(reports_to_run, selected_provider_name, selected_model_id, model_name_slug)
    print("\nProcessing finished.")

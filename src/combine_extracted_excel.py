import os
import sys
import pandas as pd
import argparse
import config

def combine_extracted_excel(dataset_name, provider_name, model_name_slug, report_ids=None):
    """
    Combine extracted Excel files for the specified dataset, provider, and model
    into a single large Excel file. If report_ids is provided, only those IDs
    will be merged; otherwise, all .xlsx in the directory are merged.
    """
    extracted_excel_dir = config.get_extracted_excel_dir(provider_name, model_name_slug, dataset_name)
    if not os.path.isdir(extracted_excel_dir):
        print(f"Error: The directory for extracted Excel files does not exist: {extracted_excel_dir}", file=sys.stderr)
        return

    df_list = []

    if report_ids:
        # Only merge the specified IDs
        filenames = [f"{rid}_output.xlsx" for rid in report_ids]
    else:
        # Merge all .xlsx files in directory
        filenames = [fn for fn in os.listdir(extracted_excel_dir) if fn.lower().endswith(".xlsx")]

    for filename in filenames:
        file_path = os.path.join(extracted_excel_dir, filename)
        if not os.path.exists(file_path):
            print(f"Warning: File not found, skipping: {file_path}", file=sys.stderr)
            continue

        print(f"Processing file: {file_path}")
        try:
            # Always read with header=0 so columns align
            df = pd.read_excel(file_path, header=0)
            df_list.append(df)
        except Exception as e:
            print(f"Error reading file {file_path}: {e}", file=sys.stderr)

    if not df_list:
        print(f"No valid Excel files found to combine in {extracted_excel_dir}", file=sys.stderr)
        return

    combined_df = pd.concat(df_list, ignore_index=True)

    output_dir = config.get_overall_analysis_dir(provider_name, model_name_slug, dataset_name)
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(
        output_dir,
        f"{dataset_name}_{provider_name}_{model_name_slug}_extracted_data_combined.xlsx"
    )

    try:
        combined_df.to_excel(output_file, index=False)
        print(f"Successfully combined Excel files. Output saved to: {output_file}")
    except Exception as e:
        print(f"Error saving combined Excel file: {e}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Combine extracted Excel files into one. Optionally specify report IDs to merge only those."
    )
    parser.add_argument(
        "dataset_name",
        choices=list(config.DATASET_CONFIGS.keys()),
        help=f"Dataset name ({', '.join(config.DATASET_CONFIGS.keys())})."
    )
    parser.add_argument(
        "provider_name",
        choices=list(config.LLM_PROVIDERS.keys()),
        help="LLM provider (e.g., openai, gemini, claude)."
    )
    parser.add_argument(
        "model_name_slug",
        help="Model name slug (e.g., gpt-4o, gemini-1.5-pro-latest)."
    )
    parser.add_argument(
        "-i", "--report-ids",
        nargs="+",
        help="Specific report IDs to combine (e.g. 0184 0207 0552). If omitted, all files will be merged."
    )
    args = parser.parse_args()

    combine_extracted_excel(
        args.dataset_name,
        args.provider_name,
        args.model_name_slug,
        report_ids=args.report_ids
    )

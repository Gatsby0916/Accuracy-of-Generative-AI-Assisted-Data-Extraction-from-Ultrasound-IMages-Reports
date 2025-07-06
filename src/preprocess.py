# src/preprocess.py

import os
import sys
import re
import argparse
import pdfplumber
from pdf2image import convert_from_path
import config

# --- HELPER FUNCTIONS (Moved from main.py and adapted) ---

def find_report_ids_from_pdfs(pdf_directory, dataset_name):
    """
    Scans the specified directory for PDF files and extracts report IDs.
    Handles different naming conventions for different datasets.
    """
    report_ids = set()
    patterns = {
        "benson": re.compile(r'^(RRI\s?\d{3,})\.pdf$', re.IGNORECASE),
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
            # For benson, "RRI 002.pdf" becomes "RRI002"
            report_id = match.group(1).replace(" ", "")
            report_ids.add(report_id)

    sorted_ids = sorted(list(report_ids))
    print(f"Found {len(sorted_ids)} report IDs.")
    return sorted_ids

def find_pdf_path(report_id, pdf_dir):
    """
    Finds the full path of a PDF file given a report ID, handling variations.
    Example: ID "RRI002" can match "RRI002.pdf" or "RRI 002.pdf"
    """
    # Simple case: ID matches filename base
    if os.path.exists(os.path.join(pdf_dir, f"{report_id}.pdf")):
        return os.path.join(pdf_dir, f"{report_id}.pdf")
    
    # Handle space case for benson: RRI002 -> RRI 002.pdf
    if report_id.startswith("RRI"):
        report_num = report_id[3:]
        spaced_name = f"RRI {report_num}.pdf"
        if os.path.exists(os.path.join(pdf_dir, spaced_name)):
            return os.path.join(pdf_dir, spaced_name)

    return None # Return None if no match is found

# --- PROCESSING FUNCTIONS (No changes needed) ---

def process_image_based_dataset(report_id, pdf_path, output_dir):
    """Converts a PDF file to a series of PNG images."""
    print(f"  - Processing {os.path.basename(pdf_path)} -> PNGs")
    try:
        images = convert_from_path(pdf_path)
        for i, image in enumerate(images):
            image.save(os.path.join(output_dir, f"{report_id}_page_{i + 1}.png"), 'PNG')
        return True
    except Exception as e:
        print(f"    Error converting {os.path.basename(pdf_path)}: {e}", file=sys.stderr)
        return False

def process_text_based_dataset(report_id, pdf_path, output_dir):
    """Extracts all text from a PDF file and saves it to a .txt file."""
    print(f"  - Processing {os.path.basename(pdf_path)} -> TXT")
    try:
        full_text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n\n--- Page Break ---\n\n"
        
        with open(os.path.join(output_dir, f"{report_id}.txt"), 'w', encoding='utf-8') as f:
            f.write(full_text)
        return True
    except Exception as e:
        print(f"    Error extracting text from {os.path.basename(pdf_path)}: {e}", file=sys.stderr)
        return False

# --- BATCH PROCESSING MAIN FUNCTION ---

def main(dataset_name):
    """
    Main batch preprocessing function. Processes all reports for a given dataset.
    """
    if dataset_name not in config.DATASET_CONFIGS:
        print(f"Error: Dataset '{dataset_name}' not found in config.py.", file=sys.stderr)
        sys.exit(1)

    dataset_config = config.DATASET_CONFIGS[dataset_name]
    data_type = dataset_config["data_type"]
    pdf_dir = dataset_config["pdf_dir"]
    output_dir = config.get_processed_data_dir(dataset_name)

    print(f"\n--- Starting Batch Preprocessing for Dataset: {dataset_name} ---")
    print(f"Data Type: {data_type}")
    print(f"Input PDF Directory: {pdf_dir}")
    print(f"Output Directory: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    report_ids = find_report_ids_from_pdfs(pdf_dir, dataset_name)
    if not report_ids:
        print("No reports to process. Exiting.")
        return

    success_count = 0
    fail_count = 0
    for i, report_id in enumerate(report_ids):
        print(f"\nProcessing report {i+1}/{len(report_ids)}: {report_id}")
        pdf_path = find_pdf_path(report_id, pdf_dir)
        
        if not pdf_path:
            print(f"  - Error: Could not find PDF file for report ID {report_id}. Skipping.", file=sys.stderr)
            fail_count += 1
            continue

        success = False
        if data_type == "image":
            success = process_image_based_dataset(report_id, pdf_path, output_dir)
        elif data_type == "text":
            success = process_text_based_dataset(report_id, pdf_path, output_dir)
        
        if success:
            success_count += 1
        else:
            fail_count += 1

    print("\n--- Batch Preprocessing Complete ---")
    print(f"Successfully processed: {success_count}")
    print(f"Failed to process: {fail_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch pre-process a dataset's PDF files into images or text.")
    parser.add_argument(
        '--dataset',
        required=True,
        choices=list(config.DATASET_CONFIGS.keys()),
        help="Specify the dataset to process (e.g., 'benson', 'sugo')."
    )
    args = parser.parse_args()
    main(args.dataset)
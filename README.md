# Accuracy of Generative AI–Assisted Data Extraction from Ultrasound Image Reports

## Project Overview

This repository demonstrates how to leverage large language models (LLMs) such as OpenAI GPT-4 Turbo to automatically extract structured data from locally stored medical report PDFs or images and compare the results against human‑annotated ground truth. The aim is to reduce repetitive data‑entry work for healthcare professionals and quantitatively assess the accuracy of AI‑assisted extraction in real‑world clinical workflows.

## Key Features

* **Excel → JSON Template Generation**: Build a JSON output template directly from a human‑annotated Excel sheet, defining all required fields and default values.
* **PDF → Image/Text Conversion**: Convert PDF reports to PNG (for image‑based datasets) or extract raw text (for text‑based datasets).
* **Data Preparation & Standardization**: Clean ground truth Excel data and generate consistent JSON templates to enforce strict LLM output formatting.
* **LLM‑Based Extraction**: Send images or text plus JSON templates to the OpenAI API (GPT‑4 Turbo, 4o, Mini) and receive structured JSON.
* **Result Validation & Correction**: Compare raw LLM output against the template, automatically fix minor key mismatches (e.g., typos) and fill missing fields with default values.
* **Format Conversion**: Transform validated JSON into per‑report Excel files for review and downstream analysis.
* **Accuracy Evaluation**: Compare each cell in the LLM‑extracted Excel against the ground truth; compute accuracy at both field and report levels.
* **Discrepancy Reporting**: Generate detailed text reports listing all mismatches, including ground truth vs. extracted values.
* **Aggregate Analysis & Visualization**: Combine individual results, compute summary statistics (mean, median, standard deviation), and produce visual charts.

## Directory Structure

```text
LLM-test/
├── .gitignore            # ignores data/, venv/, .env, results/
├── requirements.txt      # Python dependencies
├── README.md             # Project documentation (this file)
├── data/                 # Raw inputs (ignored by Git)
│   ├── ground_truth/     # Human‑annotated Excel files
│   ├── raw_reports/      # PDF reports (subfolders per dataset)
│   │   ├── BENSON DEID RRI REPORTS
│   │   ├── IMAGENDO ID REPORTS
│   │   └── raw_sugo
│   └── templates/        # JSON templates generated from Excel via `src/json_template_generator.py`
│       ├── json_template_sugo.json
│       └── json_template_Benson.json
└── src/                  # Source code
    ├── config.py         # Path and dataset configuration
    ├── preprocess.py     # PDF → PNG or TXT
    ├── api_interaction.py# LLM prompt generation and API calls
    ├── data_validation.py# JSON vs. template validation and correction
    ├── json_to_excel.py  # JSON → Excel conversion
    ├── evaluation.py     # Accuracy computation against ground truth
    ├── main.py           # End‑to‑end workflow driver
    ├── combine_extracted_excel.py # Merge multiple Excel outputs
    └── reporting.py      # Aggregate reporting and visualization
```

````

> **Note:** The `data/`, `results/`, `venv/`, and `.env` files contain local data or secrets and should be added to `.gitignore`.

## Installation & Setup

1. **Clone the Repository**

   ```bash
   git clone https://github.com/Gatsby0916/Accuracy-of-Generative-AI-Assisted-Data-Extraction-from-Ultrasound-IMages-Reports
   cd LLM-test
````

2. **Create & Activate Python Virtual Environment**
   *(Python 3.7+ recommended)*

   ```bash
   python -m venv venv
   # Windows PowerShell
   ```

environ:
.\venv\Scripts\Activate.ps1

# macOS/Linux

source venv/bin/activate

````

3. **Install Dependencies**

```bash
pip install -r requirements.txt
````

4. **(Windows) Install Poppler for PDF2Image**

   * Download Poppler‑Windows, unzip to `C:\Program Files\poppler-<version>`, add its `bin` folder to your PATH.
   * On macOS: `brew install poppler`
   * On Ubuntu: `sudo apt-get install poppler-utils`

5. **Configure Environment Variables**
   Create a `.env` in project root:

   ```dotenv
   OPENAI_API_KEY="sk-..."
   ```

6. **Verify ****`config.py`**** Paths**

   * Ensure `DATASET_CONFIGS` correctly points to your raw PDFs and Excel/JSON templates.

## Usage Workflow

> All commands assume your virtual environment is active and current directory is project root.

### 1. Generate JSON Template from Excel

When you have a new or updated ground truth Excel file, generate the corresponding JSON template by running:

```bash
python src/data_extraction.py --dataset <dataset_name>
```

This will read the headers from `data/ground_truth/<dataset>.xlsx` and write a JSON template to `data/templates/json_template_<dataset>.json` (as configured in `src/config.py`).

### 2. Preprocess PDFs

* **Image‑based dataset (e.g., Benson)**

  ```bash
  python src/preprocess.py --dataset benson
  ```
* **Text‑based dataset (e.g., Sugo or Benson text)**

  ```bash
  python src/preprocess.py --dataset sugo
  python src/preprocess.py --dataset benson_text
  ```

### 3. Run End‑to‑End Extraction & Evaluation

```bash
python src/main.py
```

Follow the prompts to select dataset, LLM provider, model, and optionally specific report IDs.

* Skip accuracy evaluation if no ground truth:

  ```bash
  python src/main.py --dataset benson_text --skip-eval
  ```
* Process only specific reports:

  ```bash
  python src/main.py --dataset sugo -i 0184 0207 0552
  ```

### 4. Aggregate & Visualize Results

* **Combine Excel outputs**:

  ```bash
  python src/combine_extracted_excel.py sugo openai gpt-4o -i 0184 0207 0552
  ```
* **Generate summary reports & charts**:

  ```bash
  python src/reporting.py sugo openai gpt-4o
  ```

All final results and charts will be under `results/overall_analysis/` for review.

## Dependencies

List of core dependencies in `requirements.txt`:

```text
pandas
pdfplumber
pdf2image
openai
google-generativeai
anthropic
matplotlib
seaborn
tabulate
python-dotenv
```

Install via:

```bash
pip install -r requirements.txt
```

---

This README provides a comprehensive guide for medical students or researchers—even without a deep Python background—to set up, run, and understand the entire AI‑assisted extraction pipeline. Feel free to adjust dataset keys or paths in `src/config.py` as needed. Happy extracting!

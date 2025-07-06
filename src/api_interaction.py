import sys
import base64
import json
import os
from dotenv import load_dotenv
import config # Import the config module

# Load per-field metadata once
try:
    FIELDS_METADATA = json.load(open(config.METADATA_PATH, 'r', encoding='utf-8'))
except Exception as e:
    print(f"Error loading metadata: {e}", file=sys.stderr)
    sys.exit(1)
def build_field_rules(metadata):
    lines = []
    for field, info in metadata.items():
        desc = info["description"]
        if info["type"] == "numeric":
            lines.append(f"- **{field}** ({info['unit']}): {desc}")
        elif info["type"] == "date":
            lines.append(f"- **{field}** (date, {info['format']}): {desc}")
        else:  # enum
            allowed = "/".join(info["allowed_values"])
            line = f"- **{field}**: {desc} Allowed: [{allowed}]."
            if "mapping" in info:
                map_pairs = ", ".join(f"{k}->{v}" for k,v in info["mapping"].items())
                line += f" Map: {map_pairs}."
            default = info.get("default_value") or info.get("default_missing", "")
            line += f" Default if missing: {default}."
            lines.append(line)
    return "\n".join(lines)

# --- Load Environment Variables (Load once at the start) ---
# Construct the path to the .env file relative to the project root
dotenv_path = os.path.join(config.PROJECT_ROOT, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    # print(f"Successfully loaded .env file from: {dotenv_path}") # Optional: for debugging
else:
    # Fallback to loading from system environment if .env is not found
    # print(f"Warning: .env file not found at {dotenv_path}. Attempting to load from system environment.")
    load_dotenv() # This will load from system environment if .env is not found or if called without path

# --- Helper Function: Encode image to base64 ---
def encode_image(image_path):
    """
    Encodes an image file to a base64 string.
    Args:
        image_path (str): The path to the image file.
    Returns:
        str: The base64 encoded string of the image, or None if an error occurs.
    """
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    except FileNotFoundError:
        print(f"Error: Image file not found during encoding: {image_path}")
        return None
    except Exception as e:
        print(f"An error occurred while encoding image {image_path}: {e}")
        return None

# --- Base LLM Client Class ---
# In src/api_interaction.py


# --- MODIFIED: The extract_data method is now more flexible ---
class BaseLLMClient:
    """Base class for LLM API clients."""
    def __init__(self, api_key, model_id, max_tokens):
        self.api_key = api_key
        self.model_id = model_id
        self.max_tokens = max_tokens if max_tokens is not None else 4000 # Default if not specified

    def extract_data(self, prompt_payload):
        """
        Sends a request to the LLM API to extract data.
        This method now takes a pre-constructed 'prompt_payload'.
        This method must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement the extract_data method.")
# In src/api_interaction.py

# --- OpenAI Client ---
# --- MODIFIED: extract_data now uses a generic payload ---
class OpenAIClient(BaseLLMClient):
    """Client for interacting with OpenAI API."""
    def __init__(self, api_key, model_id, max_tokens):
        super().__init__(api_key, model_id, max_tokens)
        try:
            from openai import OpenAI as OpenAI_SDK # Alias to avoid conflict
            self.client = OpenAI_SDK(api_key=self.api_key)
        except ImportError:
            print("Error: openai Python package not installed. Please run 'pip install openai'", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"OpenAI client initialization error: {e}", file=sys.stderr)
            sys.exit(1)

    def extract_data(self, prompt_payload):
        print(f"Sending request to OpenAI ({self.model_id})...")
        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": prompt_payload}],
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )
            response_content = response.choices[0].message.content
            return json.loads(response_content)
        except Exception as e:
            print(f"OpenAI API call or response handling error: {e}", file=sys.stderr)
            raise

# --- Gemini Client ---
# --- MODIFIED: extract_data now uses a generic payload ---
class GeminiClient(BaseLLMClient):
    """Client for interacting with Google Gemini API."""
    def __init__(self, api_key, model_id, max_tokens):
        super().__init__(api_key, model_id, max_tokens)
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model_id)
        except ImportError:
            print("Error: google-generativeai Python package not installed. Please run 'pip install google-generativeai'", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Gemini client initialization error: {e}", file=sys.stderr)
            sys.exit(1)

    def extract_data(self, prompt_payload):
        print(f"Sending request to Gemini ({self.model_id})...")
        try:
            import google.generativeai as genai 
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=self.max_tokens,
                response_mime_type="application/json" 
            )
            response = self.client.generate_content(
                prompt_payload,
                generation_config=generation_config
            )
            # Simplified response handling for JSON
            return json.loads(response.text)
        except Exception as e:
            print(f"Gemini API call or response handling error: {e}", file=sys.stderr)
            raise

# --- Claude Client ---
# --- MODIFIED: extract_data now uses a generic payload ---
class ClaudeClient(BaseLLMClient):
    """Client for interacting with Anthropic Claude API."""
    def __init__(self, api_key, model_id, max_tokens):
        super().__init__(api_key, model_id, max_tokens)
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.api_key)
        except ImportError:
            print("Error: anthropic Python package not installed. Please run 'pip install anthropic'", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Claude client initialization error: {e}", file=sys.stderr)
            sys.exit(1)

    def extract_data(self, prompt_payload):
        print(f"Sending request to Claude ({self.model_id})...")
        try:
            response = self.client.messages.create(
                model=self.model_id,
                max_tokens=self.max_tokens, 
                messages=[
                    {
                        "role": "user",
                        "content": prompt_payload,
                    }
                ]
            )
            
            json_string = ""
            if response.content and isinstance(response.content, list):
                for block in response.content:
                    if block.type == "text":
                        json_string = block.text
                        break 

            if not json_string:
                raise ValueError("Could not extract text from Claude response.")

            # Clean up potential markdown code blocks
            if "```json" in json_string:
                json_string = json_string.split("```json", 1)[1].rsplit("```", 1)[0].strip()
            elif json_string.strip().startswith("```") and json_string.strip().endswith("```"):
                json_string = json_string.strip()[3:-3].strip()
            
            return json.loads(json_string)
        except Exception as e:
            print(f"Claude API call or response handling error: {e}", file=sys.stderr)
            raise
# --- Factory Function to Get LLM Client ---
def get_llm_client(provider_name, model_id):
    """
    Factory function to get an instance of the appropriate LLM client.
    """
    if provider_name not in config.LLM_PROVIDERS:
        print(f"Error: Unknown LLM provider '{provider_name}'. Please check config.py.")
        sys.exit(1)

    provider_config = config.LLM_PROVIDERS[provider_name]
    api_key_env_var = provider_config["api_key_env"]
    api_key = os.getenv(api_key_env_var)
    
    max_tokens_setting = provider_config.get("max_tokens", 4000) 

    if not api_key:
        print(f"Error: Environment variable {api_key_env_var} is not set or loaded. Please check your .env file.")
        sys.exit(1)

    client_type = provider_config.get("client_name")
    if client_type == "openai":
        return OpenAIClient(api_key, model_id, max_tokens_setting)
    elif client_type == "gemini":
        return GeminiClient(api_key, model_id, max_tokens_setting)
    elif client_type == "claude":
        return ClaudeClient(api_key, model_id, max_tokens_setting)
    else:
        print(f"Error: Client type '{client_type}' for provider '{provider_name}' is not implemented.")
        sys.exit(1)
# In src/api_interaction.py

# --- NEW: Function to generate the payload for the API call ---
def generate_api_payload(data_type, prompt_text, data_content):
    """
    Constructs the appropriate payload for the LLM API call based on data type.
    
    Args:
        data_type (str): 'image' or 'text'.
        prompt_text (str): The instructional part of the prompt.
        data_content (list or str): A list of base64 images or a single text string.

    Returns:
        The payload suitable for the LLM client.
    """
    # For text-based datasets, the payload is just a combined string.
    if data_type == 'text':
        # The prompt for text will include the report's content directly.
        return f"{prompt_text}\n\n# Report Content to Analyze:\n```text\n{data_content}\n```"

    # For image-based datasets, the payload is a list of text and image parts.
    # This format is required by modern multi-modal models (OpenAI, Claude 3+).
    elif data_type == 'image':
        payload = [{"type": "text", "text": prompt_text}]
        for img_b64 in data_content:
            payload.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"}
            })
        # Note for Gemini: The Gemini client can handle this list format directly.
        return payload
    
    else:
        raise ValueError(f"Unsupported data_type for payload generation: {data_type}")
# --- Generic Prompt Generation ---
# In src/api_interaction.py

# --- Generic Prompt Generation ---
def generate_prompt(json_template_str: str) -> str:
    """
    Build a detailed instruction prompt that includes:
      1) Task objective
      2) JSON template
      3) Auto-generated per-field rules
      4) A minimal example
    """
    # 1) Task header
    prompt = (
        "# Task Objective\n"
        "Accurately extract information from the provided medical report "
        "and populate it strictly according to the JSON template and field rules below. "
        "Your output must be a single, valid JSON object—no extra text.\n\n"
    )

    # 2) JSON template
    prompt += (
        "# JSON Output Template\n"
        "```json\n"
        f"{json_template_str.strip()}\n"
        "```\n\n"
    )

    # 3) Auto-generated Field Rules
    prompt += "# Field Rules\n"
    prompt += build_field_rules(FIELDS_METADATA)
    prompt += "\n\n"

    # 4) Minimal example
    prompt += (
        "## Example Output\n"
        "```json\n"
        "{\n"
        '  "Uterus size length (mm)": "65.3",\n'
        '  "Uterus size width (mm)" : "45.0",\n'
        '  "Uterus size height (mm)": "70.2",\n'
        '  "Uterus Volume (cc) (((L*W*H)/1000)*0.53)": "31.8",\n'
        '  "Surgery Performed": "2",\n'
        '  "Surgery Date": "2",\n'
        '  "Surgeon": "2"\n'
        "}\n"
        "```\n\n"
    )

    # 5) Final note
    # ...existing code...
    prompt += (
        "**Note:** If a field is not present in the report, use its default missing value "
        "(e.g., NA or NR). Do not output any explanatory text—only the JSON object.\n"
        "**Important:**\n"
        "- For comment fields (e.g., Adnexa comments), if no abnormality, fill '0', do **not** copy phrases like \"Normal bilaterally.\".\n"
        "- For enum fields, always use the **numeric codes** per mapping—do not output text.\n"
        "- For date fields, strictly use `YYYY-MM-DD`.\n"
        "- Your final answer must be **only** the JSON object—no extra words."
    )
    # ...existing code...

    return prompt


# --- Main Function ---
# In src/api_interaction.py

# --- Main Function ---
def main(dataset_name, report_id, provider_name, model_id):
    """
    Main processing logic for a single report using a specific LLM.
    """
    print(f"\n--- Starting API Interaction for Report: {report_id}, Dataset: {dataset_name} ---")
    
    # 1. Get all necessary configurations from config.py
    model_name_slug = model_id.replace('/', '_').replace(':', '_')
    try:
        dataset_config = config.DATASET_CONFIGS[dataset_name]
        data_type = dataset_config["data_type"]
        template_path = dataset_config["template_json"]
        processed_data_dir = config.get_processed_data_dir(dataset_name)
        output_dir = config.get_extracted_json_raw_dir(provider_name, model_name_slug, dataset_name)
        os.makedirs(output_dir, exist_ok=True)
    except KeyError:
        print(f"FATAL: Dataset '{dataset_name}' not found in config.DATASET_CONFIGS.", file=sys.stderr)
        sys.exit(1)

    # 2. Load the processed data content (either a text string or a list of images)
    data_content = None
    if data_type == 'text':
        text_file_path = os.path.join(processed_data_dir, f"{report_id}.txt")
        try:
            with open(text_file_path, 'r', encoding='utf-8') as f:
                data_content = f.read()
            print(f"Successfully loaded text content from: {text_file_path}")
        except FileNotFoundError:
            print(f"FATAL: Processed text file not found: {text_file_path}. Please check the 'preprocess.py' step.", file=sys.stderr)
            sys.exit(1)
            
    elif data_type == 'image':
        image_files = [f for f in os.listdir(processed_data_dir) if f.startswith(f"{report_id}_page_") and f.endswith(".png")]
        if not image_files:
            print(f"FATAL: No processed images found for report '{report_id}' in {processed_data_dir}. Please check the 'preprocess.py' step.", file=sys.stderr)
            sys.exit(1)
        
        base64_images = [encode_image(os.path.join(processed_data_dir, img_file)) for img_file in sorted(image_files)]
        data_content = [img for img in base64_images if img] # Filter out any None values if encoding failed
        print(f"Successfully loaded and encoded {len(data_content)} images for report {report_id}")

    if not data_content:
        print(f"FATAL: Failed to load any data content for report {report_id}.", file=sys.stderr)
        sys.exit(1)

    # --- THIS IS THE CORRECTED PART ---
    # All logic is now inside a single, robust try...except block.
    try:
        # 3. Generate the instructional prompt and the final API payload
        print("Generating prompt and API payload...")
        with open(template_path, "r", encoding="utf-8") as f:
            json_template_str = f.read()
        
        prompt_instructions = generate_prompt(json_template_str)
        api_payload = generate_api_payload(data_type, prompt_instructions, data_content)

        # 4. Initialize client and call the API
        llm_client = get_llm_client(provider_name, model_id)
        extracted_data = llm_client.extract_data(api_payload)
        
        # 5. Validate and save the output
        if not isinstance(extracted_data, dict):
            raise ValueError(f"LLM did not return a valid JSON object (dictionary).")

        extracted_data["Report ID"] = report_id # Add the report ID for tracking
        
        output_file = os.path.join(output_dir, f"{report_id}_extracted_data.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(extracted_data, f, indent=config.JSON_INDENT, ensure_ascii=config.ENSURE_ASCII)
        print(f"Successfully saved extracted data to: {output_file}")

    except Exception as e:
        # This block will now catch ANY error from steps 3, 4, or 5
        print(f"A critical error occurred in the API interaction step: {e}", file=sys.stderr)
        raise # Re-raise the exception to fail the step in main.py

# --- Script Execution Block ---
# --- MODIFIED: Accepts new arguments from main.py ---
if __name__ == "__main__":
    # This script is designed to be called by main.py, so we expect arguments.
    if len(sys.argv) != 5:
        print(f"Usage: python {os.path.basename(__file__)} <dataset_name> <report_id> <provider_name> <model_id>", file=sys.stderr)
        sys.exit(1)
    
    dataset_name_arg = sys.argv[1]
    report_id_arg = sys.argv[2]
    provider_name_arg = sys.argv[3]
    model_id_arg = sys.argv[4]
    
    try:
        main(dataset_name_arg, report_id_arg, provider_name_arg, model_id_arg)
        print(f"\nAPI interaction for report {report_id_arg} completed successfully.")
    except Exception:
        # The detailed error is printed within the functions.
        print(f"\nAPI interaction for report {report_id_arg} FAILED.", file=sys.stderr)
        sys.exit(1)

# **1. Numerical Fields (Measurements, Sizes, Counts):**
#    - Applies to fields containing "(mm)", "(ml)", "thickness", "measurements", "size", "number", "count", "distance", "age", etc., indicating measurement or count.
#    - **Rule:** Find the corresponding **numeric** value from the report images and fill it in. If the value is not explicitly mentioned in the report, or the corresponding structure does not exist, please uniformly fill in `"0"`.
#    - **Example:**
#      ```json
#      "Uterine Size (Body + Cervix - 3 planes in mm) - Length": "80", 
#      "Left ovary measurements - Width (mm)": "19",
#      "Endometrial thickness (Sag plane in mm to nearest mm)": "7",
#      "Number of fibroids": "1", 
#      "Right ovary -  No. follicles between 2 and 9 mm in diameter": "7", 
#      "Abnormal junction zone thickening - Anterior (mm)": "9", 
#      "Distance from anal verge length (mm)": "0" 
#      ```

# **2. Boolean/Status Fields (Yes/No, Presence/Absence, Identified/Not Identified, Status):**
#    - Applies to fields containing "identified", "presence of", "status", or those explicitly representing a "Yes/No" judgment.
#    - **Rule:**
#      - If the report image explicitly states the condition is **"Yes", "Present", "Identified", "Positive", "Active", "Complete", "Conventional", "Normal"** or another similar **affirmative** description, please fill in `"1"`.
#      - If the report image explicitly states **"No", "Absent", "Not identified", "Negative", "Inactive"** or another similar **negative** description, or if the item is **not mentioned at all** in the report, please uniformly fill in `"0"`.
#    - **Example:**
#      ```json
#      "Presence of Uterus": "1",        
#      "Fibroids identified": "1",          
#      "Kissing ovaries identified": "0",   
#      "Hematosalpinx identified": "0",     
#      "Presence of Adenomyosis": "1",      
#      "Submucosal fibroids identified": "0", 
#      "Uterovesical region status": "0"    
#      ```
#      * **Special Note:** For 'status' type fields, carefully judge whether the description in the report indicates an affirmative abnormal state (fill "1") or a negative abnormal state/normal (fill "0").

# **3. Specific Category/Code Fields (Position, Location, Type):**
#    - Applies to fields whose meaning is a preset category or code, such as "Left ovary position", "Uteroscaral ligament nodules - location", "Pouch of Douglas obliteration status".
#    - **Rule:** Find and extract the **exact matching** category code (usually a number `1`, `2`, `3`, etc.) or specific categorical term (like `Left`, `Right`, `Both`, `Partial`, `Complete`) from the report images. If it's not explicitly mentioned in the report, please fill in `"0"`.
#    - **Example:**
#      ```json
#      "Left ovary position": "1",      
#      "Right ovary position": "3",     
#      "Uteroscaral ligament nodules - location": "0", 
#      "Pouch of Douglas obliteration status": "2" 
#      ```
#      * **Important:** For situations requiring mapping (e.g., Complete -> "2"), strictly follow the implicit or explicit mapping rules. If the rules are unclear, prioritize extracting the original text. However, based on our previous agreement, use the number if it can be mapped to a number. If the original text is text with no numeric mapping, use the text; if not mentioned, use "0".

# **4. Descriptive Text Fields (Comments, Description, Features):**
#    - Applies to fields containing "comments", "description", "features (free text)", "Other salient findings", etc., which require a textual description.
#    - **Rule:** **Accurately copy** the relevant original description from the report images. Pay attention to preserving the original text, including medical terminology and possible abbreviations. If no corresponding descriptive information is found in the report, set the field value to an **empty string `""`**.
#    - **Example:**
#      ```json
#      "Fibroid description": "9mm intramural anterior fundus", 
#      "Adnexa comments": "Small left paratubal cyst noted.", 
#      "Uterine anatomy comments": "", 
#      "Other salient findings (free text)": "Incidental finding of small renal cyst on right kidney upper pole seen on edge of image.",
#      "Rectum and Colon lesion features (free text)": "" 
#      ```
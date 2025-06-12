import sys
import base64
import json
import os
from dotenv import load_dotenv
import config # Import the config module

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
class BaseLLMClient:
    """Base class for LLM API clients."""
    def __init__(self, api_key, model_id, max_tokens):
        self.api_key = api_key
        self.model_id = model_id
        self.max_tokens = max_tokens if max_tokens is not None else 4000 # Default if not specified

    def extract_data(self, prompt_text, base64_images):
        """
        Sends a request to the LLM API to extract data.
        This method must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement the extract_data method.")

# --- OpenAI Client ---
class OpenAIClient(BaseLLMClient):
    """Client for interacting with OpenAI API."""
    def __init__(self, api_key, model_id, max_tokens):
        super().__init__(api_key, model_id, max_tokens)
        try:
            from openai import OpenAI as OpenAI_SDK # Alias to avoid conflict
            self.client = OpenAI_SDK(api_key=self.api_key)
        except ImportError:
            print("Error: openai Python package not installed. Please run 'pip install openai'")
            sys.exit(1)
        except Exception as e:
            print(f"OpenAI client initialization error: {e}")
            sys.exit(1)

    def extract_data(self, prompt_text, base64_images):
        content_payload = [{"type": "text", "text": prompt_text}]
        for img_b64 in base64_images:
            content_payload.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"}
            })
        
        print(f"Sending request to OpenAI ({self.model_id})...")
        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": content_payload}],
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"} # Specific to some OpenAI models like gpt-4-turbo
            )
            response_content = response.choices[0].message.content
            if not isinstance(response_content, str):
                 print(f"Error: OpenAI response content is not a string. Received: {type(response_content)}")
                 raise ValueError("OpenAI response content is not a string.")
            return json.loads(response_content)
        except Exception as e:
            print(f"OpenAI API call or response handling error: {e}")
            raise

# --- Gemini Client ---
class GeminiClient(BaseLLMClient):
    """Client for interacting with Google Gemini API."""
    def __init__(self, api_key, model_id, max_tokens):
        super().__init__(api_key, model_id, max_tokens)
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model_id)
        except ImportError:
            print("Error: google-generativeai Python package not installed. Please run 'pip install google-generativeai'")
            sys.exit(1)
        except Exception as e:
            print(f"Gemini client initialization error: {e}")
            sys.exit(1)

    def extract_data(self, prompt_text, base64_images):
        prompt_parts = [prompt_text]
        for img_b64 in base64_images:
            prompt_parts.append({"mime_type": "image/png", "data": img_b64})

        print(f"Sending request to Gemini ({self.model_id})...")
        try:
            import google.generativeai as genai 
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=self.max_tokens,
                response_mime_type="application/json" 
            )
            response = self.client.generate_content(
                prompt_parts,
                generation_config=generation_config
            )
            
            json_text = None
            if hasattr(response, 'text') and response.text:
                json_text = response.text
            elif response.parts and hasattr(response.parts[0], 'text') and response.parts[0].text:
                json_text = response.parts[0].text
            else: 
                if hasattr(response, 'candidates'):
                    for candidate in response.candidates:
                        if candidate.content and candidate.content.parts:
                            for part in candidate.content.parts:
                                if hasattr(part, 'text') and part.text and part.text.strip().startswith('{'):
                                    json_text = part.text
                                    break
                            if json_text:
                                break
                if not json_text:
                    print("Error: Could not find valid JSON text in Gemini response.")
                    print(f"Gemini raw response (partial): {str(response)[:500]}...") 
                    raise ValueError("Could not extract JSON text from Gemini response.")
            
            return json.loads(json_text)
        except json.JSONDecodeError as json_err:
            print(f"Gemini JSON decoding error: {json_err}")
            print(f"Received non-JSON text: {json_text[:500] if 'json_text' in locals() else 'N/A'}...")
            raise
        except Exception as e:
            print(f"Gemini API call or response handling error: {e}")
            raise

# --- Claude Client ---
class ClaudeClient(BaseLLMClient):
    """Client for interacting with Anthropic Claude API."""
    def __init__(self, api_key, model_id, max_tokens):
        super().__init__(api_key, model_id, max_tokens)
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.api_key)
        except ImportError:
            print("Error: anthropic Python package not installed. Please run 'pip install anthropic'")
            sys.exit(1)
        except Exception as e:
            print(f"Claude client initialization error: {e}")
            sys.exit(1)

    def extract_data(self, prompt_text, base64_images):
        messages_content = [{"type": "text", "text": prompt_text}]
        for img_b64 in base64_images:
            messages_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png", 
                    "data": img_b64,
                },
            })
        
        print(f"Sending request to Claude ({self.model_id})...")
        try:
            response = self.client.messages.create(
                model=self.model_id,
                max_tokens=self.max_tokens, 
                messages=[
                    {
                        "role": "user",
                        "content": messages_content,
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
                print("Error: Could not find valid text content in Claude response.")
                raise ValueError("Could not extract text from Claude response.")

            json_string_stripped = json_string.strip()
            if json_string_stripped.startswith("```json"):
                json_string_stripped = json_string_stripped[len("```json"):].strip()
                if json_string_stripped.endswith("```"):
                    json_string_stripped = json_string_stripped[:-len("```")].strip()
            elif json_string_stripped.startswith("```") and json_string_stripped.endswith("```"):
                 json_string_stripped = json_string_stripped[len("```"):-len("```")].strip()
            
            # --- ADDED DEBUG PRINT HERE ---
            print(f"--- Claude Raw String to Parse (Full, after stripping markdown) ---")
            print(json_string_stripped)
            print(f"--- End Claude Raw String ---")
            # --- END ADDED DEBUG PRINT ---
            
            return json.loads(json_string_stripped)
        except json.JSONDecodeError as json_err:
            print(f"Claude JSON decoding error: {json_err}")
            # The error message from json_err (json_err.pos, json_err.msg) is usually very helpful.
            # The snippet below is a fallback if the full string was too long to easily inspect in logs.
            # However, with the full print above, this snippet becomes less critical for direct debugging.
            error_char_index = json_err.pos 
            context_window = 150 # Characters before and after the error point
            start_index = max(0, error_char_index - context_window)
            end_index = min(len(json_string_stripped), error_char_index + context_window)
            print(f"Text snippet around the error (position {error_char_index}):\n'{json_string_stripped[start_index:end_index]}'")
            raise
        except Exception as e:
            print(f"Claude API call or response handling error: {e}")
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

# --- Generic Prompt Generation ---
def generate_prompt(json_template_str):
    """
    Generates the detailed prompt for information extraction.
    """
    return f"""
# Task Objective
Accurately extract information from the provided series of MRI report images and populate it strictly according to the JSON template structure and field instructions provided below. The final output must be a single, complete, and correctly formatted JSON object.

# JSON Output Template
Please fill the extracted information into the following JSON structure. Ensure all fields are included and follow the filling rules for each field:
```json
{json_template_str}
```

# Detailed Filling Rules and Examples

Please read the following rules carefully and refer to the examples for information extraction and formatting:

**1. Numerical Fields (Measurements, Sizes, Counts):**
   - Applies to fields containing "(mm)", "(ml)", "thickness", "measurements", "size", "number", "count", "distance", "age", etc., indicating measurement or count.
   - **Rule:** Find the corresponding **numeric** value from the report images and fill it in. If the value is not explicitly mentioned in the report, or the corresponding structure does not exist, please uniformly fill in `"0"`.
   - **Example:**
     ```json
     "Uterine Size (Body + Cervix - 3 planes in mm) - Length": "80", 
     "Left ovary measurements - Width (mm)": "19",
     "Endometrial thickness (Sag plane in mm to nearest mm)": "7",
     "Number of fibroids": "1", 
     "Right ovary -  No. follicles between 2 and 9 mm in diameter": "7", 
     "Abnormal junction zone thickening - Anterior (mm)": "9", 
     "Distance from anal verge length (mm)": "0" 
     ```

**2. Boolean/Status Fields (Yes/No, Presence/Absence, Identified/Not Identified, Status):**
   - Applies to fields containing "identified", "presence of", "status", or those explicitly representing a "Yes/No" judgment.
   - **Rule:**
     - If the report image explicitly states the condition is **"Yes", "Present", "Identified", "Positive", "Active", "Complete", "Conventional", "Normal"** or another similar **affirmative** description, please fill in `"1"`.
     - If the report image explicitly states **"No", "Absent", "Not identified", "Negative", "Inactive"** or another similar **negative** description, or if the item is **not mentioned at all** in the report, please uniformly fill in `"0"`.
   - **Example:**
     ```json
     "Presence of Uterus": "1",        
     "Fibroids identified": "1",          
     "Kissing ovaries identified": "0",   
     "Hematosalpinx identified": "0",     
     "Presence of Adenomyosis": "1",      
     "Submucosal fibroids identified": "0", 
     "Uterovesical region status": "0"    
     ```
     * **Special Note:** For 'status' type fields, carefully judge whether the description in the report indicates an affirmative abnormal state (fill "1") or a negative abnormal state/normal (fill "0").

**3. Specific Category/Code Fields (Position, Location, Type):**
   - Applies to fields whose meaning is a preset category or code, such as "Left ovary position", "Uteroscaral ligament nodules - location", "Pouch of Douglas obliteration status".
   - **Rule:** Find and extract the **exact matching** category code (usually a number `1`, `2`, `3`, etc.) or specific categorical term (like `Left`, `Right`, `Both`, `Partial`, `Complete`) from the report images. If it's not explicitly mentioned in the report, please fill in `"0"`.
   - **Example:**
     ```json
     "Left ovary position": "1",      
     "Right ovary position": "3",     
     "Uteroscaral ligament nodules - location": "0", 
     "Pouch of Douglas obliteration status": "2" 
     ```
     * **Important:** For situations requiring mapping (e.g., Complete -> "2"), strictly follow the implicit or explicit mapping rules. If the rules are unclear, prioritize extracting the original text. However, based on our previous agreement, use the number if it can be mapped to a number. If the original text is text with no numeric mapping, use the text; if not mentioned, use "0".

**4. Descriptive Text Fields (Comments, Description, Features):**
   - Applies to fields containing "comments", "description", "features (free text)", "Other salient findings", etc., which require a textual description.
   - **Rule:** **Accurately copy** the relevant original description from the report images. Pay attention to preserving the original text, including medical terminology and possible abbreviations. If no corresponding descriptive information is found in the report, set the field value to an **empty string `""`**.
   - **Example:**
     ```json
     "Fibroid description": "9mm intramural anterior fundus", 
     "Adnexa comments": "Small left paratubal cyst noted.", 
     "Uterine anatomy comments": "", 
     "Other salient findings (free text)": "Incidental finding of small renal cyst on right kidney upper pole seen on edge of image.",
     "Rectum and Colon lesion features (free text)": "" 
     ```

**General Instructions:**

* **Accuracy:** Extract information as accurately as possible, especially numerical values and key terms. Pay attention to any circles, marks, or arrows in the report.
* **Completeness:** Ensure the JSON output includes **all fields** from the template, and assign a value to each field according to the rules above (`"0"`, `"1"`, a numeric string, an original description string, or `""`).
* **Source:** All extracted information must be **directly sourced** from the provided report images. Do not make any external inferences or assumptions.
* **Format:** The output must be a **single, complete, and strictly correctly formatted** JSON object. Please ensure your response strictly adheres to the JSON format and only contains the JSON object itself, without any additional text, explanations, or Markdown tags.

Please begin extraction.
"""

# --- Main Function ---
def main(report_id, provider_name, model_id): 
    """
    Main processing logic for a single report using a specific LLM.
    """
    report_id_formatted = report_id[:3] + " " + report_id[3:] 
    model_name_slug = model_id.replace('/', '_').replace(':', '_')

    image_folder = config.PROCESSED_IMAGES_DIR      
    template_path = config.TEMPLATE_JSON_PATH      
    output_folder = config.get_extracted_json_raw_dir(provider_name, model_name_slug)

    try:
        os.makedirs(output_folder, exist_ok=True)
    except Exception as e:
        print(f"Error: Could not create output directory '{output_folder}' for {provider_name}/{model_name_slug}: {e}")
        raise 

    image_paths = [
        os.path.join(image_folder, f"{report_id_formatted}_page_{i}.png")
        for i in range(config.PAGES_PER_REPORT)
    ]
    base64_images = []
    for img_path in image_paths:
        encoded_image = encode_image(img_path)
        if encoded_image:
            base64_images.append(encoded_image)

    if not base64_images:
        print(f"Error: No valid image files found or could be encoded for report {report_id_formatted}.")
        raise FileNotFoundError(f"No valid images found or could be encoded for report {report_id_formatted} in {image_folder}")
        
    print(f"Loaded {len(base64_images)} image files for report {report_id_formatted} for processing.")

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            json_template = json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON template file not found: {template_path}")
        raise 
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON template file {template_path}: {e}")
        raise 
        
    json_template_str = json.dumps(json_template, indent=config.JSON_INDENT, ensure_ascii=config.ENSURE_ASCII)
    prompt = generate_prompt(json_template_str)
    llm_client = get_llm_client(provider_name, model_id)
    output_file = os.path.join(output_folder, f"{report_id_formatted}_extracted_data.json")

    try:
        print(f"Sending request to {provider_name.capitalize()} API ({model_id}) for report: {report_id_formatted}...")
        extracted_data = llm_client.extract_data(prompt, base64_images)
        
        print(f"{provider_name.capitalize()} API request successful. Processing response...")
        if not isinstance(extracted_data, dict): 
            print(f"Error: Data returned from {provider_name.capitalize()} is not a valid JSON object (dictionary). Received type: {type(extracted_data)}")
            raise ValueError(f"LLM ({provider_name}/{model_id}) did not return a valid JSON object (dictionary).")

        extracted_data["Report ID"] = report_id_formatted 

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(extracted_data, f, indent=config.JSON_INDENT, ensure_ascii=config.ENSURE_ASCII)
        print(f"Extracted information has been successfully saved to: {output_file}")

    except Exception as e:
        print(f"A critical error occurred while calling the {provider_name.capitalize()} API ({model_id}) or processing its response: {e}")
        raise 

# --- Script Execution Block ---
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"Usage: python {os.path.basename(__file__)} <report_id> <provider_name> <model_id>")
        print("Example: python api_interaction.py RRI002 openai gpt-4o")
        sys.exit(1)
    
    report_id_arg = sys.argv[1]
    provider_name_arg = sys.argv[2]
    model_id_arg = sys.argv[3] 
    
    try:
        main(report_id_arg, provider_name_arg, model_id_arg)
        print(f"\nAPI interaction for report {report_id_arg} ({provider_name_arg.capitalize()}/{model_id_arg}) completed.")
    except Exception as e:
        print(f"\nAn error occurred while processing report {report_id_arg} ({provider_name_arg.capitalize()}/{model_id_arg}). API interaction aborted.")
        sys.exit(1)

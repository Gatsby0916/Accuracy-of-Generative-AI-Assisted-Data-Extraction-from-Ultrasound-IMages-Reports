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
        print(f"错误：编码时图像文件未找到: {image_path}")
        return None
    except Exception as e:
        print(f"编码图像 {image_path} 时发生错误: {e}")
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
            print("错误: openai Python包未安装。请运行 'pip install openai'")
            sys.exit(1)
        except Exception as e:
            print(f"OpenAI客户端初始化错误: {e}")
            sys.exit(1)

    def extract_data(self, prompt_text, base64_images):
        content_payload = [{"type": "text", "text": prompt_text}]
        for img_b64 in base64_images:
            content_payload.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"}
            })
        
        print(f"正在向 OpenAI ({self.model_id}) 发送请求...")
        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": content_payload}],
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"} # Specific to some OpenAI models like gpt-4-turbo
            )
            response_content = response.choices[0].message.content
            if not isinstance(response_content, str):
                 print(f"错误: OpenAI响应内容不是字符串。收到: {type(response_content)}")
                 raise ValueError("OpenAI response content is not a string.")
            return json.loads(response_content)
        except Exception as e:
            print(f"OpenAI API调用或响应处理错误: {e}")
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
            print("错误: google-generativeai Python包未安装。请运行 'pip install google-generativeai'")
            sys.exit(1)
        except Exception as e:
            print(f"Gemini客户端初始化错误: {e}")
            sys.exit(1)

    def extract_data(self, prompt_text, base64_images):
        prompt_parts = [prompt_text]
        for img_b64 in base64_images:
            prompt_parts.append({"mime_type": "image/png", "data": img_b64})

        print(f"正在向 Gemini ({self.model_id}) 发送请求...")
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
                    print("错误: Gemini响应中未找到有效的JSON文本。")
                    print(f"Gemini原始响应 (部分): {str(response)[:500]}...") 
                    raise ValueError("Could not extract JSON text from Gemini response.")
            
            return json.loads(json_text)
        except json.JSONDecodeError as json_err:
            print(f"Gemini JSON解码错误: {json_err}")
            print(f"收到的非JSON文本: {json_text[:500] if 'json_text' in locals() else 'N/A'}...")
            raise
        except Exception as e:
            print(f"Gemini API调用或响应处理错误: {e}")
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
            print("错误: anthropic Python包未安装。请运行 'pip install anthropic'")
            sys.exit(1)
        except Exception as e:
            print(f"Claude客户端初始化错误: {e}")
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
        
        print(f"正在向 Claude ({self.model_id}) 发送请求...")
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
                print("错误: Claude响应中未找到有效的文本内容。")
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
            print(f"Claude JSON解码错误: {json_err}")
            # The error message from json_err (json_err.pos, json_err.msg) is usually very helpful.
            # The snippet below is a fallback if the full string was too long to easily inspect in logs.
            # However, with the full print above, this snippet becomes less critical for direct debugging.
            error_char_index = json_err.pos 
            context_window = 150 # Characters before and after the error point
            start_index = max(0, error_char_index - context_window)
            end_index = min(len(json_string_stripped), error_char_index + context_window)
            print(f"发生错误的文本片段 (位置 {error_char_index}):\n'{json_string_stripped[start_index:end_index]}'")
            raise
        except Exception as e:
            print(f"Claude API调用或响应处理错误: {e}")
            raise

# --- Factory Function to Get LLM Client ---
def get_llm_client(provider_name, model_id):
    """
    Factory function to get an instance of the appropriate LLM client.
    """
    if provider_name not in config.LLM_PROVIDERS:
        print(f"错误: 未知的LLM提供商 '{provider_name}'。请检查config.py。")
        sys.exit(1)

    provider_config = config.LLM_PROVIDERS[provider_name]
    api_key_env_var = provider_config["api_key_env"]
    api_key = os.getenv(api_key_env_var)
    
    max_tokens_setting = provider_config.get("max_tokens", 4000) 

    if not api_key:
        print(f"错误: 环境变量 {api_key_env_var} 未设置或未加载。请检查您的 .env 文件。")
        sys.exit(1)

    client_type = provider_config.get("client_name")
    if client_type == "openai":
        return OpenAIClient(api_key, model_id, max_tokens_setting)
    elif client_type == "gemini":
        return GeminiClient(api_key, model_id, max_tokens_setting)
    elif client_type == "claude":
        return ClaudeClient(api_key, model_id, max_tokens_setting)
    else:
        print(f"错误: 提供商 '{provider_name}' 的客户端类型 '{client_type}' 未实现。")
        sys.exit(1)

# --- Generic Prompt Generation ---
def generate_prompt(json_template_str):
    """
    Generates the detailed prompt for information extraction.
    """
    return f"""
# 任务目标
从提供的一系列 MRI 报告图像中精确提取信息，并严格按照下面提供的 JSON 模板结构和字段说明进行填充。最终输出必须是一个完整的、格式正确的 JSON 对象。

# JSON 输出模板
请将提取的信息填入以下 JSON 结构中。确保所有字段都被包含，并遵循每个字段的填写规则：
```json
{json_template_str}
```

# 详细填写规则与示例

请仔细阅读以下规则，并参考示例进行信息提取和格式化：

**1. 数值型字段 (Measurements, Sizes, Counts):**
   - 适用于字段名中包含 "(mm)", "(ml)", "thickness", "measurements", "size", "number", "count", "distance", "age" 等表示度量或计数的字段。
   - **规则:** 从报告图像中找到对应的**数字**值并填入。如果报告中未明确提及该数值，或者对应的结构不存在，请统一填写 `"0"`。
   - **示例:**
     ```json
     "Uterine Size (Body + Cervix - 3 planes in mm) - Length": "80", 
     "Left ovary measurements - Width (mm)": "19",
     "Endometrial thickness (Sag plane in mm to nearest mm)": "7",
     "Number of fibroids": "1", 
     "Right ovary -  No. follicles between 2 and 9 mm in diameter": "7", 
     "Abnormal junction zone thickening - Anterior (mm)": "9", 
     "Distance from anal verge length (mm)": "0" 
     ```

**2. 布尔型/状态型字段 (Yes/No, Presence/Absence, Identified/Not Identified, Status):**
   - 适用于字段名中包含 "identified", "presence of", "status", 或明确表示“是/否”判断的字段。
   - **规则:**
     - 如果报告图像明确指出该情况为 **"Yes", "Present", "Identified", "Positive", "Active", "Complete", "Conventional", "Normal"** 或其他类似的**肯定**描述，请填写 `"1"`。
     - 如果报告图像明确指出为 **"No", "Absent", "Not identified", "Negative", "Inactive"** 或其他类似的**否定**描述，或者该项在报告中**完全没有被提及**，请统一填写 `"0"`。
   - **示例:**
     ```json
     "Presence of Uterus": "1",        
     "Fibroids identified": "1",          
     "Kissing ovaries identified": "0",   
     "Hematosalpinx identified": "0",     
     "Presence of Adenomyosis": "1",      
     "Submucosal fibroids identified": "0", 
     "Uterovesical region status": "0"    
     ```
     * **特别注意:** 对于 'status' 类字段，请仔细判断报告中的描述是肯定异常状态（填 "1"）还是否定异常状态/正常（填 "0"）。

**3. 特定分类/编码字段 (Position, Location, Type):**
   - 适用于字段含义是预设分类或编码的字段，例如 "Left ovary position", "Uteroscaral ligament nodules - location", "Pouch of Douglas obliteration status"。
   - **规则:** 从报告图像中找到并提取**完全匹配**的分类代码（通常是数字 `1`, `2`, `3` 等）或特定的分类术语（如 `Left`, `Right`, `Both`, `Partial`, `Complete`）。如果报告中未明确提及，请填写 `"0"`。
   - **示例:**
     ```json
     "Left ovary position": "1",      
     "Right ovary position": "3",     
     "Uteroscaral ligament nodules - location": "0", 
     "Pouch of Douglas obliteration status": "2" 
     ```
     * **重要:** 对于需要映射的情况（如 Complete -> "2"），请严格按照隐含的或明确的映射规则。如果规则不清晰，请优先提取原文。但根据我们之前的约定，如果能映射为数字就用数字。如果原文是文本且无数字映射，则用文本，若未提及则用 "0"。

**4. 描述性文本字段 (Comments, Description, Features):**
   - 适用于字段名中包含 "comments", "description", "features (free text)", "Other salient findings" 等需要文字描述的字段。
   - **规则:** 从报告图像中**准确复制**相关的原文描述。注意保持文本的原貌，包括医学术语和可能的缩写。如果报告中没有找到对应的描述信息，请将该字段值设为**空字符串 `""`**。
   - **示例:**
     ```json
     "Fibroid description": "9mm intramural anterior fundus", 
     "Adnexa comments": "Small left paratubal cyst noted.", 
     "Uterine anatomy comments": "", 
     "Other salient findings (free text)": "Incidental finding of small renal cyst on right kidney upper pole seen on edge of image.",
     "Rectum and Colon lesion features (free text)": "" 
     ```

**通用指令:**

* **精确性:** 尽可能精确地提取信息，特别是数值和关键术语。注意报告中可能存在的圈阅、标记或箭头指示。
* **完整性:** 确保 JSON 输出包含模板中的**所有字段**，并根据上述规则赋予每个字段一个值 (`"0"`, `"1"`, 数字字符串, 原文描述字符串, 或 `""`)。
* **来源:** 所有提取的信息必须**直接来源于**提供的报告图像。不要做任何外部推断或假设。
* **格式:** 输出必须是**单一、完整且格式严格正确**的 JSON 对象。请确保您的回复严格遵循JSON格式，并且只包含JSON对象本身，不要有任何额外的文本、解释或Markdown标记。

请开始提取。
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
        print(f"错误：为 {provider_name}/{model_name_slug} 创建输出目录 '{output_folder}' 时出错: {e}")
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
        print(f"错误：未找到或无法编码报告 {report_id_formatted} 的任何有效图像文件。")
        raise FileNotFoundError(f"No valid images found or could be encoded for report {report_id_formatted} in {image_folder}")
        
    print(f"已为报告 {report_id_formatted} 加载 {len(base64_images)} 个图像文件进行处理。")

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            json_template = json.load(f)
    except FileNotFoundError:
        print(f"错误：JSON模板文件未找到: {template_path}")
        raise 
    except json.JSONDecodeError as e:
        print(f"错误：解析JSON模板文件 {template_path} 时出错: {e}")
        raise 
        
    json_template_str = json.dumps(json_template, indent=config.JSON_INDENT, ensure_ascii=config.ENSURE_ASCII)
    prompt = generate_prompt(json_template_str)
    llm_client = get_llm_client(provider_name, model_id)
    output_file = os.path.join(output_folder, f"{report_id_formatted}_extracted_data.json")

    try:
        print(f"正在向 {provider_name.capitalize()} API ({model_id}) 发送请求 (报告: {report_id_formatted})...")
        extracted_data = llm_client.extract_data(prompt, base64_images)
        
        print(f"{provider_name.capitalize()} API 请求成功。正在处理响应...")
        if not isinstance(extracted_data, dict): 
            print(f"错误: {provider_name.capitalize()} 返回的数据不是有效的JSON对象（字典）。收到类型: {type(extracted_data)}")
            raise ValueError(f"LLM ({provider_name}/{model_id}) did not return a valid JSON object (dictionary).")

        extracted_data["Report ID"] = report_id_formatted 

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(extracted_data, f, indent=config.JSON_INDENT, ensure_ascii=config.ENSURE_ASCII)
        print(f"提取的信息已成功保存到: {output_file}")

    except Exception as e:
        print(f"调用 {provider_name.capitalize()} API ({model_id}) 或处理其响应时发生严重错误: {e}")
        raise 

# --- Script Execution Block ---
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"用法: python {os.path.basename(__file__)} <report_id> <provider_name> <model_id>")
        print("示例: python api_interaction.py RRI002 openai gpt-4o")
        sys.exit(1)
    
    report_id_arg = sys.argv[1]
    provider_name_arg = sys.argv[2]
    model_id_arg = sys.argv[3] 
    
    try:
        main(report_id_arg, provider_name_arg, model_id_arg)
        print(f"\n报告 {report_id_arg} ({provider_name_arg.capitalize()}/{model_id_arg}) 的API交互处理完成。")
    except Exception as e:
        print(f"\n处理报告 {report_id_arg} ({provider_name_arg.capitalize()}/{model_id_arg}) 时发生错误，API交互中止。")
        sys.exit(1)

import sys
import base64
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
import config # <--- 导入 config 模块

# --- Load Environment Variables ---
dotenv_path = os.path.join(config.PROJECT_ROOT, '.env') # <--- 使用 config.PROJECT_ROOT
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print(f"成功加载 .env 文件: {dotenv_path}")
else:
    print(f"警告: .env 文件未在预期位置找到: {dotenv_path}. 将尝试从系统环境变量加载。")
    load_dotenv()

# --- Get API Key ---
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("错误：环境变量 OPENAI_API_KEY 未设置或未加载。")
    sys.exit(1)

client = OpenAI(api_key=api_key)

# project_root defined in config, no need to redefine here

# Function: Encode image to base64 (no changes needed in function itself)
def encode_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    except FileNotFoundError:
        print(f"错误：编码时图像文件未找到: {image_path}")
        return None

def main(report_id):
    report_id_formatted = report_id[:3] + " " + report_id[3:]

    # --- Use Paths from config ---
    image_folder = config.PROCESSED_IMAGES_DIR # <--- 使用 config
    template_path = config.TEMPLATE_JSON_PATH # <--- 使用 config
    output_folder = config.EXTRACTED_JSON_RAW_DIR # <--- 使用 config

    # --- Prepare Image Data ---
    # Use PAGES_PER_REPORT from config
    image_paths = [os.path.join(image_folder, f"{report_id_formatted}_page_{i}.png") for i in range(config.PAGES_PER_REPORT)] # <--- 使用 config

    base64_images = []
    valid_image_paths = []
    for img_path in image_paths:
        encoded_image = encode_image(img_path)
        if encoded_image:
            base64_images.append(encoded_image)
            valid_image_paths.append(img_path)

    if not base64_images:
        print(f"错误：未找到或无法编码报告 {report_id_formatted} 的任何有效图像文件。")
        sys.exit(1)
    print(f"已加载 {len(base64_images)} 个图像文件进行处理。")

    # --- Load JSON Template ---
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            json_template = json.load(f)
    except FileNotFoundError:
        print(f"错误：JSON 模板文件未找到: {template_path}")
        sys.exit(1)
    # Use formatting constants from config
    json_template_str = json.dumps(json_template, indent=config.JSON_INDENT, ensure_ascii=config.ENSURE_ASCII) # <--- 使用 config

    # --- Construct Prompt (Detailed Version) ---
    prompt = f"""
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
     "Abnormal junction zone thickening - Anterior (mm)": "9", // 直接填数字 9 或 9.0 均可，模型倾向于整数则填 "9"
     "Distance from anal verge length (mm)": "0" // 报告未提及距离，填 "0"
     ```

**2. 布尔型/状态型字段 (Yes/No, Presence/Absence, Identified/Not Identified, Status):**
   - 适用于字段名中包含 "identified", "presence of", "status", 或明确表示“是/否”判断的字段。
   - **规则:**
     - 如果报告图像明确指出该情况为 **"Yes", "Present", "Identified", "Positive", "Active", "Complete", "Conventional", "Normal"** 或其他类似的**肯定**描述，请填写 `"1"`。
     - 如果报告图像明确指出为 **"No", "Absent", "Not identified", "Negative", "Inactive"** 或其他类似的**否定**描述，或者该项在报告中**完全没有被提及**，请统一填写 `"0"`。
   - **示例:**
     ```json
     "Presence of Uterus": "1",          // 报告通常会写 Uterus: Present
     "Fibroids identified": "1",           // 报告提及发现子宫肌瘤
     "Kissing ovaries identified": "0",    // 报告未提及或写 No kissing ovaries
     "Hematosalpinx identified": "0",      // 报告提及 No hematosalpinx 或未提及
     "Presence of Adenomyosis": "1",       // 报告诊断有 Adenomyosis
     "Submucosal fibroids identified": "0", // 报告没有专门提到 Submucosal 类型，或明确说无
     "Uterovesical region status": "0"     // 报告描述为 Normal，根据规则映射为 "0" (因为 Normal 意味着没有异常发现，是“否定”异常)
                                          // 或者如果明确要区分 Normal 和 Absent，需要调整规则，但目前按 0 处理
     ```
     * **特别注意:** 对于 'status' 类字段，请仔细判断报告中的描述是肯定异常状态（填 "1"）还是否定异常状态/正常（填 "0"）。

**3. 特定分类/编码字段 (Position, Location, Type):**
   - 适用于字段含义是预设分类或编码的字段，例如 "Left ovary position", "Uteroscaral ligament nodules - location", "Pouch of Douglas obliteration status"。
   - **规则:** 从报告图像中找到并提取**完全匹配**的分类代码（通常是数字 `1`, `2`, `3` 等）或特定的分类术语（如 `Left`, `Right`, `Both`, `Partial`, `Complete`）。如果报告中未明确提及，请填写 `"0"`。
   - **示例:**
     ```json
     "Left ovary position": "1",       // 报告中标注或描述为位置 1
     "Right ovary position": "3",      // 报告中标注或描述为位置 3
     "Uteroscaral ligament nodules - location": "0", // 报告未提及位置，填 "0"
     "Pouch of Douglas obliteration status": "2" // 报告描述为 Complete，假设映射为 "2"
     ```
     * **重要:** 对于需要映射的情况（如 Complete -> "2"），请严格按照隐含的或明确的映射规则。如果规则不清晰，请优先提取原文。但根据我们之前的约定，如果能映射为数字就用数字。如果原文是文本且无数字映射，则用文本，若未提及则用 "0"。

**4. 描述性文本字段 (Comments, Description, Features):**
   - 适用于字段名中包含 "comments", "description", "features (free text)", "Other salient findings" 等需要文字描述的字段。
   - **规则:** 从报告图像中**准确复制**相关的原文描述。注意保持文本的原貌，包括医学术语和可能的缩写。如果报告中没有找到对应的描述信息，请将该字段值设为**空字符串 `""`**。
   - **示例:**
     ```json
     "Fibroid description": "9mm intramural anterior fundus", 
     "Adnexa comments": "Small left paratubal cyst noted.", 
     "Uterine anatomy comments": "", // 报告中未对子宫解剖结构做额外评论
     "Other salient findings (free text)": "Incidental finding of small renal cyst on right kidney upper pole seen on edge of image.",
     "Rectum and Colon lesion features (free text)": "" // 未描述相关特征
     ```

**通用指令:**

* **精确性:** 尽可能精确地提取信息，特别是数值和关键术语。注意报告中可能存在的圈阅、标记或箭头指示。
* **完整性:** 确保 JSON 输出包含模板中的**所有字段**，并根据上述规则赋予每个字段一个值 (`"0"`, `"1"`, 数字字符串, 原文描述字符串, 或 `""`)。
* **来源:** 所有提取的信息必须**直接来源于**提供的报告图像。不要做任何外部推断或假设。
* **格式:** 输出必须是**单一、完整且格式严格正确**的 JSON 对象。

请开始提取。
"""



    # --- Construct API Message Content ---
    content = [{"type": "text", "text": prompt}]
    for base64_image in base64_images:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}})

    # --- Define Output Path ---
    os.makedirs(output_folder, exist_ok=True)
    output_file = os.path.join(output_folder, f"{report_id_formatted}_extracted_data.json")

    # --- Send API Request ---
    try:
        print(f"正在向 OpenAI API 发送请求 (报告: {report_id_formatted})...")
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL_NAME, # <--- 使用 config
            messages=[{"role": "user", "content": content}],
            max_tokens=config.MAX_TOKENS, # <--- 使用 config
            response_format={"type": "json_object"}
        )
        print("API 请求成功。正在处理响应...")
        extracted_data = json.loads(response.choices[0].message.content)
        extracted_data["Report ID"] = report_id_formatted

        # --- Save Output ---
        with open(output_file, "w", encoding="utf-8") as f:
             # Use formatting constants from config
            json.dump(extracted_data, f, indent=config.JSON_INDENT, ensure_ascii=config.ENSURE_ASCII) # <--- 使用 config
        print(f"提取的信息已保存到: {output_file}")

    except Exception as e:
        print(f"调用 OpenAI API 或处理响应时发生错误: {e}")
        raise

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"用法: python {os.path.basename(__file__)} <report_id>")
        sys.exit(1)
    report_id_arg = sys.argv[1]
    try:
        main(report_id_arg)
        print(f"\n报告 {report_id_arg} 处理完成。")
    except Exception as e:
        print(f"\n处理报告 {report_id_arg} 时发生错误，已中止。")
        sys.exit(1)

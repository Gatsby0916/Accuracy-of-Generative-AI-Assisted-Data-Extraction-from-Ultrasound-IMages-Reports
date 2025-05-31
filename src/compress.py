from PIL import Image
import os

def compress_png(input_path, output_path, target_size_mb=4.5, quality=85, resize_factor=0.8):
    """
    尝试压缩PNG图片以满足目标大小。
    会先尝试优化，然后尝试调整尺寸。

    :param input_path: 输入图片路径
    :param output_path: 输出图片路径 (如果和input_path相同，则覆盖原文件)
    :param target_size_mb: 目标文件大小上限 (MB)
    :param quality: 主要用于转换为JPEG时的质量，对于PNG优化意义不大，但保留参数
    :param resize_factor: 如果需要调整尺寸，使用的缩放比例 (例如0.7表示缩小到70%)
    """
    try:
        img = Image.open(input_path)
        original_size_bytes = os.path.getsize(input_path)
        target_size_bytes = target_size_mb * 1024 * 1024

        print(f"原始图片 '{input_path}' 大小: {original_size_bytes / (1024*1024):.2f} MB")

        # 步骤1: 先尝试优化保存
        # 注意：如果 output_path 和 input_path 相同，这里会覆盖原图
        img.save(output_path, optimize=True)
        current_size_bytes = os.path.getsize(output_path)
        print(f"仅优化后图片 '{output_path}' 大小: {current_size_bytes / (1024*1024):.2f} MB")

        # 步骤2: 如果仅优化后仍然过大，则基于原始图片进行尺寸调整并再次保存
        if current_size_bytes > target_size_bytes:
            print(f"图片 '{output_path}' (仅优化后) 仍然大于 {target_size_mb} MB ({current_size_bytes / (1024*1024):.2f} MB)，将尝试调整尺寸...")
            
            # 重新加载原始图片进行尺寸调整，以避免基于已优化（可能已改变）的图片操作
            # 或者，如果img对象未被save操作改变很多（对于PNG通常是这样），也可以直接用img
            img_for_resize = Image.open(input_path) # 确保从最原始的状态开始resize
            original_width, original_height = img_for_resize.size
            
            new_width = int(original_width * resize_factor)
            new_height = int(original_height * resize_factor)

            # 确保至少有一个像素的宽度和高度
            if new_width < 1: new_width = 1
            if new_height < 1: new_height = 1
            
            print(f"将尺寸从 {original_width}x{original_height} 调整到 {new_width}x{new_height} (缩放因子: {resize_factor})")

            resized_img = img_for_resize.resize((new_width, new_height), Image.Resampling.LANCZOS)
            resized_img.save(output_path, optimize=True) # 再次保存，覆盖之前的版本
            current_size_bytes = os.path.getsize(output_path)
            print(f"调整尺寸并优化后图片 '{output_path}' 大小: {current_size_bytes / (1024*1024):.2f} MB")

        if current_size_bytes <= target_size_bytes:
            print(f"图片 '{output_path}' 已成功处理，当前大小符合目标。")
        else:
            print(f"警告：所有尝试后，图片 '{output_path}' 大小仍为 {current_size_bytes / (1024*1024):.2f} MB。")
            print(f"可能需要更小的 resize_factor (当前为 {resize_factor}) 或其他手动处理方法。")

        return True

    except FileNotFoundError:
        print(f"错误：文件未找到 {input_path}")
        return False
    except Exception as e:
        print(f"压缩图片时发生错误 ({input_path}): {e}")
        return False

# --- 如何使用 ---
if __name__ == "__main__":
    # --- 用户配置区域 ---

    # 1. 指定要压缩的报告ID中的页面号。
    #    根据之前的API错误 'messages.0.content.2.image...'，索引为2的图像是问题图像。
    #    如果图像是从 page_0.png 开始编号的，那么索引2对应 page_2.png。
    page_number_to_compress = "0"  # <--- 请确认并修改这个页码 (例如 "0", "1", "2", 或 "3")

    # 2. 基础路径和报告ID（文件名中带空格）
    base_path = r"C:\Users\李海毅\Desktop\ultrasound\LLM-test\results\processed_images"
    report_id_in_filename = "RRI 449"  # <--- 这是文件名中的部分，例如 "RRI 416"

    # 3. 调整压缩参数
    # Claude API 限制 5MB，目标设为4.5MB留有余地。
    # 如果图片在“仅优化后”仍然大于 target_size_mb，将会使用此 resize_factor。
    # 如果0.7还是太大，尝试0.6, 0.5等。
    compression_resize_factor = 0.2  # <--- 调整这个缩放因子

    # --- 配置结束 ---


    # 构建输入和输出文件的完整路径
    input_filename = f"{report_id_in_filename}_page_{page_number_to_compress}.png"
    input_image_path = os.path.join(base_path, input_filename)
    
    # 输出路径与输入路径相同，表示直接覆盖原文件
    # !!! 重要：如果您想保留原始大文件，请在运行此脚本前手动备份它 !!!
    output_image_path = input_image_path 

    if os.path.exists(input_image_path):
        print(f"准备处理图片: {input_image_path}")
        if input_image_path == output_image_path:
            print("输出路径与输入路径相同，将会直接覆盖原文件。")
            # backup_path = input_image_path + ".backup" # 可选：创建备份
            # import shutil
            # shutil.copy2(input_image_path, backup_path)
            # print(f"已备份原始文件到: {backup_path}")
        
        compress_png(input_image_path, output_image_path, 
                       target_size_mb=4.5, 
                       resize_factor=compression_resize_factor)
    else:
        print(f"错误：输入文件 '{input_image_path}' 不存在。请仔细检查配置的页码和路径。")
from pdf2image import convert_from_path
import os
import sys
import config # <--- 导入 config 模块

# project_root defined in config, no need to redefine here

# --- Use Paths from config ---
# Use the default scan directory defined in config
# This could also be made a command-line argument for more flexibility
pdf_folder = config.DEFAULT_PDF_SCAN_DIR # <--- 使用 config
output_dir = config.PROCESSED_IMAGES_DIR # <--- 使用 config

def convert_pdfs_to_images(source_dir, target_dir):
    """Converts all PDFs in source_dir to PNG images in target_dir."""
    if not os.path.isdir(source_dir):
        print(f"错误：PDF 源文件夹未找到: {source_dir}")
        return False # Indicate failure

    os.makedirs(target_dir, exist_ok=True)
    print(f"PDF 源文件夹: {source_dir}")
    print(f"图像输出文件夹: {target_dir}")

    processed_count = 0
    error_count = 0
    skipped_count = 0

    try:
        # Consider defining the range in config if it's fixed, otherwise process all found PDFs
        # For now, let's process all PDFs found in the directory
        pdf_files = [f for f in os.listdir(source_dir) if f.lower().endswith(".pdf")]
        print(f"在源目录中找到 {len(pdf_files)} 个 PDF 文件。")

        for pdf_file in pdf_files:
            pdf_path = os.path.join(source_dir, pdf_file)
            print(f"\n正在处理: {pdf_path} ...")
            try:
                images = convert_from_path(pdf_path) # Add poppler_path if needed: poppler_path=config.POPPLER_PATH
                pdf_name_base = os.path.splitext(pdf_file)[0] # Get filename without extension

                for idx, image in enumerate(images):
                    image_name = f'{pdf_name_base}_page_{idx}.png'
                    image_save_path = os.path.join(target_dir, image_name)
                    image.save(image_save_path, 'PNG')

                print(f"成功转换 {len(images)} 页。")
                processed_count += 1
            except Exception as e:
                print(f"!! 处理 {pdf_file} 时出错: {e}")
                error_count += 1
        
        print(f"\n处理完成。成功转换 {processed_count} 个 PDF 文件，发生 {error_count} 个错误。")
        return True # Indicate success

    except Exception as e:
        print(f"扫描或处理 PDF 文件时发生意外错误: {e}")
        return False # Indicate failure


if __name__ == "__main__":
    # This script is often run standalone for preprocessing
    # You might want command-line arguments here too, e.g., for source/target dirs
    success = convert_pdfs_to_images(pdf_folder, output_dir)
    if not success:
        sys.exit(1)

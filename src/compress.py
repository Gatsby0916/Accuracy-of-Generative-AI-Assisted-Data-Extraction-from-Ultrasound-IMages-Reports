from PIL import Image
import os

def compress_png(input_path, output_path, target_size_mb=4.5, quality=85, resize_factor=0.8):
    """
    Tries to compress a PNG image to meet a target size.
    It will first try to optimize, then try to resize.

    :param input_path: Input image path
    :param output_path: Output image path (if same as input_path, the original file will be overwritten)
    :param target_size_mb: Target file size limit (MB)
    :param quality: Mainly used for quality when converting to JPEG, less significant for PNG optimization, but the parameter is kept
    :param resize_factor: The scaling factor to use if resizing is needed (e.g., 0.8 means scale to 80%)
    """
    try:
        img = Image.open(input_path)
        original_size_bytes = os.path.getsize(input_path)
        target_size_bytes = target_size_mb * 1024 * 1024

        print(f"Original image '{input_path}' size: {original_size_bytes / (1024*1024):.2f} MB")

        # Step 1: First, try to save with optimization
        # Note: If output_path is the same as input_path, the original file will be overwritten here
        img.save(output_path, optimize=True)
        current_size_bytes = os.path.getsize(output_path)
        print(f"Image size after optimization only '{output_path}': {current_size_bytes / (1024*1024):.2f} MB")

        # Step 2: If it's still too large after optimization only, resize based on the original image and save again
        if current_size_bytes > target_size_bytes:
            print(f"Image '{output_path}' (after optimization only) is still larger than {target_size_mb} MB ({current_size_bytes / (1024*1024):.2f} MB), attempting to resize...")
            
            # Reload the original image for resizing to avoid operating on the potentially altered optimized image
            # Alternatively, if the img object was not significantly changed by the save operation (as is often the case for PNGs), you can use img directly
            img_for_resize = Image.open(input_path) # Ensure resizing starts from the most original state
            original_width, original_height = img_for_resize.size
            
            new_width = int(original_width * resize_factor)
            new_height = int(original_height * resize_factor)

            # Ensure at least one pixel for width and height
            if new_width < 1: new_width = 1
            if new_height < 1: new_height = 1
            
            print(f"Resizing from {original_width}x{original_height} to {new_width}x{new_height} (scaling factor: {resize_factor})")

            resized_img = img_for_resize.resize((new_width, new_height), Image.Resampling.LANCZOS)
            resized_img.save(output_path, optimize=True) # Save again, overwriting the previous version
            current_size_bytes = os.path.getsize(output_path)
            print(f"Image size after resizing and optimizing '{output_path}': {current_size_bytes / (1024*1024):.2f} MB")

        if current_size_bytes <= target_size_bytes:
            print(f"Image '{output_path}' has been successfully processed, current size meets the target.")
        else:
            print(f"Warning: After all attempts, the size of image '{output_path}' is still {current_size_bytes / (1024*1024):.2f} MB.")
            print(f"A smaller resize_factor (current is {resize_factor}) or other manual methods may be needed.")

        return True

    except FileNotFoundError:
        print(f"Error: File not found {input_path}")
        return False
    except Exception as e:
        print(f"An error occurred while compressing the image ({input_path}): {e}")
        return False

# --- How to Use ---
if __name__ == "__main__":
    # --- User Configuration Area ---

    # 1. Specify the page number within the report ID to be compressed.
    #    Based on the previous API error 'messages.0.content.2.image...', the image at index 2 is the problematic one.
    #    If the images are numbered starting from page_0.png, then index 2 corresponds to page_2.png.
    page_number_to_compress = "0"  # <--- Please confirm and modify this page number (e.g., "0", "1", "2", or "3")

    # 2. Base path and Report ID (with a space in the filename)
    base_path = r"C:\Users\YourUser\Desktop\ultrasound\LLM-test\results\processed_images" #<- CHANGE THIS
    report_id_in_filename = "RRI 449"  # <--- This is the part in the filename, e.g., "RRI 416"

    # 3. Adjust Compression Parameters
    # The Claude API limit is 5MB, so the target is set to 4.5MB to leave some margin.
    # If the image is still larger than target_size_mb after "optimization only", this resize_factor will be used.
    # If 0.7 is still too large, try 0.6, 0.5, etc.
    compression_resize_factor = 0.2  # <--- Adjust this scaling factor

    # --- End of Configuration ---


    # Construct the full paths for input and output files
    input_filename = f"{report_id_in_filename}_page_{page_number_to_compress}.png"
    input_image_path = os.path.join(base_path, input_filename)
    
    # The output path is the same as the input path, meaning the original file will be overwritten
    # !!! Important: If you want to keep the original large file, please back it up manually before running this script !!!
    output_image_path = input_image_path 

    if os.path.exists(input_image_path):
        print(f"Preparing to process image: {input_image_path}")
        if input_image_path == output_image_path:
            print("Output path is the same as the input path; the original file will be overwritten.")
            # backup_path = input_image_path + ".backup" # Optional: create a backup
            # import shutil
            # shutil.copy2(input_image_path, backup_path)
            # print(f"Backed up original file to: {backup_path}")
        
        compress_png(input_image_path, output_image_path, 
                     target_size_mb=4.5, 
                     resize_factor=compression_resize_factor)
    else:
        print(f"Error: Input file '{input_image_path}' does not exist. Please double-check the configured page number and path.")

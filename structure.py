import os

def print_directory_structure(root_path, indent="", exclude_dirs=["venv", ".git", "__pycache__"]):
    """Recursively print directory tree, filtering out specified directories."""
    items = sorted(os.listdir(root_path))
    for index, item in enumerate(items):
        item_path = os.path.join(root_path, item)
        if os.path.isdir(item_path):
            if item in exclude_dirs:
                continue
            connector = "└──" if index == len(items) - 1 else "├──"
            print(f"{indent}{connector} {item}/")
            # 递归调用，缩进层级加深
            new_indent = indent + ("    " if index == len(items) - 1 else "│   ")
            print_directory_structure(item_path, new_indent, exclude_dirs)
        else:
            connector = "└──" if index == len(items) - 1 else "├──"
            print(f"{indent}{connector} {item}")

# 用法示例（请自行修改为所需路径）:
print_directory_structure("c:/Users/李海毅/Desktop/ultrasound/LLM-test")

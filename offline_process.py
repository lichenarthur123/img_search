import os
import shutil

def process_files(input_dir, output_dir):
    """
    处理输入文件夹中的文件：
    - 合并所有txt文件为desc.txt
    - 重命名图片文件为数字编号.png
    
    参数:
        input_dir: 输入文件夹路径
        output_dir: 输出文件夹路径
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 处理txt文件
    txt_content = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith('.txt'):
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    txt_content.append(f.read())
    
    # 写入合并的txt文件
    if txt_content:
        with open(os.path.join(output_dir, 'desc.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(txt_content))
    
    # 处理图片文件
    img_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')
    img_count = 0
    
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith(img_extensions):
                src_path = os.path.join(root, file)
                dst_path = os.path.join(output_dir, f"{img_count}.png")
                shutil.copy2(src_path, dst_path)
                img_count += 1
    
    return {
        'txt_file': os.path.join(output_dir, 'desc.txt') if txt_content else None,
        'image_count': img_count
    }
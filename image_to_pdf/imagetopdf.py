import os
from pathlib import Path
from PIL import Image

def readdirs(current_path=None):
    """获取当前目录下的所有子目录"""
    if current_path is None:
        current_path = Path(__file__).parent.resolve()
    else:
        current_path = Path(current_path)
    
    dirs = [d.name for d in current_path.iterdir() if d.is_dir()]
    print(f"目录列表: {dirs}")
    return dirs

def readfiles(directory):
    """获取指定目录下的所有文件"""
    dir_path = Path(directory)
    files = [f.name for f in dir_path.iterdir() if f.is_file()]
    print(f"文件列表: {files}")
    return files

def imagetopdf(dir_name, outpdf):
    """将目录中的图片转换为PDF"""
    current_path = Path(__file__).parent.resolve()
    folder_path = current_path / dir_name
    
    if not folder_path.exists():
        print(f"错误: 目录 {folder_path} 不存在")
        return
    
    # 获取所有图片文件
    image_extensions = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif')
    image_files = sorted([
        f for f in folder_path.iterdir() 
        if f.is_file() and f.suffix.lower() in image_extensions
    ])
    
    if not image_files:
        print(f"警告: {dir_name} 中没有找到图片文件")
        return
    
    print(f"找到 {len(image_files)} 张图片: {[f.name for f in image_files]}")
    
    # 转换所有图片为RGB模式并优化
    images = []
    for img_path in image_files:
        img = Image.open(img_path)
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        images.append(img)
    
    # 保存为PDF
    output_path = current_path / f"{outpdf}.pdf"
    images[0].save(
        output_path, 
        "PDF", 
        resolution=100.0, 
        save_all=True, 
        append_images=images[1:]
    )
    
    # 关闭图片以释放内存
    for img in images:
        img.close()
    
    print(f"成功生成 PDF: {output_path}")

if __name__ == '__main__':
    dirs = readdirs()
    print(f"共找到 {len(dirs)} 个目录")
    
    for dir_name in dirs:
        try:
            imagetopdf(dir_name, dir_name)
            print(f"✓ 完成: {dir_name}")
        except Exception as e:
            print(f"✗ 错误 ({dir_name}): {e}")

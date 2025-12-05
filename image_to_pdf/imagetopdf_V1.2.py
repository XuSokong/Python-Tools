import os
import io
from pathlib import Path
from PIL import Image
from concurrent.futures import ThreadPoolExecutor  # 用于并行处理图片

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

def process_image(img_path):
    """处理单张图片（转为RGB并压缩），返回处理后的图片对象"""
    try:
        # 使用内存缓冲减少IO操作
        with Image.open(img_path) as img:
            # 转换颜色模式
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # 压缩图片（根据需要调整质量参数）
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=90)  # 保留质量的同时减少体积
            buffer.seek(0)
            return Image.open(buffer)
    except Exception as e:
        print(f"处理图片 {img_path.name} 出错: {e}")
        return None

def imagetopdf(dir_name, outpdf):
    """将目录中的图片转换为PDF（优化版）"""
    current_path = Path(__file__).parent.resolve()
    folder_path = current_path / dir_name
    
    if not folder_path.exists():
        print(f"错误: 目录 {folder_path} 不存在")
        return
    
    # 获取所有图片文件（按文件名排序）
    image_extensions = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif')
    image_files = sorted([
        f for f in folder_path.iterdir() 
        if f.is_file() and f.suffix.lower() in image_extensions
    ])
    
    if not image_files:
        print(f"警告: {dir_name} 中没有找到图片文件")
        return
    
    print(f"找到 {len(image_files)} 张图片: {[f.name for f in image_files]}")
    
    # 并行处理图片（利用多核CPU提高效率）
    images = []
    with ThreadPoolExecutor() as executor:
        # 提交所有图片处理任务
        results = executor.map(process_image, image_files)
        
        # 过滤处理失败的图片
        for img in results:
            if img:
                images.append(img)
    
    if not images:
        print(f"错误: 所有图片处理失败")
        return
    
    # 保存为PDF（优化参数）
    output_path = current_path / f"{outpdf}.pdf"
    try:
        images[0].save(
            output_path, 
            "PDF", 
            resolution=150.0,  # 适度提高分辨率同时控制体积
            save_all=True, 
            append_images=images[1:],
            optimize=True,    # 启用PDF优化
            compress=True     # 压缩PDF内容
        )
        print(f"成功生成 PDF: {output_path}")
    except Exception as e:
        print(f"生成PDF失败: {e}")
    finally:
        # 确保所有图片都被关闭释放内存
        for img in images:
            img.close()

if __name__ == '__main__':
    dirs = readdirs()
    print(f"共找到 {len(dirs)} 个目录")
    
    # 对目录处理也进行并行优化（适用于多目录场景）
    with ThreadPoolExecutor() as executor:
        for dir_name in dirs:
            executor.submit(
                lambda d: imagetopdf(d, d), 
                dir_name
            )
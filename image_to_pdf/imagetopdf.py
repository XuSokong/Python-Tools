import os
import sys
import multiprocessing
from pathlib import Path
from PIL import Image

class Tee(object):
    """同时将输出发送到终端和文件"""
    def __init__(self, filename, mode='a'):
        self.file = open(filename, mode, encoding='utf-8')
        self.stdout = sys.stdout
        sys.stdout = self
    
    def __del__(self):
        sys.stdout = self.stdout
        self.file.close()
    
    def write(self, data):
        self.stdout.write(data)
        self.file.write(data)
        self.flush()
    
    def flush(self):
        self.stdout.flush()
        self.file.flush()

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
    
    try:
        if not folder_path.exists():
            print(f"错误: 目录 {folder_path} 不存在")
            return (dir_name, False)
        
        # 获取所有图片文件
        image_extensions = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif')
        image_files = sorted([
            f for f in folder_path.iterdir() 
            if f.is_file() and f.suffix.lower() in image_extensions
        ])
        
        if not image_files:
            print(f"警告: {dir_name} 中没有找到图片文件")
            return (dir_name, True)  # 没有图片也算成功处理
        
        print(f"找到 {len(image_files)} 张图片: {[f.name for f in image_files]}")
        
        # 转换所有图片为RGB模式并优化
        images = []
        for i, img_path in enumerate(image_files, 1):
            print(f"  处理图片 {i}/{len(image_files)}: {img_path.name}")
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
        return (dir_name, True)
    except Exception as e:
        print(f"处理 {dir_name} 时出错: {e}")
        return (dir_name, False)

if __name__ == '__main__':
    # 初始化日志文件
    log_file = 'jpgtopdg.log'
    tee = Tee(log_file, 'a')  # 使用'a'模式追加日志文件
    
    dirs = readdirs()
    total_dirs = len(dirs)
    print(f"共找到 {total_dirs} 个目录")
    
    if total_dirs == 0:
        print("没有找到任何目录，程序退出。")
        exit()
    
    # 获取CPU核心数量，设置进程池大小
    cpu_count = multiprocessing.cpu_count()
    pool_size = min(cpu_count, total_dirs)  # 最多使用CPU核心数或目录数（取较小值）
    print(f"使用 {pool_size} 个进程并行处理...")
    
    success_count = 0
    fail_count = 0
    failed_dirs = []
    
    # 创建进程池并处理目录
    with multiprocessing.Pool(pool_size) as pool:
        # 准备参数元组列表 (dir_name, dir_name)
        params = [(dir_name, dir_name) for dir_name in dirs]
        
        # 使用starmap并行处理，保持输入顺序
        for result in pool.starmap(imagetopdf, params):
            dir_name, status = result
            if status:
                print(f"✓ 完成: {dir_name}")
                success_count += 1
            else:
                print(f"✗ 失败: {dir_name}")
                fail_count += 1
                failed_dirs.append(dir_name)
    
    # 打印最终统计信息
    print(f"\n{'='*50}")
    print("处理完成统计:")
    print(f"总目录数: {total_dirs}")
    print(f"成功目录数: {success_count}")
    print(f"失败目录数: {fail_count}")
    
    if failed_dirs:
        print(f"失败的目录: {', '.join(failed_dirs)}")
    print(f"{'='*50}")
    
    # 清理日志
    del tee

import os

def readdirs():
    # 获取当前程序所在的绝对路径
    current_path = os.path.abspath(os.path.dirname(__file__))
    # 使用os.listdir获取指定目录下的所有文件和目录名
    dirs_and_files = os.listdir(current_path)
    dirs = []
    for item in dirs_and_files:
        if os.path.isdir(os.path.join(current_path, item)):
            dirs.append(item)
    print("目录列表:", dirs)
    return dirs

def readfiles(dir):
    files = []
    dirs_and_files = os.listdir(dir)
    for item in dirs_and_files:
        if os.path.isfile(os.path.join(dir, item)):
            files.append(item)
    print("文件列表:", files)
    return files
def imagetopdf(dir,outpdf):
    from PIL import Image
    # 获取当前程序所在的绝对路径
    current_path = os.path.abspath(os.path.dirname(__file__))
    folder_path = os.path.join(current_path, dir)
    # 获取文件夹下的所有图片文件
    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg','.webp'))]
    image_files.sort()  # 按文件名排序
    print(image_files)
    # 打开第一个图片作为封面
    cover = Image.open(os.path.join(folder_path, image_files[0]))
    # 创建PDF文件
    cover.save(outpdf + '.pdf', "PDF", resolution=100.0, save_all=True, append_images=[Image.open(os.path.join(folder_path, img)) for img in image_files[1:]])

if __name__ == '__main__':
    dir = readdirs()
    print(len(dir))
    for i in range(0,len(dir)):
        imagetopdf(dir[i],dir[i])
        print("finished ",dir[i])

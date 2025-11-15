# 图片转PDF工具

这个Python程序可以读取文件夹下的所有图片文件，并将它们合成为一个PDF文件。

## 功能特点

- 支持多种图片格式：JPG, JPEG, PNG, BMP, GIF, TIFF, WEBP
- 自动按文件名排序
- 自动处理透明背景（转换为白色背景）
- 支持命令行参数

## 安装依赖

```bash
pip install -r requirements.txt
```

或者直接安装：

```bash
pip install Pillow
```

## 使用方法

### 基本用法

```bash
# 将当前文件夹的图片转换为output.pdf
python img2pdf.py

# 指定图片文件夹和输出文件名
python img2pdf.py images output.pdf

# 使用完整路径
python img2pdf.py /path/to/images /path/to/output.pdf
```

### 命令行参数

```bash
python img2pdf.py [图片文件夹] [输出PDF文件名]
```

- `图片文件夹`：包含图片的文件夹路径（默认：当前文件夹）
- `输出PDF文件名`：生成的PDF文件名（默认：output.pdf）

### 示例

```bash
# 将images文件夹中的图片合成为document.pdf
python img2pdf.py images document.pdf

# 将当前文件夹的图片合成为my_photos.pdf
python img2pdf.py . my_photos.pdf
```

## 注意事项

- 图片会按照文件名自然排序
- 支持的图片格式：.jpg, .jpeg, .png, .bmp, .gif, .tiff, .webp
- 带透明通道的图片会自动转换为白色背景
- 确保文件夹中至少有一张有效的图片文件

## 代码说明

程序主要包含以下功能：

1. `get_image_files()` - 扫描文件夹获取所有图片文件
2. `images_to_pdf()` - 将图片列表转换为PDF
3. `main()` - 处理命令行参数并执行转换

## 许可

MIT License

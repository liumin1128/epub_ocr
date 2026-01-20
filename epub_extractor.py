#!/usr/bin/env python3
"""
EPUB 图片和OCR结果提取工具
将每一页的图片和OCR识别结果保存到独立文件夹中，便于复用
"""

import zipfile
import re
import os
import sys
from pathlib import Path

try:
    from PIL import Image
    import pytesseract
except ImportError:
    print("请先安装依赖:")
    print("  pip install Pillow pytesseract")
    print("  brew install tesseract tesseract-lang")
    exit(1)


def extract_all_images(epub_path: str, output_dir: str) -> list[tuple[int, str]]:
    """从EPUB中提取所有图片到指定目录"""
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    image_files = []
    
    with zipfile.ZipFile(epub_path, 'r') as epub:
        for name in epub.namelist():
            if name.lower().endswith(('.png', '.jpg', '.jpeg')):
                match = re.search(r'index-(\d+)', name)
                if match:
                    page_num = int(match.group(1))
                    data = epub.read(name)
                    ext = Path(name).suffix
                    output_path = os.path.join(images_dir, f"page_{page_num:04d}{ext}")
                    
                    with open(output_path, 'wb') as f:
                        f.write(data)
                    image_files.append((page_num, output_path))
    
    image_files.sort(key=lambda x: x[0])
    return image_files


def ocr_single_page(image_path: str, ocr_dir: str, page_num: int) -> str:
    """对单页进行OCR并保存结果"""
    ocr_file = os.path.join(ocr_dir, f"page_{page_num:04d}.txt")
    
    # 如果已经有OCR结果，直接读取
    if os.path.exists(ocr_file):
        with open(ocr_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    # 否则进行OCR识别
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang='chi_sim+eng')
        
        # 保存结果
        with open(ocr_file, 'w', encoding='utf-8') as f:
            f.write(text)
        
        return text
    except Exception as e:
        print(f"OCR失败: {e}")
        return ""


def process_pages(epub_path: str, output_dir: str, start_page: int = 1, end_page: int = 20):
    """处理指定范围的页面"""
    
    # 创建目录结构
    images_dir = os.path.join(output_dir, "images")
    ocr_dir = os.path.join(output_dir, "ocr")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(ocr_dir, exist_ok=True)
    
    print(f"输出目录: {output_dir}")
    print(f"  - 图片目录: {images_dir}")
    print(f"  - OCR目录:  {ocr_dir}")
    print()
    
    # 检查是否已经提取过图片
    existing_images = list(Path(images_dir).glob("page_*.png")) + list(Path(images_dir).glob("page_*.jpg"))
    
    if not existing_images:
        print("步骤1: 提取图片...")
        image_files = extract_all_images(epub_path, output_dir)
        print(f"  共提取 {len(image_files)} 张图片")
    else:
        print(f"步骤1: 图片已存在，共 {len(existing_images)} 张")
        # 构建图片列表
        image_files = []
        for img_path in sorted(existing_images):
            match = re.search(r'page_(\d+)', img_path.name)
            if match:
                page_num = int(match.group(1))
                image_files.append((page_num, str(img_path)))
        image_files.sort(key=lambda x: x[0])
    
    print()
    
    # OCR处理指定范围
    print(f"步骤2: OCR识别第 {start_page} - {end_page} 页...")
    print("-" * 50)
    
    processed = 0
    skipped = 0
    
    for page_num, img_path in image_files:
        if page_num < start_page or page_num > end_page:
            continue
        
        ocr_file = os.path.join(ocr_dir, f"page_{page_num:04d}.txt")
        
        if os.path.exists(ocr_file):
            print(f"  第 {page_num:3d} 页: [已存在] 跳过")
            skipped += 1
        else:
            print(f"  第 {page_num:3d} 页: OCR识别中...", end='', flush=True)
            text = ocr_single_page(img_path, ocr_dir, page_num)
            line_count = len(text.strip().split('\n')) if text.strip() else 0
            print(f" 完成 ({line_count} 行)")
            processed += 1
    
    print("-" * 50)
    print(f"完成! 新处理: {processed} 页, 跳过: {skipped} 页")
    print()
    print(f"OCR结果保存在: {ocr_dir}")
    print("可以直接查看 .txt 文件来分析章节结构")


def main():
    epub_path = "test.epub"
    output_dir = "epub_extracted"  # 提取结果保存目录
    
    # 解析命令行参数
    start_page = 1
    end_page = 20
    
    if len(sys.argv) >= 2:
        end_page = int(sys.argv[1])
    if len(sys.argv) >= 3:
        start_page = int(sys.argv[1])
        end_page = int(sys.argv[2])
    
    print("=" * 60)
    print("EPUB 图片和OCR提取工具")
    print("=" * 60)
    print(f"EPUB文件: {epub_path}")
    print(f"处理范围: 第 {start_page} - {end_page} 页")
    print()
    
    process_pages(epub_path, output_dir, start_page, end_page)


if __name__ == "__main__":
    main()

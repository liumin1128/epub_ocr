#!/usr/bin/env python3
"""
增强版EPUB图片提取和OCR识别
- 图像预处理提高OCR精度
- 结果持久化存储
"""

import zipfile
import re
import os
from pathlib import Path

try:
    from PIL import Image, ImageEnhance, ImageFilter
    import pytesseract
    import cv2
    import numpy as np
except ImportError as e:
    print("请先安装依赖:")
    print("  pip install Pillow pytesseract opencv-python numpy")
    exit(1)


def preprocess_image(image_path: str) -> Image.Image:
    """
    图像预处理，提高OCR识别率
    """
    # 使用OpenCV读取图片
    img = cv2.imread(image_path)
    
    # 1. 转灰度
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. 放大图片 (提高小字识别率)
    scale = 2
    height, width = gray.shape
    gray = cv2.resize(gray, (width * scale, height * scale), interpolation=cv2.INTER_CUBIC)
    
    # 3. 降噪
    gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    
    # 4. 自适应二值化 (处理光照不均)
    binary = cv2.adaptiveThreshold(
        gray, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 
        31, 10
    )
    
    # 5. 形态学操作 - 去除小噪点
    kernel = np.ones((1, 1), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    
    # 转回PIL格式
    return Image.fromarray(binary)


def ocr_image_enhanced(image_path: str) -> str:
    """
    增强版OCR识别
    """
    try:
        # 预处理图片
        processed_img = preprocess_image(image_path)
        
        # Tesseract配置
        # PSM 6: 假设为统一的文本块
        # OEM 3: 默认LSTM引擎
        config = '--psm 6 --oem 3 -c preserve_interword_spaces=1'
        
        text = pytesseract.image_to_string(
            processed_img, 
            lang='chi_sim+eng',
            config=config
        )
        return text
    except Exception as e:
        print(f"OCR失败: {e}")
        return ""


def extract_images_from_epub(epub_path: str, output_dir: str) -> list[tuple[int, str]]:
    """从EPUB中提取所有图片"""
    image_files = []
    os.makedirs(output_dir, exist_ok=True)
    
    with zipfile.ZipFile(epub_path, 'r') as epub:
        for name in epub.namelist():
            if name.lower().endswith(('.png', '.jpg', '.jpeg')):
                match = re.search(r'index-(\d+)', name)
                if match:
                    page_num = int(match.group(1))
                    data = epub.read(name)
                    ext = Path(name).suffix
                    output_path = os.path.join(output_dir, f"page_{page_num:04d}{ext}")
                    with open(output_path, 'wb') as f:
                        f.write(data)
                    image_files.append((page_num, output_path))
    
    image_files.sort(key=lambda x: x[0])
    return image_files


def process_pages(epub_path: str, output_base: str, start_page: int = 1, end_page: int = 20):
    """
    处理指定范围的页面
    """
    img_dir = os.path.join(output_base, "images")
    ocr_dir = os.path.join(output_base, "ocr_enhanced")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(ocr_dir, exist_ok=True)
    
    print("=" * 60)
    print("增强版 EPUB OCR 提取工具")
    print("=" * 60)
    print(f"文件: {epub_path}")
    print(f"处理范围: 第 {start_page} - {end_page} 页\n")
    
    # 检查图片是否已提取
    existing_images = list(Path(img_dir).glob("page_*.png")) + list(Path(img_dir).glob("page_*.jpg"))
    
    if not existing_images:
        print("步骤1: 提取图片...")
        image_files = extract_images_from_epub(epub_path, img_dir)
        print(f"  共提取 {len(image_files)} 张图片")
    else:
        print(f"步骤1: 使用已提取的图片 ({len(existing_images)} 张)")
        image_files = []
        for img_path in sorted(existing_images):
            match = re.search(r'page_(\d+)', img_path.name)
            if match:
                page_num = int(match.group(1))
                image_files.append((page_num, str(img_path)))
        image_files.sort(key=lambda x: x[0])
    
    print(f"\n步骤2: OCR识别 (增强模式)...")
    
    processed = 0
    for page_num, img_path in image_files:
        if page_num < start_page or page_num > end_page:
            continue
        
        ocr_file = os.path.join(ocr_dir, f"page_{page_num:04d}.txt")
        
        # 检查是否已处理
        if os.path.exists(ocr_file):
            print(f"  第 {page_num} 页: 已存在，跳过")
            continue
        
        print(f"  第 {page_num} 页: OCR识别中...", end='', flush=True)
        
        text = ocr_image_enhanced(img_path)
        
        # 保存OCR结果
        with open(ocr_file, 'w', encoding='utf-8') as f:
            f.write(text)
        
        # 统计字符数
        char_count = len(text.replace('\n', '').replace(' ', ''))
        print(f" 完成 ({char_count} 字符)")
        processed += 1
    
    print(f"\n处理完成！共处理 {processed} 页")
    print(f"OCR结果保存在: {ocr_dir}")


def main():
    import sys
    
    epub_path = "test.epub"
    output_base = "epub_extracted"
    
    # 默认处理前20页，可通过命令行参数指定
    start_page = 1
    end_page = 20
    
    if len(sys.argv) >= 3:
        start_page = int(sys.argv[1])
        end_page = int(sys.argv[2])
    elif len(sys.argv) == 2:
        end_page = int(sys.argv[1])
    
    process_pages(epub_path, output_base, start_page, end_page)


if __name__ == "__main__":
    main()

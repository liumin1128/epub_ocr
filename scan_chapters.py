#!/usr/bin/env python3
"""
使用OCR技术扫描全书，找到所有章节起始页
"""

import zipfile
import re
import tempfile
import os
from pathlib import Path

try:
    from PIL import Image
    import pytesseract
except ImportError:
    print("请先安装依赖:")
    print("  pip install Pillow pytesseract")
    print("  brew install tesseract tesseract-lang  # macOS")
    exit(1)


def extract_images_from_epub(epub_path: str, output_dir: str) -> list[str]:
    """从EPUB中提取所有图片"""
    image_files = []
    
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
    return image_files  # 返回 (页码, 路径) 元组


def ocr_image(image_path: str) -> str:
    """对单张图片进行OCR识别"""
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang='chi_sim+eng')
        return text
    except Exception as e:
        return ""


def extract_chapter_from_page(text: str) -> str | None:
    """
    检查页面是否是章节起始页
    章节起始页特征：页面顶部有"第X章"标题
    """
    lines = text.strip().split('\n')
    if not lines:
        return None
    
    # 检查前几行是否有章节标题
    first_lines = ' '.join(lines[:5])
    
    # 匹配章节标题
    pattern = r'第[一二三四五六七八九十百千\d]+章[^\n]{0,30}'
    match = re.search(pattern, first_lines)
    
    if match:
        title = match.group().strip()
        # 清理标题
        title = re.sub(r'\s+', ' ', title)
        title = re.sub(r'[…\.]{2,}.*$', '', title)
        title = title.strip()
        return title
    
    return None


def scan_all_pages(image_files: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """扫描所有页面找到章节起始页"""
    chapters = []
    total = len(image_files)
    
    print(f"正在扫描全书 {total} 页，查找章节起始页...")
    print("（这可能需要几分钟时间）\n")
    
    for i, (page_num, img_path) in enumerate(image_files):
        # 进度显示
        if (i + 1) % 20 == 0 or i == 0:
            print(f"  进度: {i+1}/{total} ({(i+1)*100//total}%)", end='\r', flush=True)
        
        text = ocr_image(img_path)
        chapter = extract_chapter_from_page(text)
        
        if chapter:
            chapters.append((page_num, chapter))
            print(f"\n  ✓ 第 {page_num} 页: {chapter}")
    
    print(f"\n  进度: {total}/{total} (100%)")
    return chapters


def main():
    epub_path = "test.epub"
    
    print("=" * 60)
    print("EPUB 章节扫描工具")
    print("=" * 60)
    print(f"文件: {epub_path}\n")
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        print("步骤1: 提取图片...")
        image_files = extract_images_from_epub(epub_path, tmp_dir)
        print(f"  共提取 {len(image_files)} 张图片\n")
        
        print("步骤2: 全书扫描...")
        chapters = scan_all_pages(image_files)
        
        print("\n" + "=" * 60)
        if chapters:
            print(f"共找到 {len(chapters)} 个章节:")
            print("=" * 60)
            for i, (page, title) in enumerate(chapters, 1):
                print(f"  {i}. [第{page}页] {title}")
        else:
            print("未能识别出章节信息")
        print("=" * 60)


if __name__ == "__main__":
    main()

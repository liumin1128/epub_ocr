#!/usr/bin/env python3
"""
OCR识别EPUB目录页，提取章节名（最终版）
策略：扫描前30页，找到目录页并提取所有章节标题
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


def extract_images_from_epub(epub_path: str, output_dir: str) -> list[tuple[int, str]]:
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
    return image_files


def ocr_image(image_path: str) -> str:
    """对单张图片进行OCR识别"""
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang='chi_sim+eng')
        return text
    except Exception as e:
        return ""


def is_toc_page(text: str) -> bool:
    """判断是否是目录页"""
    # 目录页特征：包含"目录"且有多个带数字的行（页码）
    has_toc_marker = bool(re.search(r'目\s*录|目\s*次|CONTENTS', text, re.IGNORECASE))
    # 统计包含数字的行数（目录通常每行末尾有页码）
    lines_with_numbers = len(re.findall(r'[^\n]+\d+\s*$', text, re.MULTILINE))
    
    return has_toc_marker or lines_with_numbers >= 5


def extract_toc_entries(text: str) -> list[str]:
    """从目录页文本中提取章节条目"""
    entries = []
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 匹配章节格式
        # 1. 第X章 标题 ... (页码)
        chapter_match = re.match(r'(第[一二三四五六七八九十百千\d]+[章节篇部卷回][\s\S]*?)[\.\…]+\s*\(?\d+\)?$', line)
        if chapter_match:
            title = chapter_match.group(1).strip()
            title = re.sub(r'\s+', ' ', title)
            if title and title not in entries:
                entries.append(title)
            continue
        
        # 2. 独立的章节标题行
        chapter_match = re.match(r'(第[一二三四五六七八九十百千\d]+[章节篇部卷回][^\d]{0,30})', line)
        if chapter_match:
            title = chapter_match.group(1).strip()
            title = re.sub(r'[\.\…]+.*$', '', title)
            title = re.sub(r'\s+', ' ', title)
            if len(title) > 3 and title not in entries:
                entries.append(title)
    
    return entries


def scan_for_toc(image_files: list[tuple[int, str]], max_pages: int = 30) -> list[str]:
    """扫描前N页查找目录页并提取章节"""
    all_chapters = []
    
    print(f"正在扫描前 {min(max_pages, len(image_files))} 页...")
    
    for i, (page_num, img_path) in enumerate(image_files[:max_pages]):
        print(f"  第 {page_num} 页... ", end='', flush=True)
        
        text = ocr_image(img_path)
        
        if is_toc_page(text):
            chapters = extract_toc_entries(text)
            if chapters:
                print(f"【目录页】找到 {len(chapters)} 个章节")
                all_chapters.extend(chapters)
            else:
                print("【目录页】无法解析章节")
        else:
            print("普通页面")
    
    # 去重
    seen = set()
    unique = []
    for ch in all_chapters:
        if ch not in seen:
            seen.add(ch)
            unique.append(ch)
    
    return unique


def main():
    epub_path = "test.epub"
    
    print("=" * 60)
    print("EPUB 目录提取工具")
    print("=" * 60)
    print(f"文件: {epub_path}\n")
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        print("步骤1: 提取图片...")
        image_files = extract_images_from_epub(epub_path, tmp_dir)
        print(f"  共提取 {len(image_files)} 张图片\n")
        
        print("步骤2: 查找目录页...")
        chapters = scan_for_toc(image_files)
        
        print("\n" + "=" * 60)
        if chapters:
            print(f"从目录页提取到 {len(chapters)} 个章节:")
            print("=" * 60)
            for i, title in enumerate(chapters, 1):
                print(f"  {i}. {title}")
        else:
            print("未找到目录页或无法解析章节")
        print("=" * 60)


if __name__ == "__main__":
    main()

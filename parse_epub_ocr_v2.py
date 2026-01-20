#!/usr/bin/env python3
"""
使用OCR技术解析图片版EPUB文件，提取中文章节名（优化版）
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
    return [f[1] for f in image_files]


def ocr_image(image_path: str) -> str:
    """对单张图片进行OCR识别"""
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang='chi_sim+eng')
        return text
    except Exception as e:
        print(f"OCR失败 {image_path}: {e}")
        return ""


def extract_chapter_titles_clean(text: str) -> list[str]:
    """从OCR文本中提取干净的章节标题"""
    chapters = []
    
    # 匹配 "第X章 标题" 格式
    pattern = r'第[一二三四五六七八九十百千\d]+章[\s\S]{0,50}'
    matches = re.findall(pattern, text)
    
    for match in matches:
        # 清理：去掉换行、多余空格、省略号后的内容
        clean = match.strip()
        clean = re.sub(r'\s+', ' ', clean)  # 合并多个空格
        clean = re.sub(r'[…\.]{2,}.*$', '', clean)  # 去掉省略号及后面内容
        clean = re.sub(r'\(\d+\)$', '', clean)  # 去掉页码
        clean = clean.strip()
        
        if len(clean) > 3 and clean not in chapters:
            chapters.append(clean)
    
    return chapters


def find_toc_and_extract_chapters(image_files: list[str], max_pages: int = 25) -> list[str]:
    """
    查找目录页并提取章节
    """
    all_chapters = []
    toc_found = False
    
    print(f"正在扫描前 {min(max_pages, len(image_files))} 页寻找目录...")
    
    for i, img_path in enumerate(image_files[:max_pages]):
        print(f"  OCR识别第 {i+1} 页...", end=' ', flush=True)
        text = ocr_image(img_path)
        
        # 检查是否是目录页
        is_toc = '目录' in text or '目 录' in text or '目 次' in text
        
        # 提取章节标题
        chapters = extract_chapter_titles_clean(text)
        
        if is_toc:
            toc_found = True
            print(f"【目录页】找到 {len(chapters)} 个章节")
        elif chapters:
            print(f"找到 {len(chapters)} 个章节")
        else:
            print("普通页面")
        
        all_chapters.extend(chapters)
    
    # 去重并保持顺序
    seen = set()
    unique_chapters = []
    for ch in all_chapters:
        if ch not in seen:
            seen.add(ch)
            unique_chapters.append(ch)
    
    return unique_chapters


def main():
    epub_path = "test.epub"
    
    print("=" * 60)
    print("EPUB OCR章节提取工具 (优化版)")
    print("=" * 60)
    print(f"文件: {epub_path}\n")
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        print("步骤1: 提取图片...")
        image_files = extract_images_from_epub(epub_path, tmp_dir)
        print(f"  共提取 {len(image_files)} 张图片\n")
        
        print("步骤2: OCR识别目录页...")
        chapters = find_toc_and_extract_chapters(image_files)
        
        print("\n" + "=" * 60)
        if chapters:
            print(f"共找到 {len(chapters)} 个章节:")
            print("=" * 60)
            for i, chapter in enumerate(chapters, 1):
                print(f"  {i}. {chapter}")
        else:
            print("未能识别出章节信息")
            print("=" * 60)


if __name__ == "__main__":
    main()

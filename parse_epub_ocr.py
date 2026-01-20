#!/usr/bin/env python3
"""
使用OCR技术解析图片版EPUB文件，提取中文章节名
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
                # 提取页码用于排序
                match = re.search(r'index-(\d+)', name)
                if match:
                    page_num = int(match.group(1))
                    data = epub.read(name)
                    ext = Path(name).suffix
                    output_path = os.path.join(output_dir, f"page_{page_num:04d}{ext}")
                    with open(output_path, 'wb') as f:
                        f.write(data)
                    image_files.append((page_num, output_path))
    
    # 按页码排序
    image_files.sort(key=lambda x: x[0])
    return [f[1] for f in image_files]


def ocr_image(image_path: str) -> str:
    """对单张图片进行OCR识别"""
    try:
        img = Image.open(image_path)
        # 使用中文简体识别
        text = pytesseract.image_to_string(img, lang='chi_sim')
        return text
    except Exception as e:
        print(f"OCR失败 {image_path}: {e}")
        return ""


def extract_chapter_titles(text: str) -> list[str]:
    """从OCR文本中提取章节标题"""
    chapters = []
    
    # 常见的中文章节模式
    patterns = [
        r'第[一二三四五六七八九十百千\d]+[章节篇部卷回][\s\S]{0,30}',  # 第X章/节/篇
        r'[第]?\d+[\.、\s][^\n]{2,20}',  # 1. 标题 或 1、标题
        r'(?:前言|序言|序|引言|导论|绑论|结语|后记|附录|目录)',  # 特殊章节
        r'[A-Z][a-z]+\s+\d+',  # Chapter 1 等
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            # 清理匹配结果
            clean = match.strip().replace('\n', ' ')
            if len(clean) > 1 and clean not in chapters:
                chapters.append(clean)
    
    return chapters


def find_toc_pages(image_files: list[str], max_pages: int = 20) -> list[str]:
    """
    智能查找目录页
    目录页通常在前20页，且包含多个章节标题
    """
    toc_chapters = []
    
    print(f"正在扫描前 {min(max_pages, len(image_files))} 页寻找目录...")
    
    for i, img_path in enumerate(image_files[:max_pages]):
        print(f"  OCR识别第 {i+1} 页...", end=' ')
        text = ocr_image(img_path)
        
        # 检查是否是目录页（包含"目录"二字或多个章节模式）
        is_toc = '目录' in text or '目 录' in text
        chapters = extract_chapter_titles(text)
        
        if is_toc or len(chapters) >= 3:
            print(f"找到 {len(chapters)} 个章节标题")
            toc_chapters.extend(chapters)
        else:
            print(f"普通页面")
    
    return toc_chapters


def scan_all_pages_for_chapters(image_files: list[str]) -> list[tuple[int, str]]:
    """
    扫描所有页面，查找章节起始页
    返回: [(页码, 章节名), ...]
    """
    chapters = []
    
    print(f"\n正在扫描所有 {len(image_files)} 页查找章节...")
    
    for i, img_path in enumerate(image_files):
        if (i + 1) % 50 == 0:
            print(f"  已处理 {i+1}/{len(image_files)} 页...")
        
        text = ocr_image(img_path)
        
        # 检查页面开头是否有章节标题（章节起始页特征）
        lines = text.strip().split('\n')
        if lines:
            first_lines = ' '.join(lines[:3])  # 取前3行
            
            # 严格匹配章节开头
            chapter_pattern = r'^[\s]*第[一二三四五六七八九十百千\d]+[章节篇部卷回]'
            if re.match(chapter_pattern, first_lines):
                # 提取完整章节名
                match = re.search(r'第[一二三四五六七八九十百千\d]+[章节篇部卷回][^\n]{0,30}', first_lines)
                if match:
                    chapter_name = match.group().strip()
                    chapters.append((i + 1, chapter_name))
                    print(f"  第 {i+1} 页: {chapter_name}")
    
    return chapters


def main():
    epub_path = "test.epub"
    
    print(f"=" * 60)
    print(f"EPUB OCR章节提取工具")
    print(f"=" * 60)
    print(f"文件: {epub_path}\n")
    
    # 创建临时目录存放提取的图片
    with tempfile.TemporaryDirectory() as tmp_dir:
        print("步骤1: 提取图片...")
        image_files = extract_images_from_epub(epub_path, tmp_dir)
        print(f"  共提取 {len(image_files)} 张图片\n")
        
        print("步骤2: 从目录页提取章节...")
        toc_chapters = find_toc_pages(image_files)
        
        if toc_chapters:
            print(f"\n" + "=" * 60)
            print(f"从目录页找到 {len(toc_chapters)} 个章节:")
            print("=" * 60)
            for i, chapter in enumerate(toc_chapters, 1):
                print(f"  {i}. {chapter}")
        else:
            print("\n未在目录页找到章节，尝试扫描全书...")
            chapters = scan_all_pages_for_chapters(image_files)
            
            if chapters:
                print(f"\n" + "=" * 60)
                print(f"从全书扫描找到 {len(chapters)} 个章节:")
                print("=" * 60)
                for page, name in chapters:
                    print(f"  第{page}页: {name}")
            else:
                print("\n未能识别出章节信息")


if __name__ == "__main__":
    main()

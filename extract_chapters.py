#!/usr/bin/env python3
"""
从已保存的OCR结果中提取章节名
"""

import re
import os
from pathlib import Path


def extract_chapters_from_ocr(ocr_dir: str) -> list[str]:
    """从OCR文本文件中提取章节名"""
    chapters = []
    
    # 读取所有OCR文件
    ocr_files = sorted(Path(ocr_dir).glob("page_*.txt"))
    
    for ocr_file in ocr_files:
        with open(ocr_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # 查找"第X章"格式的标题
        # 匹配：第一章、第二章、第1章、第2章 等
        pattern = r'第[一二三四五六七八九十百千零\d]+章[^\n\d]{0,30}'
        matches = re.findall(pattern, text)
        
        for match in matches:
            # 清理标题
            title = match.strip()
            title = re.sub(r'\s+', ' ', title)
            title = re.sub(r'[…\.]+.*$', '', title)  # 去掉省略号后的内容
            title = title.strip()
            
            # 去重
            if title and len(title) > 3 and title not in chapters:
                # 检查是否是真正的章节标题（不是页眉）
                # 页眉通常很短或包含"|"
                if '|' not in title and len(title) < 50:
                    chapters.append(title)
    
    return chapters


def main():
    ocr_dir = "epub_extracted/ocr"
    
    if not os.path.exists(ocr_dir):
        print(f"OCR目录不存在: {ocr_dir}")
        print("请先运行 epub_extractor.py 提取OCR结果")
        return
    
    print("=" * 50)
    print("从OCR结果提取章节名")
    print("=" * 50)
    
    chapters = extract_chapters_from_ocr(ocr_dir)
    
    if chapters:
        print(f"\n找到 {len(chapters)} 个章节:\n")
        for i, ch in enumerate(chapters, 1):
            print(f"  {i}. {ch}")
    else:
        print("\n未找到章节信息")
    
    print()


if __name__ == "__main__":
    main()

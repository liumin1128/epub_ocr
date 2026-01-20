#!/usr/bin/env python3
"""
解析EPUB文件并打印所有章节名
"""

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_epub_chapters(epub_path: str) -> list[str]:
    """
    解析EPUB文件，提取所有章节名
    
    Args:
        epub_path: EPUB文件路径
        
    Returns:
        章节名列表
    """
    chapters = []
    
    with zipfile.ZipFile(epub_path, 'r') as epub:
        # 1. 读取 container.xml 获取 OPF 文件路径
        container_xml = epub.read('META-INF/container.xml')
        container_tree = ET.fromstring(container_xml)
        
        # 获取 OPF 文件路径
        ns = {'container': 'urn:oasis:names:tc:opendocument:xmlns:container'}
        rootfile = container_tree.find('.//container:rootfile', ns)
        opf_path = rootfile.get('full-path')
        opf_dir = str(Path(opf_path).parent)
        
        # 2. 读取 OPF 文件
        opf_content = epub.read(opf_path)
        opf_tree = ET.fromstring(opf_content)
        
        # OPF 命名空间
        opf_ns = {
            'opf': 'http://www.idpf.org/2007/opf',
            'dc': 'http://purl.org/dc/elements/1.1/'
        }
        
        # 3. 尝试从 NCX 文件获取目录（EPUB 2）
        ncx_item = opf_tree.find('.//opf:item[@media-type="application/x-dtbncx+xml"]', opf_ns)
        if ncx_item is not None:
            ncx_href = ncx_item.get('href')
            ncx_path = f"{opf_dir}/{ncx_href}" if opf_dir != '.' else ncx_href
            chapters = parse_ncx(epub, ncx_path)
            if chapters:
                return chapters
        
        # 4. 尝试从 NAV 文件获取目录（EPUB 3）
        nav_item = opf_tree.find('.//opf:item[@properties="nav"]', opf_ns)
        if nav_item is not None:
            nav_href = nav_item.get('href')
            nav_path = f"{opf_dir}/{nav_href}" if opf_dir != '.' else nav_href
            chapters = parse_nav(epub, nav_path)
            if chapters:
                return chapters
        
        # 5. 如果都没有，从 spine 和 manifest 获取
        chapters = parse_from_spine(epub, opf_tree, opf_ns, opf_dir)
    
    return chapters


def parse_ncx(epub: zipfile.ZipFile, ncx_path: str) -> list[str]:
    """从 NCX 文件解析章节名"""
    chapters = []
    try:
        ncx_content = epub.read(ncx_path)
        ncx_tree = ET.fromstring(ncx_content)
        ncx_ns = {'ncx': 'http://www.daisy.org/z3986/2005/ncx/'}
        
        nav_points = ncx_tree.findall('.//ncx:navPoint', ncx_ns)
        for nav_point in nav_points:
            text_elem = nav_point.find('.//ncx:text', ncx_ns)
            if text_elem is not None and text_elem.text:
                chapters.append(text_elem.text.strip())
    except Exception:
        pass
    return chapters


def parse_nav(epub: zipfile.ZipFile, nav_path: str) -> list[str]:
    """从 NAV 文件解析章节名（EPUB 3）"""
    chapters = []
    try:
        nav_content = epub.read(nav_path)
        nav_tree = ET.fromstring(nav_content)
        
        # XHTML 命名空间
        xhtml_ns = {'xhtml': 'http://www.w3.org/1999/xhtml'}
        epub_ns = {'epub': 'http://www.idpf.org/2007/ops'}
        
        # 查找 toc nav
        nav_elem = nav_tree.find('.//xhtml:nav[@epub:type="toc"]', {**xhtml_ns, **epub_ns})
        if nav_elem is None:
            # 尝试不带命名空间
            for nav in nav_tree.iter():
                if nav.tag.endswith('nav') and nav.get('{http://www.idpf.org/2007/ops}type') == 'toc':
                    nav_elem = nav
                    break
        
        if nav_elem is not None:
            for a_tag in nav_elem.iter():
                if a_tag.tag.endswith('a') and a_tag.text:
                    chapters.append(a_tag.text.strip())
    except Exception:
        pass
    return chapters


def parse_from_spine(epub: zipfile.ZipFile, opf_tree: ET.Element, 
                     opf_ns: dict, opf_dir: str) -> list[str]:
    """从 spine 和 manifest 解析章节名"""
    chapters = []
    
    # 获取 manifest 中的所有项
    manifest = {}
    for item in opf_tree.findall('.//opf:item', opf_ns):
        item_id = item.get('id')
        href = item.get('href')
        media_type = item.get('media-type')
        manifest[item_id] = {'href': href, 'media-type': media_type}
    
    # 按 spine 顺序获取章节
    spine = opf_tree.find('.//opf:spine', opf_ns)
    if spine is not None:
        for itemref in spine.findall('opf:itemref', opf_ns):
            idref = itemref.get('idref')
            if idref in manifest:
                item = manifest[idref]
                if item['media-type'] in ['application/xhtml+xml', 'text/html']:
                    href = item['href']
                    file_path = f"{opf_dir}/{href}" if opf_dir != '.' else href
                    title = extract_title_from_html(epub, file_path)
                    if title:
                        chapters.append(title)
    
    return chapters


def extract_title_from_html(epub: zipfile.ZipFile, file_path: str) -> str:
    """从 HTML/XHTML 文件中提取标题"""
    try:
        content = epub.read(file_path)
        tree = ET.fromstring(content)
        
        # 尝试获取 <title> 标签
        for elem in tree.iter():
            if elem.tag.endswith('title') and elem.text:
                return elem.text.strip()
            # 或者获取 <h1> 标签
            if elem.tag.endswith('h1') and elem.text:
                return elem.text.strip()
    except Exception:
        pass
    return ""


def main():
    epub_path = "test.epub"
    
    print(f"解析 EPUB 文件: {epub_path}")
    print("-" * 50)
    
    chapters = parse_epub_chapters(epub_path)
    
    if chapters:
        print(f"共找到 {len(chapters)} 个章节:\n")
        for i, chapter in enumerate(chapters, 1):
            print(f"  {i}. {chapter}")
    else:
        print("未找到章节信息")


if __name__ == "__main__":
    main()

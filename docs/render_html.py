#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨会话长程记忆数据集文档渲染工具 (docs/render_html.py)
---------------------------------------------------------------
设计规范：
  - 风格：Parchment（米纸学术）与 Twilight（暮色极简）双主题
  - 排版原则：纯净整洁、零杂乱符号、零 Emoji、去除生硬模板黑括号
  - 功能特性：
    1. 侧边栏折叠大纲 (TOC) + ScrollSpy 实时滚动跟随
    2. 栏目分类筛选（架构拓扑 / 多样性规范 / 缺陷排查 / 实测汇总）
    3. 关键词即时检索过滤
    4. 规范代码块（修复前 vs 修复后对比网格 + 一键复制代码）
    5. 分栏卡片视图 vs Markdown 原生源码视图切换
"""

import sys
import re
import html
from pathlib import Path

# 确保在 Windows 控制台中文编码正常
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

def get_paths():
    curr_dir = Path(__file__).resolve().parent
    if (curr_dir / "update.md").exists():
        md_path = curr_dir / "update.md"
        html_path = curr_dir / "update.html"
    elif (curr_dir / "docs" / "update.md").exists():
        md_path = curr_dir / "docs" / "update.md"
        html_path = curr_dir / "docs" / "update.html"
    else:
        md_path = Path("docs/update.md").resolve()
        html_path = Path("docs/update.html").resolve()
    return md_path, html_path

def md_text_to_html(md_chunk: str) -> str:
    """将 Markdown 段落中的常用格式转为高可读性 HTML"""
    lines = md_chunk.strip().splitlines()
    out = []
    
    for line in lines:
        line_s = line.strip()
        if not line_s:
            continue
            
        # 章节小标 #### xxx (去除可能残留的黑括号)
        if line_s.startswith('#### '):
            sub = line_s[5:].strip().strip('【】')
            out.append(f'<div class="section-sublabel">{sub}</div>')
            continue
            
        formatted = line
        formatted = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', formatted)
        formatted = re.sub(r'`(.*?)`', r'<code>\1</code>', formatted)
        
        # 列表格式
        list_match = re.match(r'^\s*(\d+\.|\-|\•)\s+(.*)', line)
        if list_match:
            item_text = list_match.group(2)
            item_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', item_text)
            item_text = re.sub(r'`(.*?)`', r'<code>\1</code>', item_text)
            prefix = list_match.group(1)
            out.append(f'<div class="bullet-item"><span class="bullet-prefix">{prefix}</span><div class="bullet-content">{item_text}</div></div>')
        else:
            out.append(f'<p>{formatted}</p>')
            
    return "\n".join(out)

def extract_contrasts(body: str):
    """提取修复前与修复后对比块（去除所有 emoji 与花哨符号）"""
    # 优先切分 #### 对比分析 / #### 对照分析
    split_pos = -1
    for kw in ["#### 对比分析", "#### 对照分析", "#### 对照代码与实测案例", "#### 对照"]:
        pos = body.find(kw)
        if pos != -1:
            split_pos = pos
            break

    if split_pos != -1:
        clean_body = body[:split_pos].strip()
        contrast_chunk = body[split_pos:]
    else:
        clean_body = body.strip()
        contrast_chunk = body

    # 尝试匹配 **修复前...**: ```lang ... ``` 和 **修复后...**: ```lang ... ```
    bad_m = re.search(r'\*\*(?:修复前|问题表现|改造前|优化前|传统做法)(.*?)\*\*\s*[:：]?\s*```([a-zA-Z0-9_-]*)\n(.*?)```', contrast_chunk, re.DOTALL)
    good_m = re.search(r'\*\*(?:修复后|规范表现|改造后|优化后|现行)(.*?)\*\*\s*[:：]?\s*```([a-zA-Z0-9_-]*)\n(.*?)```', contrast_chunk, re.DOTALL)

    if bad_m and good_m:
        bad_title = bad_m.group(1).strip(" ：:（）()") or "缺陷表现"
        bad_lang = bad_m.group(2).strip() or "JSON"
        bad_code = bad_m.group(3).strip()

        good_title = good_m.group(1).strip(" ：:（）()") or "规范表现"
        good_lang = good_m.group(2).strip() or "JSON"
        good_code = good_m.group(3).strip()
        return clean_body, bad_title, bad_code, bad_lang, good_title, good_code, good_lang

    # 兜底：提取对比区域内的两个代码块
    code_blocks = re.findall(r'```([a-zA-Z0-9_-]*)\n(.*?)```', contrast_chunk, re.DOTALL)
    if len(code_blocks) >= 2:
        bad_lang = code_blocks[0][0].strip() or "TEXT"
        bad_code = code_blocks[0][1].strip()
        good_lang = code_blocks[1][0].strip() or "TEXT"
        good_code = code_blocks[1][2 if len(code_blocks[1]) > 2 else 1].strip()
        return clean_body, "缺陷表现", bad_code, bad_lang, "规范表现", good_code, good_lang

    return clean_body, "缺陷表现", "", "TEXT", "规范表现", "", "TEXT"

def parse_summary_table(md_text: str) -> str:
    """提取并转换实测总结对照表格"""
    table_m = re.search(r'##\s*(?:[一二三四五]、|栏目[一二三四五][：:])?实测修复结果与验证数据汇总.*?\n(.*?)(?=\n##|\Z)', md_text, re.DOTALL)
    if not table_m:
        return ""
    chunk = table_m.group(1)
    t_lines = [l.strip() for l in chunk.splitlines() if l.strip().startswith('|')]
    if len(t_lines) < 3:
        return ""
    
    headers = [c.strip() for c in t_lines[0].strip('|').split('|')]
    rows_html = []
    for line in t_lines[2:]:
        cols = [c.strip() for c in line.strip('|').split('|')]
        if len(cols) >= 3:
            c0 = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', cols[0])
            c1 = re.sub(r'`(.*?)`', r'<code>\1</code>', cols[1])
            c1 = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', c1)
            c2 = re.sub(r'`(.*?)`', r'<code>\1</code>', cols[2])
            c2 = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', c2)
            rows_html.append(f'<tr><td>{c0}</td><td>{c1}</td><td>{c2}</td></tr>')
            
    th_html = "".join([f'<th>{h}</th>' for h in headers])
    return f"""
    <div class="table-wrapper">
        <table>
            <thead><tr>{th_html}</tr></thead>
            <tbody>
                {"".join(rows_html)}
            </tbody>
        </table>
    </div>
    """

def render_html_page(md_path: Path, html_path: Path):
    print(f"[*] 读取 Markdown 源文件: {md_path}")
    md_text = md_path.read_text(encoding="utf-8")

    # 1. 解析所有条目块
    sections = re.split(r'\n##\s+', md_text)
    cards = []
    idx = 1

    for sec in sections[1:]:
        sec_title = sec.splitlines()[0].strip()
        if any(k in sec_title for k in ['时间线归档', '实测修复结果', '核心元数据', '目录大纲']):
            continue
        
        if '架构' in sec_title or '拓扑' in sec_title:
            cat_code = 'arch'
            badge_title = '架构拓扑'
        elif '多样性' in sec_title or '提示词' in sec_title:
            cat_code = 'gov'
            badge_title = '多样性规范'
        else:
            cat_code = 'bug'
            badge_title = '缺陷修复'
            
        h3_blocks = re.findall(r'(?:^|\n)###\s+([^#\n].*?)\n(.*?)(?=\n###\s+[^#]|\n##\s+|\Z)', sec, re.DOTALL)
        for title_raw, body_raw in h3_blocks:
            title = title_raw.strip()
            date_cat_m = re.search(r'>\s*\*\*归档时间\*\*[：:]\s*`?(.*?)`?\s*\|\s*\*\*分类\*\*[：:]\s*`?(.*?)`?', body_raw)
            date_tag = date_cat_m.group(1).strip() if date_cat_m else '2026-09-28'

            clean_body, bad_title, bad_code, bad_lang, good_title, good_code, good_lang = extract_contrasts(body_raw)
            # 移除已在卡片头部徽章展示过的归档时间与分类元信息行
            clean_body = re.sub(r'^\s*>\s*\*\*归档时间\*\*.*?\n+', '', clean_body).strip()
            desc_html = md_text_to_html(clean_body)

            cards.append({
                "idx": idx,
                "id": f"entry-{idx}",
                "title": title,
                "date_tag": date_tag,
                "cat_code": cat_code,
                "cat_name": badge_title,
                "desc_html": desc_html,
                "bad_title": bad_title,
                "bad_code": bad_code,
                "bad_lang": bad_lang.upper(),
                "good_title": good_title,
                "good_code": good_code,
                "good_lang": good_lang.upper(),
            })
            idx += 1

    print(f"[+] 解析到 {len(cards)} 项条目与技术规范")

    # 2. 生成目录树 (TOC)
    arch_cards = [c for c in cards if c["cat_code"] == "arch"]
    gov_cards = [c for c in cards if c["cat_code"] == "gov"]
    bug_cards = [c for c in cards if c["cat_code"] == "bug"]

    def render_toc_link(c):
        short_title = c["title"][:26] + "..." if len(c["title"]) > 26 else c["title"]
        return f"""
        <li class="toc-item">
            <a href="#{c['id']}" class="toc-link" data-target="{c['id']}" title="{c['title']}">
                <span class="toc-text">{short_title}</span>
            </a>
        </li>"""

    toc_html_parts = []
    if arch_cards:
        toc_html_parts.append('<div class="toc-group-title">架构设计与模板拓扑</div><ul class="toc-list">')
        for c in arch_cards:
            toc_html_parts.append(render_toc_link(c))
        toc_html_parts.append('</ul>')

    if gov_cards:
        toc_html_parts.append('<div class="toc-group-title">数据多样性与提示词规则</div><ul class="toc-list">')
        for c in gov_cards:
            toc_html_parts.append(render_toc_link(c))
        toc_html_parts.append('</ul>')

    if bug_cards:
        curr_d = None
        for c in bug_cards:
            d_prefix = c["date_tag"].split()[0] if c["date_tag"] else "历史记录"
            if d_prefix != curr_d:
                if curr_d is not None:
                    toc_html_parts.append('</ul>')
                curr_d = d_prefix
                toc_html_parts.append(f'<div class="toc-group-title">核心缺陷排查 ({curr_d})</div><ul class="toc-list">')
            toc_html_parts.append(render_toc_link(c))
        if curr_d is not None:
            toc_html_parts.append('</ul>')

    toc_html_parts.append("""
        <div class="toc-group-title">实测验证与数据对比</div>
        <ul class="toc-list">
            <li class="toc-item">
                <a href="#summary-section" class="toc-link" data-target="summary-section">
                    <span class="toc-text">100画像全量质检对照表</span>
                </a>
            </li>
        </ul>
    """)
    toc_html = "\n".join(toc_html_parts)

    # 3. 渲染各个条目卡片
    def render_card(c):
        badge_class = f"badge-{c['cat_code']}"
        bad_title_display = f"修复前：{c['bad_title']}" if c['bad_title'] and c['bad_title'] != "缺陷表现" else "修复前表现"
        good_title_display = f"修复后：{c['good_title']}" if c['good_title'] and c['good_title'] != "规范表现" else "修复后表现"
        return f"""
        <article class="issue-card" id="{c['id']}" data-cat="{c['cat_code']}">
            <div class="issue-header">
                <div class="issue-title-group">
                    <h2>{c['title']}</h2>
                </div>
                <div class="issue-tag-group">
                    <span class="issue-cat-badge {badge_class}">{c['cat_name']}</span>
                    <span class="issue-date-tag">{c['date_tag']}</span>
                </div>
            </div>
            
            <div class="desc-block">
                {c['desc_html']}
            </div>
            
            <div class="contrast-grid">
                <div class="contrast-box bad">
                    <div class="contrast-header">
                        <div class="contrast-title"><span class="contrast-pill-bad">修复前</span> {c['bad_title']}</div>
                        <span class="code-lang-tag">{c['bad_lang']}</span>
                    </div>
                    <div class="code-block">
                        <div class="code-header">
                            <span class="code-lang">修复前</span>
                            <button class="copy-btn" onclick="copyCode(this)" title="复制代码">
                                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                                <span>复制</span>
                            </button>
                        </div>
                        <pre><code>{html.escape(c['bad_code'])}</code></pre>
                    </div>
                </div>
                
                <div class="contrast-box good">
                    <div class="contrast-header">
                        <div class="contrast-title"><span class="contrast-pill-good">修复后</span> {c['good_title']}</div>
                        <span class="code-lang-tag">{c['good_lang']}</span>
                    </div>
                    <div class="code-block">
                        <div class="code-header">
                            <span class="code-lang">修复后</span>
                            <button class="copy-btn" onclick="copyCode(this)" title="复制代码">
                                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                                <span>复制</span>
                            </button>
                        </div>
                        <pre><code>{html.escape(c['good_code'])}</code></pre>
                    </div>
                </div>
            </div>
        </article>"""

    arch_cards_html = "\n".join([render_card(c) for c in arch_cards])
    gov_cards_html = "\n".join([render_card(c) for c in gov_cards])
    bug_cards_html = "\n".join([render_card(c) for c in bug_cards])
    summary_table_html = parse_summary_table(md_text)

    # 4. 组装完整 HTML 页面 (Parchment & Twilight 风格)
    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="parchment">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>跨会话长程记忆数据集：生成问题排查、架构拓扑与多样性规范手册</title>
    <style>
        :root[data-theme="parchment"] {{
            --bg-color: #f7f4ec;
            --surface-color: #eee9dc;
            --surface-elevated: #e6dfcf;
            --border-color: #dcd4c0;
            --border-subtle: #e6dfd1;
            --text-primary: #2d3748;
            --text-secondary: #5c687a;
            --text-muted: #798696;
            --accent-primary: #a35d28;
            --accent-glow: rgba(163, 93, 40, 0.08);
            --code-bg: #eae3d2;
            --code-text: #8d3a2b;
            --pre-bg: #ece5d6;
            --pre-text: #2d3748;
            --callout-note-bg: #e5ede3;
            --callout-note-border: #709775;
            --callout-note-text: #2b5133;
            --callout-warn-bg: #f5eedb;
            --callout-warn-border: #c48a37;
            --callout-warn-text: #704b12;
            --callout-imp-bg: #e5eaf5;
            --callout-imp-border: #5c7cb6;
            --callout-imp-text: #1e3863;
            --contrast-bad-bg: #fae8e5;
            --contrast-bad-border: #e8b0a5;
            --contrast-bad-text: #a83220;
            --contrast-good-bg: #eaf3e9;
            --contrast-good-border: #a8d3a6;
            --contrast-good-text: #2b6e36;
            --table-header: #e4dccb;
            --table-alt: #f1ecdf;
            --tag-bg: #dfd5be;
            --tag-text: #59472d;
            --toggle-bg: #dfd6c2;
            --card-shadow: 0 4px 18px rgba(45, 55, 72, 0.04);
            --card-hover-shadow: 0 8px 24px rgba(163, 93, 40, 0.1);
        }}

        :root[data-theme="twilight"] {{
            --bg-color: #1a1e24;
            --surface-color: #232931;
            --surface-elevated: #2c343f;
            --border-color: #39424e;
            --border-subtle: #2d3642;
            --text-primary: #dce1e8;
            --text-secondary: #9da7b3;
            --text-muted: #707b88;
            --accent-primary: #e09f67;
            --accent-glow: rgba(224, 159, 103, 0.1);
            --code-bg: #15181d;
            --code-text: #f08d70;
            --pre-bg: #171b21;
            --pre-text: #cdd3dc;
            --callout-note-bg: #202b28;
            --callout-note-border: #4d7a68;
            --callout-note-text: #8bbfa8;
            --callout-warn-bg: #2b251d;
            --callout-warn-border: #8a6c38;
            --callout-warn-text: #d9b168;
            --callout-imp-bg: #1d2533;
            --callout-imp-border: #4a638c;
            --callout-imp-text: #96b5e3;
            --contrast-bad-bg: #2d1e20;
            --contrast-bad-border: #5c3035;
            --contrast-bad-text: #f07167;
            --contrast-good-bg: #1c2b22;
            --contrast-good-border: #355e42;
            --contrast-good-text: #70c48a;
            --table-header: #262e38;
            --table-alt: #1f242c;
            --tag-bg: #323c48;
            --tag-text: #d2a679;
            --toggle-bg: #323b47;
            --card-shadow: 0 4px 18px rgba(0, 0, 0, 0.2);
            --card-hover-shadow: 0 8px 24px rgba(224, 159, 103, 0.12);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            transition: background-color 0.25s ease, color 0.25s ease, border-color 0.25s ease;
        }}

        html {{
            scroll-behavior: smooth;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            line-height: 1.85;
            padding: 24px 16px;
            font-size: 15.5px;
            text-rendering: optimizeLegibility;
            -webkit-font-smoothing: antialiased;
        }}

        .layout-wrapper {{
            display: flex;
            justify-content: center;
            align-items: flex-start;
            max-width: 1400px;
            margin: 0 auto;
            gap: 32px;
            position: relative;
        }}

        /* 左侧固定侧边栏大纲 */
        .sidebar-toc {{
            width: 300px;
            flex-shrink: 0;
            position: sticky;
            top: 24px;
            max-height: calc(100vh - 48px);
            display: flex;
            flex-direction: column;
            transition: all 0.25s ease;
            z-index: 90;
        }}

        .toc-card {{
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 18px 14px;
            display: flex;
            flex-direction: column;
            max-height: calc(100vh - 48px);
            box-shadow: var(--card-shadow);
        }}

        .toc-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 12px;
            margin-bottom: 12px;
            border-bottom: 1px solid var(--border-color);
            flex-shrink: 0;
        }}

        .toc-title {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.95rem;
            font-weight: 700;
            color: var(--text-primary);
        }}

        .toc-title svg {{
            color: var(--accent-primary);
        }}

        .toc-action-btn {{
            background: transparent;
            border: 1px solid transparent;
            border-radius: 6px;
            color: var(--text-muted);
            cursor: pointer;
            padding: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }}

        .toc-action-btn:hover {{
            background: var(--surface-elevated);
            color: var(--accent-primary);
            border-color: var(--border-color);
        }}

        /* 搜索框 */
        .search-box {{
            position: relative;
            margin-bottom: 12px;
            flex-shrink: 0;
        }}

        .search-input {{
            width: 100%;
            padding: 7px 12px 7px 32px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            background: var(--bg-color);
            font-size: 0.84rem;
            color: var(--text-primary);
            outline: none;
            transition: border-color 0.2s;
        }}

        .search-input:focus {{
            border-color: var(--accent-primary);
        }}

        .search-icon {{
            position: absolute;
            left: 10px;
            top: 50%;
            transform: translateY(-50%);
            display: flex;
            align-items: center;
            color: var(--text-muted);
        }}

        /* 栏目分类 Pills */
        .category-pills {{
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-bottom: 12px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border-color);
            flex-shrink: 0;
        }}

        .cat-pill {{
            background: var(--tag-bg);
            color: var(--tag-text);
            border: 1px solid transparent;
            padding: 3px 8px;
            border-radius: 5px;
            font-size: 0.74rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
        }}

        .cat-pill:hover {{
            color: var(--accent-primary);
            border-color: var(--accent-primary);
        }}

        .cat-pill.active {{
            background: var(--accent-primary);
            color: #ffffff;
            border-color: var(--accent-primary);
        }}

        .toc-body {{
            overflow-y: auto;
            flex: 1;
            padding-right: 4px;
        }}

        .toc-body::-webkit-scrollbar {{
            width: 5px;
        }}
        .toc-body::-webkit-scrollbar-thumb {{
            background: var(--border-color);
            border-radius: 4px;
        }}

        .toc-group-title {{
            font-size: 0.76rem;
            font-weight: 700;
            color: var(--accent-primary);
            letter-spacing: 0.04em;
            margin: 10px 0 4px 6px;
        }}

        .toc-list {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}

        .toc-item {{
            margin: 2px 0;
            line-height: 1.4;
        }}

        .toc-link {{
            display: flex;
            align-items: center;
            gap: 7px;
            padding: 4px 8px;
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 0.83rem;
            border-radius: 6px;
            transition: all 0.2s ease;
            border-left: 2px solid transparent;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .toc-link:hover {{
            color: var(--accent-primary);
            background: var(--accent-glow);
        }}

        .toc-link.active {{
            color: var(--accent-primary);
            background: var(--accent-glow);
            border-left-color: var(--accent-primary);
            font-weight: 600;
        }}

        .toc-badge {{
            flex-shrink: 0;
            font-size: 0.72rem;
            background: var(--tag-bg);
            color: var(--tag-text);
            padding: 1px 5px;
            border-radius: 4px;
            font-weight: 700;
        }}

        .toc-text {{
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        /* 侧边栏折叠支持 */
        body.toc-collapsed .sidebar-toc {{
            display: none;
        }}

        body.toc-collapsed #expandTocBtn {{
            display: inline-flex !important;
        }}

        /* 右侧主内容区 */
        .main-content {{
            flex: 1;
            min-width: 0;
            max-width: 1020px;
        }}

        /* 顶栏控制条 */
        .top-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            flex-wrap: wrap;
            gap: 12px;
        }}

        .nav-links {{
            display: flex;
            gap: 10px;
            align-items: center;
        }}

        .nav-btn {{
            background-color: var(--surface-color);
            color: var(--text-secondary);
            border: 1px solid var(--border-color);
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 0.84rem;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 5px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.2s ease;
        }}

        .nav-btn:hover {{
            color: var(--accent-primary);
            border-color: var(--accent-primary);
        }}

        .nav-btn.active {{
            background: var(--accent-primary);
            color: #ffffff;
            border-color: var(--accent-primary);
        }}

        .theme-switch-btn {{
            background-color: var(--toggle-bg);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.84rem;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-weight: 600;
            transition: all 0.2s ease;
        }}

        .theme-switch-btn:hover {{
            opacity: 0.9;
        }}

        /* 文档头部 Header */
        header.doc-header {{
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 24px;
            margin-bottom: 32px;
        }}

        .header-tag {{
            display: inline-block;
            background: var(--tag-bg);
            color: var(--tag-text);
            font-size: 0.8rem;
            font-weight: 650;
            padding: 3px 10px;
            border-radius: 4px;
            margin-bottom: 12px;
        }}

        h1.doc-title {{
            font-size: 2.05rem;
            color: var(--text-primary);
            margin-bottom: 12px;
            line-height: 1.35;
            font-weight: 700;
            letter-spacing: -0.3px;
        }}

        .doc-lead {{
            font-size: 0.95rem;
            color: var(--text-secondary);
            margin-bottom: 18px;
        }}

        .header-meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
            margin-top: 16px;
        }}

        .meta-stat-card {{
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 10px 14px;
        }}

        .meta-stat-label {{
            font-size: 0.74rem;
            color: var(--text-muted);
            margin-bottom: 2px;
        }}

        .meta-stat-val {{
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--accent-primary);
        }}

        /* 栏目区块标题 */
        .column-section-header {{
            margin-top: 40px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--border-color);
            display: flex;
            align-items: baseline;
            gap: 12px;
            flex-wrap: wrap;
        }}

        .column-section-header h2 {{
            font-size: 1.42rem;
            color: var(--text-primary);
            border-left: 4px solid var(--accent-primary);
            padding-left: 12px;
            font-weight: 650;
            margin: 0;
        }}

        .column-section-desc {{
            font-size: 0.84rem;
            color: var(--text-muted);
        }}

        /* 问题卡片 */
        .issue-card {{
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 22px 24px;
            margin-bottom: 24px;
            box-shadow: var(--card-shadow);
            transition: all 0.25s ease;
        }}

        .issue-card:hover {{
            box-shadow: var(--card-hover-shadow);
        }}

        .issue-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 14px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 12px;
            flex-wrap: wrap;
            gap: 8px;
        }}

        .issue-title-group {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .issue-num {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            background-color: var(--surface-elevated);
            border: 1px solid var(--border-color);
            color: var(--accent-primary);
            font-size: 0.88rem;
            font-weight: 750;
            flex-shrink: 0;
        }}

        .issue-header h2 {{
            font-size: 1.12rem;
            font-weight: 650;
            color: var(--text-primary);
            margin: 0;
            border-left: none;
            padding-left: 0;
        }}

        .issue-tag-group {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .issue-cat-badge {{
            font-size: 0.72rem;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 650;
        }}

        .badge-arch {{ background: var(--callout-imp-bg); color: var(--callout-imp-text); border: 1px solid var(--callout-imp-border); }}
        .badge-gov {{ background: var(--callout-warn-bg); color: var(--callout-warn-text); border: 1px solid var(--callout-warn-border); }}
        .badge-bug {{ background: var(--callout-note-bg); color: var(--callout-note-text); border: 1px solid var(--callout-note-border); }}

        .issue-date-tag {{
            font-size: 0.76rem;
            color: var(--text-muted);
            background: var(--surface-elevated);
            border: 1px solid var(--border-color);
            padding: 2px 8px;
            border-radius: 4px;
        }}

        .desc-block {{
            margin-bottom: 16px;
            font-size: 0.92rem;
        }}

        .section-sublabel {{
            font-weight: 700;
            color: var(--accent-primary);
            margin-top: 14px;
            margin-bottom: 6px;
            font-size: 0.95rem;
        }}

        .bullet-item {{
            display: flex;
            gap: 8px;
            margin-bottom: 6px;
            line-height: 1.7;
        }}

        .bullet-prefix {{
            color: var(--accent-primary);
            font-weight: 700;
            flex-shrink: 0;
        }}

        .bullet-content {{
            flex: 1;
        }}

        code {{
            font-family: "JetBrains Mono", Consolas, Menlo, Monaco, monospace;
            background-color: var(--code-bg);
            color: var(--code-text);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.88em;
        }}

        /* 核心对比网格 */
        .contrast-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-top: 14px;
        }}

        @media (max-width: 960px) {{
            .contrast-grid {{
                grid-template-columns: 1fr;
            }}
            .sidebar-toc {{
                display: none;
            }}
        }}

        .contrast-box {{
            border-radius: 8px;
            padding: 14px 16px;
            font-size: 0.85rem;
            min-width: 0;
            overflow-wrap: anywhere;
        }}

        .contrast-box.bad {{
            background: var(--contrast-bad-bg);
            border: 1px solid var(--contrast-bad-border);
        }}

        .contrast-box.good {{
            background: var(--contrast-good-bg);
            border: 1px solid var(--contrast-good-border);
        }}

        .contrast-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
        }}

        .contrast-pill-bad {{
            display: inline-block;
            background-color: var(--contrast-bad-border);
            color: var(--contrast-bad-text);
            font-size: 0.72rem;
            font-weight: 700;
            padding: 1px 6px;
            border-radius: 4px;
            margin-right: 6px;
        }}

        .contrast-pill-good {{
            display: inline-block;
            background-color: var(--contrast-good-border);
            color: var(--contrast-good-text);
            font-size: 0.72rem;
            font-weight: 700;
            padding: 1px 6px;
            border-radius: 4px;
            margin-right: 6px;
        }}

        .contrast-box.bad .contrast-title {{
            font-weight: 700;
            font-size: 0.86rem;
            color: var(--contrast-bad-text);
        }}

        .contrast-box.good .contrast-title {{
            font-weight: 700;
            font-size: 0.86rem;
            color: var(--contrast-good-text);
        }}

        .code-lang-tag {{
            font-family: "JetBrains Mono", Consolas, monospace;
            font-size: 0.72rem;
            color: var(--text-muted);
            font-weight: 600;
        }}

        /* 代码块组件 */
        .code-block {{
            background-color: var(--pre-bg);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            margin-top: 8px;
            overflow: hidden;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.02);
        }}

        .code-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 5px 10px;
            background-color: var(--surface-color);
            border-bottom: 1px solid var(--border-color);
            font-size: 0.74rem;
            user-select: none;
        }}

        .code-lang {{
            font-family: "JetBrains Mono", Consolas, monospace;
            font-weight: 700;
            color: var(--accent-primary);
            letter-spacing: 0.5px;
        }}

        .copy-btn {{
            background: transparent;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            color: var(--text-muted);
            padding: 2px 8px;
            font-size: 0.74rem;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            transition: all 0.2s;
        }}

        .copy-btn:hover {{
            color: var(--accent-primary);
            border-color: var(--accent-primary);
            background: var(--surface-elevated);
        }}

        .copy-btn.copied {{
            color: #2b5133;
            border-color: #709775;
            background: #e5ede3;
        }}

        pre {{
            background-color: transparent;
            border: none;
            padding: 12px 14px;
            overflow-x: auto;
            margin: 0;
            line-height: 1.55;
        }}

        pre code {{
            background-color: transparent;
            color: var(--pre-text);
            padding: 0;
            border-radius: 0;
            font-size: 0.83rem;
            font-family: "JetBrains Mono", Consolas, Menlo, Monaco, monospace;
            display: block;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
        }}

        /* 表格样式 */
        .table-wrapper {{
            overflow-x: auto;
            margin: 16px 0;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.88rem;
            margin: 0;
        }}

        th, td {{
            border: 1px solid var(--border-color);
            padding: 10px 14px;
            text-align: left;
        }}

        th {{
            background-color: var(--table-header);
            color: var(--text-primary);
            font-weight: 650;
        }}

        tr:nth-child(even) {{
            background-color: var(--table-alt);
        }}

        .summary-card {{
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
            box-shadow: var(--card-shadow);
        }}

        .summary-header {{
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 10px;
        }}

        /* 原生 Markdown 视图 */
        #markdown-view-container {{
            display: none;
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
            box-shadow: var(--card-shadow);
        }}

        .md-toolbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border-color);
        }}

        .btn-copy-md {{
            background: var(--accent-primary);
            color: #ffffff;
            border: none;
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 0.84rem;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s;
        }}

        .btn-copy-md:hover {{
            opacity: 0.9;
        }}

        .raw-md-textarea {{
            width: 100%;
            height: 75vh;
            font-family: "JetBrains Mono", Consolas, monospace;
            font-size: 0.85rem;
            background: var(--bg-color);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
            line-height: 1.6;
            resize: vertical;
            white-space: pre;
            overflow-x: auto;
        }}

        footer {{
            margin-top: 48px;
            padding-top: 24px;
            border-top: 1px solid var(--border-color);
            color: var(--text-muted);
            font-size: 0.86rem;
            text-align: center;
        }}
    </style>
</head>
<body>

    <div class="layout-wrapper">
        <!-- 左侧大纲导航栏 -->
        <aside class="sidebar-toc" id="sidebarToc">
            <div class="toc-card">
                <div class="toc-header">
                    <div class="toc-title">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <line x1="8" y1="6" x2="21" y2="6"></line>
                            <line x1="8" y1="12" x2="21" y2="12"></line>
                            <line x1="8" y1="18" x2="21" y2="18"></line>
                            <line x1="3" y1="6" x2="3.01" y2="6"></line>
                            <line x1="3" y1="12" x2="3.01" y2="12"></line>
                            <line x1="3" y1="18" x2="3.01" y2="18"></line>
                        </svg>
                        <span>大纲导航</span>
                    </div>
                    <button class="toc-action-btn" onclick="toggleDesktopToc()" title="收起大纲">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="15 18 9 12 15 6"></polyline>
                        </svg>
                    </button>
                </div>

                <!-- 搜索框 -->
                <div class="search-box">
                    <span class="search-icon">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                    </span>
                    <input type="text" class="search-input" id="searchInput" placeholder="搜索问题或关键词..." oninput="filterIssues()">
                </div>

                <!-- 栏目分类筛选 Pills -->
                <div class="category-pills">
                    <button class="cat-pill active" data-cat="all" onclick="selectCategory('all')">全部 ({len(cards)})</button>
                    <button class="cat-pill" data-cat="arch" onclick="selectCategory('arch')">拓扑规范 ({len(arch_cards)})</button>
                    <button class="cat-pill" data-cat="gov" onclick="selectCategory('gov')">多样性规范 ({len(gov_cards)})</button>
                    <button class="cat-pill" data-cat="bug" onclick="selectCategory('bug')">缺陷排查 ({len(bug_cards)})</button>
                    <button class="cat-pill" data-cat="summary" onclick="selectCategory('summary')">实测汇总</button>
                </div>

                <!-- TOC 树状列表 -->
                <nav class="toc-body" id="tocBody">
                    {toc_html}
                </nav>
            </div>
        </aside>

        <!-- 主内容区 -->
        <main class="main-content">
            <div class="top-bar">
                <div class="nav-links">
                    <button class="nav-btn" id="expandTocBtn" onclick="toggleDesktopToc()" style="display: none;" title="展开大纲">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="9 18 15 12 9 6"></polyline>
                        </svg>
                        <span>显示大纲</span>
                    </button>
                    <button class="nav-btn active" id="btnCardView" onclick="switchView('card')">分栏卡片</button>
                    <button class="nav-btn" id="btnMdView" onclick="switchView('markdown')">Markdown 源码</button>
                    <span style="color: var(--border-color)">|</span>
                    <span style="font-size: 0.85rem; color: var(--text-muted);">docs/update.md</span>
                </div>
                
                <button class="theme-switch-btn" onclick="toggleTheme()" id="themeBtn">
                    切换暮色
                </button>
            </div>

            <!-- 卡片视图容器 -->
            <div id="card-view-container">
                <!-- 文档主头部 -->
                <header class="doc-header">
                    <span class="header-tag">跨会话记忆数据集研发体系</span>
                    <h1 class="doc-title">生成问题排查、架构拓扑与多样性规范手册</h1>
                    <p class="doc-lead">系统归档 001~100 号画像跨会话长程记忆数据集在流水线生成、质量检验、生命周期因果演进与业务对齐过程中的问题排查、解决方案与技术规范。</p>
                    
                    <div class="header-meta-grid">
                        <div class="meta-stat-card">
                            <div class="meta-stat-label">记录周期</div>
                            <div class="meta-stat-val">09.28 - 10.10</div>
                        </div>
                        <div class="meta-stat-card">
                            <div class="meta-stat-label">排查与规范总项</div>
                            <div class="meta-stat-val">{len(cards)} 项</div>
                        </div>
                        <div class="meta-stat-card">
                            <div class="meta-stat-label">覆盖画像样本</div>
                            <div class="meta-stat-val">100 个画像</div>
                        </div>
                        <div class="meta-stat-card">
                            <div class="meta-stat-label">累计会话总数</div>
                            <div class="meta-stat-val">1410 个会话</div>
                        </div>
                        <div class="meta-stat-card">
                            <div class="meta-stat-label">全量质检通过率</div>
                            <div class="meta-stat-val" style="color: var(--contrast-good-text);">100.0% 一次通过</div>
                        </div>
                    </div>
                </header>

                <!-- 架构设计与模板拓扑规范 -->
                <section class="column-section" data-cat="arch">
                    <div class="column-section-header">
                        <h2>架构设计与模板拓扑规范</h2>
                        <span class="column-section-desc">解析 12~16 轮动态规划、16 槽位模板全景因果拓扑（Causal DAG）与安全裁剪机制</span>
                    </div>
                    {arch_cards_html}
                </section>

                <!-- 数据多样性机制与提示词规则 -->
                <section class="column-section" data-cat="gov">
                    <div class="column-section-header">
                        <h2>数据多样性机制与提示词规则</h2>
                        <span class="column-section-desc">双层解耦：基于数学取模/哈希的多样性发散机制 与 提示词/代码约束规则对照</span>
                    </div>
                    {gov_cards_html}
                </section>

                <!-- 核心缺陷排查与数据治理实录 -->
                <section class="column-section" data-cat="bug">
                    <div class="column-section-header">
                        <h2>核心缺陷排查与数据治理实录</h2>
                        <span class="column-section-desc">收录 15 项真实数据缺陷、根因推演、代码级修复方案与实测对比</span>
                    </div>
                    {bug_cards_html}
                </section>

                <!-- 实测修复结果与验证数据汇总 -->
                <section class="column-section" id="summary-section" data-cat="summary">
                    <div class="column-section-header">
                        <h2>实测修复结果与验证数据汇总</h2>
                        <span class="column-section-desc">全量 100 画像（1410 会话）在 16 项对比维度下的实测结果</span>
                    </div>
                    <div class="summary-card">
                        <div class="summary-header">全量实测验证数据表 (100 Persona / 1410 Sessions)</div>
                        <p style="font-size: 0.92rem; color: var(--text-secondary); margin-bottom: 14px;">针对上述 {len(cards)} 项问题与架构规范，已全面更新生成代码与质检套件，并在 100 个画像上完成清洗与质检校验：</p>
                        {summary_table_html}
                    </div>
                </section>
            </div>

            <!-- 原生 Markdown 源码视图 -->
            <div id="markdown-view-container">
                <div class="md-toolbar">
                    <div>
                        <strong style="color: var(--accent-primary); font-size: 1.05rem;">docs/update.md 原生源码</strong>
                        <span style="font-size: 0.8rem; color: var(--text-muted); margin-left: 8px;">(单一定义源，支持随时编辑并通过 python docs/render_html.py 一键同步)</span>
                    </div>
                    <button class="btn-copy-md" onclick="copyMarkdownSource()">复制 Markdown 全文</button>
                </div>
                <textarea class="raw-md-textarea" id="mdSourceArea" readonly>{html.escape(md_text)}</textarea>
            </div>

            <footer>
                <p>跨会话长程记忆数据集生成系统 · 研发问题排查与架构规范手册</p>
                <p style="margin-top: 6px;">Markdown源文件：<a href="update.md" style="color: var(--accent-primary); text-decoration: none;">docs/update.md</a> | HTML渲染器：docs/render_html.py</p>
            </footer>
        </main>
    </div>

    <!-- 交互脚本：双主题切换、大纲收起展开、实时检索、ScrollSpy、代码复制 -->
    <script>
        // 1. 主题切换逻辑 (Parchment 米纸 vs Twilight 暮色)
        function toggleTheme() {{
            const current = document.documentElement.getAttribute('data-theme') || 'parchment';
            const next = current === 'parchment' ? 'twilight' : 'parchment';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('doc-theme', next);
            updateThemeBtn(next);
        }}

        function updateThemeBtn(theme) {{
            const btn = document.getElementById('themeBtn');
            if (btn) {{
                btn.innerHTML = theme === 'twilight' ? '切换米纸' : '切换暮色';
            }}
        }}

        // 2. 侧边栏展开与折叠
        function toggleDesktopToc() {{
            const isCollapsed = document.body.classList.toggle('toc-collapsed');
            localStorage.setItem('toc-collapsed', isCollapsed ? 'true' : 'false');
        }}

        // 3. 视图切换 (卡片 vs Markdown 源码)
        function switchView(mode) {{
            const cardView = document.getElementById('card-view-container');
            const mdView = document.getElementById('markdown-view-container');
            const btnCard = document.getElementById('btnCardView');
            const btnMd = document.getElementById('btnMdView');

            if (mode === 'markdown') {{
                cardView.style.display = 'none';
                mdView.style.display = 'block';
                btnCard.classList.remove('active');
                btnMd.classList.add('active');
            }} else {{
                cardView.style.display = 'block';
                mdView.style.display = 'none';
                btnCard.classList.add('active');
                btnMd.classList.remove('active');
            }}
        }}

        // 4. 代码块一键复制
        function copyCode(btn) {{
            const block = btn.closest('.code-block');
            const code = block ? block.querySelector('pre code') : null;
            if (!code) return;
            const text = code.innerText;
            navigator.clipboard.writeText(text).then(() => {{
                const origHtml = btn.innerHTML;
                btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg> <span>已复制</span>';
                btn.classList.add('copied');
                setTimeout(() => {{
                    btn.innerHTML = origHtml;
                    btn.classList.remove('copied');
                }}, 2000);
            }}).catch(() => {{
                const ta = document.createElement('textarea');
                ta.value = text;
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
                btn.innerHTML = '<span>已复制</span>';
                setTimeout(() => {{ btn.innerHTML = '<span>复制</span>'; }}, 2000);
            }});
        }}

        // 5. 复制 Markdown 全文源码
        function copyMarkdownSource() {{
            const textarea = document.getElementById('mdSourceArea');
            textarea.select();
            document.execCommand('copy');
            alert('Markdown 全文已复制到剪贴板。');
        }}

        // 6. 栏目分类筛选
        function selectCategory(cat) {{
            document.querySelectorAll('.cat-pill').forEach(pill => {{
                pill.classList.toggle('active', pill.dataset.cat === cat);
            }});

            const sections = document.querySelectorAll('.column-section');
            const cards = document.querySelectorAll('.issue-card');

            if (cat === 'all') {{
                sections.forEach(s => s.style.display = 'block');
                cards.forEach(c => c.style.display = 'block');
            }} else {{
                sections.forEach(s => {{
                    s.style.display = (s.dataset.cat === cat) ? 'block' : 'none';
                }});
                cards.forEach(c => {{
                    c.style.display = (c.dataset.cat === cat) ? 'block' : 'none';
                }});
            }}
        }}

        // 7. 实时搜索过滤
        function filterIssues() {{
            const keyword = document.getElementById('searchInput').value.trim().toLowerCase();
            const cards = document.querySelectorAll('.issue-card');

            cards.forEach(card => {{
                const text = card.innerText.toLowerCase();
                if (!keyword || text.includes(keyword)) {{
                    card.style.display = 'block';
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}

        // 8. 滚动跟随高亮 (ScrollSpy)
        function initScrollSpy() {{
            const links = Array.from(document.querySelectorAll('.toc-link'));
            if (!links.length) return;

            const targets = links.map(link => {{
                const href = link.getAttribute('href');
                if (!href || !href.startsWith('#')) return null;
                const id = decodeURIComponent(href.slice(1));
                return {{
                    link: link,
                    element: document.getElementById(id)
                }};
            }}).filter(item => item && item.element !== null);

            if (!targets.length) return;

            function onScroll() {{
                const scrollPos = window.scrollY + 120;
                let currentItem = targets[0];
                for (let i = 0; i < targets.length; i++) {{
                    if (targets[i].element.offsetTop <= scrollPos) {{
                        currentItem = targets[i];
                    }} else {{
                        break;
                    }}
                }}
                targets.forEach(item => {{
                    if (item === currentItem) {{
                        if (!item.link.classList.contains('active')) {{
                            item.link.classList.add('active');
                            item.link.scrollIntoView({{ block: 'nearest', behavior: 'smooth' }});
                        }}
                    }} else {{
                        item.link.classList.remove('active');
                    }}
                }});
            }}

            window.addEventListener('scroll', onScroll, {{ passive: true }});
            onScroll();
        }}

        // 页面初始化
        (function() {{
            const savedTheme = localStorage.getItem('doc-theme') || 'parchment';
            document.documentElement.setAttribute('data-theme', savedTheme);
            updateThemeBtn(savedTheme);

            const isCollapsed = localStorage.getItem('toc-collapsed') === 'true';
            if (isCollapsed) {{
                document.body.classList.add('toc-collapsed');
            }}

            initScrollSpy();
        }})();
    </script>
</body>
</html>
"""

    html_path.write_text(full_html, encoding="utf-8")
    print(f"[✓] 渲染完成！已成功输出: {html_path} (大小: {len(full_html) // 1024} KB)")



# ==============================================================================
# 通用认知架构与演进规划文档渲染器 (用于 memory_evolution_plan.md 等)
# ==============================================================================

DOC_HTML_SHELL = """<!DOCTYPE html>
<html lang="zh-CN" data-theme="parchment">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{PAGE_TITLE}</title>
    <!-- KaTeX 本地与多重 CDN 双通道高可用样式与字体 -->
    <link rel="stylesheet" href="katex.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.css" onerror="this.onerror=null;this.href='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css';">
    <script src="katex.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.js" onerror="this.onerror=null;this.src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js';"></script>
    <!-- Highlight.js for code syntax highlighting -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css" id="hljs-light">
    <!-- Mermaid.js for dynamic diagrams -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        :root[data-theme="parchment"] {
            --bg-color: #f7f4ec;
            --surface-color: #eee9dc;
            --surface-elevated: #e6dfcf;
            --border-color: #dcd4c0;
            --border-subtle: #e6dfd1;
            --text-primary: #2d3748;
            --text-secondary: #5c687a;
            --text-muted: #798696;
            --accent-primary: #a35d28;
            --accent-glow: rgba(163, 93, 40, 0.08);
            --code-bg: #eae3d2;
            --code-text: #8d3a2b;
            --pre-bg: #ece5d6;
            --pre-text: #2d3748;
            --callout-note-bg: #e5ede3;
            --callout-note-border: #709775;
            --callout-note-text: #2b5133;
            --callout-warn-bg: #f5eedb;
            --callout-warn-border: #c48a37;
            --callout-warn-text: #704b12;
            --callout-imp-bg: #e5eaf5;
            --callout-imp-border: #5c7cb6;
            --callout-imp-text: #1e3863;
            --math-bg: #eee7d7;
            --math-border: #c9bea6;
            --table-header: #e4dccb;
            --table-alt: #f1ecdf;
            --tag-bg: #dfd5be;
            --tag-text: #59472d;
            --toggle-bg: #dfd6c2;
            --card-shadow: 0 4px 18px rgba(45, 55, 72, 0.04);
            --card-hover-shadow: 0 8px 24px rgba(163, 93, 40, 0.1);
            --diagram-bg: #fbf9f3;
            --diagram-box-bg: #ffffff;
            --diagram-box-border: #d2c8b2;
            --diagram-text: #2d3748;
            --diagram-arrow: #8c7853;
        }

        :root[data-theme="twilight"] {
            --bg-color: #1a1e24;
            --surface-color: #232931;
            --surface-elevated: #2c343f;
            --border-color: #39424e;
            --border-subtle: #2d3642;
            --text-primary: #dce1e8;
            --text-secondary: #9da7b3;
            --text-muted: #707b88;
            --accent-primary: #e09f67;
            --accent-glow: rgba(224, 159, 103, 0.1);
            --code-bg: #15181d;
            --code-text: #f08d70;
            --pre-bg: #171b21;
            --pre-text: #cdd3dc;
            --callout-note-bg: #202b28;
            --callout-note-border: #4d7a68;
            --callout-note-text: #8bbfa8;
            --callout-warn-bg: #2b251d;
            --callout-warn-border: #8a6c38;
            --callout-warn-text: #d9b168;
            --callout-imp-bg: #1d2533;
            --callout-imp-border: #4a638c;
            --callout-imp-text: #96b5e3;
            --math-bg: #1f252d;
            --math-border: #3b4654;
            --table-header: #262e38;
            --table-alt: #1f242c;
            --tag-bg: #323c48;
            --tag-text: #d2a679;
            --toggle-bg: #323b47;
            --card-shadow: 0 4px 18px rgba(0, 0, 0, 0.2);
            --card-hover-shadow: 0 8px 24px rgba(224, 159, 103, 0.15);
            --diagram-bg: #171b21;
            --diagram-box-bg: #222933;
            --diagram-box-border: #3f4c5e;
            --diagram-text: #dce1e8;
            --diagram-arrow: #e09f67;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            transition: background-color 0.25s ease, color 0.25s ease, border-color 0.25s ease;
        }

        html {
            scroll-behavior: smooth;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            line-height: 1.7;
            font-size: 15px;
            padding: 0;
            margin: 0;
        }

        .layout-wrapper {
            display: flex;
            min-height: 100vh;
        }

        /* 侧边栏 TOC */
        .sidebar-toc {
            width: 290px;
            background-color: var(--surface-color);
            border-right: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            height: 100vh;
            padding: 24px 18px;
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
            z-index: 100;
        }

        .toc-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 12px;
            margin-bottom: 12px;
            border-bottom: 1px solid var(--border-color);
            flex-shrink: 0;
        }

        .toc-title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.95rem;
            font-weight: 700;
            color: var(--text-primary);
        }

        .toc-action-btn {
            background: none;
            border: none;
            cursor: pointer;
            color: var(--text-muted);
            padding: 4px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .toc-action-btn:hover {
            color: var(--accent-primary);
            background-color: var(--surface-elevated);
        }

        .toc-body {
            flex: 1;
            overflow-y: auto;
            padding-right: 4px;
        }

        .toc-list {
            list-style: none;
        }

        .toc-item {
            margin-bottom: 4px;
        }

        .toc-item.toc-level-2 {
            margin-top: 10px;
            font-weight: 600;
        }

        .toc-item.toc-level-3 {
            padding-left: 14px;
            font-size: 0.88rem;
            color: var(--text-secondary);
        }

        .toc-link {
            display: block;
            padding: 4px 8px;
            color: inherit;
            text-decoration: none;
            border-radius: 4px;
            transition: all 0.2s;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .toc-link:hover {
            background-color: var(--surface-elevated);
            color: var(--accent-primary);
        }

        .toc-link.active {
            background-color: var(--accent-glow);
            color: var(--accent-primary);
            font-weight: 700;
            border-left: 3px solid var(--accent-primary);
        }

        /* 主内容区域 */
        .main-content {
            flex: 1;
            padding: 36px 48px 80px;
            overflow-x: hidden;
        }

        .container {
            max-width: 980px;
            margin: 0 auto;
        }

        .top-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 32px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border-color);
        }

        .nav-links {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .nav-btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 6px;
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            font-size: 0.85rem;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.2s;
        }

        .nav-btn:hover {
            border-color: var(--accent-primary);
            color: var(--accent-primary);
            background-color: var(--surface-elevated);
        }

        .theme-switch-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 14px;
            border-radius: 6px;
            background-color: var(--toggle-bg);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            font-size: 0.85rem;
            cursor: pointer;
            font-weight: 500;
        }

        .theme-switch-btn:hover {
            border-color: var(--accent-primary);
            color: var(--accent-primary);
        }

        /* Markdown 内容体 */
        .markdown-body {
            color: var(--text-primary);
        }

        .markdown-body h1 {
            font-size: 1.95rem;
            font-weight: 800;
            line-height: 1.35;
            margin-bottom: 20px;
            color: var(--text-primary);
            letter-spacing: -0.02em;
        }

        .markdown-body h2 {
            font-size: 1.45rem;
            font-weight: 700;
            line-height: 1.4;
            margin-top: 48px;
            margin-bottom: 18px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-primary);
        }

        .markdown-body h3 {
            font-size: 1.15rem;
            font-weight: 600;
            line-height: 1.45;
            margin-top: 30px;
            margin-bottom: 14px;
            color: var(--text-primary);
        }

        .markdown-body h4 {
            font-size: 1rem;
            font-weight: 600;
            margin-top: 22px;
            margin-bottom: 10px;
            color: var(--text-secondary);
        }

        .markdown-body p {
            margin-bottom: 16px;
            line-height: 1.75;
            color: var(--text-primary);
        }

        .markdown-body ul, .markdown-body ol {
            margin-bottom: 18px;
            padding-left: 24px;
        }

        .markdown-body li {
            margin-bottom: 8px;
            line-height: 1.7;
        }

        .markdown-body strong {
            font-weight: 700;
            color: var(--text-primary);
        }

        .markdown-body code {
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            background-color: var(--code-bg);
            color: var(--code-text);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.9em;
        }

        .markdown-body pre {
            background-color: var(--pre-bg);
            color: var(--pre-text);
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
            border: 1px solid var(--border-color);
            margin: 18px 0 24px;
            line-height: 1.5;
        }

        .markdown-body pre code {
            background-color: transparent;
            color: inherit;
            padding: 0;
            font-size: 0.88rem;
        }

        .doc-intro {
            background-color: var(--surface-color);
            border-left: 4px solid var(--accent-primary);
            padding: 16px 20px;
            border-radius: 0 8px 8px 0;
            margin-bottom: 32px;
            color: var(--text-secondary);
            font-size: 0.96rem;
            line-height: 1.7;
        }

        blockquote {
            background-color: var(--surface-color);
            border-left: 4px solid var(--border-color);
            padding: 12px 18px;
            margin: 18px 0;
            border-radius: 0 6px 6px 0;
            color: var(--text-secondary);
        }

        /* Callout Alerts (Parchment & Twilight) */
        .callout-card {
            border-radius: 8px;
            padding: 16px 20px;
            margin: 22px 0;
            border-left: 4px solid var(--accent-primary);
            background-color: var(--surface-color);
        }

        .callout-card.callout-important {
            background-color: var(--callout-imp-bg);
            border-color: var(--callout-imp-border);
            color: var(--callout-imp-text);
        }

        .callout-card.callout-tip, .callout-card.callout-note {
            background-color: var(--callout-note-bg);
            border-color: var(--callout-note-border);
            color: var(--callout-note-text);
        }

        .callout-card.callout-warn, .callout-card.callout-warning {
            background-color: var(--callout-warn-bg);
            border-color: var(--callout-warn-border);
            color: var(--callout-warn-text);
        }

        .callout-header {
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 700;
            font-size: 0.95rem;
            margin-bottom: 10px;
        }

        .callout-badge {
            display: inline-flex;
            align-items: center;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.03em;
        }

        .callout-important .callout-badge {
            background-color: var(--callout-imp-border);
            color: #ffffff;
        }

        .callout-tip .callout-badge, .callout-note .callout-badge {
            background-color: var(--callout-note-border);
            color: #ffffff;
        }

        .callout-warn .callout-badge {
            background-color: var(--callout-warn-border);
            color: #ffffff;
        }

        .callout-content {
            font-size: 0.92rem;
            line-height: 1.7;
        }

        .callout-content p {
            margin: 6px 0;
            color: inherit;
        }

        .callout-content ul, .callout-content ol {
            margin: 6px 0;
            padding-left: 20px;
            color: inherit;
        }

        .callout-content li {
            margin-bottom: 6px;
            line-height: 1.6;
        }

        .callout-content strong {
            color: inherit;
        }


        .table-wrapper {
            margin: 22px 0 28px;
            overflow-x: auto;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.92rem;
            text-align: left;
        }

        thead tr {
            background-color: var(--table-header);
        }

        th {
            padding: 11px 14px;
            font-weight: 600;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-primary);
        }

        td {
            padding: 11px 14px;
            border-bottom: 1px solid var(--border-subtle);
            color: var(--text-secondary);
        }

        tbody tr:nth-child(even) {
            background-color: var(--table-alt);
        }

        tbody tr:last-child td {
            border-bottom: none;
        }

        .diagram-container {
            margin: 24px 0 32px;
            padding: 24px;
            background-color: var(--diagram-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            display: flex;
            flex-direction: column;
            align-items: center;
            box-shadow: var(--card-shadow);
        }

        .diagram-caption {
            margin-top: 14px;
            font-size: 0.86rem;
            font-weight: 600;
            color: var(--text-muted);
            letter-spacing: 0.03em;
        }

        .math-block {
            background-color: var(--math-bg);
            border: 1px solid var(--math-border);
            border-radius: 8px;
            padding: 14px 18px;
            margin: 18px 0 24px;
            position: relative;
        }

        .math-block-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 10px;
            font-size: 0.78rem;
        }

        .math-badge {
            color: var(--accent-primary);
            font-weight: 600;
            letter-spacing: 0.05em;
        }

        .math-copy-btn {
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            cursor: pointer;
            color: var(--text-secondary);
        }

        .math-copy-btn:hover {
            color: var(--accent-primary);
            border-color: var(--accent-primary);
        }

        .roadmap-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 16px;
            margin: 24px 0 32px;
        }

        .roadmap-card {
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 18px;
            box-shadow: var(--card-shadow);
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .roadmap-card:hover {
            transform: translateY(-2px);
            box-shadow: var(--card-hover-shadow);
            border-color: var(--accent-primary);
        }

        .roadmap-phase {
            font-size: 0.8rem;
            font-weight: 700;
            color: var(--accent-primary);
            text-transform: uppercase;
            margin-bottom: 6px;
        }

        .roadmap-title {
            font-size: 1.02rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 8px;
        }

        .roadmap-desc {
            font-size: 0.86rem;
            color: var(--text-secondary);
            line-height: 1.6;
        }

        body.toc-collapsed .sidebar-toc {
            display: none;
        }
    </style>
</head>
<body>
    <div class="layout-wrapper">
        <aside class="sidebar-toc" id="sidebarToc">
            <div class="toc-header">
                <div class="toc-title">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="8" y1="6" x2="21" y2="6"></line>
                        <line x1="8" y1="12" x2="21" y2="12"></line>
                        <line x1="8" y1="18" x2="21" y2="18"></line>
                        <line x1="3" y1="6" x2="3.01" y2="6"></line>
                        <line x1="3" y1="12" x2="3.01" y2="12"></line>
                        <line x1="3" y1="18" x2="3.01" y2="18"></line>
                    </svg>
                    <span>目录大纲</span>
                </div>
                <button class="toc-action-btn" onclick="toggleDesktopToc()" title="收起大纲">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="15 18 9 12 15 6"></polyline>
                    </svg>
                </button>
            </div>
            <nav class="toc-body">
                <ul class="toc-list">
{TOC_ITEMS}
                </ul>
            </nav>
        </aside>

        <main class="main-content">
            <div class="container">
                <div class="top-bar">
                    <div class="nav-links">
                        <button class="nav-btn" id="expandTocBtn" onclick="toggleDesktopToc()" style="display: none;" title="展开大纲侧边栏">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="9 18 15 12 9 6"></polyline>
                            </svg>
                            <span>显示大纲</span>
                        </button>
                        <a href="update.html" class="nav-btn">排查手册 update.html</a>
                        <span style="color: var(--border-color)">|</span>
                        <span style="font-size: 0.88rem; color: var(--text-muted);">{MD_FILENAME}</span>
                    </div>
                    <button class="theme-switch-btn" onclick="toggleTheme()" id="themeBtn">
                        切换暮色
                    </button>
                </div>

                <article class="markdown-body">
{ARTICLE_BODY}
                </article>
            </div>
        </main>
    </div>

    <script>
        function toggleTheme() {
            const html = document.documentElement;
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'parchment' ? 'twilight' : 'parchment';
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            document.getElementById('themeBtn').innerText = newTheme === 'parchment' ? '切换暮色' : '切换米纸';
        }

        const savedTheme = localStorage.getItem('theme') || 'parchment';
        document.documentElement.setAttribute('data-theme', savedTheme);
        document.getElementById('themeBtn').innerText = savedTheme === 'parchment' ? '切换暮色' : '切换米纸';

        function toggleDesktopToc() {
            document.body.classList.toggle('toc-collapsed');
            const isCollapsed = document.body.classList.contains('toc-collapsed');
            document.getElementById('expandTocBtn').style.display = isCollapsed ? 'inline-flex' : 'none';
        }

        function copyLatex(btn) {
            const tex = btn.getAttribute('data-tex');
            if (tex) {
                navigator.clipboard.writeText(tex).then(() => {
                    const orig = btn.innerText;
                    btn.innerText = '已复制 LaTeX';
                    btn.style.color = 'var(--accent-primary)';
                    setTimeout(() => {
                        btn.innerText = orig;
                        btn.style.color = '';
                    }, 1800);
                }).catch(err => {
                    console.error('复制失败:', err);
                });
            }
        }

        window.addEventListener('DOMContentLoaded', () => {
            if (window.katex) {
                document.querySelectorAll('.katex-inline').forEach(el => {
                    const tex = el.getAttribute('data-tex');
                    if (tex) {
                        try {
                            el.innerHTML = katex.renderToString(tex, { displayMode: false, throwOnError: false });
                        } catch(e) {}
                    }
                });

                document.querySelectorAll('.katex-display-container').forEach(el => {
                    const tex = el.getAttribute('data-tex');
                    if (tex) {
                        try {
                            el.innerHTML = katex.renderToString(tex, { displayMode: true, throwOnError: false });
                        } catch(e) {}
                    }
                });
            }

            if (window.mermaid) {
                mermaid.initialize({
                    startOnLoad: true,
                    theme: document.documentElement.getAttribute('data-theme') === 'twilight' ? 'dark' : 'neutral'
                });
            }

            if (window.hljs) {
                hljs.highlightAll();
            }

            const links = document.querySelectorAll('.toc-link');
            const sections = [];
            links.forEach(link => {
                const targetId = link.getAttribute('href').slice(1);
                const section = document.getElementById(targetId);
                if (section) {
                    sections.push({ id: targetId, el: section, link: link });
                }
            });

            window.addEventListener('scroll', () => {
                const scrollPos = window.scrollY + 100;
                let activeId = null;
                for (let i = 0; i < sections.length; i++) {
                    if (sections[i].el.offsetTop <= scrollPos) {
                        activeId = sections[i].id;
                    }
                }
                links.forEach(link => {
                    if (link.getAttribute('href') === '#' + activeId) {
                        link.classList.add('active');
                    } else {
                        link.classList.remove('active');
                    }
                });
            });
        });
    </script>
</body>
</html>
"""

def parse_doc_markdown(md_text: str):
    lines = md_text.splitlines()
    title = "跨会话长程记忆认知架构演进方案"
    body_parts = []
    toc_items = []
    
    i = 0
    n = len(lines)
    
    in_code_block = False
    code_lang = ""
    code_lines = []
    
    in_raw_html_block = False
    raw_html_lines = []
    
    in_table = False
    table_lines = []
    
    def flush_table():
        nonlocal in_table, table_lines
        if not in_table or not table_lines:
            in_table = False
            table_lines = []
            return
        
        headers = [c.strip() for c in table_lines[0].strip('|').split('|')]
        rows = []
        for line in table_lines[2:]:
            cols = [c.strip() for c in line.strip('|').split('|')]
            if cols:
                rows.append(cols)
                
        th_html = "".join([f"<th>{h}</th>" for h in headers])
        tr_html = []
        for r in rows:
            tds = []
            for c in r:
                c_fmt = c
                c_fmt = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', c_fmt)
                c_fmt = re.sub(r'`(.*?)`', r'<code>\1</code>', c_fmt)
                c_fmt = re.sub(r'\$(.*?)\$', r'<span class="katex-inline" data-tex="\1">$\1$</span>', c_fmt)
                tds.append(f"<td>{c_fmt}</td>")
            tr_html.append(f"<tr>{''.join(tds)}</tr>")
            
        table_html = f"""
        <div class="table-wrapper">
            <table>
                <thead><tr>{th_html}</tr></thead>
                <tbody>
                    {''.join(tr_html)}
                </tbody>
            </table>
        </div>
        """
        body_parts.append(table_html)
        in_table = False
        table_lines = []

    while i < n:
        line = lines[i]
        line_s = line.strip()
        
        # Raw HTML (like <div class="diagram-container"> or <svg> or <div class="roadmap-grid">)
        if not in_code_block and not in_raw_html_block:
            if line_s.startswith('<div class="diagram-container">') or line_s.startswith('<svg') or line_s.startswith('<div class="roadmap-grid">'):
                flush_table()
                in_raw_html_block = True
                raw_html_lines = [line]
                i += 1
                continue
                
        if in_raw_html_block:
            raw_html_lines.append(line)
            if line_s == '</div>' and (len(raw_html_lines) > 2 and ('</div>' in raw_html_lines[-2] or '</svg>' in raw_html_lines[-2] or '</div>' in raw_html_lines[-1])):
                body_parts.append("\n".join(raw_html_lines))
                in_raw_html_block = False
                raw_html_lines = []
            elif line_s == '</svg>' and not any('diagram-container' in l for l in raw_html_lines):
                body_parts.append("\n".join(raw_html_lines))
                in_raw_html_block = False
                raw_html_lines = []
            i += 1
            continue

        # Code block
        if line_s.startswith('```'):
            flush_table()
            if in_code_block:
                in_code_block = False
                full_code = "\n".join(code_lines)
                if code_lang == 'mermaid':
                    body_parts.append(f'<div class="mermaid">\n{full_code}\n</div>')
                else:
                    body_parts.append(f'<pre><code class="language-{code_lang}">{html.escape(full_code)}</code></pre>')
                code_lines = []
                code_lang = ""
            else:
                in_code_block = True
                code_lang = line_s[3:].strip()
                code_lines = []
            i += 1
            continue
            
        if in_code_block:
            code_lines.append(line)
            i += 1
            continue
            
        # Table
        if line_s.startswith('|') and line_s.endswith('|'):
            in_table = True
            table_lines.append(line_s)
            i += 1
            continue
        elif in_table:
            flush_table()

        if not line_s:
            i += 1
            continue
            
        # HTML comments
        if line_s.startswith('<!--'):
            body_parts.append(line)
            i += 1
            continue
            
        # Title (# )
        if line_s.startswith('# '):
            title = line_s[2:].strip()
            body_parts.append(f'<h1>{title}</h1>')
            i += 1
            continue
            
        # Blockquote / Callout / Intro 处理
        if line_s.startswith('>'):
            quote_lines = []
            while i < n and (lines[i].strip().startswith('>') or (lines[i].strip() and quote_lines and lines[i].startswith('   '))):
                raw_q = lines[i].strip()
                if raw_q.startswith('>'):
                    cleaned = raw_q[1:].strip()
                else:
                    cleaned = raw_q.strip()
                quote_lines.append(cleaned)
                i += 1
            
            if not quote_lines:
                continue

            first_line = quote_lines[0]
            
            # 1. 顶层文档定位/方案概述
            if first_line.startswith('**文档定位**') or first_line.startswith('**方案概述**'):
                intro_text = " ".join([q for q in quote_lines if q])
                intro_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', intro_text)
                body_parts.append(f'<div class="doc-intro">{intro_text}</div>')
                continue
                
            # 2. GitHub-style Alert Callout ([!IMPORTANT], [!TIP], [!NOTE], [!WARNING], [!CAUTION])
            alert_m = re.match(r'^\[!(IMPORTANT|TIP|NOTE|WARNING|CAUTION)\]$', first_line, re.IGNORECASE)
            alert_type = None
            badge_text = ""
            content_lines = quote_lines
            
            if alert_m:
                raw_type = alert_m.group(1).lower()
                content_lines = quote_lines[1:]
                if raw_type in ['important', 'caution']:
                    alert_type = 'important'
                    badge_text = '重点规范'
                elif raw_type in ['tip']:
                    alert_type = 'tip'
                    badge_text = '架构提示'
                elif raw_type in ['warning']:
                    alert_type = 'warn'
                    badge_text = '风险告警'
                else:
                    alert_type = 'note'
                    badge_text = '说明'
            elif '【重点规范】' in first_line:
                alert_type = 'important'
                badge_text = '重点规范'
            elif '【核心架构收益】' in first_line or '【架构收益】' in first_line:
                alert_type = 'tip'
                badge_text = '核心收益'
                
            inner_html_parts = []
            j = 0
            m_len = len(content_lines)
            while j < m_len:
                c_line = content_lines[j].strip()
                if not c_line:
                    j += 1
                    continue
                if c_line.startswith('- ') or c_line.startswith('* '):
                    items = []
                    while j < m_len and (content_lines[j].strip().startswith('- ') or content_lines[j].strip().startswith('* ')):
                        it = content_lines[j].strip()[2:].strip()
                        it = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', it)
                        it = re.sub(r'`(.*?)`', r'<code>\1</code>', it)
                        it = re.sub(r'\$(.*?)\$', r'<span class="katex-inline" data-tex="\1">$\1$</span>', it)
                        items.append(f'<li>{it}</li>')
                        j += 1
                    inner_html_parts.append(f'<ul>{"".join(items)}</ul>')
                    continue
                num_m = re.match(r'^\d+\.\s+(.*)', c_line)
                if num_m:
                    items = []
                    while j < m_len and re.match(r'^\d+\.\s+(.*)', content_lines[j].strip()):
                        it = re.match(r'^\d+\.\s+(.*)', content_lines[j].strip()).group(1)
                        it = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', it)
                        it = re.sub(r'`(.*?)`', r'<code>\1</code>', it)
                        it = re.sub(r'\$(.*?)\$', r'<span class="katex-inline" data-tex="\1">$\1$</span>', it)
                        items.append(f'<li>{it}</li>')
                        j += 1
                    inner_html_parts.append(f'<ol>{"".join(items)}</ol>')
                    continue
                fmt_line = c_line
                fmt_line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', fmt_line)
                fmt_line = re.sub(r'`(.*?)`', r'<code>\1</code>', fmt_line)
                fmt_line = re.sub(r'\$(.*?)\$', r'<span class="katex-inline" data-tex="\1">$\1$</span>', fmt_line)
                inner_html_parts.append(f'<p>{fmt_line}</p>')
                j += 1
                
            inner_html = "\n".join(inner_html_parts)
            
            if alert_type:
                callout_html = f"""
                <div class="callout-card callout-{alert_type}">
                    <div class="callout-header">
                        <span class="callout-badge">{badge_text}</span>
                    </div>
                    <div class="callout-content">
                        {inner_html}
                    </div>
                </div>
                """
                body_parts.append(callout_html)
            else:
                body_parts.append(f'<blockquote>{inner_html}</blockquote>')
            continue

            
        if line_s in ['---', '***', '___']:
            body_parts.append('<hr style="border: none; border-top: 1px solid var(--border-color); margin: 36px 0;">')
            i += 1
            continue
            
        # Headings
        if line_s.startswith('## '):
            h_text = line_s[3:].strip()
            h_id = re.sub(r'[\s、，（）()]+', '_', h_text).strip('_')
            toc_items.append({'level': 2, 'id': h_id, 'title': h_text})
            body_parts.append(f'<h2 id="{h_id}">{h_text}</h2>')
            i += 1
            continue
            
        if line_s.startswith('### '):
            h_text = line_s[4:].strip()
            h_id = re.sub(r'[\s、，（）()]+', '_', h_text).strip('_')
            toc_items.append({'level': 3, 'id': h_id, 'title': h_text})
            body_parts.append(f'<h3 id="{h_id}">{h_text}</h3>')
            i += 1
            continue

        if line_s.startswith('#### '):
            h_text = line_s[5:].strip()
            h_id = re.sub(r'[\s、，（）()]+', '_', h_text).strip('_')
            body_parts.append(f'<h4 id="{h_id}">{h_text}</h4>')
            i += 1
            continue
            
        # Display Math ($$...$$)
        if line_s.startswith('$$'):
            math_lines = []
            if line_s.endswith('$$') and len(line_s) > 2:
                tex = line_s[2:-2].strip()
            else:
                math_lines.append(line_s[2:].strip())
                i += 1
                while i < n and not lines[i].strip().endswith('$$'):
                    math_lines.append(lines[i])
                    i += 1
                if i < n:
                    last_l = lines[i].strip()
                    math_lines.append(last_l[:-2].strip())
                tex = "\n".join(math_lines).strip()
                
            block_html = f"""
            <div class="math-block" data-tex="{html.escape(tex)}">
                <div class="math-block-header">
                    <span class="math-badge">LaTeX · 公式定义</span>
                    <button class="math-copy-btn" onclick="copyLatex(this)" data-tex="{html.escape(tex)}">复制 LaTeX</button>
                </div>
                <div class="katex-display-container" data-tex="{html.escape(tex)}"></div>
            </div>
            """
            body_parts.append(block_html)
            i += 1
            continue
            
        # Bullet list
        if line_s.startswith('- ') or line_s.startswith('* '):
            list_items = []
            while i < n and (lines[i].strip().startswith('- ') or lines[i].strip().startswith('* ')):
                item_text = lines[i].strip()[2:].strip()
                item_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', item_text)
                item_text = re.sub(r'`(.*?)`', r'<code>\1</code>', item_text)
                item_text = re.sub(r'\$(.*?)\$', r'<span class="katex-inline" data-tex="\1">$\1$</span>', item_text)
                list_items.append(f'<li>{item_text}</li>')
                i += 1
            body_parts.append(f'<ul>\n{"".join(list_items)}\n</ul>')
            continue
            
        # Numbered list
        num_m = re.match(r'^\d+\.\s+(.*)', line_s)
        if num_m:
            list_items = []
            while i < n and re.match(r'^\d+\.\s+(.*)', lines[i].strip()):
                item_text = re.match(r'^\d+\.\s+(.*)', lines[i].strip()).group(1)
                item_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', item_text)
                item_text = re.sub(r'`(.*?)`', r'<code>\1</code>', item_text)
                item_text = re.sub(r'\$(.*?)\$', r'<span class="katex-inline" data-tex="\1">$\1$</span>', item_text)
                list_items.append(f'<li>{item_text}</li>')
                i += 1
            body_parts.append(f'<ol>\n{"".join(list_items)}\n</ol>')
            continue
            
        # Normal paragraph
        p_text = line
        p_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', p_text)
        p_text = re.sub(r'`(.*?)`', r'<code>\1</code>', p_text)
        p_text = re.sub(r'\$(.*?)\$', r'<span class="katex-inline" data-tex="\1">$\1$</span>', p_text)
        body_parts.append(f'<p>{p_text}</p>')
        i += 1

    flush_table()
    
    toc_html_list = []
    for item in toc_items:
        cls = "toc-level-2" if item['level'] == 2 else "toc-level-3"
        toc_html_list.append(f'<li class="toc-item {cls}"><a href="#{item["id"]}" class="toc-link">{item["title"]}</a></li>')
        
    toc_html = "\n".join(toc_html_list)
    body_html = "\n".join(body_parts)
    return title, toc_html, body_html

def render_evolution_plan_page(md_path: Path, html_path: Path):
    print(f"[*] 读取 Markdown 源文件: {md_path}")
    md_text = md_path.read_text(encoding="utf-8")
    title, toc_html, body_html = parse_doc_markdown(md_text)
    
    full_html = DOC_HTML_SHELL
    full_html = full_html.replace("{PAGE_TITLE}", title)
    full_html = full_html.replace("{MD_FILENAME}", md_path.name)
    full_html = full_html.replace("{TOC_ITEMS}", toc_html)
    full_html = full_html.replace("{ARTICLE_BODY}", body_html)
    
    html_path.write_text(full_html, encoding="utf-8")
    print(f"[+] 渲染完成！已成功输出: {html_path} (大小: {len(full_html) // 1024} KB)")


if __name__ == '__main__':
    curr_dir = Path(__file__).resolve().parent
    args = sys.argv[1:]
    
    if args:
        target = Path(args[0])
        if not target.is_absolute():
            target = (curr_dir / target) if (curr_dir / target).exists() else target.resolve()
            
        if not target.exists():
            print(f"[ERROR] 找不到指定的 Markdown 文件: {target}")
            sys.exit(1)
            
        if "update" in target.name.lower():
            render_html_page(target, target.with_suffix(".html"))
        else:
            render_evolution_plan_page(target, target.with_suffix(".html"))
    else:
        # 无参数模式：自动全量渲染 docs/ 下的主要 Markdown 文档
        print("=" * 60)
        print("[*] render_html.py: 扫描并全量渲染 Markdown 文档")
        print("=" * 60)
        
        up_md = curr_dir / "update.md"
        if up_md.exists():
            render_html_page(up_md, curr_dir / "update.html")
            
        ev_md = curr_dir / "memory_evolution_plan.md"
        if ev_md.exists():
            render_evolution_plan_page(ev_md, curr_dir / "memory_evolution_plan.html")
            
        print("=" * 60)
        print("[+] 全部文档渲染完成！")
        print("=" * 60)

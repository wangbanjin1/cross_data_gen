#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨会话长程认知记忆数据集文档中心 HTML 渲染引擎 (docs/render_html.py)
----------------------------------------------------------------------
功能特性：
  1. 自动扫描并渲染 docs/ 下全量 Markdown 文档（含根目录、specs/、guides/、archive/）
  2. 双主题支持：Parchment（米纸学术）与 Twilight（暮色极简）一键切换
  3. 跨文档全局门户导航：支持在所有 HTML 文档间无缝跳转，自动重写内部 .md 链接为 .html
  4. Mermaid 图表规范强化：严格遵循纯白底色 (#FFFFFF)、全量粗体文字、2px~2.5px 加粗线条
  5. KaTeX 数学公式渲染：支持块级公式 ($$...$$) 一键复制 LaTeX 与行内公式 ($...$) 安全隔离渲染
  6. 专属视图支持：defect_triage_log.md 支持分栏对比卡片 + 分类筛选 + 实时检索视图；所有文档均支持阅读视图与 Markdown 源码视图切换
"""

import sys
import re
import html
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


DOCS_PORTAL_ITEMS = [
    ("README.html", "文档中心总览 (README)"),
    ("specs/cognitive_memory_dev_spec.html", "三层认知记忆与双轨评测规范"),
    ("跨 Session 记忆数据集生成器思路.html", "跨 Session 生成器总体设计"),
    ("记忆建模与数据集生成要求.html", "记忆建模与生成要求"),
    ("specs/persona_spec.html", "Persona 画像建模规范"),
    ("guides/cli_usage.html", "CLI 命令行与流水线指南"),
    ("archive/defect_triage_log.html", "001~150 批次缺陷治理实录"),
    ("archive/memory_evolution_proposal.html", "认知架构演进提案 (RFC)"),
]


def build_portal_links_html(rel_prefix: str, current_rel_html: str) -> str:
    links = []
    norm_curr = current_rel_html.replace("\\", "/")
    for href, label in DOCS_PORTAL_ITEMS:
        active_cls = " active" if href == norm_curr else ""
        full_href = f"{rel_prefix}{href}"
        links.append(
            f'<a href="{full_href}" class="portal-nav-item{active_cls}" title="{html.escape(label)}">{html.escape(label)}</a>'
        )
    return "\n".join(links)


def format_inline_markdown(text: str) -> str:
    """
    安全处理行内 Markdown 语法：
    1. 保护行内代码 `...`
    2. 保护行内数学公式 $...$
    3. 转换 Markdown 链接 [text](url)，自动将相对路径 .md 转为 .html
    4. 转换粗体 **...** 与斜体 *...*
    """
    if not text:
        return ""

    placeholders = {}
    counter = [0]

    def store_ph(val: str) -> str:
        key = f"@@PH_{counter[0]}@@"
        counter[0] += 1
        placeholders[key] = val
        return key

    # 1. 保护行内代码 `...`
    def repl_code(m):
        code_inner = html.escape(m.group(1))
        return store_ph(f"<code>{code_inner}</code>")

    text = re.sub(r"`([^`]+)`", repl_code, text)

    # 2. 保护行内块级公式 $$...$$ 与行内公式 $...$ (避免匹配货币或空 $)
    def repl_display_math(m):
        tex = m.group(1).strip()
        if not tex:
            return m.group(0)
        esc_tex = html.escape(tex)
        return store_ph(
            f'<div class="math-block" data-tex="{esc_tex}"><div class="katex-display-container" data-tex="{esc_tex}">$${esc_tex}$$</div></div>'
        )

    text = re.sub(r"\$\$([^$\n]+?)\$\$", repl_display_math, text)

    def repl_math(m):
        tex = m.group(1).strip()
        if not tex:
            return m.group(0)
        esc_tex = html.escape(tex)
        return store_ph(f'<span class="katex-inline" data-tex="{esc_tex}">${esc_tex}$</span>')

    text = re.sub(r"(?<!\$)\$(?!\$)([^$\n]+?)(?<!\$)\$(?!\$)", repl_math, text)

    # 3. 转换链接 [label](href)
    def repl_link(m):
        label = m.group(1)
        href = m.group(2).strip()
        # 将指向本地 .md 的链接自动转为 .html
        if not href.startswith(("http://", "https://", "mailto:", "#")):
            if ".md#" in href:
                href = href.replace(".md#", ".html#")
            elif href.endswith(".md"):
                href = href[:-3] + ".html"
        label_fmt = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", label)
        return store_ph(f'<a href="{href}" class="md-link">{label_fmt}</a>')

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", repl_link, text)

    # 4. 转换粗体 **...**
    text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)

    # 还原占位符
    for key, val in placeholders.items():
        text = text.replace(key, val)

    return text


def slugify_heading(h_text: str) -> str:
    clean = re.sub(r"<[^>]+>", "", h_text)
    clean = re.sub(r"[`*_~]", "", clean)
    clean = re.sub(r"[^\w\u4e00-\u9fa5\- ]+", "", clean).strip()
    clean = re.sub(r"\s+", "-", clean).lower()
    return clean or "section"


# ==============================================================================
# 专用渲染器 1：排查与治理实录卡片视图 (用于 archive/defect_triage_log.md)
# ==============================================================================

def md_text_to_html(md_chunk: str) -> str:
    lines = md_chunk.strip().splitlines()
    out = []
    for line in lines:
        line_s = line.strip()
        if not line_s:
            continue
        if line_s.startswith("#### "):
            sub = line_s[5:].strip().strip("【】")
            out.append(f'<div class="section-sublabel">{format_inline_markdown(sub)}</div>')
            continue

        list_match = re.match(r"^\s*(\d+\.|\-|\•|\*)\s+(.*)", line)
        if list_match:
            prefix = list_match.group(1)
            item_text = format_inline_markdown(list_match.group(2))
            out.append(
                f'<div class="bullet-item"><span class="bullet-prefix">{prefix}</span><div class="bullet-content">{item_text}</div></div>'
            )
        else:
            out.append(f"<p>{format_inline_markdown(line_s)}</p>")
    return "\n".join(out)


def extract_contrasts(body: str):
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

    bad_m = re.search(
        r"\*\*(?:修复前|问题表现|改造前|优化前|传统做法)(.*?)\*\*\s*[:：]?\s*```([a-zA-Z0-9_-]*)\n(.*?)```",
        contrast_chunk,
        re.DOTALL,
    )
    good_m = re.search(
        r"\*\*(?:修复后|规范表现|改造后|优化后|现行)(.*?)\*\*\s*[:：]?\s*```([a-zA-Z0-9_-]*)\n(.*?)```",
        contrast_chunk,
        re.DOTALL,
    )

    if bad_m and good_m:
        bad_title = bad_m.group(1).strip(" ：:（）()") or "缺陷表现"
        bad_lang = bad_m.group(2).strip() or "JSON"
        bad_code = bad_m.group(3).strip()

        good_title = good_m.group(1).strip(" ：:（）()") or "规范表现"
        good_lang = good_m.group(2).strip() or "JSON"
        good_code = good_m.group(3).strip()
        return clean_body, bad_title, bad_code, bad_lang, good_title, good_code, good_lang

    code_blocks = re.findall(r"```([a-zA-Z0-9_-]*)\n(.*?)```", contrast_chunk, re.DOTALL)
    if len(code_blocks) >= 2:
        bad_lang = code_blocks[0][0].strip() or "TEXT"
        bad_code = code_blocks[0][1].strip()
        good_lang = code_blocks[1][0].strip() or "TEXT"
        good_code = code_blocks[1][1].strip()
        return clean_body, "缺陷表现", bad_code, bad_lang, "规范表现", good_code, good_lang

    return clean_body, "缺陷表现", "", "TEXT", "规范表现", "", "TEXT"


def parse_summary_table(md_text: str) -> str:
    table_m = re.search(
        r"##\s*(?:[一二三四五]、|栏目[一二三四五][：:])?实测修复结果与验证数据汇总.*?\n(.*?)(?=\n##|\Z)",
        md_text,
        re.DOTALL,
    )
    if not table_m:
        return ""
    chunk = table_m.group(1)
    t_lines = [l.strip() for l in chunk.splitlines() if l.strip().startswith("|")]
    if len(t_lines) < 3:
        return ""

    headers = [format_inline_markdown(c.strip()) for c in t_lines[0].strip("|").split("|")]
    rows_html = []
    for line in t_lines[2:]:
        cols = [format_inline_markdown(c.strip()) for c in line.strip("|").split("|")]
        if len(cols) >= 3:
            rows_html.append("<tr>" + "".join(f"<td>{c}</td>" for c in cols) + "</tr>")

    th_html = "".join([f"<th>{h}</th>" for h in headers])
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


def render_triage_card_page(md_path: Path, html_path: Path, docs_root: Path):
    print(f"[*] 渲染排查实录卡片页面: {md_path.relative_to(docs_root)}")
    md_text = md_path.read_text(encoding="utf-8")

    rel_html = html_path.relative_to(docs_root).as_posix()
    depth = len(html_path.relative_to(docs_root).parts) - 1
    rel_prefix = "../" * depth
    portal_links_html = build_portal_links_html(rel_prefix, rel_html)

    sections = re.split(r"\n##\s+", md_text)
    cards = []
    idx = 1

    for sec in sections[1:]:
        sec_title = sec.splitlines()[0].strip()
        if any(k in sec_title for k in ["时间线归档", "实测修复结果", "核心元数据", "目录大纲"]):
            continue

        if "架构" in sec_title or "拓扑" in sec_title:
            cat_code = "arch"
            badge_title = "架构拓扑"
        elif "多样性" in sec_title or "提示词" in sec_title:
            cat_code = "gov"
            badge_title = "多样性规范"
        else:
            cat_code = "bug"
            badge_title = "缺陷修复"

        h3_blocks = re.findall(r"(?:^|\n)###\s+([^#\n].*?)\n(.*?)(?=\n###\s+[^#]|\n##\s+|\Z)", sec, re.DOTALL)
        for title_raw, body_raw in h3_blocks:
            title = title_raw.strip()
            date_cat_m = re.search(r">\s*\*\*归档时间\*\*[：:]\s*`?(.*?)`?\s*\|\s*\*\*分类\*\*[：:]\s*`?(.*?)`?", body_raw)
            date_tag = date_cat_m.group(1).strip() if date_cat_m else "2026-10"

            clean_body, bad_title, bad_code, bad_lang, good_title, good_code, good_lang = extract_contrasts(body_raw)
            clean_body = re.sub(r"^\s*>\s*\*\*归档时间\*\*.*?\n+", "", clean_body).strip()
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

    arch_cards = [c for c in cards if c["cat_code"] == "arch"]
    gov_cards = [c for c in cards if c["cat_code"] == "gov"]
    bug_cards = [c for c in cards if c["cat_code"] == "bug"]

    def render_toc_link(c):
        short_title = c["title"][:26] + "..." if len(c["title"]) > 26 else c["title"]
        return f"""
        <li class="toc-item">
            <a href="#{c['id']}" class="toc-link" data-target="{c['id']}" title="{html.escape(c['title'])}">
                <span class="toc-text">{html.escape(short_title)}</span>
            </a>
        </li>"""

    toc_html_parts = []
    if arch_cards:
        toc_html_parts.append('<div class="toc-group-title">架构设计与模板拓扑</div><ul class="toc-list">')
        for c in arch_cards:
            toc_html_parts.append(render_toc_link(c))
        toc_html_parts.append("</ul>")

    if gov_cards:
        toc_html_parts.append('<div class="toc-group-title">数据多样性与提示词规则</div><ul class="toc-list">')
        for c in gov_cards:
            toc_html_parts.append(render_toc_link(c))
        toc_html_parts.append("</ul>")

    if bug_cards:
        toc_html_parts.append('<div class="toc-group-title">核心缺陷排查与治理</div><ul class="toc-list">')
        for c in bug_cards:
            toc_html_parts.append(render_toc_link(c))
        toc_html_parts.append("</ul>")

    toc_html_parts.append("""
        <div class="toc-group-title">实测验证与数据对比</div>
        <ul class="toc-list">
            <li class="toc-item">
                <a href="#summary-section" class="toc-link" data-target="summary-section">
                    <span class="toc-text">全量质检对照表</span>
                </a>
            </li>
        </ul>
    """)
    toc_html = "\n".join(toc_html_parts)

    def render_card(c):
        badge_class = f"badge-{c['cat_code']}"
        return f"""
        <article class="issue-card" id="{c['id']}" data-cat="{c['cat_code']}">
            <div class="issue-header">
                <div class="issue-title-group">
                    <span class="issue-num">{c['idx']}</span>
                    <h2>{html.escape(c['title'])}</h2>
                </div>
                <div class="issue-tag-group">
                    <span class="issue-cat-badge {badge_class}">{c['cat_name']}</span>
                    <span class="issue-date-tag">{html.escape(c['date_tag'])}</span>
                </div>
            </div>
            <div class="desc-block">
                {c['desc_html']}
            </div>
            <div class="contrast-grid">
                <div class="contrast-box bad">
                    <div class="contrast-header">
                        <div class="contrast-title"><span class="contrast-pill-bad">修复前</span> {html.escape(c['bad_title'])}</div>
                        <span class="code-lang-tag">{c['bad_lang']}</span>
                    </div>
                    <div class="code-block">
                        <div class="code-header">
                            <span class="code-lang">修复前</span>
                            <button class="copy-btn" onclick="copyCode(this)"><span>复制</span></button>
                        </div>
                        <pre><code>{html.escape(c['bad_code'])}</code></pre>
                    </div>
                </div>
                <div class="contrast-box good">
                    <div class="contrast-header">
                        <div class="contrast-title"><span class="contrast-pill-good">修复后</span> {html.escape(c['good_title'])}</div>
                        <span class="code-lang-tag">{c['good_lang']}</span>
                    </div>
                    <div class="code-block">
                        <div class="code-header">
                            <span class="code-lang">修复后</span>
                            <button class="copy-btn" onclick="copyCode(this)"><span>复制</span></button>
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

    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="parchment">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>跨会话长程记忆数据集：生成问题排查与数据治理实录</title>
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

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        html {{ scroll-behavior: smooth; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            line-height: 1.8;
            padding: 24px 16px;
            font-size: 15px;
        }}
        .layout-wrapper {{
            display: flex;
            justify-content: center;
            align-items: flex-start;
            max-width: 1420px;
            margin: 0 auto;
            gap: 28px;
        }}
        .sidebar-toc {{
            width: 310px;
            flex-shrink: 0;
            position: sticky;
            top: 20px;
            max-height: calc(100vh - 40px);
            display: flex;
            flex-direction: column;
        }}
        .toc-card {{
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px 14px;
            display: flex;
            flex-direction: column;
            max-height: calc(100vh - 40px);
            box-shadow: var(--card-shadow);
        }}
        .portal-nav-box {{
            margin-bottom: 12px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border-color);
        }}
        .portal-nav-title {{
            font-size: 0.76rem;
            font-weight: 700;
            color: var(--accent-primary);
            margin-bottom: 6px;
            letter-spacing: 0.04em;
        }}
        .portal-nav-list {{
            display: flex;
            flex-direction: column;
            gap: 2px;
        }}
        .portal-nav-item {{
            display: block;
            padding: 4px 8px;
            font-size: 0.8rem;
            color: var(--text-secondary);
            text-decoration: none;
            border-radius: 5px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .portal-nav-item:hover {{
            background: var(--surface-elevated);
            color: var(--accent-primary);
        }}
        .portal-nav-item.active {{
            background: var(--accent-glow);
            color: var(--accent-primary);
            font-weight: 700;
            border-left: 3px solid var(--accent-primary);
        }}
        .toc-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 10px;
            margin-bottom: 10px;
            border-bottom: 1px solid var(--border-color);
        }}
        .toc-title {{ font-size: 0.92rem; font-weight: 700; }}
        .toc-action-btn {{
            background: transparent;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            padding: 4px;
        }}
        .search-box {{ margin-bottom: 10px; }}
        .search-input {{
            width: 100%;
            padding: 7px 10px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            background: var(--bg-color);
            font-size: 0.83rem;
            color: var(--text-primary);
        }}
        .category-pills {{
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border-color);
        }}
        .cat-pill {{
            background: var(--tag-bg);
            color: var(--tag-text);
            border: none;
            padding: 3px 8px;
            border-radius: 5px;
            font-size: 0.74rem;
            font-weight: 600;
            cursor: pointer;
        }}
        .cat-pill.active {{
            background: var(--accent-primary);
            color: #ffffff;
        }}
        .toc-body {{ overflow-y: auto; flex: 1; padding-right: 4px; }}
        .toc-group-title {{
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--accent-primary);
            margin: 8px 0 4px 6px;
        }}
        .toc-list {{ list-style: none; }}
        .toc-item {{ margin: 2px 0; }}
        .toc-link {{
            display: block;
            padding: 4px 8px;
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 0.81rem;
            border-radius: 5px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .toc-link:hover, .toc-link.active {{
            color: var(--accent-primary);
            background: var(--accent-glow);
        }}
        body.toc-collapsed .sidebar-toc {{ display: none; }}
        body.toc-collapsed #expandTocBtn {{ display: inline-flex !important; }}
        .main-content {{ flex: 1; min-width: 0; max-width: 1040px; }}
        .top-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .nav-links {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
        .nav-btn {{
            background-color: var(--surface-color);
            color: var(--text-secondary);
            border: 1px solid var(--border-color);
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 0.83rem;
            text-decoration: none;
            cursor: pointer;
        }}
        .nav-btn:hover, .nav-btn.active {{
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
            font-size: 0.83rem;
            cursor: pointer;
            font-weight: 600;
        }}
        header.doc-header {{
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 22px;
            margin-bottom: 28px;
        }}
        .header-tag {{
            display: inline-block;
            background: var(--tag-bg);
            color: var(--tag-text);
            font-size: 0.78rem;
            font-weight: 650;
            padding: 3px 10px;
            border-radius: 4px;
            margin-bottom: 10px;
        }}
        h1.doc-title {{ font-size: 1.9rem; margin-bottom: 10px; }}
        .doc-lead {{ font-size: 0.93rem; color: var(--text-secondary); margin-bottom: 16px; }}
        .md-link {{ color: var(--accent-primary); text-decoration: underline; font-weight: 600; }}
        .header-meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
            gap: 10px;
        }}
        .meta-stat-card {{
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 10px 14px;
        }}
        .meta-stat-label {{ font-size: 0.74rem; color: var(--text-muted); }}
        .meta-stat-val {{ font-size: 1.02rem; font-weight: 700; color: var(--accent-primary); }}
        .column-section-header {{
            margin: 34px 0 18px;
            padding-bottom: 8px;
            border-bottom: 2px solid var(--border-color);
            display: flex;
            align-items: baseline;
            gap: 12px;
            flex-wrap: wrap;
        }}
        .column-section-header h2 {{
            font-size: 1.35rem;
            border-left: 4px solid var(--accent-primary);
            padding-left: 10px;
        }}
        .column-section-desc {{ font-size: 0.83rem; color: var(--text-muted); }}
        .issue-card {{
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px 22px;
            margin-bottom: 22px;
            box-shadow: var(--card-shadow);
        }}
        .issue-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 10px;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .issue-title-group {{ display: flex; align-items: center; gap: 10px; }}
        .issue-num {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 26px;
            height: 26px;
            border-radius: 50%;
            background: var(--surface-elevated);
            color: var(--accent-primary);
            font-size: 0.82rem;
            font-weight: 700;
        }}
        .issue-header h2 {{ font-size: 1.08rem; font-weight: 650; }}
        .issue-tag-group {{ display: flex; gap: 6px; align-items: center; }}
        .issue-cat-badge {{ font-size: 0.72rem; padding: 2px 8px; border-radius: 4px; font-weight: 650; }}
        .badge-arch {{ background: var(--callout-imp-bg); color: var(--callout-imp-text); border: 1px solid var(--callout-imp-border); }}
        .badge-gov {{ background: var(--callout-warn-bg); color: var(--callout-warn-text); border: 1px solid var(--callout-warn-border); }}
        .badge-bug {{ background: var(--callout-note-bg); color: var(--callout-note-text); border: 1px solid var(--callout-note-border); }}
        .issue-date-tag {{
            font-size: 0.75rem;
            color: var(--text-muted);
            background: var(--surface-elevated);
            border: 1px solid var(--border-color);
            padding: 2px 8px;
            border-radius: 4px;
        }}
        .desc-block {{ margin-bottom: 14px; font-size: 0.91rem; }}
        .section-sublabel {{ font-weight: 700; color: var(--accent-primary); margin: 12px 0 6px; }}
        .bullet-item {{ display: flex; gap: 8px; margin-bottom: 6px; }}
        .bullet-prefix {{ color: var(--accent-primary); font-weight: 700; }}
        code {{
            font-family: "JetBrains Mono", Consolas, monospace;
            background-color: var(--code-bg);
            color: var(--code-text);
            padding: 2px 5px;
            border-radius: 4px;
            font-size: 0.87em;
        }}
        .contrast-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 14px;
            margin-top: 12px;
        }}
        @media (max-width: 960px) {{
            .contrast-grid {{ grid-template-columns: 1fr; }}
            .sidebar-toc {{ display: none; }}
        }}
        .contrast-box {{ border-radius: 8px; padding: 12px 14px; font-size: 0.84rem; min-width: 0; }}
        .contrast-box.bad {{ background: var(--contrast-bad-bg); border: 1px solid var(--contrast-bad-border); }}
        .contrast-box.good {{ background: var(--contrast-good-bg); border: 1px solid var(--contrast-good-border); }}
        .contrast-header {{ display: flex; justify-content: space-between; margin-bottom: 8px; }}
        .contrast-pill-bad {{
            background: var(--contrast-bad-border);
            color: var(--contrast-bad-text);
            font-size: 0.72rem;
            font-weight: 700;
            padding: 1px 6px;
            border-radius: 4px;
            margin-right: 5px;
        }}
        .contrast-pill-good {{
            background: var(--contrast-good-border);
            color: var(--contrast-good-text);
            font-size: 0.72rem;
            font-weight: 700;
            padding: 1px 6px;
            border-radius: 4px;
            margin-right: 5px;
        }}
        .code-block {{
            background: var(--pre-bg);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            overflow: hidden;
        }}
        .code-header {{
            display: flex;
            justify-content: space-between;
            padding: 4px 10px;
            background: var(--surface-color);
            border-bottom: 1px solid var(--border-color);
            font-size: 0.74rem;
        }}
        .copy-btn {{
            background: transparent;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            color: var(--text-muted);
            padding: 1px 8px;
            font-size: 0.73rem;
            cursor: pointer;
        }}
        pre {{ padding: 10px 12px; overflow-x: auto; margin: 0; line-height: 1.5; }}
        pre code {{ background: transparent; color: var(--pre-text); padding: 0; white-space: pre-wrap; overflow-wrap: anywhere; }}
        .table-wrapper {{ overflow-x: auto; margin: 14px 0; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.87rem; }}
        th, td {{ border: 1px solid var(--border-color); padding: 9px 12px; text-align: left; }}
        th {{ background: var(--table-header); font-weight: 650; }}
        tr:nth-child(even) {{ background: var(--table-alt); }}
        .summary-card {{
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
        }}
        #markdown-view-container {{
            display: none;
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
        }}
        .md-toolbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border-color);
        }}
        .btn-copy-md {{
            background: var(--accent-primary);
            color: #ffffff;
            border: none;
            padding: 6px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
        }}
        .raw-md-textarea {{
            width: 100%;
            height: 75vh;
            font-family: "JetBrains Mono", Consolas, monospace;
            font-size: 0.84rem;
            background: var(--bg-color);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 14px;
            line-height: 1.6;
        }}
    </style>
</head>
<body>
    <div class="layout-wrapper">
        <aside class="sidebar-toc" id="sidebarToc">
            <div class="toc-card">
                <div class="portal-nav-box">
                    <div class="portal-nav-title">文档中心快速导航</div>
                    <div class="portal-nav-list">
                        {portal_links_html}
                    </div>
                </div>
                <div class="toc-header">
                    <div class="toc-title">本页大纲导航</div>
                    <button class="toc-action-btn" onclick="toggleDesktopToc()" title="收起侧栏">◀</button>
                </div>
                <div class="search-box">
                    <input type="text" class="search-input" id="searchInput" placeholder="搜索问题或关键词..." oninput="filterIssues()">
                </div>
                <div class="category-pills">
                    <button class="cat-pill active" data-cat="all" onclick="selectCategory('all')">全部 ({len(cards)})</button>
                    <button class="cat-pill" data-cat="arch" onclick="selectCategory('arch')">拓扑规范 ({len(arch_cards)})</button>
                    <button class="cat-pill" data-cat="gov" onclick="selectCategory('gov')">多样性规范 ({len(gov_cards)})</button>
                    <button class="cat-pill" data-cat="bug" onclick="selectCategory('bug')">缺陷排查 ({len(bug_cards)})</button>
                    <button class="cat-pill" data-cat="summary" onclick="selectCategory('summary')">实测汇总</button>
                </div>
                <nav class="toc-body" id="tocBody">
                    {toc_html}
                </nav>
            </div>
        </aside>

        <main class="main-content">
            <div class="top-bar">
                <div class="nav-links">
                    <button class="nav-btn" id="expandTocBtn" onclick="toggleDesktopToc()" style="display: none;">展开侧栏</button>
                    <a href="{rel_prefix}README.html" class="nav-btn">◀ 返回文档中心首页</a>
                    <button class="nav-btn active" id="btnCardView" onclick="switchView('card')">分栏卡片视图</button>
                    <button class="nav-btn" id="btnMdView" onclick="switchView('markdown')">Markdown 源码</button>
                    <span style="font-size: 0.83rem; color: var(--text-muted);">docs/{rel_html[:-5]}.md</span>
                </div>
                <button class="theme-switch-btn" onclick="toggleTheme()" id="themeBtn">切换暮色</button>
            </div>

            <div id="card-view-container">
                <header class="doc-header">
                    <span class="header-tag">跨会话记忆数据集研发体系 · 历史治理归档</span>
                    <h1 class="doc-title">生成问题排查、架构拓扑与数据治理实录 (001~150 批次)</h1>
                    <p class="doc-lead">系统记录早期批次在流水线生成、质量检验、生命周期因果演进与业务对齐过程中的 21 项典型缺陷、根因分析与治理规范。最新架构规范请参阅 <a href="{rel_prefix}specs/cognitive_memory_dev_spec.html" class="md-link">“联接”Agent 三层认知记忆与双轨评测技术规范</a>。</p>
                    <div class="header-meta-grid">
                        <div class="meta-stat-card"><div class="meta-stat-label">记录周期</div><div class="meta-stat-val">09.28 - 10.16</div></div>
                        <div class="meta-stat-card"><div class="meta-stat-label">排查与规范总项</div><div class="meta-stat-val">{len(cards)} 项</div></div>
                        <div class="meta-stat-card"><div class="meta-stat-label">覆盖画像样本</div><div class="meta-stat-val">150 个画像</div></div>
                        <div class="meta-stat-card"><div class="meta-stat-label">全量质检通过率</div><div class="meta-stat-val" style="color: var(--contrast-good-text);">100.0% 一次通过</div></div>
                    </div>
                </header>

                <section class="column-section" data-cat="arch">
                    <div class="column-section-header">
                        <h2>架构设计与模板拓扑规范</h2>
                        <span class="column-section-desc">解析动态规划、候选槽位模板全景因果拓扑（Causal DAG）与安全裁剪机制</span>
                    </div>
                    {arch_cards_html}
                </section>

                <section class="column-section" data-cat="gov">
                    <div class="column-section-header">
                        <h2>数据多样性机制与提示词规则</h2>
                        <span class="column-section-desc">双层解耦：基于取模/哈希的多样性离散机制 与 提示词/代码约束规则对照</span>
                    </div>
                    {gov_cards_html}
                </section>

                <section class="column-section" data-cat="bug">
                    <div class="column-section-header">
                        <h2>核心缺陷排查与数据治理实录</h2>
                        <span class="column-section-desc">收录真实数据缺陷、根因推演、代码级修复方案与实测对比</span>
                    </div>
                    {bug_cards_html}
                </section>

                <section class="column-section" id="summary-section" data-cat="summary">
                    <div class="column-section-header">
                        <h2>实测修复结果与验证数据汇总</h2>
                        <span class="column-section-desc">各对比维度下的实测质检结果</span>
                    </div>
                    <div class="summary-card">
                        {summary_table_html}
                    </div>
                </section>
            </div>

            <div id="markdown-view-container">
                <div class="md-toolbar">
                    <strong>docs/{rel_html[:-5]}.md 原生源码</strong>
                    <button class="btn-copy-md" onclick="copyMarkdownSource()">复制 Markdown 全文</button>
                </div>
                <textarea class="raw-md-textarea" id="mdSourceArea" readonly>{html.escape(md_text)}</textarea>
            </div>
        </main>
    </div>

    <script>
        function toggleTheme() {{
            const current = document.documentElement.getAttribute('data-theme') || 'parchment';
            const next = current === 'parchment' ? 'twilight' : 'parchment';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('doc-theme', next);
            document.getElementById('themeBtn').innerText = next === 'twilight' ? '切换米纸' : '切换暮色';
        }}
        function toggleDesktopToc() {{
            document.body.classList.toggle('toc-collapsed');
        }}
        function switchView(mode) {{
            document.getElementById('card-view-container').style.display = mode === 'markdown' ? 'none' : 'block';
            document.getElementById('markdown-view-container').style.display = mode === 'markdown' ? 'block' : 'none';
            document.getElementById('btnCardView').classList.toggle('active', mode !== 'markdown');
            document.getElementById('btnMdView').classList.toggle('active', mode === 'markdown');
        }}
        function copyCode(btn) {{
            const block = btn.closest('.code-block');
            const code = block ? block.querySelector('pre code') : null;
            if (!code) return;
            navigator.clipboard.writeText(code.innerText).then(() => {{
                btn.innerHTML = '<span>已复制</span>';
                setTimeout(() => {{ btn.innerHTML = '<span>复制</span>'; }}, 1800);
            }});
        }}
        function copyMarkdownSource() {{
            const ta = document.getElementById('mdSourceArea');
            navigator.clipboard.writeText(ta.value);
        }}
        function selectCategory(cat) {{
            document.querySelectorAll('.cat-pill').forEach(p => p.classList.toggle('active', p.dataset.cat === cat));
            document.querySelectorAll('.column-section').forEach(s => {{
                s.style.display = (cat === 'all' || s.dataset.cat === cat) ? 'block' : 'none';
            }});
            document.querySelectorAll('.issue-card').forEach(c => {{
                c.style.display = (cat === 'all' || c.dataset.cat === cat) ? 'block' : 'none';
            }});
        }}
        function filterIssues() {{
            const kw = document.getElementById('searchInput').value.trim().toLowerCase();
            document.querySelectorAll('.issue-card').forEach(card => {{
                card.style.display = (!kw || card.innerText.toLowerCase().includes(kw)) ? 'block' : 'none';
            }});
        }}
        (function() {{
            const saved = localStorage.getItem('doc-theme') || 'parchment';
            document.documentElement.setAttribute('data-theme', saved);
            document.getElementById('themeBtn').innerText = saved === 'twilight' ? '切换米纸' : '切换暮色';
        }})();
    </script>
</body>
</html>
"""
    html_path.write_text(full_html, encoding="utf-8")
    print(f"[+] 完成输出: {html_path.relative_to(docs_root)} ({len(full_html) // 1024} KB)")


# ==============================================================================
# 通用高保真学术文档渲染器 (用于 docs/ 下其余全部 Markdown 文档)
# ==============================================================================

DOC_HTML_SHELL = """<!DOCTYPE html>
<html lang="zh-CN" data-theme="parchment">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{PAGE_TITLE}</title>
    <!-- KaTeX 数学公式样式与渲染脚本 -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.css" onerror="this.onerror=null;this.href='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css';">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.js" onerror="this.onerror=null;this.src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js';"></script>
    <!-- Highlight.js 代码高亮 -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
    <!-- Mermaid.js 动态图表渲染 -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        :root[data-theme="parchment"] {
            --bg-color: #f7f4ec;
            --surface-color: #eee9dc;
            --surface-elevated: #e6dfcf;
            --border-color: #dcd4c0;
            --border-subtle: #e6dfd1;
            --text-primary: #2d3748;
            --text-secondary: #4a5568;
            --text-muted: #718096;
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
            --card-shadow: 0 4px 18px rgba(45, 55, 72, 0.05);
        }

        :root[data-theme="twilight"] {
            --bg-color: #1a1e24;
            --surface-color: #232931;
            --surface-elevated: #2c343f;
            --border-color: #39424e;
            --border-subtle: #2d3642;
            --text-primary: #dce1e8;
            --text-secondary: #b0bac6;
            --text-muted: #707b88;
            --accent-primary: #e09f67;
            --accent-glow: rgba(224, 159, 103, 0.12);
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
            --card-shadow: 0 4px 18px rgba(0, 0, 0, 0.25);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        html {
            scroll-behavior: smooth;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            line-height: 1.78;
            font-size: 15.2px;
        }

        .layout-wrapper {
            display: flex;
            min-height: 100vh;
        }

        /* 侧边栏导航与目录 */
        .sidebar-toc {
            width: 310px;
            background-color: var(--surface-color);
            border-right: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            height: 100vh;
            padding: 20px 16px;
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
            z-index: 100;
        }

        .portal-nav-box {
            margin-bottom: 14px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border-color);
            flex-shrink: 0;
        }

        .portal-nav-title {
            font-size: 0.76rem;
            font-weight: 700;
            color: var(--accent-primary);
            margin-bottom: 6px;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }

        .portal-nav-list {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .portal-nav-item {
            display: block;
            padding: 4px 8px;
            font-size: 0.81rem;
            color: var(--text-secondary);
            text-decoration: none;
            border-radius: 5px;
            transition: all 0.15s;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .portal-nav-item:hover {
            background-color: var(--surface-elevated);
            color: var(--accent-primary);
        }

        .portal-nav-item.active {
            background-color: var(--accent-glow);
            color: var(--accent-primary);
            font-weight: 700;
            border-left: 3px solid var(--accent-primary);
        }

        .toc-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 10px;
            margin-bottom: 10px;
            border-bottom: 1px solid var(--border-color);
            flex-shrink: 0;
        }

        .toc-title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.9rem;
            font-weight: 700;
            color: var(--text-primary);
        }

        .toc-action-btn {
            background: none;
            border: none;
            cursor: pointer;
            color: var(--text-muted);
            padding: 4px 6px;
            border-radius: 4px;
            font-size: 0.8rem;
        }

        .toc-action-btn:hover {
            color: var(--accent-primary);
            background-color: var(--surface-elevated);
        }

        .toc-search-box {
            margin-bottom: 10px;
            flex-shrink: 0;
        }

        .toc-search-input {
            width: 100%;
            padding: 6px 10px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            background: var(--bg-color);
            color: var(--text-primary);
            font-size: 0.82rem;
            outline: none;
        }

        .toc-search-input:focus {
            border-color: var(--accent-primary);
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
            margin-bottom: 3px;
        }

        .toc-item.toc-level-2 {
            margin-top: 8px;
            font-weight: 600;
            font-size: 0.85rem;
        }

        .toc-item.toc-level-3 {
            padding-left: 12px;
            font-size: 0.81rem;
            color: var(--text-secondary);
        }

        .toc-item.toc-level-4 {
            padding-left: 22px;
            font-size: 0.78rem;
            color: var(--text-muted);
        }

        .toc-link {
            display: block;
            padding: 4px 8px;
            color: inherit;
            text-decoration: none;
            border-radius: 4px;
            transition: all 0.15s;
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
            padding: 32px 48px 80px;
            overflow-x: hidden;
        }

        @media (max-width: 960px) {
            .sidebar-toc {
                display: none;
            }
            .main-content {
                padding: 20px 18px 60px;
            }
        }

        .container {
            max-width: 1020px;
            margin: 0 auto;
        }

        .top-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 28px;
            padding-bottom: 14px;
            border-bottom: 1px solid var(--border-color);
            flex-wrap: wrap;
            gap: 10px;
        }

        .nav-links {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }

        .nav-btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 12px;
            border-radius: 6px;
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            font-size: 0.84rem;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.2s;
        }

        .nav-btn:hover, .nav-btn.active {
            border-color: var(--accent-primary);
            color: #ffffff;
            background-color: var(--accent-primary);
        }

        .theme-switch-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 14px;
            border-radius: 20px;
            background-color: var(--toggle-bg);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            font-size: 0.84rem;
            cursor: pointer;
            font-weight: 600;
        }

        /* Markdown 正文排版 */
        .markdown-body {
            color: var(--text-primary);
        }

        .markdown-body h1 {
            font-size: 1.95rem;
            font-weight: 800;
            line-height: 1.35;
            margin-bottom: 20px;
            padding-bottom: 14px;
            border-bottom: 2px solid var(--border-color);
            color: var(--text-primary);
        }

        .markdown-body h2 {
            font-size: 1.42rem;
            font-weight: 700;
            line-height: 1.4;
            margin-top: 42px;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border-color);
            border-left: 4px solid var(--accent-primary);
            padding-left: 12px;
            color: var(--text-primary);
        }

        .markdown-body h3 {
            font-size: 1.15rem;
            font-weight: 650;
            line-height: 1.45;
            margin-top: 28px;
            margin-bottom: 12px;
            color: var(--text-primary);
        }

        .markdown-body h4 {
            font-size: 1.0rem;
            font-weight: 650;
            margin-top: 20px;
            margin-bottom: 8px;
            color: var(--accent-primary);
        }

        .markdown-body p {
            margin-bottom: 14px;
            line-height: 1.78;
        }

        .markdown-body ul, .markdown-body ol {
            margin-bottom: 16px;
            padding-left: 24px;
        }

        .markdown-body ul ul, .markdown-body ol ul, .markdown-body ul ol {
            margin-top: 6px;
            margin-bottom: 6px;
        }

        .markdown-body li {
            margin-bottom: 6px;
            line-height: 1.72;
        }

        .markdown-body strong {
            font-weight: 700;
            color: var(--text-primary);
        }

        .md-link {
            color: var(--accent-primary);
            text-decoration: underline;
            text-underline-offset: 3px;
            font-weight: 600;
        }

        .md-link:hover {
            opacity: 0.85;
        }

        .markdown-body code {
            font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            background-color: var(--code-bg);
            color: var(--code-text);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.88em;
        }

        /* 代码块带复制栏 */
        .code-card {
            background-color: var(--pre-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            margin: 16px 0 22px;
            overflow: hidden;
            box-shadow: var(--card-shadow);
        }

        .code-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 6px 14px;
            background-color: var(--surface-color);
            border-bottom: 1px solid var(--border-color);
            font-size: 0.76rem;
        }

        .code-card-lang {
            font-family: "JetBrains Mono", Consolas, monospace;
            font-weight: 700;
            color: var(--accent-primary);
            text-transform: uppercase;
        }

        .code-copy-btn {
            background-color: var(--bg-color);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            color: var(--text-secondary);
            padding: 2px 8px;
            font-size: 0.74rem;
            cursor: pointer;
        }

        .code-copy-btn:hover {
            color: var(--accent-primary);
            border-color: var(--accent-primary);
        }

        .markdown-body pre {
            background-color: transparent;
            color: var(--pre-text);
            padding: 14px 16px;
            overflow-x: auto;
            margin: 0;
            line-height: 1.55;
        }

        .markdown-body pre code {
            background-color: transparent;
            color: inherit;
            padding: 0;
            font-size: 0.86rem;
            white-space: pre;
        }

        .doc-intro {
            background-color: var(--surface-color);
            border-left: 4px solid var(--accent-primary);
            padding: 14px 18px;
            border-radius: 0 8px 8px 0;
            margin-bottom: 26px;
            color: var(--text-secondary);
            font-size: 0.94rem;
        }

        blockquote {
            background-color: var(--surface-color);
            border-left: 4px solid var(--accent-primary);
            padding: 12px 18px;
            margin: 16px 0;
            border-radius: 0 6px 6px 0;
            color: var(--text-secondary);
        }

        /* GitHub Alert Callout Cards */
        .callout-card {
            border-radius: 8px;
            padding: 14px 18px;
            margin: 18px 0;
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

        .callout-card.callout-warn {
            background-color: var(--callout-warn-bg);
            border-color: var(--callout-warn-border);
            color: var(--callout-warn-text);
        }

        .callout-header {
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 700;
            font-size: 0.9rem;
            margin-bottom: 8px;
        }

        .callout-badge {
            display: inline-flex;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 700;
            color: #ffffff;
            background-color: var(--accent-primary);
        }

        .callout-important .callout-badge { background-color: var(--callout-imp-border); }
        .callout-tip .callout-badge, .callout-note .callout-badge { background-color: var(--callout-note-border); }
        .callout-warn .callout-badge { background-color: var(--callout-warn-border); }

        /* 表格样式 */
        .table-wrapper {
            margin: 18px 0 24px;
            overflow-x: auto;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            box-shadow: var(--card-shadow);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.89rem;
            text-align: left;
        }

        thead tr {
            background-color: var(--table-header);
        }

        th {
            padding: 10px 14px;
            font-weight: 700;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-primary);
        }

        td {
            padding: 10px 14px;
            border-bottom: 1px solid var(--border-subtle);
            color: var(--text-secondary);
            vertical-align: top;
        }

        tbody tr:nth-child(even) {
            background-color: var(--table-alt);
        }

        /* Mermaid 图表容器：强制纯白底色 (#FFFFFF)、加粗字体、加粗线条 */
        .mermaid-wrapper {
            margin: 22px 0 28px;
            padding: 24px;
            background-color: #FFFFFF !important;
            border: 2px solid #111111;
            border-radius: 10px;
            overflow-x: auto;
            text-align: center;
            box-shadow: var(--card-shadow);
        }

        .mermaid {
            background-color: #FFFFFF !important;
            color: #111111 !important;
            font-weight: 700 !important;
            display: inline-block;
            min-width: 320px;
        }

        .mermaid svg {
            background-color: #FFFFFF !important;
            font-weight: 700 !important;
        }

        .mermaid svg text,
        .mermaid svg span,
        .mermaid svg .nodeLabel,
        .mermaid svg .edgeLabel,
        .mermaid svg .messageText,
        .mermaid svg .labelText,
        .mermaid svg .loopText {
            font-weight: 700 !important;
            color: #111111 !important;
            fill: #111111 !important;
        }

        .mermaid svg path,
        .mermaid svg line,
        .mermaid svg rect,
        .mermaid svg polygon,
        .mermaid svg circle {
            stroke-width: 2.2px !important;
        }

        /* 数学公式块 */
        .math-block {
            background-color: var(--math-bg);
            border: 1px solid var(--math-border);
            border-radius: 8px;
            padding: 14px 18px;
            margin: 16px 0 22px;
            overflow-x: auto;
            text-align: center;
        }

        .math-block-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
            padding-bottom: 6px;
            border-bottom: 1px dashed var(--border-color);
            font-size: 0.76rem;
        }

        .math-badge {
            color: var(--accent-primary);
            font-weight: 700;
        }

        .math-copy-btn {
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.74rem;
            cursor: pointer;
            color: var(--text-secondary);
        }

        /* 原生 Markdown 源码视图 */
        #markdown-source-view {
            display: none;
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 20px;
        }

        .md-source-toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border-color);
        }

        .raw-md-textarea {
            width: 100%;
            height: 75vh;
            font-family: "JetBrains Mono", Consolas, monospace;
            font-size: 0.85rem;
            background: var(--bg-color);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 14px;
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
            <div class="portal-nav-box">
                <div class="portal-nav-title">文档中心快速导航</div>
                <div class="portal-nav-list">
{PORTAL_LINKS}
                </div>
            </div>
            <div class="toc-header">
                <div class="toc-title">
                    <span>本页目录大纲</span>
                </div>
                <button class="toc-action-btn" onclick="toggleDesktopToc()" title="收起目录">◀</button>
            </div>
            <div class="toc-search-box">
                <input type="text" class="toc-search-input" id="tocSearchInput" placeholder="筛选目录章节..." oninput="filterToc()">
            </div>
            <nav class="toc-body">
                <ul class="toc-list" id="tocList">
{TOC_ITEMS}
                </ul>
            </nav>
        </aside>

        <main class="main-content">
            <div class="container">
                <div class="top-bar">
                    <div class="nav-links">
                        <button class="nav-btn" id="expandTocBtn" onclick="toggleDesktopToc()" style="display: none;">展开目录</button>
                        <a href="{HOME_HREF}" class="nav-btn">◀ 文档中心首页</a>
                        <button class="nav-btn active" id="btnReadView" onclick="switchDocView('read')">阅读视图</button>
                        <button class="nav-btn" id="btnSourceView" onclick="switchDocView('source')">Markdown 源码</button>
                        <span style="color: var(--border-color)">|</span>
                        <span style="font-size: 0.84rem; color: var(--text-muted);">{MD_REL_PATH}</span>
                    </div>
                    <button class="theme-switch-btn" onclick="toggleTheme()" id="themeBtn">
                        切换暮色
                    </button>
                </div>

                <article class="markdown-body" id="docReadView">
{ARTICLE_BODY}
                </article>

                <div id="markdown-source-view">
                    <div class="md-source-toolbar">
                        <strong>{MD_REL_PATH} 原生 Markdown 源码</strong>
                        <button class="nav-btn active" onclick="copyRawMarkdown()">复制全文源码</button>
                    </div>
                    <textarea class="raw-md-textarea" id="rawMdArea" readonly>{RAW_MD_ESCAPED}</textarea>
                </div>
            </div>
        </main>
    </div>

    <script>
        function toggleTheme() {
            const htmlEl = document.documentElement;
            const currentTheme = htmlEl.getAttribute('data-theme') || 'parchment';
            const newTheme = currentTheme === 'parchment' ? 'twilight' : 'parchment';
            htmlEl.setAttribute('data-theme', newTheme);
            localStorage.setItem('doc-theme', newTheme);
            document.getElementById('themeBtn').innerText = newTheme === 'parchment' ? '切换暮色' : '切换米纸';
        }

        function toggleDesktopToc() {
            document.body.classList.toggle('toc-collapsed');
            const isCollapsed = document.body.classList.contains('toc-collapsed');
            document.getElementById('expandTocBtn').style.display = isCollapsed ? 'inline-flex' : 'none';
        }

        function switchDocView(mode) {
            const readEl = document.getElementById('docReadView');
            const srcEl = document.getElementById('markdown-source-view');
            document.getElementById('btnReadView').classList.toggle('active', mode !== 'source');
            document.getElementById('btnSourceView').classList.toggle('active', mode === 'source');
            readEl.style.display = mode === 'source' ? 'none' : 'block';
            srcEl.style.display = mode === 'source' ? 'block' : 'none';
        }

        function copyRawMarkdown() {
            const area = document.getElementById('rawMdArea');
            navigator.clipboard.writeText(area.value);
        }

        function copyCodeCard(btn) {
            const card = btn.closest('.code-card');
            const code = card ? card.querySelector('pre code') : null;
            if (!code) return;
            navigator.clipboard.writeText(code.innerText).then(() => {
                const orig = btn.innerText;
                btn.innerText = '已复制';
                setTimeout(() => { btn.innerText = orig; }, 1800);
            });
        }

        function copyLatex(btn) {
            const tex = btn.getAttribute('data-tex');
            if (tex) {
                navigator.clipboard.writeText(tex).then(() => {
                    const orig = btn.innerText;
                    btn.innerText = '已复制 LaTeX';
                    setTimeout(() => { btn.innerText = orig; }, 1800);
                });
            }
        }

        function filterToc() {
            const kw = document.getElementById('tocSearchInput').value.trim().toLowerCase();
            document.querySelectorAll('#tocList .toc-item').forEach(li => {
                li.style.display = (!kw || li.innerText.toLowerCase().includes(kw)) ? 'block' : 'none';
            });
        }

        window.addEventListener('DOMContentLoaded', () => {
            const savedTheme = localStorage.getItem('doc-theme') || 'parchment';
            document.documentElement.setAttribute('data-theme', savedTheme);
            document.getElementById('themeBtn').innerText = savedTheme === 'parchment' ? '切换暮色' : '切换米纸';

            if (window.katex) {
                document.querySelectorAll('.katex-inline').forEach(el => {
                    const tex = el.getAttribute('data-tex');
                    if (tex) {
                        try {
                            el.innerHTML = katex.renderToString(tex, { displayMode: false, throwOnError: false });
                        } catch (e) {}
                    }
                });
                document.querySelectorAll('.katex-display-container').forEach(el => {
                    const tex = el.getAttribute('data-tex');
                    if (tex) {
                        try {
                            el.innerHTML = katex.renderToString(tex, { displayMode: true, throwOnError: false });
                        } catch (e) {}
                    }
                });
            }

            if (window.mermaid) {
                mermaid.initialize({
                    startOnLoad: true,
                    theme: 'base',
                    themeVariables: {
                        background: '#FFFFFF',
                        primaryColor: '#FFFFFF',
                        primaryTextColor: '#111111',
                        primaryBorderColor: '#111111',
                        lineColor: '#111111',
                        secondaryColor: '#FFFFFF',
                        tertiaryColor: '#FFFFFF',
                        mainBkg: '#FFFFFF',
                        nodeBorder: '#111111',
                        clusterBkg: '#FFFFFF',
                        clusterBorder: '#111111',
                        actorBkg: '#FFFFFF',
                        actorBorder: '#111111',
                        actorTextColor: '#111111',
                        signalColor: '#111111',
                        signalTextColor: '#111111',
                        labelBoxBkgColor: '#FFFFFF',
                        labelBoxBorderColor: '#111111',
                        labelTextColor: '#111111',
                        noteBkgColor: '#FFFFFF',
                        noteBorderColor: '#111111',
                        noteTextColor: '#111111'
                    }
                });
            }

            if (window.hljs) {
                hljs.highlightAll();
            }

            const links = document.querySelectorAll('.toc-link');
            const sections = [];
            links.forEach(link => {
                const targetId = decodeURIComponent(link.getAttribute('href').slice(1));
                const section = document.getElementById(targetId);
                if (section) {
                    sections.push({ id: targetId, el: section, link: link });
                }
            });

            window.addEventListener('scroll', () => {
                const scrollPos = window.scrollY + 110;
                let activeId = sections.length ? sections[0].id : null;
                for (let i = 0; i < sections.length; i++) {
                    if (sections[i].el.offsetTop <= scrollPos) {
                        activeId = sections[i].id;
                    }
                }
                links.forEach(link => {
                    const hrefId = decodeURIComponent(link.getAttribute('href').slice(1));
                    link.classList.toggle('active', hrefId === activeId);
                });
            }, { passive: true });
        });
    </script>
</body>
</html>
"""


def split_table_row(line_s: str) -> list[str]:
    """切分 Markdown 表格行，支持转义竖线 \\|"""
    inner = line_s.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    parts = re.split(r"(?<!\\)\|", inner)
    return [p.replace("\\|", "|").strip() for p in parts]


def parse_doc_markdown(md_text: str):
    lines = md_text.splitlines()
    title = "跨会话认知记忆数据集技术文档"
    body_parts = []
    toc_items = []
    used_ids = {}

    def get_unique_id(h_text: str) -> str:
        base_id = slugify_heading(h_text)
        if base_id not in used_ids:
            used_ids[base_id] = 1
            return base_id
        used_ids[base_id] += 1
        return f"{base_id}-{used_ids[base_id]}"

    i = 0
    n = len(lines)

    in_code_block = False
    code_lang = ""
    code_lines = []

    in_table = False
    table_lines = []

    def flush_table():
        nonlocal in_table, table_lines
        if not in_table or not table_lines:
            in_table = False
            table_lines = []
            return

        if len(table_lines) < 2:
            for tl in table_lines:
                body_parts.append(f"<p>{format_inline_markdown(tl)}</p>")
            in_table = False
            table_lines = []
            return

        headers = split_table_row(table_lines[0])
        # 检查第2行是否为分隔行 (| --- | --- |)
        start_row_idx = 2 if re.match(r"^[\s|:\-]+$", table_lines[1]) else 1
        rows = [split_table_row(tl) for tl in table_lines[start_row_idx:]]

        th_html = "".join([f"<th>{format_inline_markdown(h)}</th>" for h in headers])
        tr_html = []
        for r in rows:
            if not any(r):
                continue
            tds = [f"<td>{format_inline_markdown(c)}</td>" for c in r]
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

        # 1. 代码块 (```lang ... ```)
        if line_s.startswith("```"):
            flush_table()
            if in_code_block:
                in_code_block = False
                full_code = "\n".join(code_lines)
                if code_lang.lower() == "mermaid":
                    body_parts.append(
                        f'<div class="mermaid-wrapper"><div class="mermaid">\n{full_code}\n</div></div>'
                    )
                else:
                    disp_lang = code_lang.upper() if code_lang else "TEXT"
                    lang_cls = f' class="language-{code_lang}"' if code_lang else ""
                    body_parts.append(
                        f"""
                        <div class="code-card">
                            <div class="code-card-header">
                                <span class="code-card-lang">{html.escape(disp_lang)}</span>
                                <button class="code-copy-btn" onclick="copyCodeCard(this)">复制代码</button>
                            </div>
                            <pre><code{lang_cls}>{html.escape(full_code)}</code></pre>
                        </div>
                        """
                    )
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

        # 2. 表格行
        if line_s.startswith("|") and line_s.endswith("|"):
            in_table = True
            table_lines.append(line_s)
            i += 1
            continue
        elif in_table:
            flush_table()

        if not line_s:
            i += 1
            continue

        # 3. 注释行
        if line_s.startswith("<!--"):
            i += 1
            continue

        # 4. 水平分割线
        if line_s in ["---", "***", "___"]:
            body_parts.append('<hr style="border: none; border-top: 1px solid var(--border-color); margin: 32px 0;">')
            i += 1
            continue

        # 5. 各级标题
        if line_s.startswith("# "):
            title_raw = line_s[2:].strip()
            title = re.sub(r"[`*_]", "", title_raw)
            body_parts.append(f"<h1>{format_inline_markdown(title_raw)}</h1>")
            i += 1
            continue

        if line_s.startswith("## "):
            h_text = line_s[3:].strip()
            h_id = get_unique_id(h_text)
            toc_items.append({"level": 2, "id": h_id, "title": re.sub(r"[`*_]", "", h_text)})
            body_parts.append(f'<h2 id="{h_id}">{format_inline_markdown(h_text)}</h2>')
            i += 1
            continue

        if line_s.startswith("### "):
            h_text = line_s[4:].strip()
            h_id = get_unique_id(h_text)
            toc_items.append({"level": 3, "id": h_id, "title": re.sub(r"[`*_]", "", h_text)})
            body_parts.append(f'<h3 id="{h_id}">{format_inline_markdown(h_text)}</h3>')
            i += 1
            continue

        if line_s.startswith("#### "):
            h_text = line_s[5:].strip()
            h_id = get_unique_id(h_text)
            toc_items.append({"level": 4, "id": h_id, "title": re.sub(r"[`*_]", "", h_text)})
            body_parts.append(f'<h4 id="{h_id}">{format_inline_markdown(h_text)}</h4>')
            i += 1
            continue

        # 6. 块级数学公式 ($$...$$)
        if line_s.startswith("$$"):
            math_lines = []
            if line_s.endswith("$$") and len(line_s) > 4:
                tex = line_s[2:-2].strip()
            else:
                first_part = line_s[2:].strip()
                if first_part:
                    math_lines.append(first_part)
                i += 1
                while i < n and not lines[i].strip().endswith("$$"):
                    math_lines.append(lines[i])
                    i += 1
                if i < n:
                    last_l = lines[i].strip()[:-2].strip()
                    if last_l:
                        math_lines.append(last_l)
                tex = "\n".join(math_lines).strip()

            esc_tex = html.escape(tex)
            body_parts.append(
                f"""
                <div class="math-block" data-tex="{esc_tex}">
                    <div class="math-block-header">
                        <span class="math-badge">LaTeX · 数学公式</span>
                        <button class="math-copy-btn" onclick="copyLatex(this)" data-tex="{esc_tex}">复制公式</button>
                    </div>
                    <div class="katex-display-container" data-tex="{esc_tex}">$${esc_tex}$$</div>
                </div>
                """
            )
            i += 1
            continue

        # 7. 引用块与 GitHub Callout Alerts
        if line_s.startswith(">"):
            quote_lines = []
            while i < n and lines[i].strip().startswith(">"):
                raw_q = lines[i].strip()[1:].strip()
                quote_lines.append(raw_q)
                i += 1

            non_empty = [q for q in quote_lines if q]
            if not non_empty:
                continue

            first_line = non_empty[0]
            alert_m = re.match(r"^\[!(IMPORTANT|TIP|NOTE|WARNING|CAUTION)\](.*)$", first_line, re.IGNORECASE)
            alert_type = None
            badge_text = ""
            content_lines = quote_lines

            if alert_m:
                raw_type = alert_m.group(1).lower()
                rest_first = alert_m.group(2).strip()
                content_lines = ([rest_first] if rest_first else []) + quote_lines[1:]
                if raw_type in ["important", "caution"]:
                    alert_type = "important"
                    badge_text = "重点规范"
                elif raw_type == "tip":
                    alert_type = "tip"
                    badge_text = "最佳实践"
                elif raw_type == "warning":
                    alert_type = "warn"
                    badge_text = "注意告警"
                else:
                    alert_type = "note"
                    badge_text = "补充说明"

            inner_parts = []
            for c_line in content_lines:
                if not c_line:
                    continue
                inner_parts.append(f"<p>{format_inline_markdown(c_line)}</p>")
            inner_html = "\n".join(inner_parts)

            if alert_type:
                body_parts.append(
                    f"""
                    <div class="callout-card callout-{alert_type}">
                        <div class="callout-header">
                            <span class="callout-badge">{badge_text}</span>
                        </div>
                        <div class="callout-content">
                            {inner_html}
                        </div>
                    </div>
                    """
                )
            else:
                body_parts.append(f"<blockquote>{inner_html}</blockquote>")
            continue

        # 8. 列表块（支持缩进嵌套列表与列表内嵌块级公式）
        list_m = re.match(r"^(\s*)([-*•]|\d+\.)\s+(.*)", line)
        if list_m:
            list_html_lines = []
            stack = []  # [(indent_len, tag_name)]

            while i < n:
                curr_line = lines[i]
                curr_s = curr_line.strip()
                if not curr_s:
                    # 若空行后紧跟列表项，继续保持列表上下文
                    if i + 1 < n and re.match(r"^(\s*)([-*•]|\d+\.)\s+", lines[i + 1]):
                        i += 1
                        continue
                    break

                # 检查列表内缩进的块级公式 $$...$$
                if curr_s.startswith("$$") and stack:
                    if curr_s.endswith("$$") and len(curr_s) > 4:
                        tex = curr_s[2:-2].strip()
                    else:
                        m_lines = [curr_s[2:].strip()] if curr_s[2:].strip() else []
                        i += 1
                        while i < n and not lines[i].strip().endswith("$$"):
                            m_lines.append(lines[i])
                            i += 1
                        if i < n and lines[i].strip()[:-2].strip():
                            m_lines.append(lines[i].strip()[:-2].strip())
                        tex = "\n".join(m_lines).strip()
                    esc_tex = html.escape(tex)
                    list_html_lines.append(
                        f'<div class="math-block" data-tex="{esc_tex}"><div class="katex-display-container" data-tex="{esc_tex}">$${esc_tex}$$</div></div>'
                    )
                    i += 1
                    continue

                item_m = re.match(r"^(\s*)([-*•]|\d+\.)\s+(.*)", curr_line)
                if not item_m:
                    # 列表项的多行续行文本
                    if curr_line.startswith("  ") and stack:
                        list_html_lines.append(f" {format_inline_markdown(curr_s)}")
                        i += 1
                        continue
                    break

                indent = len(item_m.group(1).expandtabs(4))
                marker = item_m.group(2)
                content_str = format_inline_markdown(item_m.group(3))
                tag = "ol" if marker.endswith(".") else "ul"

                if not stack:
                    stack.append((indent, tag))
                    list_html_lines.append(f"<{tag}><li>{content_str}")
                elif indent > stack[-1][0]:
                    stack.append((indent, tag))
                    list_html_lines.append(f"<{tag}><li>{content_str}")
                else:
                    list_html_lines.append("</li>")
                    while len(stack) > 1 and indent < stack[-1][0]:
                        _, closed_tag = stack.pop()
                        list_html_lines.append(f"</{closed_tag}></li>")
                    if stack[-1][1] != tag:
                        _, closed_tag = stack.pop()
                        list_html_lines.append(f"</{closed_tag}>")
                        stack.append((indent, tag))
                        list_html_lines.append(f"<{tag}>")
                    list_html_lines.append(f"<li>{content_str}")
                i += 1

            while stack:
                _, closed_tag = stack.pop()
                list_html_lines.append(f"</li></{closed_tag}>")

            body_parts.append("\n".join(list_html_lines))
            continue

        # 9. 常规段落
        body_parts.append(f"<p>{format_inline_markdown(line_s)}</p>")
        i += 1

    flush_table()

    toc_html_list = []
    for item in toc_items:
        cls = f"toc-level-{item['level']}"
        toc_html_list.append(
            f'<li class="toc-item {cls}"><a href="#{item["id"]}" class="toc-link" title="{html.escape(item["title"])}">{html.escape(item["title"])}</a></li>'
        )

    toc_html = "\n".join(toc_html_list)
    body_html = "\n".join(body_parts)
    return title, toc_html, body_html


def render_general_doc_page(md_path: Path, html_path: Path, docs_root: Path):
    rel_md = md_path.relative_to(docs_root).as_posix()
    rel_html = html_path.relative_to(docs_root).as_posix()
    depth = len(html_path.relative_to(docs_root).parts) - 1
    rel_prefix = "../" * depth
    home_href = f"{rel_prefix}README.html"

    print(f"[*] 渲染文档页面: {rel_md} -> {rel_html}")
    md_text = md_path.read_text(encoding="utf-8")
    title, toc_html, body_html = parse_doc_markdown(md_text)
    portal_links_html = build_portal_links_html(rel_prefix, rel_html)

    full_html = DOC_HTML_SHELL
    full_html = full_html.replace("{PAGE_TITLE}", html.escape(title))
    full_html = full_html.replace("{PORTAL_LINKS}", portal_links_html)
    full_html = full_html.replace("{TOC_ITEMS}", toc_html)
    full_html = full_html.replace("{HOME_HREF}", home_href)
    full_html = full_html.replace("{MD_REL_PATH}", f"docs/{rel_md}")
    full_html = full_html.replace("{ARTICLE_BODY}", body_html)
    full_html = full_html.replace("{RAW_MD_ESCAPED}", html.escape(md_text))

    html_path.write_text(full_html, encoding="utf-8")
    print(f"[+] 完成输出: {rel_html} ({len(full_html) // 1024} KB)")

    # 若当前为 docs/README.md，同步生成 docs/index.html 便于直接打开门户
    if rel_md == "README.md":
        index_path = docs_root / "index.html"
        index_path.write_text(full_html, encoding="utf-8")
        print(f"[+] 同步生成门户首页: index.html ({len(full_html) // 1024} KB)")


def render_single_file(md_path: Path, docs_root: Path):
    html_path = md_path.with_suffix(".html")
    if md_path.name == "defect_triage_log.md":
        render_triage_card_page(md_path, html_path, docs_root)
    else:
        render_general_doc_page(md_path, html_path, docs_root)


def main():
    docs_root = Path(__file__).resolve().parent
    args = sys.argv[1:]

    if args:
        target = Path(args[0])
        if not target.is_absolute():
            target = (docs_root / target) if (docs_root / target).exists() else target.resolve()
        if not target.exists():
            print(f"[ERROR] 找不到指定的 Markdown 文件: {target}")
            sys.exit(1)
        render_single_file(target, docs_root)
    else:
        print("=" * 68)
        print("[*] docs/render_html.py: 扫描并全量渲染 docs/ 下所有 Markdown 文档")
        print("=" * 68)
        md_files = sorted(docs_root.rglob("*.md"))
        for md_file in md_files:
            render_single_file(md_file, docs_root)
        print("=" * 68)
        print(f"[+] 全量渲染完成！共生成 {len(md_files)} 份 HTML 文档 (+ index.html 门户首页)")
        print("=" * 68)


if __name__ == "__main__":
    main()

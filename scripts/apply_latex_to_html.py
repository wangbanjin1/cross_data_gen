import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

import sys
import re
import json
import shutil
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# 读取已预渲染好的公式
with open('temp_rendered_formulas.json', 'r', encoding='utf-8') as f:
    rendered = json.load(f)

html_path = Path('docs/memory_evolution_plan.html')
# 备份原文件
shutil.copyfile(html_path, html_path.with_suffix('.html.bak'))

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 更新 <head> 中的样式与脚本引用
old_mathjax = """    <!-- MathJax for rendering LaTeX formulas -->
    <script>
        window.MathJax = {
            tex: {
                inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
                processEscapes: true
            },
            options: {
                skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code']
            },
            chtml: {
                matchFontHeight: false
            }
        };
    </script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" onerror="this.onerror=null;this.src='https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-mml-chtml.js';"></script>"""

new_katex_head = """    <!-- KaTeX 本地与多重 CDN 双通道高可用样式与字体 -->
    <link rel="stylesheet" href="katex.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.css" onerror="this.onerror=null;this.href='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css';">
    <script src="katex.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.js" onerror="this.onerror=null;this.src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js';"></script>"""

if old_mathjax in content:
    content = content.replace(old_mathjax, new_katex_head)
    logger.info("[+] 替换 <head> KaTeX 引用成功")
else:
    logger.info("[!] 警告: 未精确匹配 old_mathjax，尝试正则替换")
    content = re.sub(r'<!-- MathJax.*?<script id="MathJax-script".*?</script>', new_katex_head, content, flags=re.DOTALL)

# 2. 增强 .math-block 样式
old_math_css = """        /* 数学公式容器 */
        .math-block {
            background-color: var(--math-bg);
            border: 1px solid var(--math-border);
            border-radius: 8px;
            padding: 14px 20px;
            margin: 18px 0;
            overflow-x: auto;
            text-align: center;
        }"""

new_math_css = """        /* 数学公式容器增强样式 (LaTeX 渲染专用) */
        .math-block {
            background-color: var(--math-bg);
            border: 1px solid var(--math-border);
            border-radius: 8px;
            padding: 16px 20px;
            margin: 18px 0;
            overflow-x: auto;
            text-align: center;
            position: relative;
            box-shadow: var(--card-shadow);
        }

        .math-block .katex-display {
            margin: 8px 0;
        }

        .math-block-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
            padding-bottom: 6px;
            border-bottom: 1px dashed var(--border-color);
        }

        .math-badge {
            font-size: 0.72rem;
            font-weight: 700;
            color: var(--accent-primary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .math-copy-btn {
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            font-size: 0.72rem;
            padding: 2px 8px;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.2s;
            font-family: inherit;
        }

        .math-copy-btn:hover {
            color: var(--accent-primary);
            border-color: var(--accent-primary);
            background: var(--surface-elevated);
        }

        .katex-inline {
            padding: 0 2px;
            display: inline-block;
            vertical-align: -0.05em;
        }"""

if old_math_css in content:
    content = content.replace(old_math_css, new_math_css)
    logger.info("[+] 替换 .math-block 增强 CSS 成功")
else:
    logger.info("[!] 警告: 未精确匹配 old_math_css")

# 3. 完善 TOC 目录大纲
old_toc_work = """                    <li class="toc-item toc-level-2"><a href="#工作记忆工单账本检索" class="toc-link">工作记忆工单账本检索</a></li>
                    <li class="toc-item toc-level-3"><a href="#时态推断与检索流程图" class="toc-link">时态推断与检索流程图</a></li>
                    <li class="toc-item toc-level-3"><a href="#历史工单流水账结构" class="toc-link">历史工单流水账结构</a></li>"""

new_toc_work = """                    <li class="toc-item toc-level-2"><a href="#工作记忆工单账本检索" class="toc-link">工作记忆工单账本检索</a></li>
                    <li class="toc-item toc-level-3"><a href="#时态推断与检索流程图" class="toc-link">时态推断与检索流程图</a></li>
                    <li class="toc-item toc-level-3"><a href="#时态相对指称计算与检索逻辑" class="toc-link">时态相对指称计算与检索逻辑</a></li>
                    <li class="toc-item toc-level-3"><a href="#历史工单流水账结构" class="toc-link">历史工单流水账结构</a></li>"""

if old_toc_work in content:
    content = content.replace(old_toc_work, new_toc_work)
    logger.info("[+] 更新 TOC 大纲（增加时态相对指称小节）成功")

# 4. 更新“交互指标两条线”背景描述（包含 $\to$ 公式渲染）
old_lines_intro = """                    <!-- 交互指标两条线 -->
                    <h2 id="交互指标两条线">交互指标两条线</h2>
                    <p>
                        在数据构造与下游模型评测中，必须构建具备明确对照关系的**两条交互主线**：
                    </p>"""

arrow_html = f'<span class="katex-inline" data-tex="\\to">{rendered["to"]["html"]}</span>'
new_lines_intro = f"""                    <!-- 交互指标两条线 -->
                    <h2 id="交互指标两条线">交互指标两条线</h2>
                    <p>
                        在数据构造与评测体系中，必须建立清晰可量化的评估标尺。系统以<strong>冷启动无记忆多轮澄清</strong>与<strong>热启动有记忆轮次极速压缩</strong>作为两条对照主线：
                    </p>
                    <ul>
                        <li><strong>主线一（冷启动无记忆多轮澄清线）</strong>：用户首次发起业务时，智能体严禁脑补参数或默认开通。首轮未提供关键槽位时必须精准反问澄清，严格保证交互轮数不少于 2 轮（典型为 2~3 轮），完成“用户发起 {arrow_html} 客服反问澄清 {arrow_html} 用户补全并确认 {arrow_html} 客服受理收尾”的完整闭环，参数早泄率与擅自默认率必须为 0.0%；</li>
                        <li><strong>主线二（热启动有记忆轮次极速压缩线）</strong>：智能体已沉淀相应语义偏好或唤醒历史工单时，准确命中记忆槽位并直接向用户反问确认，交互轮次收敛至 1~2 轮，免去繁琐基础参数盘问，实现极速闭环。</li>
                    </ul>"""

if old_lines_intro in content:
    content = content.replace(old_lines_intro, new_lines_intro)
    logger.info("[+] 更新交互指标两条线描述成功")

# 5. 更新核心评测指标公式（TCG, CSCR, ERRA, EMTAR 全部渲染并附带复制按钮）
old_metrics_block = re.search(r'<h3 id="核心评测指标公式">.*?</div>\s*(?=<!-- 工作记忆工单账本检索 -->)', content, re.DOTALL)
if old_metrics_block:
    tcg_html = rendered["tcg"]["html"]
    cscr_html = rendered["cscr"]["html"]
    erra_html = rendered["erra"]["html"]
    emtar_html = rendered["emtar"]["html"]
    
    t_cold_html = rendered["t_cold"]["html"]
    range_cold_html = rendered["range_cold"]["html"]
    t_hot_html = rendered["t_hot"]["html"]
    range_hot_html = rendered["range_hot"]["html"]
    target_tcg_html = rendered["target_tcg"]["html"]

    new_metrics_section = f"""<h3 id="核心评测指标公式">核心评测指标公式</h3>

                    <div class="callout callout-important">
                        <div class="callout-title">指标一：交互轮数压缩增益 (Turn Compression Gain, TCG)</div>
                        <p>用于衡量长程记忆机制为用户带来的交互轮次效率提升比率：</p>
                        <div class="math-block" data-tex="{rendered['tcg']['tex']}">
                            <div class="math-block-header">
                                <span class="math-badge">LaTeX · TCG 公式</span>
                                <button class="math-copy-btn" onclick="copyLatex(this)" data-tex="{rendered['tcg']['tex']}">复制 LaTeX</button>
                            </div>
                            {tcg_html}
                        </div>
                        <p>
                            其中：
                        </p>
                        <ul>
                            <li><span class="katex-inline" data-tex="\\bar{{T}}_{{\\text{{cold}}}}">{t_cold_html}</span> 表示无记忆冷启动会话的平均交互轮数（理论基准：<span class="katex-inline" data-tex="2.5 \\sim 3.0">{range_cold_html}</span> 轮）；</li>
                            <li><span class="katex-inline" data-tex="\\bar{{T}}_{{\\text{{hot}}}}">{t_hot_html}</span> 表示有记忆热启动会话的平均交互轮数（理论基准：<span class="katex-inline" data-tex="1.0 \\sim 2.0">{range_hot_html}</span> 轮）；</li>
                            <li><strong>基准目标</strong>：<span class="katex-inline" data-tex="\\text{{TCG}} \\ge 35\\% \\sim 50\\%">{target_tcg_html}</span>。</li>
                        </ul>
                    </div>

                    <div class="callout callout-warn">
                        <div class="callout-title">指标二：零记忆澄清完整率 (Cold-Start Clarification Rate, CSCR)</div>
                        <p>衡量智能体在无先验记忆时的抗幻觉与规范反问能力：</p>
                        <div class="math-block" data-tex="{rendered['cscr']['tex']}">
                            <div class="math-block-header">
                                <span class="math-badge">LaTeX · CSCR 公式</span>
                                <button class="math-copy-btn" onclick="copyLatex(this)" data-tex="{rendered['cscr']['tex']}">复制 LaTeX</button>
                            </div>
                            {cscr_html}
                        </div>
                        <p>
                            首轮缺少画质/时延/时长等关键通信槽位时，智能体动作必须包含 <code>Clarify_Slot</code> 或 <code>Request_Info</code>，且严禁提前私自默认开通。<strong>目标达标线：100.0%</strong>。
                        </p>
                    </div>

                    <div class="callout callout-note">
                        <div class="callout-title">指标三：工作记忆单据检索准确率 (Episodic Record Retrieval Accuracy, ERRA)</div>
                        <p>衡量用户使用时态相对代词时，模型在历史工单流水账中定位目标单据的准确率：</p>
                        <div class="math-block" data-tex="{rendered['erra']['tex']}">
                            <div class="math-block-header">
                                <span class="math-badge">LaTeX · ERRA 公式</span>
                                <button class="math-copy-btn" onclick="copyLatex(this)" data-tex="{rendered['erra']['tex']}">复制 LaTeX</button>
                            </div>
                            {erra_html}
                        </div>
                        <p>
                            提取的历史单据 ID 与参数继承准确率必须与标注真值严格一致。<strong>目标达标线：100.0%</strong>。
                        </p>
                    </div>

                    <div class="callout callout-important">
                        <div class="callout-title">指标四：经验记忆情境激活与采纳率 (Experiential Memory Trigger & Acceptance Rate, EMTAR)</div>
                        <p>衡量在特定外场困难情境下，智能体经验建议被合理触发并被用户采纳的比例：</p>
                        <div class="math-block" data-tex="{rendered['emtar']['tex']}">
                            <div class="math-block-header">
                                <span class="math-badge">LaTeX · EMTAR 公式</span>
                                <button class="math-copy-btn" onclick="copyLatex(this)" data-tex="{rendered['emtar']['tex']}">复制 LaTeX</button>
                            </div>
                            {emtar_html}
                        </div>
                        <p>
                            在识别到特定现场外部挑战（如人流高密拥塞、恶劣天气弱网丢包）时，智能体经验提议命中并被用户确认采纳的比例。<strong>目标达标线：&ge; 90.0%</strong>。
                        </p>
                    </div>\n\n                    """
    content = content[:old_metrics_block.start()] + new_metrics_section + content[old_metrics_block.end():]
    logger.info("[+] 更新 4 项评测指标公式渲染块（TCG, CSCR, ERRA, EMTAR）成功")
else:
    logger.info("[!] 错误: 未找到旧指标公式块")

# 6. 在工作记忆中插入“时态相对指称计算与检索逻辑”小节
old_records_h3 = """                    <h3 id="历史工单流水账结构">历史工单流水账结构</h3>"""
delta_t_html = rendered["delta_t"]["html"]
delta_t_1_html = rendered["delta_t_1"]["html"]
delta_t_2_html = rendered["delta_t_2"]["html"]
delta_t_3_7_html = rendered["delta_t_3_7"]["html"]

temporal_calc_section = f"""                    <h3 id="时态相对指称计算与检索逻辑">时态相对指称计算与检索逻辑</h3>
                    <p>
                        系统根据当前会话的基准时间 <code>reference_time</code>，动态计算与历史各工单单据的时间差 <span class="katex-inline" data-tex="\\Delta t">{delta_t_html}</span>，并构建精准自然的口语指代：
                    </p>
                    <ul>
                        <li><strong><span class="katex-inline" data-tex="\\Delta t = 1">{delta_t_1_html}</span> 天</strong>：映射为“昨天”或“昨天的那个保障”；</li>
                        <li><strong><span class="katex-inline" data-tex="\\Delta t = 2">{delta_t_2_html}</span> 天</strong>：映射为“前天”；</li>
                        <li><strong><span class="katex-inline" data-tex="3 \\le \\Delta t \\le 7">{delta_t_3_7_html}</span> 天</strong>：映射为“上周”或“上周同期的保障”；</li>
                        <li><strong>同类型最近一条记录</strong>：映射为“上次”或“上回在[地点]办的那个”。</li>
                    </ul>

                    <h3 id="历史工单流水账结构">历史工单流水账结构</h3>"""

if old_records_h3 in content:
    content = content.replace(old_records_h3, temporal_calc_section, 1)
    logger.info("[+] 插入“时态相对指称计算与检索逻辑”及行内公式成功")

# 7. 更新“经验记忆本体定义”（插入 Experience 四元组形式化定义公式）
old_exp_def = """                    <h3 id="经验记忆本体定义">经验记忆本体定义</h3>
                    <pre><code class="language-json">{"""

exp_html = rendered["experience"]["html"]
new_exp_def = f"""                    <h3 id="经验记忆本体定义">经验记忆本体定义</h3>
                    <p>
                        经验记忆不是固定的槽位配置，而是<strong>结构化的情境决策知识库</strong>，形式化定义为四元组：
                    </p>
                    <div class="math-block" data-tex="{rendered['experience']['tex']}">
                        <div class="math-block-header">
                            <span class="math-badge">LaTeX · 经验四元组形式化定义</span>
                            <button class="math-copy-btn" onclick="copyLatex(this)" data-tex="{rendered['experience']['tex']}">复制 LaTeX</button>
                        </div>
                        {exp_html}
                    </div>
                    <pre><code class="language-json">{{"""

if old_exp_def in content:
    content = content.replace(old_exp_def, new_exp_def)
    logger.info("[+] 插入“经验记忆本体定义”四元组公式成功")

# 8. 在底部的 JavaScript 中注入 copyLatex 函数
old_script_tail = """            // 代码高亮初始化
            if (window.hljs) {
                hljs.highlightAll();
            }
        });
    </script>"""

new_script_tail = """            // 代码高亮初始化
            if (window.hljs) {
                hljs.highlightAll();
            }
        });

        // 复制 LaTeX 公式源码
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
    </script>"""

if old_script_tail in content:
    content = content.replace(old_script_tail, new_script_tail)
    logger.info("[+] 注入 copyLatex 交互脚本成功")

# 写入文件
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

logger.info(f"[✓] 成功更新 {html_path}，所有数学公式均已完成 LaTeX 格式规范化与 KaTeX 预渲染！")

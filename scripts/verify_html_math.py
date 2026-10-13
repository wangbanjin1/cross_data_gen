import sys
import re
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

html_text = Path('docs/memory_evolution_plan.html').read_text(encoding='utf-8')

print("Total characters:", len(html_text))
print("Math blocks count:", html_text.count('class="math-block"'))
print("Katex inlines count:", html_text.count('class="katex-inline"'))
print("Copy buttons count:", html_text.count('copyLatex(this)'))
print("TOC links count:", html_text.count('class="toc-link"'))
print("Diagram containers count:", html_text.count('class="diagram-container"'))

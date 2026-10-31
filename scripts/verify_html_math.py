import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

import sys
import re
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

html_text = Path('docs/memory_evolution_plan.html').read_text(encoding='utf-8')

logger.info("Total characters:", len(html_text))
logger.info("Math blocks count:", html_text.count('class="math-block"'))
logger.info("Katex inlines count:", html_text.count('class="katex-inline"'))
logger.info("Copy buttons count:", html_text.count('copyLatex(this)'))
logger.info("TOC links count:", html_text.count('class="toc-link"'))
logger.info("Diagram containers count:", html_text.count('class="diagram-container"'))

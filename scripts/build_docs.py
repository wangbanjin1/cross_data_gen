"""
自动化文档构建工具 (scripts/build_docs.py)
调用 docs/render_html.py，将 docs/update.md 渲染同步至 docs/update.html。
"""

import sys
from pathlib import Path

def main():
    root = Path(__file__).resolve().parent.parent
    render_script = root / "docs" / "render_html.py"
    if not render_script.exists():
        print(f"[ERROR] {render_script} 不存在")
        sys.exit(1)

    import subprocess
    cmd = [sys.executable, str(render_script)]
    subprocess.run(cmd, check=True)

if __name__ == '__main__':
    main()

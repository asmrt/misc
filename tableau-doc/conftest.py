import sys
from pathlib import Path

# tests/ から `import twbdoc` できるよう、パッケージ配置(このファイルと同じ階層)をsys.pathに追加する。
sys.path.insert(0, str(Path(__file__).parent))

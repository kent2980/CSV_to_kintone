"""EXEエントリーポイントの回帰テスト。"""
import ast
from pathlib import Path


def test_pyinstaller_entrypoint_uses_absolute_import():
    """直接実行するスクリプトで相対インポートを使用しないこと。"""
    root = Path(__file__).resolve().parents[1]
    tree = ast.parse((root / "run_gui.py").read_text(encoding="utf-8"))
    imports = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert any(node.module == "csv_to_kintone.gui" and node.level == 0 for node in imports)
    assert all(node.level == 0 for node in imports)


def test_workflow_packages_correct_entrypoint():
    """CIがパッケージ内の__main__.pyを直接EXE化しないこと。"""
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "--paths src run_gui.py" in workflow
    assert "--paths src src/csv_to_kintone/__main__.py" not in workflow

"""接続設定通知の回帰テスト（GUI表示不要）。"""
import ast
from pathlib import Path


def test_connection_actions_use_toast():
    source = (Path(__file__).resolve().parents[1] / "src/csv_to_kintone/gui.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    app = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "App")
    methods = {node.name: node for node in app.body if isinstance(node, ast.FunctionDef)}
    assert {"notify", "_dismiss_toast", "save_connection", "test_connection"} <= methods.keys()
    save_calls = [node for node in ast.walk(methods["save_connection"]) if isinstance(node, ast.Call)]
    assert sum(isinstance(call.func, ast.Attribute) and call.func.attr == "notify" for call in save_calls) >= 2
    test_calls = [node for node in ast.walk(methods["test_connection"]) if isinstance(node, ast.Call)]
    assert sum(isinstance(call.func, ast.Attribute) and call.func.attr == "notify" for call in test_calls) >= 2


def test_toast_is_non_modal_and_auto_dismisses():
    source = (Path(__file__).resolve().parents[1] / "src/csv_to_kintone/gui.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    app = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "App")
    notify = next(node for node in app.body if isinstance(node, ast.FunctionDef) and node.name == "notify")
    calls = [node for node in ast.walk(notify) if isinstance(node, ast.Call)]
    assert any(isinstance(call.func, ast.Attribute) and call.func.attr == "place" for call in calls)
    assert any(isinstance(call.func, ast.Attribute) and call.func.attr == "after" for call in calls)
    assert not any(isinstance(call.func, ast.Attribute) and call.func.attr == "grab_set" for call in calls)

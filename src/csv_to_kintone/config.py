"""ローカル設定とWindows DPAPIによる認証情報の保管。"""
from __future__ import annotations
import json
from pathlib import Path
import win32crypt
from .core import ImportJob

DATA_DIR = Path.home() / "AppData" / "Local" / "CSV_to_kintone"


def load_settings(directory: Path = DATA_DIR) -> dict:
    """設定ファイルを読み込みます。未作成なら初期設定を返します。"""
    path = directory / "config.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"domain": "", "username": "", "jobs": [], "startup": False}


def save_settings(settings: dict, directory: Path = DATA_DIR) -> None:
    """設定を一時ファイル経由で保存します。"""
    directory.mkdir(parents=True, exist_ok=True)
    temp = directory / "config.tmp"
    temp.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(directory / "config.json")


def save_password(password: str, directory: Path = DATA_DIR) -> None:
    """パスワードを現在のWindowsユーザーに紐付けて暗号化保存します。"""
    directory.mkdir(parents=True, exist_ok=True)
    encrypted = win32crypt.CryptProtectData(password.encode(), None, None, None, None, 0)
    (directory / "credentials.dat").write_bytes(encrypted)


def load_password(directory: Path = DATA_DIR) -> str:
    """暗号化されたパスワードを復号します。未保存の場合は空文字です。"""
    path = directory / "credentials.dat"
    return win32crypt.CryptUnprotectData(path.read_bytes(), None, None, None, 0)[1].decode() if path.exists() else ""


def jobs_from_settings(settings: dict) -> list[ImportJob]:
    """辞書の配列からジョブ設定を生成します。"""
    return [ImportJob(**item) for item in settings.get("jobs", [])]

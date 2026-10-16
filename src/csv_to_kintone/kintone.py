"""kintone REST APIクライアント。"""
from __future__ import annotations
import base64
import requests


class KintoneAPI:
    """ユーザー認証でkintone REST APIにアクセスします。"""

    def __init__(self, domain: str, username: str, password: str):
        self.base = "https://" + domain.strip().removeprefix("https://").rstrip("/")
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        self.session = requests.Session()
        self.session.headers.update({"X-Cybozu-Authorization": token})

    def request(self, method: str, endpoint: str, **kwargs):
        """HTTPエラーを例外に変換してJSONレスポンスを返します。"""
        response = self.session.request(method, self.base + "/k/v1/" + endpoint, timeout=60, **kwargs)
        response.raise_for_status()
        return response.json()

    def fields(self, app_id: int) -> dict:
        """対象アプリのフィールド情報を取得します。"""
        return self.request("GET", "app/form/fields.json", params={"app": app_id})["properties"]

    def records(self, app_id: int) -> list[dict]:
        """カーソルAPIで全レコードを取得します。"""
        cursor = self.request("POST", "records/cursor.json", json={"app": app_id, "size": 500})["id"]
        records = []
        try:
            while True:
                data = self.request("GET", "records/cursor.json", params={"id": cursor})
                records.extend(data["records"])
                if not data["next"]:
                    break
        finally:
            try:
                self.request("DELETE", "records/cursor.json", json={"id": cursor})
            except requests.HTTPError:
                pass
        return records

    def add(self, app_id: int, records: list[dict]) -> None:
        """レコードを最大100件ずつ登録します。"""
        self.request("POST", "records.json", json={"app": app_id, "records": records})

    def update(self, app_id: int, records: list[dict]) -> None:
        """レコードを最大100件ずつ更新します。"""
        self.request("PUT", "records.json", json={"app": app_id, "records": records})

    def delete(self, app_id: int, ids: list[str]) -> None:
        """レコードを最大100件ずつ削除します。"""
        self.request("DELETE", "records.json", json={"app": app_id, "ids": ids})

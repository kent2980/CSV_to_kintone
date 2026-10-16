"""Windows用CSVインポートGUI。"""
import threading
from pathlib import Path
import customtkinter as ctk
import pystray
from PIL import Image
from .config import DATA_DIR, load_settings, save_settings, load_password, save_password, jobs_from_settings
from .core import execute_import
from .kintone import KintoneAPI


class App(ctk.CTk):
    """ジョブ設定・接続・実行履歴を4タブで管理する画面。"""

    def __init__(self):
        super().__init__()
        self.title("CSV to kintone")
        self.geometry("900x650")
        self.settings = load_settings()
        self.running = set()
        self.stopping = False
        self.after_ids = {}
        self.tray = None
        self.protocol("WM_DELETE_WINDOW", self.withdraw)
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=12)
        for name in ("インポート管理", "インポート設定", "接続設定", "実行履歴"):
            self.tabs.add(name)
        self.log_box = ctk.CTkTextbox(self.tabs.tab("実行履歴"))
        self.log_box.pack(fill="both", expand=True)
        self.build_connection()
        self.build_editor()
        self.build_jobs()
        self.start_tray()

    def build_connection(self):
        tab = self.tabs.tab("接続設定")
        self.domain = ctk.CTkEntry(tab, placeholder_text="example.cybozu.com", width=420)
        self.domain.insert(0, self.settings.get("domain", ""))
        self.domain.pack(pady=8)
        self.username = ctk.CTkEntry(tab, placeholder_text="ユーザー名", width=420)
        self.username.insert(0, self.settings.get("username", ""))
        self.username.pack(pady=8)
        self.password = ctk.CTkEntry(tab, placeholder_text="パスワード", show="*", width=420)
        try:
            self.password.insert(0, load_password())
        except Exception:
            pass
        self.password.pack(pady=8)
        ctk.CTkButton(tab, text="接続情報を保存", command=self.save_connection).pack(pady=8)
        ctk.CTkButton(tab, text="接続テスト", command=self.test_connection).pack(pady=8)

    def save_connection(self):
        self.settings["domain"] = self.domain.get().strip()
        self.settings["username"] = self.username.get().strip()
        save_password(self.password.get())
        save_settings(self.settings)
        self.log("接続情報を保存しました")

    def client(self):
        return KintoneAPI(self.domain.get(), self.username.get(), self.password.get())

    def test_connection(self):
        def task():
            try:
                self.client().request("GET", "apps.json", params={"limit": 1})
                self.after(0, lambda: self.log("接続テスト成功"))
            except Exception as error:
                message = str(error)
                self.after(0, lambda: self.log("接続テスト失敗: " + message))
        threading.Thread(target=task, daemon=True).start()

    def build_editor(self):
        tab = self.tabs.tab("インポート設定")
        self.inputs = {}
        for key, label in (("id", "ジョブID"), ("name", "ジョブ名"), ("csv_path", "CSVパス"), ("app_id", "アプリID"), ("interval_minutes", "実行間隔（分）"), ("field_mapping", "マッピングJSON（CSV列名: フィールドラベル）"), ("duplicate_columns", "重複チェック列（カンマ区切り）")):
            ctk.CTkLabel(tab, text=label).pack(anchor="w")
            entry = ctk.CTkEntry(tab, width=650)
            entry.pack(pady=3)
            self.inputs[key] = entry
        ctk.CTkButton(tab, text="追加・更新", command=self.save_job).pack(pady=12)

    def save_job(self):
        import json
        try:
            data = {key: entry.get().strip() for key, entry in self.inputs.items()}
            data["app_id"] = int(data["app_id"])
            data["interval_minutes"] = int(data["interval_minutes"])
            if data["interval_minutes"] < 1 or data["app_id"] < 1:
                raise ValueError("ID・間隔は正の整数を指定してください")
            data["field_mapping"] = json.loads(data["field_mapping"] or "{}")
            data["duplicate_columns"] = [s.strip() for s in data["duplicate_columns"].split(",") if s.strip()]
            data["enabled"] = True
            jobs = self.settings.setdefault("jobs", [])
            jobs[:] = [item for item in jobs if item["id"] != data["id"]]
            jobs.append(data)
            save_settings(self.settings)
            self.build_jobs()
            self.log("設定保存: " + data["name"])
        except Exception as error:
            self.log("設定エラー: " + str(error))

    def build_jobs(self):
        tab = self.tabs.tab("インポート管理")
        for widget in tab.winfo_children():
            widget.destroy()
        for job in jobs_from_settings(self.settings):
            row = ctk.CTkFrame(tab)
            row.pack(fill="x", pady=5)
            ctk.CTkLabel(row, text=f"{job.name} / アプリ{job.app_id} / {job.interval_minutes}分").pack(side="left", padx=8)
            ctk.CTkButton(row, text="今すぐ実行", width=100, command=lambda j=job: self.run_job(j)).pack(side="right", padx=5)
            if job.enabled:
                self.schedule(job)

    def schedule(self, job):
        if job.id in self.after_ids:
            self.after_cancel(self.after_ids.pop(job.id))
        self.after_ids[job.id] = self.after(job.interval_minutes * 60000, lambda: self.scheduled(job))

    def scheduled(self, job):
        if not self.stopping:
            self.run_job(job)
            self.schedule(job)

    def run_job(self, job):
        if job.id in self.running or self.stopping:
            return
        self.running.add(job.id)
        def task():
            try:
                result = execute_import(job, self.client(), str(DATA_DIR / "backups"))
                message = f"{job.name}: {result.status} 追加{result.created} 更新{result.updated} 削除{result.deleted} {result.error_message or ''}"
                self.after(0, lambda: self.log(message))
            finally:
                self.after(0, lambda: self.running.discard(job.id))
        threading.Thread(target=task, daemon=True).start()

    def log(self, message):
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")

    def start_tray(self):
        image = Image.new("RGB", (64, 64), "#1976d2")
        menu = pystray.Menu(
            pystray.MenuItem("画面を開く", lambda: self.after(0, self.deiconify)),
            pystray.MenuItem("終了", lambda: self.after(0, self.exit_app)),
        )
        self.tray = pystray.Icon("CSV_to_kintone", image, "CSV to kintone", menu)
        threading.Thread(target=self.tray.run, daemon=True).start()

    def exit_app(self):
        self.stopping = True
        if self.running:
            self.after(500, self.exit_app)
            return
        if self.tray:
            self.tray.stop()
        self.destroy()


def main():
    """GUIを起動します。"""
    ctk.set_appearance_mode("system")
    App().mainloop()

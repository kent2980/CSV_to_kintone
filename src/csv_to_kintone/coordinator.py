"""実行中ジョブとアプリ単位の排他制御。"""
from threading import Lock


class JobCoordinator:
    """ジョブIDとアプリIDの重複実行を防ぎます。"""

    def __init__(self):
        self._lock = Lock()
        self._jobs = set()
        self._apps = set()

    def acquire(self, job_id: str, app_id: int) -> bool:
        """空きがあれば実行枠を確保します。戻り値は確保成否です。"""
        with self._lock:
            if job_id in self._jobs or app_id in self._apps:
                return False
            self._jobs.add(job_id)
            self._apps.add(app_id)
            return True

    def release(self, job_id: str, app_id: int) -> None:
        """実行完了後に確保した枠を解放します。"""
        with self._lock:
            self._jobs.discard(job_id)
            self._apps.discard(app_id)

    def busy(self) -> bool:
        """実行中のジョブが存在するか返します。"""
        with self._lock:
            return bool(self._jobs)

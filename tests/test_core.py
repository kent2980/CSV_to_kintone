from pathlib import Path
import pytest
from csv_to_kintone.core import ImportJob, execute_import, read_csv, resolve_field_codes

def test_empty_csv_does_not_delete(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("name\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_csv(str(path))

def test_mapping_by_label():
    assert resolve_field_codes({"code": {"label": "棚番", "type": "SINGLE_LINE_TEXT"}}, ["場所"], {"場所": "棚番"}) == {"場所": "code"}

class FakeClient:
    def __init__(self):
        self.deleted = []
        self.added = []
    def fields(self, app_id):
        return {"name": {"label": "name", "type": "SINGLE_LINE_TEXT"}}
    def records(self, app_id):
        return [{"$id": {"value": "1"}, "name": {"value": "old"}}]
    def delete(self, app_id, ids):
        self.deleted.extend(ids)
    def add(self, app_id, records):
        self.added.extend(records)
    def update(self, app_id, records):
        pass

def test_replace_with_backup(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("name\nnew\n", encoding="utf-8")
    client = FakeClient()
    result = execute_import(ImportJob("id", "job", str(path), 1), client, str(tmp_path / "backups"))
    assert result.status == "success"
    assert result.deleted == 1
    assert result.created == 1
    assert result.backup_path is not None
    assert client.deleted == ["1"]


def test_backup_failure_prevents_delete(tmp_path, monkeypatch):
    from csv_to_kintone import core
    path = tmp_path / "data.csv"
    path.write_text("name\\nnew\\n".replace("\\n", "\n"), encoding="utf-8")
    client = FakeClient()
    def fail(*args):
        raise OSError("disk full")
    monkeypatch.setattr(core, "create_backup", fail)
    result = execute_import(ImportJob("id", "job", str(path), 1), client, str(tmp_path))
    assert result.status == "failed"
    assert client.deleted == []
    assert client.added == []

def test_unsupported_existing_field_prevents_delete(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("name\nnew\n", encoding="utf-8")
    client = FakeClient()
    client.records = lambda app_id: [{"$id": {"value": "1"}, "name": {"value": "old"}, "attachment": {"type": "FILE", "value": [{"fileKey": "abc"}]}}]
    result = execute_import(ImportJob("id", "job", str(path), 1), client, str(tmp_path))
    assert result.status == "failed"
    assert client.deleted == []

def test_missing_required_field_prevents_delete(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("name\nnew\n", encoding="utf-8")
    client = FakeClient()
    client.fields = lambda app_id: {
        "name": {"label": "name", "type": "SINGLE_LINE_TEXT"},
        "required": {"label": "required", "type": "SINGLE_LINE_TEXT", "required": True}
    }
    result = execute_import(ImportJob("id", "job", str(path), 1), client, str(tmp_path))
    assert result.status == "failed"
    assert client.deleted == []

def test_failed_post_keeps_backup_and_reports_partial_failure(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("name\nnew\n", encoding="utf-8")
    client = FakeClient()
    client.add = lambda *args: (_ for _ in ()).throw(RuntimeError("write failure"))
    result = execute_import(ImportJob("id", "job", str(path), 1), client, str(tmp_path))
    assert result.status == "failed"
    assert result.deleted == 1
    assert result.backup_path is not None
    assert Path(result.backup_path).exists()

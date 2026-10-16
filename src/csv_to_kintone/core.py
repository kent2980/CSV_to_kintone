"""CSVインポートの業務ロジック。"""
import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

@dataclass
class ImportJob:
    id: str
    name: str
    csv_path: str
    app_id: int
    enabled: bool = True
    interval_minutes: int = 60
    field_mapping: dict = field(default_factory=dict)
    duplicate_columns: list = field(default_factory=list)

@dataclass
class ImportResult:
    job_id: str
    status: str = "failed"
    created: int = 0
    updated: int = 0
    deleted: int = 0
    backup_path: str | None = None
    error_message: str | None = None

def read_csv(path: str):
    """CSVヘッダーとデータを読み込み、空データや不正行を拒否します。"""
    with open(path, encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        if not columns or len(set(columns)) != len(columns) or any(not c for c in columns):
            raise ValueError("CSVヘッダーが不正です")
        rows = list(reader)
    if not rows or any(None in row or None in row.values() for row in rows):
        raise ValueError("CSVが空、または不正な行があります")
    return columns, rows

def resolve_field_codes(fields: dict, columns: list, mapping: dict):
    """CSV列名とフィールドラベルを対応付けてコードを返します。"""
    if set(mapping) - set(columns):
        raise ValueError("マッピング対象のCSV列が存在しません")
    result = {}
    supported = {"SINGLE_LINE_TEXT", "MULTI_LINE_TEXT", "NUMBER", "DATE", "DATETIME", "DROP_DOWN", "RADIO_BUTTON", "LINK"}
    for col in columns:
        label = mapping.get(col, col)
        matches = [code for code, prop in fields.items() if prop.get("label") == label]
        if len(matches) != 1 or fields[matches[0]].get("type") not in supported:
            raise ValueError(f"フィールド未発見・重複・未対応: {label}")
        result[col] = matches[0]
    if len(set(result.values())) != len(result):
        raise ValueError("フィールドの割当が重複しています")
    return result

def create_backup(app_id: int, records: list, directory: str):
    """削除前の全レコードをJSONに保存し、再読込して検証します。"""
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"app_{app_id}_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
    content = {"app_id": app_id, "records": records}
    temporary = path.with_suffix(".tmp")
    try:
        temporary.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
        if json.loads(temporary.read_text(encoding="utf-8")) != content:
            raise ValueError("バックアップ検証に失敗")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return str(path)

def execute_import(job: ImportJob, client, backup_dir: str) -> ImportResult:
    """CSVを検証してUPSERTまたはバックアップ付き全件入替を実行します。"""
    result = ImportResult(job_id=job.id)
    try:
        columns, rows = read_csv(job.csv_path)
        codes = resolve_field_codes(client.fields(job.app_id), columns, job.field_mapping)
        keys = job.duplicate_columns
        if len(keys) != len(set(keys)) or any(key not in columns for key in keys):
            raise ValueError("重複チェック列が不正です")
        payload = [{codes[col]: {"value": row[col]} for col in columns} for row in rows]
        existing = client.records(job.app_id)
        if keys:
            index = {}
            for record in existing:
                key = tuple(str(record[codes[col]]["value"]) for col in keys)
                if key in index:
                    raise ValueError("kintone側に重複キーがあります")
                index[key] = record
            seen, added, updated = set(), [], []
            for row, record in zip(rows, payload):
                key = tuple(row[col] for col in keys)
                if key in seen or any(not value.strip() for value in key):
                    raise ValueError("CSV内に空欄・重複キーがあります")
                seen.add(key)
                if key in index:
                    updated.append({"id": index[key]["$id"]["value"], "record": record})
                else:
                    added.append(record)
            for offset in range(0, len(updated), 100):
                batch = updated[offset:offset + 100]
                client.update(job.app_id, batch)
                result.updated += len(batch)
            for offset in range(0, len(added), 100):
                batch = added[offset:offset + 100]
                client.add(job.app_id, batch)
                result.created += len(batch)
        else:
            result.backup_path = create_backup(job.app_id, existing, backup_dir)
            ids = [record["$id"]["value"] for record in existing]
            for offset in range(0, len(ids), 100):
                batch = ids[offset:offset + 100]
                client.delete(job.app_id, batch)
                result.deleted += len(batch)
            for offset in range(0, len(payload), 100):
                batch = payload[offset:offset + 100]
                client.add(job.app_id, batch)
                result.created += len(batch)
        result.status = "success"
    except Exception as error:
        result.error_message = str(error)
    return result

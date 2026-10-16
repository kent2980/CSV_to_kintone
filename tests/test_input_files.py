"""CSV / XLSXの入力検証。"""
from datetime import date, datetime
from zipfile import ZipFile, ZIP_DEFLATED
import re
from openpyxl import Workbook
import pytest
from csv_to_kintone.core import read_csv, read_input_file


def workbook(tmp_path, header, rows):
    path = tmp_path / "sample.xlsx"
    book = Workbook()
    sheet = book.active
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    book.save(path)
    return path


def test_xlsx_values_and_headers(tmp_path):
    path = workbook(tmp_path, ["管理No", "数量", "日付"], [["001", 12, date(2026, 10, 16)]])
    columns, rows = read_input_file(str(path))
    assert columns == ["管理No", "数量", "日付"]
    assert rows == [{"管理No": "001", "数量": "12", "日付": "2026-10-16"}]


def test_xlsx_empty_data_is_rejected(tmp_path):
    path = workbook(tmp_path, ["name"], [])
    with pytest.raises(ValueError, match="0件"):
        read_input_file(str(path))


def test_xlsx_duplicate_header_is_rejected(tmp_path):
    path = workbook(tmp_path, ["name", "name"], [["a", "b"]])
    with pytest.raises(ValueError, match="ヘッダー"):
        read_input_file(str(path))


def test_xlsx_blank_header_is_rejected(tmp_path):
    path = workbook(tmp_path, ["name", None], [["a", "b"]])
    with pytest.raises(ValueError, match="ヘッダー"):
        read_input_file(str(path))


def test_xlsx_formula_without_cached_result_fails_closed(tmp_path):
    path = workbook(tmp_path, ["name"], [["=1+1"]])
    with pytest.raises(ValueError, match="数式"):
        read_input_file(str(path))


def test_xlsx_formula_with_cached_result(tmp_path):
    """保存済みの計算結果を取得する。"""
    path = workbook(tmp_path, ["name", "total"], [["a", "=1+2"]])
    with ZipFile(path, "r") as archive:
        members = [(item, archive.read(item.filename)) for item in archive.infolist()]
    with ZipFile(path, "w") as archive:
        for item, data in members:
            if item.filename == "xl/worksheets/sheet1.xml":
                xml = data.decode("utf-8")
                xml = re.sub(r'(<f>1\\+2</f><v>)(</v>)', r'\\g<1>3\\2', xml)
                data = xml.encode("utf-8")
            archive.writestr(item, data)
    columns, rows = read_input_file(str(path))
    assert columns == ["name", "total"]
    assert rows == [{"name": "a", "total": "3"}]


def test_xlsx_missing_formula_cache_prevents_delete(tmp_path):
    from csv_to_kintone.core import ImportJob, execute_import
    from test_core import FakeClient
    path = workbook(tmp_path, ["name"], [["=1+2"]])
    client = FakeClient()
    result = execute_import(ImportJob("id", "job", str(path), 1), client, str(tmp_path))
    assert result.status == "failed"
    assert "数式" in result.error_message
    assert client.deleted == []


def test_xlsx_blank_row_is_ignored(tmp_path):
    path = workbook(tmp_path, ["name"], [["a"], [None], ["b"]])
    _, rows = read_input_file(str(path))
    assert rows == [{"name": "a"}, {"name": "b"}]


def test_xlsx_extension_case_insensitive(tmp_path):
    path = workbook(tmp_path, ["name"], [["a"]])
    renamed = path.with_suffix(".XLSX")
    path.rename(renamed)
    assert read_input_file(str(renamed))[1] == [{"name": "a"}]


def test_unsupported_file_extension(tmp_path):
    path = tmp_path / "data.xls"
    path.write_text("name", encoding="utf-8")
    with pytest.raises(ValueError, match="未対応"):
        read_input_file(str(path))


def test_csv_still_supported(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("name\na\n", encoding="utf-8")
    assert read_input_file(str(path)) == read_csv(str(path))

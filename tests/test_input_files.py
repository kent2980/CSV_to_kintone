"""CSV / XLSXの入力検証。"""
from datetime import date, datetime
from zipfile import ZipFile, ZIP_DEFLATED
from xml.etree import ElementTree as ET
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
                root = ET.fromstring(data)
                namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
                cell = root.find(f".//{namespace}c[@r='B2']")
                assert cell is not None
                formula = cell.find(f"{namespace}f")
                assert formula is not None and formula.text == "1+2"
                cached = cell.find(f"{namespace}v")
                if cached is None:
                    cached = ET.SubElement(cell, f"{namespace}v")
                cached.text = "3"
                data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
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


def test_cp932_csv_with_japanese_headers(tmp_path):
    path = tmp_path / "shift_jis.csv"
    path.write_bytes("指図,機種名\\n001,基板A\\n".replace("\\n", "\n").encode("cp932"))
    assert read_input_file(str(path)) == (
        ["指図", "機種名"],
        [{"指図": "001", "機種名": "基板A"}],
    )


def test_utf8_bom_csv_still_supported(tmp_path):
    path = tmp_path / "utf8.csv"
    path.write_text("指図,機種名\\n001,基板A\\n".replace("\\n", "\n"), encoding="utf-8-sig")
    assert read_input_file(str(path))[1] == [{"指図": "001", "機種名": "基板A"}]


def test_invalid_csv_encoding_does_not_delete(tmp_path):
    from csv_to_kintone.core import ImportJob, execute_import
    from test_core import FakeClient
    path = tmp_path / "broken.csv"
    path.write_bytes(b"\\x81".decode("unicode_escape").encode("latin1"))
    client = FakeClient()
    result = execute_import(ImportJob("id", "job", str(path), 1), client, str(tmp_path))
    assert result.status == "failed"
    assert client.deleted == []

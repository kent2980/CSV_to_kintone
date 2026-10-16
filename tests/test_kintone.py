"""カーソルのクリーンアップとAPIエラーのテスト。"""
from unittest.mock import Mock
import pytest
import requests
from csv_to_kintone.kintone import KintoneAPI


def test_cursor_cleanup_ignores_gaia_cn01():
    api = KintoneAPI("example.cybozu.com", "user", "password")
    calls = []
    def request(method, endpoint, **kwargs):
        calls.append(method)
        if method == "POST":
            return {"id": "cursor"}
        if method == "GET":
            return {"records": [{"$id": {"value": "1"}}], "next": False}
        raise ValueError("kintone API DELETE records/cursor.json: HTTP 404 - GAIA_CN01: expired")
    api.request = request
    assert len(api.records(1)) == 1
    assert calls == ["POST", "GET", "DELETE"]


def test_cursor_cleanup_other_errors_are_not_ignored():
    api = KintoneAPI("example.cybozu.com", "user", "password")
    def request(method, endpoint, **kwargs):
        if method == "POST":
            return {"id": "cursor"}
        if method == "GET":
            return {"records": [], "next": False}
        raise ValueError("kintone API DELETE records/cursor.json: HTTP 403 - CB_NO02: forbidden")
    api.request = request
    with pytest.raises(ValueError, match="CB_NO02"):
        api.records(1)


def test_api_error_includes_kintone_details():
    api = KintoneAPI("example.cybozu.com", "user", "password")
    response = Mock()
    response.status_code = 400
    response.json.return_value = {"code": "CB_VA01", "message": "invalid field", "errors": {"records[0].field": {"messages": ["bad"]}}}
    response.raise_for_status.side_effect = requests.HTTPError("400")
    api.session.request = Mock(return_value=response)
    with pytest.raises(ValueError, match="CB_VA01") as error:
        api.add(1, [{"field": {"value": "bad"}}])
    assert "records[0].field" in str(error.value)

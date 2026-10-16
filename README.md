# CSV_to_kintone

Windows用のCSV → kintoneインポートツール（開発中）。

## 予定機能
- 複数CSVとkintoneアプリの組み合わせを設定
- CSV列名からkintoneフィールドラベルを経由してフィールドコードを解決
- 複合キーUPSERT、キー未指定時はバックアップ後の全件入替
- 定期実行、タスクトレイ常駐、Windows用EXE

## 開発環境
Windows / Python 3.12

```powershell
python -m pip install -e ".[test]"
python -m pytest
python -m csv_to_kintone
```

## EXE
[最新版リリース](https://github.com/kent2980/CSV_to_kintone/releases/latest)

※リリースはビルド・検証完了後に公開します。現時点ではEXEの配布を保証しません。

## 注意
開発途中のため、本番kintoneアプリで実行しないでください。特に重複チェック列未指定のジョブは既存レコードを削除します。

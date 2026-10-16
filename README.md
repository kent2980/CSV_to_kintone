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

## XLSX読み込み
CSVに加えて.xlsx形式に対応しています。XLSXは先頭シートの1行目を列名、2行目以降をデータとして読み込みます。空行は無視し、日付はISO形式に変換します。数式セルはExcelに保存された計算結果を取得します。計算結果が未保存の数式セル、重複・空欄の列名、データ0件は安全のため停止します。openpyxlは数式を再計算しないため、Excelで再計算して保存してください。旧.xlsは対象外です。Excelの表示書式ではなくセルの値を使用します。先頭ゼロを保持する識別子はExcel側で文字列として保存してください。

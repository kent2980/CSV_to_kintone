"""PyInstaller用エントリーポイント。パッケージ絶対インポートを使用します。"""
from csv_to_kintone.gui import main


if __name__ == "__main__":
    main()

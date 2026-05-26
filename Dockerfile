# Python3.9が入った環境をベースにする
FROM mcr.microsoft.com/playwright/python:v1.60.0-jammy

# 作業フォルダを作成
WORKDIR /app

# 必要なファイルをコピー
COPY . /app

# ライブラリをインストール
RUN pip install --no-cache-dir -r requirements.txt

# ポート8000番を開放
EXPOSE 8000

# サーバーを起動
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
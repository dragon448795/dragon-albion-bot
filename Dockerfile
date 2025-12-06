# 使用官方 Python 3.9 鏡像
FROM python:3.9-slim

# 設定工作目錄
WORKDIR /app

# 複製依賴檔案
COPY requirements.txt .

# 安裝依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製所有程式碼
COPY . .

# 運行 BOT
CMD ["python", "main.py"]
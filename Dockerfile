FROM python:3.12-slim

WORKDIR /app

# 先複製依賴，利用 Docker layer cache
COPY requirements_api.txt .
RUN pip install --no-cache-dir -r requirements_api.txt

# 複製應用程式碼
COPY app/ ./app/

# output/ 透過 volume mount 進來（qa_final.json, qa_embeddings.npy）
# 啟動時環境變數注入 OPENAI_API_KEY

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HF_HOME=/hf_cache
WORKDIR /app
RUN adduser --disabled-password --gecos "" appuser && mkdir -p /hf_cache && chown -R appuser /hf_cache

# deps first
COPY requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# app layer
COPY . .
RUN chown -R appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8000"]
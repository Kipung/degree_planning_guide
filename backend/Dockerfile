FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HF_HOME=/hf_cache PYTHONPATH=/app
WORKDIR /app
RUN adduser --disabled-password --gecos "" appuser \
    && mkdir -p /hf_cache

COPY requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

COPY --chown=appuser:appuser . .
USER appuser

EXPOSE 8000
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8000"]
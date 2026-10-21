FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home appuser
COPY --chown=appuser:appuser clause_ledger ./clause_ledger
USER appuser
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn clause_ledger.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]

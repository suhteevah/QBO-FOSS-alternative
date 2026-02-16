FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for psycopg2 and tesseract
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create non-root user
RUN addgroup --system appuser && adduser --system --ingroup appuser appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "openledger.main:app", "--host", "0.0.0.0", "--port", "8000"]

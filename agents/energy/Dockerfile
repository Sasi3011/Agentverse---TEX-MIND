FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/models /app/data

# Copy the models and backend code
# Assuming models were pre-trained and exist in the models directory
COPY models/ /app/models/
COPY . /app/

ENV TARIFF_RATE_PER_KWH_INR=7.5
ENV PYTHONPATH=/app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8005"]

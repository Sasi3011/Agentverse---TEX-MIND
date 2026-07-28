FROM python:3.11-slim

WORKDIR /app

# Build dependencies for Prophet / pystan
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-generate dataset and train models at build time
RUN python generate_dataset.py && python scripts/train_model.py

EXPOSE 8008

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8008"]

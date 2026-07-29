FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN python scripts/generate_data.py
RUN python model.py
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]

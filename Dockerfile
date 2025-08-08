FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && playwright install --with-deps

COPY . .

CMD ["python", "main.py"]

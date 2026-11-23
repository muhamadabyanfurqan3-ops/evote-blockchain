FROM python:3.11-slim

WORKDIR /app

# Hindari buffering log stdout/stderr
ENV PYTHONUNBUFFERED=1

# Salin dependensi dan install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Salin source code
COPY . .

# Buat folder data persisten
RUN mkdir -p data

# Default command (dapat di-override di docker-compose)
CMD ["python", "-m", "coordinator", "--port", "5000"]

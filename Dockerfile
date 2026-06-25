# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install system dependencies required for WeasyPrint and psycopg2
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libpq-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Expose port 8080
EXPOSE 8080

# ถ้ามีการใช้ Entrypoint script ต้องระวังเรื่อง Line Ending (CRLF vs LF)
# ถ้าไฟล์ .sh สร้างบน Windows อาจจะรันไม่ได้บน Linux
COPY ./entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//g' /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

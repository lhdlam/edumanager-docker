# ============================================================
# Dockerfile - EduManager Flask App
# ============================================================
FROM python:3.11-slim

# Đặt working directory
WORKDIR /app

# Cài đặt dependencies trước (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ source code
COPY . .

# Tạo thư mục data để lưu SQLite database
RUN mkdir -p /data

# Biến môi trường
ENV DATA_DIR=/data
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Expose port 3333
EXPOSE 3333

# Script khởi động: init DB rồi chạy gunicorn
CMD python -c "from database import init_db; init_db(); print('✅ Database initialized')" && \
    gunicorn --bind 0.0.0.0:3333 \
             --workers 2 \
             --timeout 120 \
             --access-logfile - \
             --error-logfile - \
             app:app

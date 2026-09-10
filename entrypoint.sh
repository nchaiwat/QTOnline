#!/bin/sh

# ตรวจสอบว่ากำลังรัน Database หรือไม่
if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."
    
    # วนลูปรอจนกว่า Database จะพร้อม (สำคัญมากสำหรับ Docker บน Windows ที่ DB อาจ start ช้า)
    while ! nc -z $DB_HOST $DB_PORT; do
      sleep 0.5
    done

    echo "PostgreSQL started"
fi

# ---------------------------------------------------------
# ส่วนสำคัญสำหรับ WINDOWS HOST:
# ---------------------------------------------------------
# สร้างโฟลเดอร์ instance ถ้ายังไม่มี
# บน Windows การ Mount volume อาจจะทำให้โฟลเดอร์หายไปหรือ Permission เพี้ยน
echo "Creating instance directory..."
mkdir -p /app/instance

# ฟิกซ์ Permission (ใน Container เป็น root แต่นอก Container เป็น User Windows)
chmod 777 /app/instance

# ตรวจสอบว่าไฟล์ key มีปัญหาหรือไม่ ถ้ามีให้ลบเพื่อให้ App สร้างใหม่
if [ -f /app/instance/sig.key ]; then
    chmod 666 /app/instance/sig.key
fi

echo "Environment prepared. Starting Gunicorn..."

# -w 2 --threads 4: 2 workers with 4 threads each to handle concurrent requests and avoid queue bottlenecks
exec gunicorn -w 2 --threads 4 --timeout 120 -b 0.0.0.0:8000 app:app

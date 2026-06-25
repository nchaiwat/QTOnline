#!/bin/bash

# =============================================================================
# 🚀 PO-Online: One-Click VPS Deploy Script (Docker Edition)
# คัดลอกไฟล์นี้ไปยัง VPS และรันด้วยคำสั่ง: bash vps_setup.sh
# =============================================================================

set -e # หยุดทำงานหากมีข้อผิดพลาด

echo "----------------------------------------------------"
echo "🌟 PO-Online Setup Script v1.7 (Hostinger/Ubuntu)"
echo "----------------------------------------------------"

# 1. ตรวจสอบสิทธิ์ Root
if [ "$EUID" -ne 0 ]; then 
  echo "❌ กรุณารันสคริปต์นี้ด้วยสิทธิ์ root (ใช้ sudo bash vps_setup.sh)"
  exit 1
fi

# 2. ติดตั้ง Docker & Docker Compose (ถ้ายังไม่มี)
if ! [ -x "$(command -v docker)" ]; then
  echo "📦 กำลังติดตั้ง Docker..."
  curl -fsSL https://get.docker.com -o get-docker.sh
  sh get-docker.sh
  systemctl enable --now docker
else
  echo "✅ Docker ติดตั้งอยู่แล้ว"
fi

if ! [ -x "$(command -v docker-compose)" ]; then
  echo "📦 กำลังติดตั้ง Docker Compose..."
  apt-get update && apt-get install -y docker-compose
else
  echo "✅ Docker Compose ติดตั้งอยู่แล้ว"
fi

# 3. จัดการโครงสร้างโฟลเดอร์
echo "📂 กำลังเตรียมไดเรกทอรี..."
mkdir -p instance uploads static/product_images logs
chmod -R 777 instance uploads logs static/product_images

# 4. จัดการไฟล์ Config (.env)
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    echo "📄 กำลังสร้างไฟล์ .env จาก .env.example..."
    cp .env.example .env
    # สุ่ม Secret Key ใหม่เพื่อความปลอดภัย
    RANDOM_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "fallback_secret_$(date +%s)")
    sed -i "s/your_production_secret_key_change_this_in_production/$RANDOM_SECRET/g" .env
    echo "⚠️ ไฟล์ .env ถูกสร้างแล้ว กรุณาแก้ไขค่า TELEGRAM_BOT_TOKEN ภายหลัง"
  else
    echo "❌ ไม่พบไฟล์ .env.example กรุณาอัปโหลดไฟล์ให้ครบถ้วน"
    exit 1
  fi
else
  echo "✅ พบไฟล์ .env แล้ว (ใช้ค่าเดิม)"
fi

# 5. Build และ Start Containers
echo "🚀 กำลังรัน Docker Containers..."
docker-compose down # หยุดของเก่าถ้ามี
docker-compose up -d --build

# 6. ตรวจสอบสถานะ
echo "⏳ รอให้ระบบพร้อมทำงาน (Health Check)..."
MAX_RETRIES=10
COUNT=0
# ตรวจสอบว่า Nginx ตอบรับหรือยัง (พอร์ต 80)
until $(curl --output /dev/null --silent --head --fail http://localhost/health 2>/dev/null); do
    printf '.'
    sleep 3
    COUNT=$((COUNT+1))
    if [ $COUNT -eq $MAX_RETRIES ]; then
        echo -e "\n⚠️ ระบบอาจจะใช้เวลาเริ่มนานกว่าปกติ กรุณาเช็ค 'docker-compose logs' ภายหลัง"
        break
    fi
done

echo -e "\n----------------------------------------------------"
echo "✅ สำเร็จ! ระบบ PO-Online พร้อมใช้งานแล้ว"
echo "🌐 URL: http://$(curl -s ifconfig.me)"
echo "📸 Logs: tail -f logs/app.log"
echo "----------------------------------------------------"

# คำแนะนำเพิ่มเติม
echo "💡 วิธีการย้ายข้อมูล (Database Migration):"
echo "1. Export DB จาก Windows (Local):"
echo "   pg_dump -U WAUser po_online_db > backup.sql"
echo ""
echo "2. อัปโหลด backup.sql มาไว้ในเครื่อง VPS (โฟลเดอร์เดียวกัน)"
echo ""
echo "3. รันคำสั่งกู้คืนใน VPS:"
echo "   docker cp backup.sql po-online-db:/backup.sql"
echo "   docker exec po-online-db psql -U WAUser -d po_online_db -f /backup.sql"
echo "----------------------------------------------------"

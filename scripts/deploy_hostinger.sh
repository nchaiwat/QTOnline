#!/bin/bash
# อัปเดตระบบและติดตั้ง Python
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv -y

# สร้าง Virtual Environment
python3 -m venv venv
source venv/bin/activate

# ติดตั้ง dependencies (สมมติว่าใช้ Flask/FastAPI)
pip install flask gunicorn pandas openpyxl  # เพิ่มไลบรารีตามที่ backend ใช้

# เปิด Port บน Firewall (สมมติว่าใช้ Port 8080 ตามที่ระบุในโค้ด)
sudo ufw allow 8080/tcp
sudo ufw --force enable

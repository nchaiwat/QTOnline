#!/bin/bash
# สร้างโฟลเดอร์และตั้งค่าสิทธิ์
mkdir -p /var/www/po-online
cd /var/www/po-online

# ติดตั้ง Python และ Virtual Environment
apt update && apt upgrade -y
apt install python3-pip python3-venv -y
python3 -m venv venv
source venv/bin/activate

# ติดตั้ง Library
pip install flask gunicorn pandas openpyxl python-multipart

# เปิด Port 8080
ufw allow 8080/tcp
ufw --force enable

echo "Setup Complete. Please upload your project files to /var/www/po-online"

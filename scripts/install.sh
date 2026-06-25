#!/bin/bash

echo "--- Fixing Installation Issues ---"

# 1. ตรวจสอบและติดตั้ง python3-venv (สำหรับ VPS ที่มีสิทธิ์ root)
if [ "$(id -u)" -eq 0 ] && command -v apt-get &> /dev/null; then
    if ! dpkg -s python3-venv >/dev/null 2>&1; then
        echo "Installing python3-venv..."
        apt-get update && apt-get install -y python3-venv
    fi
fi

# 2. ลบ venv เก่าทิ้ง (เพื่อแก้ปัญหา package ตีกัน)
if [ -d "venv" ]; then
    echo "Removing old virtual environment..."
    rm -rf venv
fi

# 3. สร้าง Virtual Environment ใหม่
echo "Creating fresh venv..."
python3 -m venv venv

# 4. ติดตั้งไลบรารีลงใน venv (จะไม่ชนกับระบบหลัก)
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies..."
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
else
    echo "Error: requirements.txt not found."
    exit 1
fi

echo "------------------------------------------------"
echo "✅ Installation Complete!"
echo "------------------------------------------------"
echo "Please start your app using this command:"
echo "  ./venv/bin/python app.py"
echo "------------------------------------------------"

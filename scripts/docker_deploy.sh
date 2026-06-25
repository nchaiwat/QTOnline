#!/bin/bash
# หยุดทำงานทันทีหากมีคำสั่งใดผิดพลาด
set -e

# เข้าไปยังโฟลเดอร์โปรเจกต์
cd /var/www/po-online

echo "--- Starting PO-Online Deployment ---"

echo "--- Validating Critical Files ---"
# ตรวจสอบไฟล์ที่จำเป็นต้องมีก่อน Build
FILES=("app.py" "app.html" "Dockerfile" "docker-compose.yml" "requirements.txt")
for FILE in "${FILES[@]}"; do
    if [ ! -f "$FILE" ]; then
        echo "ERROR: Missing critical file: $FILE"
        echo "Please check if your main Python file is named correctly in this script."
        exit 1
    fi
done

echo "--- Step 1: Cleaning up ---"
# ลบ Container เก่าถ้ามี
docker compose down --remove-orphans || true

echo "--- Step 2: Building & Starting Containers ---"
# ใช้ docker compose build และ up เพื่อสร้างและรันทั้ง App และ DB
DOCKER_BUILDKIT=0 docker compose up -d --build

echo "--- Step 3: Initializing Database & Users ---"
echo "Waiting 20s for Database to be ready..."
sleep 20

# สั่งรัน script init_db.py ภายใน Container App
docker exec po-online-app python init_db.py

echo "--- Step 4: Verification ---"
STATUS=$(docker inspect -f '{{.State.Status}}' po-online-app)

if [ "$STATUS" == "running" ]; then
    echo "SUCCESS: App is running at http://157.173.219.153:8080"
    echo "Default Login: sale / sale OR admin / admin"
else
    echo "ERROR: Container is $STATUS."
    docker logs po-online-app
fi

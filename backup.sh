#!/bin/bash

# =============================================================================
# 💾 PO-Online: Automated VPS Backup Script (App + DB + Uploads)
# =============================================================================

# --- 1. CONFIGURATION (ปรับเปลี่ยนตามความเหมาะสม) ---
# กำหนด Path ของโปรเจกต์ PO-Online บน VPS (กรุณาแก้ไขให้ตรงกับความจริง)
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$APP_DIR/backups"

# รายละเอียด Database
DB_CONTAINER="qt-online-db"
DB_USER="WAUser"
DB_NAME="qt_online_db"

# จำนวนวันที่ต้องการเก็บข้อมูล Backup ย้อนหลัง (ลบตัวที่เก่ากว่า N วัน)
KEEP_DAYS=30

# วันที่และเวลาสำหรับชื่อไฟล์
DATE=$(date +"%Y-%m-%d_%H%M%S")
BACKUP_FILE="po_online_backup_$DATE.tar.gz"
TEMP_SQL="db_dump_$DATE.sql"

# --- เริ่มต้นทำงาน ---
echo "========================================="
echo "⏰ Starting Backup: $(date)"
echo "📂 Project Directory: $APP_DIR"
echo "📂 Backup Directory: $BACKUP_DIR"
echo "========================================="

# 2. สร้างโฟลเดอร์สำหรับเก็บ Backup ถ้ายังไม่มี
mkdir -p "$BACKUP_DIR"

# 3. สั่ง Dump Database ออกมาจาก Docker Container
echo "🗄️ Dumping Database..."
if docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" > "$BACKUP_DIR/$TEMP_SQL"; then
    echo "✅ Database dump completed."
else
    echo "❌ Error: Failed to dump database!"
    exit 1
fi

# 4. บีบอัดไฟล์ทั้งหมด (DB SQL Dump + โฟลเดอร์ uploads + ไฟล์ config .env)
echo "📦 Packing files (DB + Uploads + .env)..."
# ใช้ tar บีบอัดของสำคัญ
tar -czf "$BACKUP_DIR/$BACKUP_FILE" \
    -C "$APP_DIR" .env uploads \
    -C "$BACKUP_DIR" "$TEMP_SQL"

# ตรวจสอบการบีบอัดสำเร็จหรือไม่
if [ $? -eq 0 ]; then
    echo "✅ Backup archive created: $BACKUP_FILE"
else
    echo "❌ Error: Failed to create tar archive!"
    rm -f "$BACKUP_DIR/$TEMP_SQL"
    exit 1
fi

# 5. ลบไฟล์ SQL ชั่วคราวออกเหลือไว้แค่ไฟล์บีบอัด .tar.gz
rm -f "$BACKUP_DIR/$TEMP_SQL"

echo "========================================="
echo "✅ Backup Process Finished Successfully!"
echo "💾 Backup stored at: $BACKUP_DIR/$BACKUP_FILE"
echo "========================================="

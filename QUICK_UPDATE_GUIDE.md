# 🔧 Quick Reference - QT-Online Updates & Deployment Guide

## ✅ สรุปการปรับปรุงล่าสุด (9 ก.ย. 2026 - Performance & CIAM Integration)

### 1️⃣ **การปรับปรุงประสิทธิภาพฐานข้อมูล (Database Optimization)**
- **สร้าง 5 PostgreSQL Indexes บน `purchase_orders`**:
  - `idx_po_sale_user_id` (สำหรับกรองเอกสารของ Sale)
  - `idx_po_status` (สำหรับกรองสถานะ Draft, Approved, ฯลฯ)
  - `idx_po_created` (สำหรับกรองตามวันที่สร้าง)
  - `idx_po_updated_at` (สำหรับกรองตามวันที่แก้ไขล่าสุด)
  - `idx_po_sale_created` (Composite Index)
- **`PurchaseOrder.to_summary_dict()`**: ดึงเฉพาะคอลัมน์ที่จำเป็นสำหรับแสดงผลตารางรายการ QT โดยไม่โหลด `items` และ `comments` ที่ซ้ำซ้อน ลดปริมาณข้อมูลและ RAM/CPU ได้กว่า **90%**
- **Default Current Month Filter**: หน้า QT Management เริ่มต้นกรองที่เดือนปัจจุบันเสมอ (`YYYY-MM`) พร้อม Query แบบ Server-side

### 2️⃣ **ระบบ Centralized Identity Management (CIAM) & Audit Logs**
- **M2M REST API Endpoints** (Header: `X-Management-API-Key` + IP Whitelist):
  - `GET /api/v1/directory/accounts`
  - `PATCH /api/v1/directory/accounts/<username>/status`
  - `POST /api/v1/directory/accounts`
- **ตารางฐานข้อมูลใหม่**:
  - `ciam_settings` (จัดเก็บ API Key, Allowed IPs, สถานะเปิด/ปิด)
  - `ciam_audit_logs` (บันทึก Audit การเชื่อมต่อทุก Request จาก CIAM)
  - `login_logs` (บันทึกประวัติการ Login เข้าใช้งานทั้งผ่าน Web และ API พร้อมเหตุผลกรณีไม่สำเร็จ)
- **หน้า System Settings (`#page-settings`)**:
  - เมนู Settings บน Top Navigation สำหรับ Administrator
  - แท็บตั้งค่า CIAM Parameters (เปิด/ปิด, API Key, Allowed IPs)
  - แท็บตรวจสอบ CIAM Connection Logs แบบ Interactive
  - แท็บตรวจสอบ User Login Activity Logs

---

## 💾 การสำรองข้อมูล (Backup) บน VPS

```bash
# 1. สร้างโฟลเดอร์สำหรับเก็บ Backup
mkdir -p backups

# 2. Dump ฐานข้อมูลทั้งหมด (ใช้ชื่อ container หรือ ID ของ postgres)
docker exec -t 9ed884bd8e40_qt-online-db pg_dumpall -U WAUser > backups/db_full_backup_$(date +%Y%m%d_%H%M%S).sql

# 3. สำรองไฟล์รูปภาพและคอนฟิก
tar -czf backups/files_backup_$(date +%Y%m%d_%H%M%S).tar.gz .env uploads/
```

---

## 🚀 ขั้นตอนการ Deploy บน VPS (อัปเดตโค้ดล่าสุด)

```bash
# 1. เข้าโฟลเดอร์โปรเจกต์ เคลียร์ไฟล์ค้าง และดึงโค้ดล่าสุด
cd /var/www/QT-Online
git stash -u
git pull origin main

# 2. Rebuild Image และเริ่มทำงาน Container web ด้วยโค้ดใหม่ (ต้องมี --build เพื่อให้ไฟล์โค้ดใหม่เข้า Image)
docker compose up -d --no-deps --build web

# 3. รัน Migration ฐานข้อมูล
docker exec -it qt-online-web python scripts/migrate_performance_and_ciam.py
```

---

## 💻 การรันโปรเจกต์ใน Local Environment

```cmd
# ชี้ไปยัง venv ของโปรเจกต์โดยตรง
.\venv\Scripts\python.exe scripts\migrate_performance_and_ciam.py

# หรือรันผ่าน Docker
docker-compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
```

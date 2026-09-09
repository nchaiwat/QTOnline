# Project Handoff Document - QT-Online

**Date:** 2026-09-09  
**Repository:** `https://github.com/nchaiwat/QTOnline.git` (`main` branch)  
**Production Server:** VPS `srv832658` (`qol.windowasia.com`)

---

## 1. Executive Summary
วันนี้ได้ดำเนินการแก้ไขปัญหาหลักและนำขึ้นสู่ Production สำเร็จเรียบร้อย:
1. **แก้ปัญหาระบบทำงานช้า (High Latency & High Resource Usage)**: เกิดจากการที่ API `/api/pos` เดิมทำ Joined Load ทุกรายการสินค้า (`items`) และความคิดเห็น (`comments`) ส่งผลให้เกิด Cartesian Product ใน PostgreSQL และ Payload ขนาดใหญ่เกินความจำเป็น
   - แก้ไขโดยเพิ่ม 5 Database Indexes บนตาราง `purchase_orders`
   - เพิ่ม `PurchaseOrder.to_summary_dict()` ดึงเฉพาะข้อมูลที่จำเป็นสำหรับตารางรายการ QT ลดขนาดข้อมูลลงกว่า 90%
2. **ปรับปรุงหน้า QT Management ให้ Default เป็นเดือนปัจจุบัน (`YYYY-MM`)**:
   - ลดภาระการโหลดข้อมูลลงเหลือเฉพาะเดือนปัจจุบันโดยกรองที่ฝั่ง Server-side ทันที
   - รองรับการเปลี่ยนเดือนหรือกดล้างตัวกรอง (Clear) เพื่อดูรายการทั้งหมดได้อย่างถูกต้อง
3. **ระบบ Centralized Identity Management (CIAM) & หน้า System Settings**:
   - พัฒนา M2M REST API 3 Endpoints ตามข้อกำหนด [CENTRAL_IDENTITY_MANAGEMENT_API_SPEC.md](CENTRAL_IDENTITY_MANAGEMENT_API_SPEC.md) (`GET /api/v1/directory/accounts`, `PATCH /api/v1/directory/accounts/<username>/status`, `POST /api/v1/directory/accounts`)
   - ระบบตรวจสอบความปลอดภัยด้วย API Key (`X-Management-API-Key`) และ Client IP Whitelist
   - ออกแบบหน้าเว็บ **System Settings (`#page-settings`)** ในระบบ พร้อมแท็บดู Audit Logs การเชื่อมต่อจาก CIAM (`ciam_audit_logs`) และแท็บประวัติการ Login (`login_logs`)
4. **แก้ไขปัญหาบันทึก Allowed IPs ไม่ลงฐานข้อมูล (ล่าสุด)**:
   - แก้ไข Payload Key Mismatch ระหว่าง Frontend (`allowed_ips`) กับ Backend (`allowedIps`)
   - เพิ่ม Cache-busting (`?_t=${Date.now()}`) และ No-cache headers เพื่อป้องกัน Browser หรือ Proxy แคชค่าคอนฟิกเดิม
   - เพิ่มการเรียงลำดับ `order_by(CiamSetting.id.asc())` ให้การอ่านและอัปเดตสอดคล้องกันแน่นอน
   - ปรับขั้นตอนการ Deploy บน VPS ให้บังคับ `cd /var/www/QT-Online` และใส่ `--build` flag ใน Docker Compose เพื่อ Rebuild โค้ดใหม่เข้า Container เสมอ

---

## 2. ไฟล์ที่มีการแก้ไขและสร้างใหม่ (Files Changed)

| ไฟล์ | ประเภท | คำอธิบาย |
| :--- | :--- | :--- |
| [models.py](file:///d:/Python/PO-Online/models.py) | Modified | เพิ่ม 5 Indexes บน `purchase_orders`, เพิ่ม `to_summary_dict()`, เพิ่ม Model `CiamSetting`, `CiamAuditLog`, `LoginLog` |
| [app.py](file:///d:/Python/PO-Online/app.py) | Modified | ปรับปรุง `GET /api/pos` ให้รองรับ `month` และ `summary=true`, เพิ่ม CIAM M2M APIs, รองรับ Payload ทั้ง camelCase/snake_case ใน Settings API, เพิ่ม No-cache headers |
| [app.html](file:///d:/Python/PO-Online/app.html) | Modified | เพิ่มเมนู Settings, หน้า `#page-settings` (3 แท็บ), ตัวกรองเดือนเริ่มต้น, ปรับปรุง `saveCiamSettings` พร้อม Loading spinner, เพิ่ม Cache-buster ใน `loadCiamSettings` |
| [docker-compose.yml](file:///d:/Python/PO-Online/docker-compose.yml) | Modified | กำหนดค่าสภาพแวดล้อม Production ให้ตรงกับ VPS (ต่อ Traefik network `root_default`, DB `qt_online_db`) |
| [scripts/migrate_performance_and_ciam.py](file:///d:/Python/PO-Online/scripts/migrate_performance_and_ciam.py) | **New** | สคริปต์ Migration แบบ Idempotent สำหรับสร้างตารางใหม่และ Indexes |
| [backup.sh](file:///d:/Python/PO-Online/backup.sh) | **New** | สคริปต์ Backup ฐานข้อมูลและไฟล์เอกสารอัตโนมัติบน VPS |
| [QUICK_UPDATE_GUIDE.md](file:///d:/Python/PO-Online/QUICK_UPDATE_GUIDE.md) | Modified | อัปเดตคู่มือสรุปวิธี Backup และ Deploy บน VPS (เน้นย้ำ `cd` และ `--build`) |
| [docs/technical_manual_th.md](file:///d:/Python/PO-Online/docs/technical_manual_th.md) | Modified | อัปเดตโครงสร้างฐานข้อมูลและ API Specifications |
| [HANDOFF.md](file:///d:/Python/PO-Online/HANDOFF.md) | **New** | สรุปผลการทำงานของรอบพัฒนานี้และอัปเดตล่าสุด |
| [MEMORY.md](file:///d:/Python/PO-Online/MEMORY.md) | **New** | ข้อควรจำสำหรับ AI Assistant (แจ้งสถานะ Git และมี CIAM ทุกครั้งเมื่อเริ่ม Session) |

---

## 3. สถานะการทำงานจริงบน Production VPS
- **Database Container:** `9ed884bd8e40_qt-online-db` (Database: `qt_online_db`, User: `WAUser`)
- **Web Container:** `qt-online-web` (ทำงานบน Network `qt-network` และ `root_default` ผ่าน Traefik)
- **สถานะการเชื่อมต่อกับ CIAM ส่วนกลาง:** **สำเร็จ (ออนไลน์)**
  - Central IAM Dashboard แสดงสถานะ **QT Online (QOL) เป็น "ออนไลน์" (Response Time ~383 ms)**
  - ซิงก์รายชื่อบัญชีสำเร็จเรียบร้อย (**17 บัญชี**)
- **ขั้นตอน Deploy มาตรฐานบน VPS:**
  ```bash
  cd /var/www/QT-Online
  git stash -u
  git pull origin main
  docker compose up -d --no-deps --build web
  ```

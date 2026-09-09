# Project Handoff Document - QT-Online

**Date:** 2026-09-09  
**Repository:** `https://github.com/nchaiwat/QTOnline.git` (`main` branch)  
**Production Server:** VPS `srv832658` (`qol.windowasia.com`)

---

## 1. Executive Summary
วันนี้ได้ดำเนินการแก้ไขปัญหาหลัก 3 ประการและนำขึ้นสู่ Production สำเร็จเรียบร้อย:
1. **แก้ปัญหาระบบทำงานช้า (High Latency & High Resource Usage)**: เกิดจากการที่ API `/api/pos` เดิมทำ Joined Load ทุกรายการสินค้า (`items`) และความคิดเห็น (`comments`) ส่งผลให้เกิด Cartesian Product ใน PostgreSQL และ Payload ขนาดใหญ่เกินความจำเป็น
   - แก้ไขโดยเพิ่ม 5 Database Indexes บนตาราง `purchase_orders`
   - เพิ่ม `PurchaseOrder.to_summary_dict()` ดึงเฉพาะข้อมูลที่จำเป็นสำหรับตารางรายการ QT ลดขนาดข้อมูลลงกว่า 90%
2. **ปรับปรุงหน้า QT Management ให้ Default เป็นเดือนปัจจุบัน (`YYYY-MM`)**:
   - ลดภาระการโหลดข้อมูลลงเหลือเฉพาะเดือนปัจจุบัน (กันยายน 2026) โดยกรองที่ฝั่ง Server-side ทันที
   - รองรับการเปลี่ยนเดือนหรือกดล้างตัวกรอง (Clear) เพื่อดูรายการทั้งหมดได้อย่างถูกต้อง
3. **ระบบ Centralized Identity Management (CIAM) & หน้า System Settings**:
   - พัฒนา M2M REST API 3 Endpoints ตามข้อกำหนด [CENTRAL_IDENTITY_MANAGEMENT_API_SPEC.md](CENTRAL_IDENTITY_MANAGEMENT_API_SPEC.md) (`GET /api/v1/directory/accounts`, `PATCH /api/v1/directory/accounts/<username>/status`, `POST /api/v1/directory/accounts`)
   - ระบบตรวจสอบความปลอดภัยด้วย API Key (`X-Management-API-Key`) และ Client IP Whitelist
   - ออกแบบหน้าเว็บ **System Settings (`#page-settings`)** ในระบบ พร้อมแท็บดู Audit Logs การเชื่อมต่อจาก CIAM (`ciam_audit_logs`) และแท็บประวัติการ Login (`login_logs`)

---

## 2. ไฟล์ที่มีการแก้ไขและสร้างใหม่ (Files Changed)

| ไฟล์ | ประเภท | คำอธิบาย |
| :--- | :--- | :--- |
| [models.py](file:///d:/Python/PO-Online/models.py) | Modified | เพิ่ม 5 Indexes บน `purchase_orders`, เพิ่ม `to_summary_dict()`, เพิ่ม Model `CiamSetting`, `CiamAuditLog`, `LoginLog` |
| [app.py](file:///d:/Python/PO-Online/app.py) | Modified | ปรับปรุง `GET /api/pos` ให้รองรับ `month` และ `summary=true`, เพิ่ม CIAM M2M APIs, เพิ่ม Admin Settings APIs, บันทึก Login Audit |
| [app.html](file:///d:/Python/PO-Online/app.html) | Modified | เพิ่มเมนู Settings, เพิ่มหน้า `#page-settings` (3 แท็บ), ปรับปรุงฟังก์ชันกรองเดือนเริ่มต้น และจัดการ Table rendering |
| [docker-compose.yml](file:///d:/Python/PO-Online/docker-compose.yml) | Modified | กำหนดค่าสภาพแวดล้อม Production ให้ตรงกับ VPS (ต่อ Traefik network `root_default`, DB `qt_online_db`) |
| [scripts/migrate_performance_and_ciam.py](file:///d:/Python/PO-Online/scripts/migrate_performance_and_ciam.py) | **New** | สคริปต์ Migration แบบ Idempotent สำหรับสร้างตารางใหม่และ Indexes |
| [backup.sh](file:///d:/Python/PO-Online/backup.sh) | **New** | สคริปต์ Backup ฐานข้อมูลและไฟล์เอกสารอัตโนมัติบน VPS |
| [QUICK_UPDATE_GUIDE.md](file:///d:/Python/PO-Online/QUICK_UPDATE_GUIDE.md) | Modified | อัปเดตคู่มือสรุปวิธี Backup และ Deploy บน VPS |
| [docs/technical_manual_th.md](file:///d:/Python/PO-Online/docs/technical_manual_th.md) | Modified | อัปเดตโครงสร้างฐานข้อมูลและ API Specifications |
| [HANDOFF.md](file:///d:/Python/PO-Online/HANDOFF.md) | **New** | สรุปผลการทำงานของรอบพัฒนานี้ |
| [MEMORY.md](file:///d:/Python/PO-Online/MEMORY.md) | **New** | ข้อควรจำสำหรับ AI Assistant ในการเริ่ม Session ถัดไป |

---

## 3. สถานะการทำงานจริงบน Production VPS
- **Database Container:** `9ed884bd8e40_qt-online-db` (Database: `qt_online_db`, User: `WAUser`)
- **Web Container:** `qt-online-web` (ทำงานบน Network `qt-network` และ `root_default` ผ่าน Traefik)
- **สถานะการ Migration:** รันสคริปต์ `scripts/migrate_performance_and_ciam.py` สำเร็จ
- **Default CIAM API Key ที่ถูกสร้าง:** `sec_po_mgmt_1adc5d422ec78b5356a8e131fc3cc481`
- **สถานะหน้าบ้าน:** เมนู Settings และฟังก์ชันกรองเดือนปัจจุบันเปิดใช้งานเรียบร้อยแล้วที่ `https://qol.windowasia.com`

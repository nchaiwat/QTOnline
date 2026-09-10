# Project Handoff Document - QT-Online

**Date:** 2026-09-10  
**Repository:** `https://github.com/nchaiwat/QTOnline.git` (`main` branch)  
**Production Server:** VPS `srv832658` (`qol.windowasia.com`)

---

## 1. Executive Summary

### 📌 การปรับปรุงล่าสุด (10 ก.ย. 2026 - Major Performance Overhaul):
1. **แก้ปัญหาระบบ Dashboard โหลดช้า (จาก 26 วินาที เหลือ < 0.2 วินาที)**:
   - **สาเหตุ:** หน้า Dashboard ใน `app.html` เรียก `/api/pos?summary=false` โดยไม่มีการกรองเดือน ทำให้ฝั่ง Backend ดึง PO 500 ใบพร้อม Joinedload 8 ตาราง (สินค้าทุกชิ้นและคอมเมนต์) แล้ว Python ต้องวนลูปคำนวณและแปลง JSON ขนาดหลาย MB ส่งไปให้ Browser วนลูปคำนวณซ้ำอีกครั้ง
   - **การแก้ไข:** ปรับปรุง Endpoint `/api/dashboard/stats` ให้รันคำสั่ง **SQL Aggregations** (`COUNT`, `SUM`, `GROUP BY`) โดยตรงบน PostgreSQL (นับยอดวันนี้, สัปดาห์นี้, เดือนนี้, Top 5 ลูกค้า, Top 5 สินค้า, 10 กิจกรรมล่าสุด) ได้ผลลัพธ์ใน 20-30 ms และปรับ `loadDashboardStats()` ใน `app.html` ให้ดึงจาก Endpoint นี้แทน
2. **แก้ปัญหากด Save แล้วหมุน "Saving..." นาน (จาก 3-5 วินาที เหลือ < 0.1 วินาที)**:
   - **สาเหตุ:** ฟังก์ชัน `send_telegram_msg()` มีการยิง HTTP Request ไปยัง Telegram API แบบ Synchronous บล็อกการทำงานของ Worker ไว้จนกว่าจะส่งเสร็จ และมีการ query รายการสินค้าแบบ N+1 ในแต่ละรายการ
   - **การแก้ไข:** ปรับ `send_telegram_msg()` ใน `utils.py` ให้ทำงานใน **Background Daemon Thread** (`threading.Thread`) ทำให้การตอบกลับคำขอ Save ไม่ต้องรอ Telegram Server และปรับ `POST/PUT /api/pos` ใน `app.py` ให้ใช้ Batch Query ดึงสินค้าทั้งหมดในครั้งเดียว
3. **แก้ปัญหาหลัง Save แล้วตาราง QT Management ค้าง "Loading..."**:
   - **สาเหตุ:** ใน `savePO()` มีคำสั่ง `poFilterMonth = '';` ซึ่งไปล้างค่าตัวกรองเดือนทิ้ง ทำให้เมื่อสลับกลับมาหน้ารายการ ระบบยิง `/api/pos?summary=true` แบบไม่มีเดือน จึงต้องโหลดข้อมูลประวัติทั้งหมด 500 ใบ
   - **การแก้ไข:** ยกเลิกการล้างค่า `poFilterMonth` โดยให้คงค่าตัวกรองเดิม หรือ Default เป็นเดือนปัจจุบัน (`YYYY-MM`) เสมอ ทำให้หน้ารายการโหลดเฉพาะเดือนปัจจุบันผ่าน Database Index ทันทีใน ~50ms
4. **แก้ปัญหาเข้าหน้า User Management ช้า (9 วินาที) ด้วย Gunicorn Multi-threading**:
   - **สาเหตุ:** Gunicorn มีแค่ 2 Workers แบบ Sync ทำให้เวลาคำขอ Dashboard หรือคำขออื่นติดพัน คำขอเข้าหน้า User Management (`/api/users`) ต้องรอคิว (Backlog Queue) นานเกือบ 10 วินาที
   - **การแก้ไข:** เพิ่ม `--threads 4` ใน `entrypoint.sh` ทำให้ 2 Workers รองรับได้ถึง 8 Concurrent Requests พร้อมกัน และปรับ `User.to_dict()` ใน `models.py` ไม่ให้ส่งก้อน Base64 ลายเซ็นเต็มก้อนออกมาในหน้ารายชื่อ

---

### 📌 การแก้ไขก่อนหน้า (10 ก.ย. 2026 - เช้า):
1. **แก้ไขปัญหา Date Filter เด้งกลับไปเดือนมิถุนายน (`QT26060020`) เมื่อคลิกปุ่ม View**:
   - แยกตัวแปร `poFilterType` (`month` หรือ `date`) ควบคุม Flatpickr ด้วย API มาตรฐาน `filterDatePicker.setDate(poFilterMonth, false)` โดยไม่เขียนทับ input
2. **แก้ไขปัญหาค้าง "Loading..." เมื่อเปลี่ยนเป็น Date (Infinite Event Loop)**:
   - ตัด `clear()` ออกจาก `renderPOTableList()`, ใส่ Loop Guard ใน Flatpickr `onChange`
3. **ปรับพฤติกรรมตัวกรองเดือน/วันที่ (Preserve Filter State)**:
   - เข้าใช้งานระบบครั้งแรก Default เดือนปัจจุบัน จดจำค่าตัวกรองไว้ตลอดแม้คลิก View แล้วกด Back กลับมา

---

## 2. ไฟล์ที่มีการแก้ไขในรอบนี้ (Files Changed)

| ไฟล์ | ประเภท | คำอธิบาย |
| :--- | :--- | :--- |
| [app.py](file:///d:/Python/PO-Online/app.py) | Modified | เพิ่ม SQL Aggregations ใน `/api/dashboard/stats`, Batch Query สินค้าใน `POST/PUT /api/pos`, ปรับ `list_customers` ใช้ `load_only` และ `to_summary_dict` |
| [app.html](file:///d:/Python/PO-Online/app.html) | Modified | ปรับปรุง `loadDashboardStats`, คงค่าตัวกรองเดือนใน `savePO`, ปรับ `customerPageSize = 50` และ Batch Render ตาราง Customer |
| [utils.py](file:///d:/Python/PO-Online/utils.py) | Modified | ปรับปรุง `send_telegram_msg` ให้ส่งแบบ Non-blocking Background Thread |
| [models.py](file:///d:/Python/PO-Online/models.py) | Modified | ลดขนาด Payload `User.to_dict()` และเพิ่ม `Customer.to_summary_dict()` |
| [entrypoint.sh](file:///d:/Python/PO-Online/entrypoint.sh) | Modified | เพิ่ม `--threads 4` และ `--timeout 120` ให้ Gunicorn เพื่อแก้ปัญหา Worker Queue Bottleneck |
| [scripts/migrate_performance_and_ciam.py](file:///d:/Python/PO-Online/scripts/migrate_performance_and_ciam.py) | Modified | เพิ่ม Index ให้กับตาราง `customers` (`inactive, id`, `customerCode`, `name`, `telephone1`) และ `products` |
| [HANDOFF.md](file:///d:/Python/PO-Online/HANDOFF.md) | Modified | บันทึกสรุปการแก้ไขปัญหา Performance ครบวงจร |


---

## 3. สถานะการทำงานจริงบน Production VPS
- **Production URL:** `https://qol.windowasia.com` (VPS `srv832658`)
- **Path บน VPS:** `/var/www/QT-Online`
- **Database Container:** `9ed884bd8e40_qt-online-db` (Database: `qt_online_db`, User: `WAUser`)
- **Web Container:** `qt-online-web` (ต่อ Network `qt-network` และ `root_default` ผ่าน Traefik)
- **CIAM Status:** ออนไลน์ เชื่อมต่อ Directory Synchronization สำเร็จ

---

## 4. ขั้นตอนการ Deploy มาตรฐานบน VPS
```bash
# 1. ต้อง cd เข้าโฟลเดอร์โปรเจกต์ก่อนเสมอ
cd /var/www/QT-Online

# 2. เคลียร์ไฟล์ค้างและดึงโค้ดล่าสุด
git stash -u
git pull origin main

# 3. บิลด์คอนเทนเนอร์ web ใหม่พร้อมโค้ดล่าสุด (ต้องใส่ --build เสมอ)
docker compose up -d --no-deps --build web

# 4. รันสคริปต์ Migration สร้าง Index (รันเพียงครั้งเดียว)
docker compose exec web python scripts/migrate_performance_and_ciam.py
```

---

## 5. สิ่งที่วางแผนทำต่อในรอบถัดไป (Next Steps / Backlog)
1. **ทดสอบการใช้งาน Date Filter และ Pagination บน Production**: ตรวจสอบการเลือกวันที่ต่างๆ ทั้งในเดือนปัจจุบันและเดือนย้อนหลัง
2. **การปรับแต่ง UX เพิ่มเติม**: พิจารณาเพิ่มตัวเลือก Pagination (แบ่งหน้า) สำหรับตาราง QT Management หากจำนวนข้อมูลในแต่ละเดือนเพิ่มขึ้นในอนาคต
3. **ตรวจสอบฟังก์ชัน Export Excel**: ทดสอบให้แน่ใจว่าตัวกรองวันที่แบบ Date (dd/mm/yyyy) ถูกส่งไปยัง API `export-excel` อย่างถูกต้องเช่นเดียวกับหน้าเว็บ

# MEMORY.md - QT-Online Project Memory & Guidelines

> ⚠️ **CRITICAL REMINDER FOR AI ASSISTANT (อ่านทุกครั้งเมื่อเริ่ม Session ใหม่):**
> 1. **โปรเจกต์นี้ใช้งาน Git:** Remote คือ `https://github.com/nchaiwat/QTOnline.git` (Branch: `main`)
> 2. **โปรเจกต์นี้มีระบบ CIAM (Centralized Identity Management):** มี Directory API (`/api/v1/directory/...`) เชื่อมต่อกับระบบจัดการตัวตนส่วนกลางขององค์กร และมีหน้า System Settings (`#page-settings`)
> 3. **เมื่อเริ่ม Session หรือก่อนเริ่มเขียนโค้ด:** ต้องทักทายและ**แจ้งให้ผู้ใช้ทราบเสมอว่าเราใช้ Git และมีระบบ CIAM เชื่อมต่ออยู่** พร้อมตรวจสอบสถานะ Git (`git status`, ตรวจสอบว่าโค้ดล่าสุดดึงมาจาก `origin/main` หรือยัง)
> 4. **การสั่งคำสั่งบน VPS:** ก่อนสั่ง `git pull` หรือคำสั่งใดๆ บน VPS **ต้องแจ้งให้ `cd /var/www/QT-Online` ก่อนทุกครั้ง** และต้องใส่ Flag `--build` ในคำสั่ง `docker compose up -d --no-deps --build web` เสมอ
> 5. **เมื่อจบงานหรือเตรียมนำขึ้น Server:** ต้องสรุปคำสั่ง `git add`, `git commit`, `git push origin main` ให้ผู้ใช้เสมอ

---

## 1. ข้อมูล Git & Repository
- **Remote URL:** `https://github.com/nchaiwat/QTOnline.git`
- **Main Branch:** `main`
- **การ Sync กับ VPS:** โค้ดบน VPS (`/var/www/QT-Online`) จะถูกดึงผ่าน `git pull origin main` ดังนั้นทุกฟีเจอร์ที่ทำเสร็จแล้วจะต้องถูก Commit และ Push ขึ้น GitHub เสมอ

---

## 2. ข้อมูลสภาพแวดล้อมใน Local (Windows)
- **Virtual Environment:** ติดตั้งอยู่ที่ `.\venv\Scripts\python.exe`
  - ⚠️ *ห้ามรัน `python` เปล่าๆ ใน CMD/PowerShell เพราะจะไปเรียก Global Python ซึ่งไม่มี Dependencies*
  - คำสั่งรันสคริปต์ที่ถูกต้อง: `.\venv\Scripts\python.exe <script.py>`
  - หรือสั่ง Activate ก่อน: `.\venv\Scripts\Activate.ps1`
- **ฐานข้อมูลใน Local:** PostgreSQL พอร์ต `5432`, DB Name: `po_online_db`, User: `postgres`

---

## 3. ข้อมูลสภาพแวดล้อม Production (VPS Hostinger `srv832658`)
- **URL ระบบจริง:** `https://qol.windowasia.com`
- **Path บน VPS:** `/var/www/QT-Online`
- **Database Container:** `9ed884bd8e40_qt-online-db` (Postgres 15)
  - ⚠️ **ชื่อฐานข้อมูลจริงบน VPS คือ `qt_online_db`** (User: `WAUser`)
- **คำสั่ง Backup ฐานข้อมูลก่อนอัปเดต:**
  ```bash
  mkdir -p backups
  docker exec -t 9ed884bd8e40_qt-online-db pg_dumpall -U WAUser > backups/db_full_backup_$(date +%Y%m%d_%H%M%S).sql
  ```
- **ขั้นตอนการ Deploy อัปเดตบน VPS (ต้อง cd เข้า /var/www/QT-Online ทุกครั้ง):**
  ```bash
  # 1. เข้าสู่โฟลเดอร์โปรเจกต์ เคลียร์ไฟล์ค้าง และดึงโค้ดล่าสุด
  cd /var/www/QT-Online
  git stash -u
  git pull origin main

  # 2. บิลด์อิมเมจใหม่และเริ่มทำงาน Container web (ต้องใส่ --build เพื่อให้โค้ดใหม่ถูก compile เข้า container)
  docker compose up -d --no-deps --build web

  # 3. รัน Migration ฐานข้อมูล (หากมีตารางหรือ index ใหม่)
  docker exec -it qt-online-web python scripts/migrate_performance_and_ciam.py
  ```
- **ข้อควรระวังเรื่อง Network & Port บน VPS:**
  - VPS มี Traefik ดักพอร์ต 80 และ 443 ไว้อยู่แล้ว
  - คอนเทนเนอร์ `qt-online-nginx` จะต่อเข้ากับเครือข่ายภายนอก `root_default` และใช้ Traefik Labels ในการ Route โดเมน
  - ⚠️ *ห้ามกำหนด `ports: - "80:80"` ใน `docker-compose.yml` บน VPS เพราะจะชนกับ Traefik*

---

## 4. โครงสร้างสถาปัตยกรรมสำคัญที่เพิ่งเพิ่ม (Sep 2026)
1. **Performance Indexing & Query:**
   - มี 5 Indexes บนตาราง `purchase_orders` (`idx_po_sale_user_id`, `idx_po_status`, `idx_po_created`, `idx_po_updated_at`, `idx_po_sale_created`)
   - หน้า `page-po-list` (QT Management) เรียก `GET /api/pos?summary=true&month=YYYY-MM` เพื่อให้ตอบสนองเร็วและใช้ `PurchaseOrder.to_summary_dict()`
2. **Centralized Identity Management (CIAM):**
   - อ้างอิงตามเอกสาร [CENTRAL_IDENTITY_MANAGEMENT_API_SPEC.md](CENTRAL_IDENTITY_MANAGEMENT_API_SPEC.md)
   - Endpoints: `GET /api/v1/directory/accounts`, `PATCH /api/v1/directory/accounts/<username>/status`, `POST /api/v1/directory/accounts`
   - ตรวจสอบความปลอดภัยด้วย `X-Management-API-Key` และ Allowed IPs Whitelist ในตาราง `ciam_settings`
   - ตารางบันทึก Audit: `ciam_audit_logs` (การเชื่อมต่อ API) และ `login_logs` (การ Login ของผู้ใช้)
3. **หน้าจอ System Settings (`#page-settings`):**
   - อยู่ใน `app.html` มองเห็นได้เฉพาะ Role `Administrator` มี 3 แท็บ (CIAM Parameters, CIAM Connection Logs, Login Activity Logs)

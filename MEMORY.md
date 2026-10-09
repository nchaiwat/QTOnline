# MEMORY.md - QT-Online Project Memory & Guidelines

> ⚠️ **CRITICAL REMINDER FOR AI ASSISTANT (อ่านทุกครั้งเมื่อเริ่ม Session ใหม่):**
> 1. **โปรเจกต์นี้ใช้งาน Git:** Remote คือ `https://github.com/nchaiwat/QTOnline.git` (Branch: `main`)
> 2. **โปรเจกต์นี้มีระบบ CIAM (Centralized Identity Management):** มี Directory API (`/api/v1/directory/...`) เชื่อมต่อกับระบบจัดการตัวตนส่วนกลางขององค์กร และมีหน้า System Settings (`#page-settings`)
> 3. **เมื่อเริ่ม Session หรือก่อนเริ่มเขียนโค้ด:** ต้องทักทายและ**แจ้งให้ผู้ใช้ทราบเสมอว่าเราใช้ Git และมีระบบ CIAM เชื่อมต่ออยู่** พร้อมตรวจสอบสถานะ Git (`git status`, ตรวจสอบว่าโค้ดล่าสุดดึงมาจาก `origin/main` หรือยัง)
>
> 📋 **ข้อตกลงและเงื่อนไขการทำงาน 5 ข้อ (ตกลงร่วมกัน - ปฏิบัติทุกครั้งอย่างเคร่งครัด):**
> 1. **ทดสอบบน Local ก่อนเสมอ:** ทุกครั้งที่แก้ไขไฟล์ใดๆ เสร็จแล้ว ต้อง Run ทดสอบบน Local ก่อนว่าทำงานถูกต้อง ไม่มี Error
> 2. **Push ขึ้น Git หลังจากทดสอบผ่าน:** ทำการ Commit และ Push ขึ้น Git หลังจากทดสอบแล้วไม่มี Error และตรงตามที่คุยกันแล้ว
> 3. **แจ้ง Command บน VPS Hostinger เสมอ:** แจ้ง Command ที่จะต้องทำบน VPS Hostinger (`/var/www/QT-Online` Linux Hosting) ให้ผู้ใช้ทราบอย่างชัดเจน
> 4. **ต้องมี `cd /var/www/QT-Online` ทุกครั้ง:** ในคำสั่งที่จะต้อง Run บน VPS ที่จะต้องแจ้งทุกครั้ง ให้มี `cd /var/www/QT-Online` ด้วยทุกครั้ง เพื่อป้องกันการสั่ง run ผิด Folder
> 5. **อัปเดต HANDOFF.md ทุกครั้ง:** ทำการเขียน [HANDOFF.md](HANDOFF.md) เก็บประวัติการแก้ไขไว้ทุกครั้ง

---

## 1. ข้อมูล Git & Repository
- **Remote URL:** `https://github.com/nchaiwat/QTOnline.git`
- **Main Branch:** `main`
- **การ Sync กับ VPS:** โค้ดบน VPS (`/var/www/QT-Online`) จะถูกดึงผ่าน `git pull origin main` ดังนั้นทุกฟีเจอร์ที่ทำเสร็จแล้วจะต้องถูก Commit และ Push ขึ้น GitHub เสมอ
- **เอกสารสำคัญของโปรเจกต์:**
  - 📖 [README.md](README.md): ภาพรวมระบบ การติดตั้ง และคู่มือการใช้งาน
  - 📘 [PRD.md](PRD.md): Product Requirements Document ข้อกำหนดผลิตภัณฑ์และฟังก์ชันทั้งหมด
  - 🤖 [AGENT.md](AGENT.md): คู่มือกฎเหล็กและข้อปฏิบัติสำหรับ AI Assistant / Developer
  - 🤝 [HANDOFF.md](HANDOFF.md): ประวัติการส่งมอบงานและการจูนประสิทธิภาพ (Performance Overhaul)
  - 🔐 [CENTRAL_IDENTITY_MANAGEMENT_API_SPEC.md](CENTRAL_IDENTITY_MANAGEMENT_API_SPEC.md): สเปกระบบ CIAM


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
1. **Performance Indexing & Query Optimization:**
   - **ตาราง `purchase_orders`:** มี 5 Indexes (`idx_po_sale_user_id`, `idx_po_status`, `idx_po_created`, `idx_po_updated_at`, `idx_po_sale_created`)
   - **ตาราง `customers`:** มี 4 Indexes (`idx_customers_inactive_id`, `idx_customers_code`, `idx_customers_name`, `idx_customers_phone`)
   - **ตาราง `products`:** มี Index (`idx_products_inactive_code`)
   - **Dashboard:** ใช้ Server-side SQL Aggregation (`/api/dashboard/stats`) คำนวณสรุปผลใน Database แทนการดึง POs ทั้งหมด
   - **Save QT:** ส่ง Telegram แจ้งเตือนผ่าน Daemon Thread แบบ Asynchronous และใช้ Batch Query รายการสินค้า
   - **Customer List:** ใช้ `Customer.to_summary_dict()` ร่วมกับ `load_only(...)` ดึงเฉพาะ 10 คอลัมน์หลัก และจำกัด pageSize เริ่มต้นที่ 50 รายการ
   - **Network & Nginx:** เปิดใช้งาน `gzip on` (ลดขนาด `app.html` จาก 452 KB เหลือ ~45 KB) และ `upstream flask_app { keepalive 32; }`
   - **Database Connection Pool:** กำหนด `SQLALCHEMY_ENGINE_OPTIONS` พร้อม `pool_pre_ping=True`, `pool_recycle=1800` ใน `app.py`
   - **DOM Rendering:** ตาราง User, Customer, และ PO Create Items ใช้ Batch HTML String Injection แทนการวนลูป `innerHTML +=`
2. **Centralized Identity Management (CIAM):**
   - อ้างอิงตามเอกสาร [CENTRAL_IDENTITY_MANAGEMENT_API_SPEC.md](CENTRAL_IDENTITY_MANAGEMENT_API_SPEC.md)
   - Endpoints: `GET /api/v1/directory/accounts`, `PATCH /api/v1/directory/accounts/<username>/status`, `POST /api/v1/directory/accounts`
   - ตรวจสอบความปลอดภัยด้วย `X-Management-API-Key` และ Allowed IPs Whitelist ในตาราง `ciam_settings`
   - ตารางบันทึก Audit: `ciam_audit_logs` (การเชื่อมต่อ API) และ `login_logs` (การ Login ของผู้ใช้)
3. **หน้าจอ System Settings (`#page-settings`):**
   - อยู่ใน `app.html` มองเห็นได้เฉพาะ Role `Administrator` มี 3 แท็บ (CIAM Parameters, CIAM Connection Logs, Login Activity Logs)
4. **CIAM Spoke Integration Specification v2.7.0 & Security Authentication:**
   - **User AD Authentication Toggle (`use_ad_auth`):** เพิ่มฟิลด์ควบคุมการล็อกอินด้วย AD Gateway ในระดับรายบุคคล พร้อม Badges บน UI ตารางผู้ใช้
   - **Active Directory Gateway Fallback:** เมื่อล็อกอินตรงที่ `/login` ระบบจะตรวจสอบรหัสผ่านผ่าน AD Gateway (`POST /api/v1/auth/ad-verify`) สำหรับบัญชีที่เปิดสิทธิ์
   - **Email & Telegram Chat ID:** เพิ่มฟิลด์ `email` และ `telegram_chat_id` ใน User Model, UI User Management และ Sync API เพื่อรองรับ Identity Governance
   - **Client IP & Full Audit Logging:** บันทึก IP Address ลงใน `transaction_logs` ครอบคลุมทุก Authentication Event ตามมาตรฐาน ISO 27001
   - **Seamless Logout to Central IAM Portal:** ผู้ใช้ที่เข้าผ่าน SSO เมื่อกด Logout จะถูกนำทางกลับไปยัง `https://ciam.windowasia.com/portal`
   - **Fix Remember Token Re-Authentication Loop:** บังคับทำลายคุกกี้ `remember_token` และ `session` บน HTTP Response โดยตรงในฟังก์ชัน `/logout` เพื่อแก้ปัญหาการเด้งกลับเข้า Dashboard หลังกด Logout
   - **Fix Duplicate JavaScript Identifiers:** จัดการ Scope ตัวแปรใน `login.html` คืนค่าการทำงานของปุ่มลูกตาเปิดดูรหัสผ่าน และ Mobile QR Login

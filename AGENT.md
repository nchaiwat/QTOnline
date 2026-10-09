# AGENT.md - AI Agent & Developer Operating Constitution

> **สำหรับ AI Coding Assistant (เช่น Antigravity, Claude, Copilot) และนักพัฒนาทุกคน**  
> เอกสารนี้เป็นคู่มือและกฎเหล็กในการทำงานกับโปรเจกต์ **QT-Online (PO-Online)** โปรดอ่านและปฏิบัติตามอย่างเคร่งครัดทุกครั้งก่อนวิเคราะห์หรือแก้ไขโค้ด

---

## ⚠️ กฎเหล็กและข้อตกลงการทำงาน 5 ข้อ (Mandatory Operating Agreement)

> **ข้อตกลงการทำงานร่วมกันอย่างเคร่งครัด (ต้องปฏิบัติทุกรอบการทำงาน):**
> 1. **ทดสอบบน Local ก่อนเสมอ:** ทุกครั้งที่แก้ไขไฟล์ใดๆ เสร็จแล้ว ต้อง Run ทดสอบบน Local ก่อนว่าทำงานถูกต้อง ไม่มี Error (ใช้ `.\venv\Scripts\python.exe`)
> 2. **Push ขึ้น Git หลังจากทดสอบผ่าน:** ทำการ Commit และ Push ขึ้น Git (`main`) หลังจากตรวจสอบแล้วว่าไม่มี Error และการทำงานตรงตามเงื่อนไขที่ตกลงกันไว้
> 3. **แจ้ง Command บน VPS Hostinger เสมอ:** แจ้งคำสั่งสำหรับรันบน VPS Hostinger (`srv832658` Linux Hosting) ให้ผู้ใช้ทราบอย่างชัดเจน
> 4. **ต้องมี `cd /var/www/QT-Online` ทุกครั้ง:** ในคำสั่งที่จะต้อง Run บน VPS ที่แจ้ง จะต้องใส่ `cd /var/www/QT-Online` นำหน้าทุกครั้งเสมอ เพื่อป้องกันการสั่ง Run ผิดโฟลเดอร์
> 5. **อัปเดต HANDOFF.md ทุกครั้ง:** ต้องทำการเขียนสรุปประวัติและรายละเอียดการแก้ไขลงใน [HANDOFF.md](HANDOFF.md) ทุกครั้งที่มีการแก้ไขงาน

---

## 📌 กฎและบริบทสำคัญประจำระบบ (Core Project Guidelines)

1. **การแจ้งเตือนบริบทตอนเริ่ม Session:**
   - ทันทีที่เริ่ม Session ใหม่ หรือตอบข้อความแรก ให้แจ้งผู้ใช้ทราบเสมอว่า:
     - โปรเจกต์นี้ใช้งาน Git ที่ Repository: `https://github.com/nchaiwat/QTOnline.git` (Branch: `main`)
     - โปรเจกต์นี้มีระบบ CIAM (Centralized Identity Management) เชื่อมต่ออยู่
   - ตรวจสอบสถานะ Git (`git status`) เสมอก่อนเริ่มการแก้ไขโค้ด

2. **สภาพแวดล้อม Local บน Windows:**
   - ห้ามรันคำสั่ง `python <file>.py` เปล่าๆ ใน CMD หรือ PowerShell เด็ดขาด เพราะจะไปเรียก Global Python ซึ่งไม่มี Packages
   - **ต้องใช้:** `.\venv\Scripts\python.exe <file>.py` หรือ `.\venv\Scripts\Activate.ps1` ก่อนเสมอ

3. **สภาพแวดล้อมบน Production VPS (Hostinger `srv832658`):**
   - **Path ของโปรเจกต์:** `/var/www/QT-Online`
   - **ต้องสั่ง `cd /var/www/QT-Online` ก่อนทุกคำสั่ง** เมื่อทำงานบน VPS
   - **คำสั่ง Deploy Web Container ต้องใส่ Flag `--build` เสมอ:**
     ```bash
     cd /var/www/QT-Online
     docker compose up -d --no-deps --build web
     ```
   - **ฐานข้อมูลจริงบน VPS:**
     - Container Name: `qt-online-db`
     - Database Name: `qt_online_db`
     - User: `WAUser`
     - Volume: `qt-online_qt_db_data` (External)
   - **ระบบเครือข่าย & Traefik:**
     - ห้ามเปิดพอร์ต `ports: - "80:80"` ใน `docker-compose.yml` บน VPS โดยเด็ดขาด เพราะพอร์ต 80 และ 443 ถูกครอบครองโดย Traefik แล้ว
     - คอนเทนเนอร์ Nginx เชื่อมต่อไปยังเครือข่ายภายนอก `root_default` และใช้ Traefik Labels ในการ Routing

4. **การป้องกันข้อมูลสูญหาย (Accidental Data Loss Prevention):**
   - **ห้าม** รันคำสั่ง `DROP TABLE`, `DROP DATABASE`, `TRUNCATE`, หรือลบข้อมูลจำนวนมากโดยไม่ระบุ `WHERE` โดยเด็ดขาด เว้นแต่จะได้รับคำยืนยันชัดเจนจากผู้ใช้
   - ก่อนการเปลี่ยนแปลง Schema หรือรันคำสั่ง Migration สำคัญบน VPS ต้องสั่งสำรองฐานข้อมูลก่อนเสมอ:
     ```bash
     cd /var/www/QT-Online
     docker exec -t qt-online-db pg_dumpall -U WAUser > backups/db_backup_$(date +%Y%m%d_%H%M%S).sql
     ```


---

## 🏛 ภาพรวมสถาปัตยกรรมและเทคโนโลยี (Tech Stack & Architecture)

- **Backend:** Flask 3.0+ / Python 3.11+
  - [app.py](file:///d:/Python/PO-Online/app.py): Application Core, API Routing (57 Endpoints), Flask-Login, Limiter
  - [models.py](file:///d:/Python/PO-Online/models.py): SQLAlchemy ORM Models (User, Customer, Product, PurchaseOrder, POItem, Comment, Notification, CiamSetting, CiamAuditLog, LoginLog)
  - [utils.py](file:///d:/Python/PO-Online/utils.py): Security, Encryption, Telegram Bot Helper, Formatting
  - [extensions.py](file:///d:/Python/PO-Online/extensions.py): Extensions initialization
  - [api_document_upload.py](file:///d:/Python/PO-Online/api_document_upload.py): Document Upload Logic
- **Frontend:** Single Page Application (SPA)
  - [app.html](file:///d:/Python/PO-Online/app.html): หน้าจอหลักของพนักงานขายและแอดมิน (Vanilla JS, Modal-driven, Multi-tab)
  - [customer_portal.html](file:///d:/Python/PO-Online/customer_portal.html): หน้าจอลูกค้าภายนอกสำหรับตรวจสอบและเซ็นชื่อดิจิทัลผ่านโทเค็น UUID
  - [po_print.html](file:///d:/Python/PO-Online/po_print.html): แม่แบบพิมพ์ใบเสนอราคามาตรฐาน
  - [login.html](file:///d:/Python/PO-Online/login.html): หน้าจอลงชื่อเข้าใช้งาน
- **Database:** PostgreSQL 15 พร้อม Performance Indexes (`idx_po_*`, `idx_customers_*`, `idx_products_*`)
- **PDF Generation:** WeasyPrint & pypdf
- **Reverse Proxy:** Nginx Alpine (เปิดใช้งาน Gzip และ Keepalive upstream ไปยัง Gunicorn)

---

## ⚡ แนวทางปฏิบัติเพื่อประสิทธิภาพขั้นสูง (Performance Guidelines)

ระบบนี้เพิ่งผ่านการทำ Major Performance Overhaul (ดูรายละเอียดใน [HANDOFF.md](file:///d:/Python/PO-Online/HANDOFF.md)) ทุกโค้ดใหม่ที่จะเขียนต้องปฏิบัติตามมาตรฐานเหล่านี้:

1. **ห้ามวนลูป `innerHTML +=` ใน Frontend:**
   - การต่อสายอักขระ HTML ในลูปจะทำให้เบราว์เซอร์เกิด DOM Reflow ซ้ำๆ $O(N^2)$
   - **วิธีที่ถูกต้อง:** ใช้อาร์เรย์รวบรวม HTML String (`htmlParts.push(...)`) หรือ DocumentFragment แล้วนำมากำหนดค่าให้ `element.innerHTML = htmlParts.join('')` ครั้งเดียว

2. **Dashboard & Summary Stats ต้องเป็น Server-Side SQL Aggregation:**
   - ห้ามเขียน API ที่ดึงรายการ PO ทั้งหมดมาวนลูปคำนวณใน Python หรือ JavaScript
   - ใช้ `func.count()`, `func.sum()`, `GROUP BY` บน PostgreSQL โดยตรงใน Endpoint `/api/dashboard/stats`

3. **Third-party Webhooks / External Calls ต้องใช้ Daemon Thread:**
   - การยิง HTTP Request ไปยังบริการภายนอก เช่น Telegram Bot API หรือ External SMS ต้องครอบด้วย `threading.Thread(target=..., daemon=True).start()` เสมอ เพื่อไม่ให้ Block กระบวนการบันทึกของ User

4. **การ Query ข้อมูลปริมาณมากใน Database:**
   - ใช้ `load_only(...)` เมื่อต้องการแสดงเฉพาะคอลัมน์สรุป เช่น ในตารางลูกค้าที่มี 40+ คอลัมน์
   - ใช้ Batch Query `Model.id.in_(...)` แทนการวนลูป Query ทีละแถว (หลีกเลี่ยง N+1 Query Problem)
   - ควบคุมการแบ่งหน้า (Pagination) ไม่ให้โหลดข้อมูลทั้งหมดทีละเกิน 50-100 แถว

5. **การตั้งค่า SQLAlchemy Connection Pool:**
   - คงค่า `pool_pre_ping=True`, `pool_recycle=1800` ใน `SQLALCHEMY_ENGINE_OPTIONS` เพื่อป้องกัน Stale/Dropped Connection

---

## 📝 กฎการแก้ไขโค้ด (Coding Conventions)

1. **รักษาความสมบูรณ์ของเอกสารและคอมเมนต์เดิม:**
   - คงคอมเมนต์ภาษาไทยที่มีอยู่แล้วในโค้ดไว้ ห้ามลบคอมเมนต์อธิบายระบบธุรกิจ
2. **การจัดการเวลาและไทม์โซน:**
   - โปรเจกต์นี้ใช้เวลาประเทศไทย (Bangkok UTC+7) เสมอ
   - ใช้ฟังก์ชัน `now_bangkok()` และ `ensure_bangkok()` จาก [utils.py](file:///d:/Python/PO-Online/utils.py)
3. **การแปลงสกุลเงินและตัวเลข:**
   - ใช้ `bahttext()` ใน Jinja2 / Python สำหรับแปลงยอดเงินเป็นภาษาไทย
   - ใช้ Decimal และ `_decimal_to_str` สำหรับการคำนวณราคาสินค้าเพื่อป้องกัน Floating Point Precision Issue
4. **ความเข้ากันได้ของระบบ SPA ใน `app.html`:**
   - เนื่องจาก `app.html` เป็นไฟล์ขนาดใหญ่ (~450 KB) ที่รวม HTML, CSS, และ JavaScript ไว้ด้วยกัน ให้ตรวจสอบ ID ของ Element และ Event Listener ให้ตรงกันเสมอเมื่อมีการเพิ่มฟิลด์หรือปุ่มใหม่

---

## 🔄 ลำดับขั้นตอนการ Deploy มาตรฐาน (Deployment Protocol)

เมื่อมีการแก้ไขโค้ดและทดสอบใน Local ผ่านแล้ว ให้ดำเนินการตามลำดับนี้:

```bash
# 1. บันทึกโค้ดเข้า Git
git status
git add .
git commit -m "feat/fix: คำอธิบายการเปลี่ยนแปลงอย่างชัดเจน"
git push origin main

# 2. ทำงานบน VPS (ผ่าน SSH เข้า hostinger srv832658)
cd /var/www/QT-Online
git stash -u
git pull origin main

# 3. บิลด์คอนเทนเนอร์ใหม่และรีสตาร์ท
docker compose up -d --no-deps --build web
docker compose restart nginx

# 4. รัน Database Migration (ถ้ามี)
docker compose exec web python scripts/migrate_performance_and_ciam.py

# 5. ตรวจสอบสถานะการทำงาน
docker compose ps
docker compose logs --tail=50 web
```

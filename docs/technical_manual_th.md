# คู่มือทางเทคนิค (Technical Manual) - PO-Online System

เอกสารฉบับนี้สรุปโครงสร้างทางเทคนิค การติดตั้ง และการดูแลรักษาระบบ PO-Online

---

## 1. สถาปัตยกรรมระบบ (System Architecture)
ระบบได้รับการพัฒนาในรูปแบบ **Client-Server Architecture** โดยมีองค์ประกอบหลักดังนี้:
- **Backend:** ทำงานบน Python 3 และ Flask Framework เป็นหลัก จัดการเรื่อง Business Logic, Authentication, และ API
- **Frontend:** เป็น Single Page Application (SPA) ที่ทำงานบนพื้นฐานของ HTML5, CSS3 (Tailwind CSS) และ Vanilla JavaScript สำหรับความเร็วและการตอบสนองที่ไหลลื่น
- **Database:** ใช้ฐานข้อมูลเชิงสัมพันธ์ระบบ **PostgreSQL** เพื่อจัดเก็บข้อมูลหลัก
- **Infrastructure:** ติดตั้งระบบบน Docker Containers สำหรับความสะดวกในการ Scale และย้ายสภาพแวดล้อม (Deployment)

---

## 2. เทคโนโลยีที่ใช้ (Technology Stack)
- **Programming Language:** Python 3.x
- **Backend Framework:** Flask, Flask-SQLAlchemy (ORM), Flask-Login (Authentication), Flask-Bcrypt (Security)
- **Frontend Libraries:** Tailwind CSS (Styling), Lucide (Icons), Chart.js (Visualization), SignaturePad (Digital Signatures)
- **PDF Generation:** WeasyPrint
- **Server:** Gunicorn (WSGI Server) รับคำขอจาก Nginx (Reverse Proxy)
- **Operating System:** Ubuntu/Linux (Containerized)

---

## 3. การเชื่อมต่อและสภาพแวดล้อม (Connection & Environment)
สำหรับการดูแลรักษาหรือพัฒนาต่อ ทีม Technical สามารถเข้าถึงระบบได้ผ่านข้อมูลดังนี้:

### 3.1 การเชื่อมต่อฐานข้อมูล (Database Connection)
ข้อมูลชุดนี้เป็นค่าเริ่มต้นที่ใช้ใน Docker และ Development Environment:
- **Database Engine:** PostgreSQL 15
- **Host:** `db` (ภายใน Docker) หรือ `localhost` (กรณี Run ภายนอกและต่อ Forward Port)
- **Port:** `5432`
- **Database Name:** `po_online_db`
- **Username:** `WAUser`
- **Password:** `Wa@!0302$$`

### 3.2 ตัวแปรสภาพแวดล้อม (Environment Variables)
ตัวแปรสำคัญที่ต้องตั้งค่าในไฟล์ `.env` หรือใน `docker-compose.yml`:
- `SECRET_KEY`: ใช้สำหรับจัดการ Session ของ Flask
- `ENCRYPTION_KEY`: ใช้สำหรับเข้ารหัสลายเซ็น (Signature) ในฐานข้อมูล
- `TELEGRAM_BOT_TOKEN`: Token ของ Bot สำหรับส่งแจ้งเตือน
- `TELEGRAM_GROUP_ID`: ID ของกลุ่ม Telegram ที่รับแจ้งเตือน
- `DATABASE_URL`: URL รูปแบบเต็ม (เช่น `postgresql://user:pass@host:port/db`)

---

## 4. โครงสร้างฐานข้อมูลโดยละเอียด (Detailed Database Schema)
ระบบประกอบด้วยตารางหลักที่เชื่อมโยงกันดังนี้:

### 4.1 ตารางผู้ใช้ (users)
- `id`: Primary Key
- `username`: ชื่อผู้ใช้สำหรับ Login
- `password`: รหัสผ่านที่เข้ารหัสด้วย Bcrypt
- `role`: บทบาท (Administrator, Sale Admin, Sale)
- `signature_image`: ลายเซ็นดิจิทัล (Base64/Encrypted)
- `target_amount`: เป้าหมายยอดขายต่อเดือน

### 4.2 ตารางใบสั่งซื้อ (purchase_orders)
- `poNumber`: รหัสใบสั่งซื้อ (รูปแบบ POYYMMXXXX)
- `status`: สถานะปัจจุบัน (Draft, Pending Review, Approved, Completed, Cancelled)
- `deliveryDate`: วันที่กำหนดส่งสินค้า
- `signedFileUrl`: ลิงก์ไปยังไฟล์ PDF ที่เซ็นแล้ว
- `customerLocationFileUrl`: แผนที่/พิกัดลูกค้า
- `customerPoFileUrl`: ไฟล์ใบสั่งซื้อต้นฉบับจากลูกค้า

### 4.3 ตารางสินค้าและลูกค้า (products & customers)
- จัดเก็บข้อมูลที่นำเข้าจากระบบ SAP ผ่านไฟล์ CSV 
- **Customers:** เก็บที่อยู่จัดส่ง (Ship-to) และที่อยู่ใบเสร็จ (Bill-to) แยกกัน
- **Products:** เก็บราคาทุน (Item Cost) และราคาขาย (Unit Price)

### 4.4 ตารางรายการสินค้าใน PO (po_items)
- เชื่อมโยงกับ `purchase_orders` ผ่าน `po_id`
- เก็บข้อมูล Snapshots ของราคาและส่วนลด ณ วันที่สร้างรายการ

---

## 5. โครงสร้างไฟล์ในโปรเจกต์ (Project Structure)
- `app.py`: ไฟล์หลักของระบบ จัดการ Routing และ API Endpoint
- `models.py`: คำจำกัดความของ Database Models และ Data Constants
- `extensions.py`: การระบะการโหลด extension ต่างๆ เช่น db, login_manager
- `utils.py`: ฟังก์ชันช่วยเหลือช่วยเหลืองานทั่วไป (เช่น การจัดรูปแบบเวลา)
- `app.html`: Frontend หลัก จัดการการสลับหน้า (SPA Mode) และ JS Logic
- `api_document_upload.py`: โมดูลแยกสำหรับการจัดการอัปโหลดไฟล์
- `Dockerfile` & `docker-compose.yml`: ไฟล์กำหนดค่าการทำงานของ Container

---

## 5. ความปลอดภัยและการจำกัดสิทธิ์ (Security & Auth)
- **Authentication:** ระบบใช้ระบบ Session พื้นฐานของ Flask-Login พร้อมการเข้ารหัสรหัสผ่านด้วย Bcrypt
- **Rate Limiting:** มีการจำกัดจำนวนครั้งในการ Login เพื่อป้องกันการโจมตีแบบ Brute Force
- **Authorization:** มีการตรวจสอบสิทธิ์ (Role-based Access Control) ก่อนทำรายการทุกครั้ง โดยแบ่งเป็น:
    - `Administrator`: สิทธิ์สูงสุด จัดการรหัสผ่านและผู้ใช้ได้ทั้งหมด
    - `Sale Admin`: ตรวจสอบและอนุมัติใบสั่งซื้อของ Sale ทุกคนได้
    - `Sale`: จัดการได้เฉพาะใบสั่งซื้อของตนเองที่สร้างขึ้น

---

## 6. รายละเอียด API (API Documentation)
ระบบสื่อสารระหว่าง Frontend และ Backend ผ่าน RESTful API ดังนี้:

### 6.1 Authentication & User
- `POST /login`: เข้าสู่ระบบ (JSON payload: username, password)
- `GET /logout`: ออกจากระบบ
- `GET /api/current_user`: ดึงข้อมูลพื้นฐานของผู้ใช้ปัจจุบัน (Role, Name, ID)
- `POST /api/change_password`: เปลี่ยนรหัสผ่านของตนเอง (ต้องระบุรหัสเดิม)

### 6.2 Purchase Orders (PO)
- `GET /api/pos`: รายการใบสั่งซื้อ (รองรับ Query Params: `status`, `month`, `search`)
- `POST /api/pos`: สร้างใบสั่งซื้อใหม่
- `GET /api/pos/<id>`: รายละเอียดใบสั่งซื้อรายใบ
- `PUT /api/pos/<id>`: อัปเดตข้อมูลหรือสถานะ PO (เช่น เปลี่ยนจาก Draft เป็น Pending Review)
- `DELETE /api/pos/<id>`: ลบใบสั่งซื้อ (ทำได้เฉพาะสถานะที่กำหนด)
- `POST /api/pos/<id>/comments`: เพิ่มบันทึกข้อความภายในใบสั่งซื้อ

### 6.3 PO Workflow Actions
- `POST /api/pos/<id>/request-cancel`: ส่งคำขอส่งยกเลิกใบสั่งซื้อ (เฉพาะ Sale)
- `POST /api/pos/<id>/approve-cancel`: อนุมัติการยกเลิกใบสั่งซื้อ (เฉพาะ Admin)
- `GET /print-po/<id>`: สร้างไฟล์ PDF ของใบสั่งซื้อสำหรับพิมพ์ออกมา

### 6.4 Document & File Management
- `POST /api/pos/<id>/upload-location`: อัปเดตแผนที่ลูกค้า (JPG/PNG/PDF)
- `POST /api/pos/<id>/upload-customer-po`: อัปเดตไฟล์ PO ต้นฉบับจากลูกค้า
- `GET /uploads/<filename>`: เข้าถึงไฟล์เอกสารที่อัปโหลดเข้าสู่ระบบ

### 6.5 Master Data (Customers & Products)
- `GET /api/customers`: รายการลูกค้า (รองรับ Search & Pagination)
- `GET /api/products`: รายการสินค้า (รองรับ Search & Pagination)
- `GET /api/customers/template`: ดาวน์โหลดไฟล์ตัวอย่าง CSV สำหรับลูกค้า
- `POST /api/customers/upload`: อัปโหลดไฟล์ CSV เพื่อนำเข้าข้อมูลลูกค้า

### 6.6 Notifications
- `GET /api/notifications`: ดึงรายการแจ้งเตือนสำหรับผู้ใช้
- `POST /api/notifications/<id>/read`: ทำเครื่องหมายแจ้งเตือนว่าอ่านแล้ว

### 6.7 Centralized Identity Management (CIAM) M2M APIs
รองรับการเชื่อมต่อกับระบบจัดการตัวตนส่วนกลางตาม [CENTRAL_IDENTITY_MANAGEMENT_API_SPEC.md](CENTRAL_IDENTITY_MANAGEMENT_API_SPEC.md) โดยต้องส่ง Header `X-Management-API-Key` และมาจาก IP Whitelist:
- `GET /api/v1/directory/accounts`: ดึงรายการบัญชีผู้ใช้ทั้งหมดสำหรับ Directory Synchronization
- `PATCH /api/v1/directory/accounts/<username>/status`: เปิดหรือปิดการใช้งานบัญชีผู้ใช้ (JSON: `is_active: bool`, `reason: str`)
- `POST /api/v1/directory/accounts`: สร้างบัญชีผู้ใช้ใหม่เข้าสู่ระบบ

### 6.8 System Administration & Audit Log APIs (Administrator Only)
- `GET /api/admin/ciam/settings`: ดึงการตั้งค่า CIAM (API Key, Allowed IPs, Is Enabled)
- `PUT /api/admin/ciam/settings`: อัปเดตการตั้งค่า CIAM
- `GET /api/admin/ciam/logs`: ดึงประวัติ Audit Logs การเชื่อมต่อจากระบบ CIAM
- `GET /api/admin/login-logs`: ดึงประวัติการ Login เข้าสู่ระบบของผู้ใช้ทั้งหมด

---

## 7. กระบวนการอัปโหลดเอกสาร (Document Handling)
ไฟล์ที่อัปโหลดเข้าสู่ระบบจะถูกเก็บไว้เป็นไฟล์บนหน่วยความจำของเซิร์ฟเวอร์ (Folder: `uploads/`) โดยมีการบันทึก Path และ Metadata ลงในฐานข้อมูล เพื่อให้สามารถเรียกดูผ่าน URL และตรวจสอบย้อนกลับได้เมื่อมีการลบหรือแก้ไข

---

## 8. การปรับปรุงประสิทธิภาพฐานข้อมูล (Performance Indexes)
ตาราง `purchase_orders` มีการสร้าง PostgreSQL Indexes เพื่อรองรับข้อมูลขนาดใหญ่และการค้นหาที่รวดเร็ว:
- `idx_po_sale_user_id` บน `sale_user_id`
- `idx_po_status` บน `status`
- `idx_po_created` บน `created`
- `idx_po_updated_at` บน `updatedAt`
- `idx_po_sale_created` บน `(sale_user_id, created)`
- ตารางรายการ `GET /api/pos` รองรับพารามิเตอร์ `summary=true` เพื่อดึงข้อมูลเฉพาะฟิลด์ที่จำเป็นผ่าน `PurchaseOrder.to_summary_dict()` ลด Payload ได้กว่า 90% และ Default ตัวกรองเดือนปัจจุบัน (`YYYY-MM`) เสมอเพื่อลด Load บนเซิร์ฟเวอร์


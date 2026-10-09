# QT-Online (PO-Online) - ระบบจัดการใบเสนอราคาและคำสั่งซื้อออนไลน์

> **ระบบบริหารจัดการใบเสนอราคา (Quotation / Purchase Order Management System)**  
> พัฒนาขึ้นสำหรับ **บริษัท วินโดว์ เอเชีย จำกัด (มหาชน)** เพื่อเพิ่มประสิทธิภาพการทำงานของฝ่ายขาย (Sales), ฝ่ายประสานงานขาย (Sale Admin), ผู้ดูแลระบบ (Administrator) และรองรับการเซ็นเอกสารดิจิทัลสำหรับลูกค้าภายนอกผ่าน Customer Portal พร้อมเชื่อมต่อระบบการจัดการตัวตนส่วนกลางขององค์กร (CIAM)

[![Version](https://img.shields.io/badge/version-1.7.4-blue.svg)](file:///d:/Python/PO-Online/app.py)
[![Python](https://img.shields.io/badge/python-3.11+-brightgreen.svg)](file:///d:/Python/PO-Online/requirements.txt)
[![Flask](https://img.shields.io/badge/framework-Flask-black.svg)](file:///d:/Python/PO-Online/app.py)
[![Database](https://img.shields.io/badge/database-PostgreSQL%2015-blue.svg)](file:///d:/Python/PO-Online/docker-compose.yml)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](file:///d:/Python/PO-Online/Dockerfile)

---

## 📑 สารบัญ (Table of Contents)

1. [ภาพรวมของระบบ (Overview)](#-ภาพรวมของระบบ-overview)
2. [โครงสร้างสถาปัตยกรรม (Architecture)](#-โครงสร้างสถาปัตยกรรม-architecture)
3. [ฟังก์ชันการทำงานหลัก (Key Features)](#-ฟังก์ชันการทำงานหลัก-key-features)
4. [บทบาทและสิทธิ์ผู้ใช้งาน (Roles & Permissions)](#-บทบาทและสิทธิ์ผู้ใช้งาน-roles--permissions)
5. [เทคโนโลยีที่ใช้ (Tech Stack)](#-เทคโนโลยีที่ใช้-tech-stack)
6. [โครงสร้างไดเรกทอรี (Directory Structure)](#-โครงสร้างไดเรกทอรี-directory-structure)
7. [การติดตั้งและใช้งานในเครื่อง (Local Development)](#-การติดตั้งและใช้งานในเครื่อง-local-development)
8. [การ Deploy บน Production VPS (Docker & Traefik)](#-การ-deploy-บน-production-vps-docker--traefik)
9. [การเชื่อมต่อระบบตัวตนส่วนกลาง (CIAM Integration)](#-การเชื่อมต่อระบบตัวตนส่วนกลาง-ciam-integration)
10. [ภาพรวม REST API (API Endpoints Overview)](#-ภาพรวม-rest-api-api-endpoints-overview)
11. [เอกสารที่เกี่ยวข้อง (Related Documentation)](#-เอกสารที่เกี่ยวข้อง-related-documentation)

---

## 🌟 ภาพรวมของระบบ (Overview)

**QT-Online** (หรือ PO-Online) คือระบบเว็บแอปพลิเคชันแบบ Single Page Application (SPA) ที่เชื่อมโยงการทำงานตั้งแต่การเปิดใบเสนอราคา (Quotation), การจัดสินค้าและคำนวณภาษีมูลค่าเพิ่ม (VAT 7%), การแนบไฟล์พิกัดจัดส่ง/เอกสารคำสั่งซื้อของลูกค้า, การส่งต่อให้ลูกค้าตรวจสอบและลงลายมือชื่อดิจิทัลผ่านสมาร์ตโฟน/แท็บเล็ต ไปจนถึงการอนุมัติและยกเลิกเอกสารตามลำดับขั้นขององค์กร

### ไฮไลต์เด่นของระบบ:
- **Zero-Latency Dashboard:** หน้าแดชบอร์ดสรุปยอดขายด้วย Server-Side SQL Aggregation ประมวลผลในหลักมิลลิวินาที
- **Customer Self-Service Portal:** ลูกค้าเปิดดูใบเสนอราคาผ่านลิงก์ปลอดภัย UUID (`/p/<token>`) พร้อมเซ็นชื่อบนหน้าจอและดาวน์โหลด PDF ได้ทันที
- **Automated Telegram Notifications:** แจ้งเตือนฝ่ายขายและทีมงานผ่าน Telegram Bot ทันทีเมื่อมีการสร้าง แก้ไข หรือลูกค้าลงชื่อสำเร็จ (ส่งผ่าน Background Daemon Thread ไม่หน่วงการบันทึก)
- **Centralized Identity Management (CIAM):** รองรับ REST API สำหรับระบบจัดการตัวตนส่วนกลางขององค์กรในการ Provision, ปิดการใช้งาน, และตรวจสอบบัญชีผู้ใช้
- **SAP ERP Integration Ready:** นำเข้า/ส่งออกข้อมูลลูกค้าและสินค้าผ่านไฟล์ CSV ตามมาตรฐานโครงสร้าง SAP Business One

---

## 🏗 โครงสร้างสถาปัตยกรรม (Architecture)

```
                            [ Web Browser / Client ]
                                        │
                         HTTPS (Port 443) / Traefik Proxy
                                        │
                          [ Nginx Reverse Proxy ]
                          (Gzip Compression, Keepalive)
                                        │ (Port 8000)
                     [ Gunicorn Application Server ]
                        (2 Workers, 4 Threads each)
                                        │
                             [ Flask Application ]
               ┌────────────────────────┼────────────────────────┐
               │                        │                        │
        [ App Routing ]          [ Business Logic ]       [ Helpers/Utils ]
           (app.py)                 (models.py)               (utils.py)
               │                        │                        │
               └────────────────────────┼────────────────────────┘
                                        │
                            SQLAlchemy Connection Pool
                            (pool_pre_ping, recycle=1800)
                                        │
                          [ PostgreSQL 15 Database ]
                       (qt_online_db / Performance Indexed)
```

---

## 🚀 ฟังก์ชันการทำงานหลัก (Key Features)

### 1. การจัดการใบเสนอราคา / คำสั่งซื้อ (Quotation & PO Management)
- สร้างใบเสนอราคาแบบรหัสอัตโนมัติ (Format: `POYYMM0001` เช่น `PO26090001`)
- คำนวณราคาสินค้า ส่วนลดแบบรายชิ้นและท้ายบิล ภาษีมูลค่าเพิ่ม (VAT 7%) และยอดรวมสุทธิอัตโนมัติ
- แปลงยอดเงินเป็นตัวอักษรภาษาไทย (`BahtText`) สำหรับพิมพ์เอกสารอย่างเป็นทางการ
- แนบลายมือชื่อดิจิทัลของพนักงานขายอัตโนมัติ
- พิมพ์ใบเสนอราคามาตรฐานผ่านหน้าพิมพ์ที่จัดรูปแบบเฉพาะ (`po_print.html`)
- ส่งออกข้อมูลใบเสนอราคาทั้งหมดเป็นไฟล์ Excel (`.xlsx`)

### 2. พอร์ทัลลูกค้าและการเซ็นชื่อออนไลน์ (Customer Portal & Signing)
- สร้าง Access Token (UUID) เฉพาะสำหรับแต่ละใบเสนอราคา
- ลิงก์สาธารณะปลอดภัย: `https://qol.windowasia.com/p/<token>`
- ลูกค้าสามารถเปิดดูรายละเอียด สแกน QR Code จากเอกสารเพื่อเข้าถึง
- ระบบ Canvas Signature ให้ลูกค้าลงลายมือชื่อดิจิทัลผ่านนิ้วมือหรือสไตลัส
- ประมวลผลสร้างเอกสาร PDF ที่มีลายเซ็นอัตโนมัติด้วย **WeasyPrint**
- เมื่อลูกค้าเซ็นชื่อแล้ว ระบบจะเปลี่ยนสถานะเป็น `Approved` และส่งข้อความแจ้งเตือนเข้า Telegram กลุ่มทันที

### 3. ระบบแนบเอกสารและพิกัดแผนที่ (Customer Document Upload)
- **แผนที่/พิกัดจัดส่ง (Customer Location):** รองรับ PDF, JPG, PNG พร้อมบีบอัดภาพและไฟล์อัตโนมัติ
- **เอกสารคำสั่งซื้อจากลูกค้า (Customer PO File):** รองรับไฟล์ใบสั่งซื้อทางการที่ลูกค้าประทับตรา
- ฝ่ายขายและแอดมินสามารถเปิดดูตัวอย่าง ลบ และอัปโหลดไฟล์ใหม่ได้ทันที

### 4. ลำดับขั้นตอนการอนุมัติและขอยกเลิก (Approval & Cancellation Workflow)
- **Draft:** บันทึกร่างใบเสนอราคา
- **Pending Review:** ส่งขออนุมัติหรือรอลูกค้าลงนาม
- **Approved:** ผ่านการอนุมัติ / ลูกค้าลงนามเรียบร้อย
- **Rejected:** ปฏิเสธเอกสาร
- **Request Cancellation:** ฝ่ายขายส่งคำขอยกเลิกพร้อมเหตุผล
- **Cancelled:** ผู้ดูแลระบบหรือ Sale Admin ตรวจสอบและอนุมัติการยกเลิก

### 5. การจัดการข้อมูลลูกค้าและสินค้า (Customers & Products Management)
- รองรับการค้นหาแบบ Real-time ตามรหัส ชื่อ หรือเบอร์โทรศัพท์ (มี Database Index รองรับ)
- มีฟังก์ชันดาวน์โหลด CSV Template และนำเข้าข้อมูลจำนวนมาก (Bulk CSV Import)
- ตารางลูกค้ารองรับข้อมูลเชื่อมต่อระบบ SAP ERP (40+ คอลัมน์) พร้อมที่อยู่จัดส่งและที่อยู่วางบิลแบบ JSON
- รองรับการอัปโหลดรูปภาพสินค้าและแคชภาพสินค้า

### 6. แดชบอร์ดสรุปยอดและการแจ้งเตือน (Dashboard & Notifications)
- สรุปยอดขายรวม ยอดขายรายเดือน สถานะเอกสารแบบ Real-time
- สรุปผลงานยอดขายเทียบกับเป้าหมายประจำตัวของพนักงานขาย (Target Amount)
- กระดิ่งแจ้งเตือนภายในระบบ (In-app Notifications) บันทึกทุกความเคลื่อนไหว
- ระบบข้อความแจ้งเตือน Telegram Bot แจ้งเตือนทันทีในกลุ่มงาน

### 7. การบริหารจัดการระบบและความปลอดภัย (Admin & CIAM)
- การจัดการผู้ใช้งาน (User Management) กำหนดสิทธิ์ เพิ่มรูปภาพลายเซ็นพนักงานขาย
- ระบบ CIAM (Centralized Identity Management) ซิงค์บัญชีผู้ใช้กับระบบส่วนกลาง
- Audit Logs และ Login Activity Logs ติดตามประวัติการเข้าใช้งานและ IP Address

---

## 👥 บทบาทและสิทธิ์ผู้ใช้งาน (Roles & Permissions)

| สิทธิ์ / ฟังก์ชัน | Sale (พนักงานขาย) | Sale Admin (ผู้ช่วยฝ่ายขาย) | Administrator (ผู้ดูแลระบบ) | ลูกค้าภายนอก (Token Link) |
| :--- | :---: | :---: | :---: | :---: |
| ดู Dashboard ภาพรวม | เฉพาะยอดของตนเอง | ทั้งหมด | ทั้งหมด | ❌ |
| สร้าง / แก้ไขใบเสนอราคา | เฉพาะของตนเอง | ทั้งหมด | ทั้งหมด | ❌ |
| อนุมัติ / ไม่อนุมัติเอกสาร | ❌ | ✅ | ✅ | ❌ |
| ขอยกเลิกใบเสนอราคา | ✅ | ✅ | ✅ | ❌ |
| อนุมัติการยกเลิกใบเสนอราคา | ❌ | ✅ | ✅ | ❌ |
| จัดการลูกค้าและสินค้า (เพิ่ม/ลบ/นำเข้า CSV) | ดู/เพิ่มได้ | ✅ เต็มรูปแบบ | ✅ เต็มรูปแบบ | ❌ |
| จัดการผู้ใช้งาน (User Management) | ❌ | ❌ | ✅ | ❌ |
| ตั้งค่า CIAM & ดู Audit Logs | ❌ | ❌ | ✅ | ❌ |
| รีเซ็ตระบบ / ล้างข้อมูลธุรกรรม | ❌ | ❌ | ✅ | ❌ |
| เปิดดูและเซ็นชื่อผ่าน Customer Portal | ❌ | ❌ | ❌ | ✅ (เฉพาะใบของตนเอง) |

---

## 💻 เทคโนโลยีที่ใช้ (Tech Stack)

### Backend
- **Python 3.11+**
- **Flask 3.0+** (Web Framework)
- **SQLAlchemy 3.1+** (ORM & Database Abstraction)
- **Flask-Login** (Session & Authentication Management)
- **Flask-Bcrypt** (Password Hashing)
- **Flask-Limiter** (Rate Limiting ป้องกัน Brute Force)
- **WeasyPrint / pypdf** (Server-side PDF Generation & Compression)
- **qrcode & Pillow** (QR Code Generation & Image Optimization)
- **Gunicorn 21.2+** (WSGI HTTP Server with Multi-threading)

### Frontend
- **Vanilla JavaScript (ES6+)** (Single Page Application Architecture)
- **HTML5 & CSS3** (Custom Responsive Design System)
- **Canvas API** (Touch/Mouse Signature Pad)
- **Font Awesome 6 & Google Fonts (Prompt / Sarabun)**

### Database & Infrastructure
- **PostgreSQL 15** (Relational Database with B-Tree Indexes)
- **Docker & Docker Compose** (Containerization)
- **Nginx Alpine** (Reverse Proxy with Gzip & Upstream Keepalive)
- **Traefik Proxy** (Edge Router with Automatic Let's Encrypt SSL/TLS on VPS)

---

## 📁 โครงสร้างไดเรกทอรี (Directory Structure)

```
d:\Python\PO-Online\
├── app.py                      # Core Flask Application & API Routes
├── models.py                   # SQLAlchemy Models & Business Logic
├── utils.py                    # Helper Functions, Timezone, Telegram, PDF
├── extensions.py               # Flask Extensions (db, bcrypt, login_manager, limiter)
├── app.html                    # Main Single Page Application (Sales & Admin Portal)
├── customer_portal.html        # Customer Signing & Quotation Review Portal
├── po_print.html               # Printable Quotation / PO Template
├── login.html                  # Responsive Login Page
├── api_document_upload.py      # Customer Document Upload Logic
├── requirements.txt            # Python Dependencies
├── Dockerfile                  # Production Docker Build
├── docker-compose.yml          # Multi-container Production Stack (PostgreSQL, Web, Nginx)
├── nginx.conf                  # Nginx Reverse Proxy with Gzip & Keepalive
├── entrypoint.sh               # Docker Entrypoint (Healthcheck & Gunicorn Runner)
├── .env.example                # Example Environment Variables Template
├── MEMORY.md                   # AI Assistant Project Guidelines & Operational Rules
├── AGENT.md                    # Agent Operating Constitution & Coding Conventions
├── PRD.md                      # Comprehensive Product Requirements Document
├── HANDOFF.md                  # Project Handoff & Performance Overhaul History
├── docs/                       # Manuals, Technical Guides, and Revision History
│   ├── technical_manual_th.md  # Detailed Technical Manual
│   ├── user_manual_th.md       # User Manual (Thai)
│   └── history/                # History of Bug Fixes & Changelogs
└── .docs/                      # Deep Technical Specs (Architecture, Schema, APIs)
    ├── SYSTEM_ARCHITECTURE.md  # Architectural Blueprint
    ├── DATABASE_SCHEMA.md      # Database Entity Relationship & Columns
    └── API_REFERENCE.md        # Detailed REST API Documentation
```

---

## 🛠 การติดตั้งและใช้งานในเครื่อง (Local Development)

### 1. ความต้องการของระบบ (Prerequisites)
- Python 3.11 หรือสูงกว่า
- PostgreSQL 15 (ติดตั้งและเปิดพอร์ต 5432)
- Git

### 2. ขั้นตอนการติดตั้ง
```bash
# 1. Clone repository
git clone https://github.com/nchaiwat/QTOnline.git
cd QTOnline

# 2. สร้าง Virtual Environment และเปิดใช้งาน (Windows PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. ติดตั้ง Dependencies
pip install -r requirements.txt

# 4. ตั้งค่า Environment Variables (.env)
cp .env.example .env
# แก้ไขค่า DATABASE_URL และ SECRET_KEY ในไฟล์ .env ให้ตรงกับเครื่องของคุณ
```

### 3. การรันระบบใน Local
> ⚠️ **ข้อควรระวัง:** บน Windows ให้รันผ่าน Python ภายใน Virtual Environment เสมอ:
```powershell
.\venv\Scripts\python.exe app.py
```
เปิดเบราว์เซอร์ไปที่: `http://localhost:5000`

---

## 🚀 การ Deploy บน Production VPS (Docker & Traefik)

- **Production URL:** `https://qol.windowasia.com`
- **Host VPS:** Hostinger `srv832658`
- **Deploy Path:** `/var/www/QT-Online`

### ขั้นตอนการ Deploy มาตรฐานบน VPS:
```bash
# 1. เข้าสู่โฟลเดอร์โปรเจกต์
cd /var/www/QT-Online

# 2. สำรองฐานข้อมูลก่อนทุกครั้ง
mkdir -p backups
docker exec -t qt-online-db pg_dumpall -U WAUser > backups/db_backup_$(date +%Y%m%d_%H%M%S).sql

# 3. เคลียร์ไฟล์ค้างและดึงโค้ดล่าสุดจาก Git
git stash -u
git pull origin main

# 4. บิลด์ Container Web ใหม่ (ต้องใส่ --build เสมอเพื่อให้โค้ดใหม่ compile)
docker compose up -d --no-deps --build web

# 5. รีสตาร์ท Nginx เพื่อโหลดการตั้งค่า Gzip และ Upstream
docker compose restart nginx

# 6. รัน Migration ฐานข้อมูล (หากมีการเพิ่ม Index หรือตารางใหม่)
docker compose exec web python scripts/migrate_performance_and_ciam.py
```

---

## 🔒 การเชื่อมต่อระบบตัวตนส่วนกลาง (CIAM Integration)

ระบบ QT-Online รองรับการเชื่อมต่อกับระบบ Identity Management ส่วนกลางของ Window Asia เพื่อบริหารจัดการบัญชีผู้ใช้งานจากศูนย์กลาง

- **Authentication:** ผ่าน Header `X-Management-API-Key`
- **IP Whitelisting:** ตรวจสอบ IP ต้นทางเทียบกับรายการในตาราง `ciam_settings`
- **Audit Logging:** ทุก Request จะถูกบันทึกในตาราง `ciam_audit_logs`

### CIAM Endpoints:
- `GET /api/v1/directory/accounts`: ดึงรายชื่อบัญชีผู้ใช้ทั้งหมด รองรับ Pagination (`page`, `pageSize`, `status`, `search`)
- `PATCH /api/v1/directory/accounts/<username>/status`: เปิดหรือปิดการใช้งานบัญชี (`"status": "active" | "inactive"`)
- `POST /api/v1/directory/accounts`: สร้างบัญชีผู้ใช้งานใหม่จากส่วนกลาง

---

## 📡 ภาพรวม REST API (API Endpoints Overview)

| Method | Endpoint | รายละเอียด | สิทธิ์เข้าถึง |
| :--- | :--- | :--- | :--- |
| `POST` | `/login` | เข้าสู่ระบบ (Rate limit: 15/min) | ทุกคน |
| `GET` | `/logout` | ออกจากระบบ | Logged In |
| `GET` | `/health` | ตรวจสอบสถานะ Server Health | ทุกคน |
| `GET` | `/api/dashboard/stats` | สรุปข้อมูลยอดขายและสถานะ Real-time | Logged In |
| `GET` | `/api/pos` | ดึงรายการใบเสนอราคา (กรองตามเดือน/สถานะ) | Logged In |
| `POST` | `/api/pos` | สร้างใบเสนอราคาใหม่ | Logged In |
| `GET` | `/api/pos/<id>` | ดูรายละเอียดใบเสนอราคา | Logged In |
| `PUT` | `/api/pos/<id>` | แก้ไขใบเสนอราคา | Owner / Admin |
| `DELETE`| `/api/pos/<id>` | ลบใบเสนอราคา | Owner / Admin |
| `POST` | `/api/pos/<id>/request-cancel` | ส่งคำขอยกเลิกใบเสนอราคา | Owner |
| `POST` | `/api/pos/<id>/approve-cancel` | อนุมัติการยกเลิกใบเสนอราคา | Admin / Sale Admin |
| `POST` | `/api/pos/<id>/upload-location`| แนบแผนที่/พิกัดจัดส่ง (บีบอัดอัตโนมัติ) | Owner / Admin |
| `POST` | `/api/pos/<id>/upload-customer-po`| แนบเอกสารใบสั่งซื้อลูกค้า | Owner / Admin |
| `GET` | `/p/<token>` | พอร์ทัลลูกค้าสำหรับตรวจสอบใบเสนอราคา | สาธารณะ (Token) |
| `POST` | `/api/p/<token>/sign` | ลูกค้าส่งลายมือชื่อดิจิทัลและสร้าง PDF | สาธารณะ (Token) |
| `GET` | `/api/customers` | ดึงรายชื่อลูกค้า (High performance load_only) | Logged In |
| `GET` | `/api/products` | ดึงรายชื่อสินค้า | Logged In |
| `GET` | `/api/v1/directory/accounts` | CIAM Sync บัญชีผู้ใช้ | CIAM API Key |

---

## 📚 เอกสารที่เกี่ยวข้อง (Related Documentation)

- 📘 [PRD.md](PRD.md): Product Requirements Document (ข้อกำหนดผลิตภัณฑ์ฉบับสมบูรณ์)
- 🤖 [AGENT.md](AGENT.md): คู่มือและข้อกำหนดสำหรับ AI Coding Assistant และผู้พัฒนา
- 🧠 [MEMORY.md](MEMORY.md): บันทึกบริบทโครงการ กฎเหล็ก และข้อมูลสภาพแวดล้อม
- 🤝 [HANDOFF.md](HANDOFF.md): ประวัติการส่งมอบงานและการปรับแต่ง Performance ครั้งใหญ่
- 🔐 [CENTRAL_IDENTITY_MANAGEMENT_API_SPEC.md](CENTRAL_IDENTITY_MANAGEMENT_API_SPEC.md): ข้อมูลทางเทคนิคระบบ CIAM API
- 🏗 [.docs/SYSTEM_ARCHITECTURE.md](.docs/SYSTEM_ARCHITECTURE.md): รายละเอียดสถาปัตยกรรมระบบเชิงลึก
- 🗄 [.docs/DATABASE_SCHEMA.md](.docs/DATABASE_SCHEMA.md): รายละเอียดตารางและฟิลด์ในฐานข้อมูล

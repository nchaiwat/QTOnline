# Customer Document Upload - Installation Guide

## 📋 สรุปการพัฒนา

ฟีเจอร์นี้เพิ่มความสามารถในการ Upload เอกสารเพิ่มเติม 2 ประเภทให้กับ PO:
1. **Customer Location/Map** - แผนที่หรือข้อมูลตำแหน่งสำหรับการส่งของ
2. **Customer PO** - เอกสาร PO ของลูกค้า (Reference Document)

---

## ✅ สิ่งที่ทำเสร็จแล้ว

### Phase 1: Database ✅
- [x] เพิ่ม 8 columns ใน `purchase_orders` table
- [x] เพิ่ม 2 relationships ใน `PurchaseOrder` model
- [x] อัปเดต `to_dict()` method
- [x] Apply migration ไปยัง database แล้ว

### Phase 2: Backend API ✅
- [x] สร้าง 4 endpoints:
  - `POST /api/pos/<id>/upload-location`
  - `POST /api/pos/<id>/upload-customer-po`
  - `DELETE /api/pos/<id>/delete-location`
  - `DELETE /api/pos/<id>/delete-customer-po`
- [x] เพิ่ม validation (file type, size)
- [x] เพิ่ม authorization checks
- [x] เพิ่ม audit logging (comments)
- [x] Auto-delete old files when replacing

### Phase 3: Frontend UI ⏳ (ต้อง integrate เอง)
- [x] สร้าง HTML component (`frontend_document_upload.html`)
- [x] สร้าง CSS styles
- [x] สร้าง JavaScript functions
- [ ] **ต้องทำ**: Integrate เข้า `app.html`

---

## 🔧 วิธีการ Integrate Frontend

### ขั้นตอนที่ 1: เพิ่ม HTML Section

เปิดไฟล์ `app.html` และหาส่วนที่แสดง PO Detail (มักจะอยู่ใน Modal หรือ Detail View)

**ตำแหน่งที่เหมาะสม**: หลังจาก PO Items Table และก่อน Comments Section

คัดลอก HTML จาก `frontend_document_upload.html` (บรรทัด 1-97) วางในตำแหน่งที่เหมาะสม:

```html
<!-- เพิ่มส่วนนี้ใน PO Detail View -->
<div id="po-documents-section" style="display: none; margin-top: 30px;">
    ...
</div>
```

### ขั้นตอนที่ 2: เพิ่ม CSS Styles

คัดลอก CSS จาก `frontend_document_upload.html` (บรรทัด 99-198) วางใน `<style>` section ของ `app.html`:

```css
/* Document Upload Card Styles */
.document-upload-card {
    ...
}
```

### ขั้นตอนที่ 3: เพิ่ม JavaScript Functions

คัดลอก JavaScript จาก `frontend_document_upload.html` (บรรทัด 200-385) วางใน `<script>` section ของ `app.html`:

```javascript
// Customer Document Upload JavaScript Functions
let currentPO = null;

function updateDocumentDisplay(po) {
    ...
}
```

### ขั้นตอนที่ 4: เรียกใช้ในฟังก์ชัน View PO

หาฟังก์ชันที่แสดง PO Detail (อาจชื่อ `viewPO`, `showPODetail`, `loadPODetail` ฯลฯ)

เพิ่มโค้ดนี้ในฟังก์ชันนั้น:

```javascript
async function viewPO(id) {  // หรือชื่ออื่นที่ใช้ในโปรเจค
    // ... existing code to load PO ...
    
    const response = await fetch(`/api/pos/${id}`);
    const po = await response.json();
    
    // NEW: Check if user can edit documents
    const canEdit = (currentUser.role === 'Administrator' || 
                     currentUser.role === 'Sale Admin' || 
                     po.saleUserId === currentUser.id);
    
    if (canEdit) {
        // Show documents section
        document.getElementById('po-documents-section').style.display = 'block';
        
        // Update document display
        updateDocumentDisplay(po);
    } else {
        // Hide documents section for unauthorized users
        document.getElementById('po-documents-section').style.display = 'none';
    }
    
    // ... rest of existing code ...
}
```

---

## 🧪 การทดสอบ

### 1. ทดสอบ Backend API (ใช้ Postman หรือ curl)

#### Upload Location File
```bash
curl -X POST http://localhost:5000/api/pos/1/upload-location \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/map.pdf" \
  --cookie "session=your_session_cookie"
```

#### Upload Customer PO File
```bash
curl -X POST http://localhost:5000/api/pos/1/upload-customer-po \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/customer_po.pdf" \
  --cookie "session=your_session_cookie"
```

#### Delete Location File
```bash
curl -X DELETE http://localhost:5000/api/pos/1/delete-location \
  --cookie "session=your_session_cookie"
```

#### Delete Customer PO File
```bash
curl -X DELETE http://localhost:5000/api/pos/1/delete-customer-po \
  --cookie "session=your_session_cookie"
```

### 2. ทดสอบ Frontend

1. **Login** เข้าระบบด้วย Sale หรือ Admin account
2. **เปิด PO** ที่ต้องการ Upload เอกสาร
3. **ตรวจสอบ** ว่าเห็นส่วน "เอกสารเพิ่มเติม" 2 การ์ด
4. **Upload ไฟล์**:
   - คลิก "อัปโหลดแผนที่" → เลือกไฟล์ → ตรวจสอบว่า Upload สำเร็จ
   - คลิก "อัปโหลด PO ลูกค้า" → เลือกไฟล์ → ตรวจสอบว่า Upload สำเร็จ
5. **ดูไฟล์**: คลิกปุ่ม "ดูไฟล์" → ตรวจสอบว่าเปิดในแท็บใหม่
6. **ลบไฟล์**: คลิกปุ่ม "ลบ" → ยืนยัน → ตรวจสอบว่าลบสำเร็จ
7. **Replace ไฟล์**: Upload ไฟล์ใหม่ → ตรวจสอบว่าไฟล์เก่าถูกลบอัตโนมัติ

### 3. ทดสอบ Authorization

1. **Sale User**: ควรเห็นเฉพาะ PO ของตัวเอง
2. **Sale Admin**: ควรเห็น PO ทั้งหมด (ยกเว้น Draft ของคนอื่น)
3. **Administrator**: ควรเห็น PO ทั้งหมด (ยกเว้น Draft ของคนอื่น)

### 4. ทดสอบ Validation

1. **File Type**: ลอง Upload ไฟล์ .txt, .exe → ควรแสดง error
2. **File Size**: ลอง Upload ไฟล์ > 10MB → ควรแสดง error
3. **No File**: คลิก Upload แต่ไม่เลือกไฟล์ → ควรไม่มีอะไรเกิดขึ้น

---

## 🔄 Restart Application

หลังจาก integrate frontend เสร็จแล้ว ให้ restart application:

### Docker
```bash
docker-compose restart web
```

### VPS (Gunicorn)
```bash
sudo systemctl restart po-online
```

### Development (Flask)
```bash
# Stop current process (Ctrl+C)
python app.py
```

---

## 📊 ตรวจสอบ Database

ตรวจสอบว่า migration ทำงานถูกต้อง:

```bash
docker exec -it po-online-db psql -U myuser -d po_online_db
```

```sql
-- ตรวจสอบ columns ใหม่
\d purchase_orders

-- ตรวจสอบข้อมูล
SELECT id, poNumber, customer_location_file, customer_po_file 
FROM purchase_orders 
WHERE customer_location_file IS NOT NULL 
   OR customer_po_file IS NOT NULL;
```

---

## 🐛 Troubleshooting

### ปัญหา: ไม่เห็นส่วน "เอกสารเพิ่มเติม"
**แก้ไข**: ตรวจสอบว่า:
1. HTML ถูก integrate แล้ว
2. ฟังก์ชัน `updateDocumentDisplay(po)` ถูกเรียกใช้
3. `document.getElementById('po-documents-section').style.display = 'block'` ถูกตั้งค่า

### ปัญหา: Upload ไม่สำเร็จ
**แก้ไข**: ตรวจสอบ:
1. Browser Console สำหรับ error messages
2. Server logs: `docker logs po-online-web`
3. File permissions ของ `/uploads` folder
4. Session cookie ยังไม่หมดอายุ

### ปัญหา: ไฟล์ Upload แล้วแต่ไม่แสดง
**แก้ไข**:
1. ตรวจสอบ database ว่ามี record
2. ตรวจสอบ `to_dict()` method ส่งข้อมูลครบ
3. Refresh หน้า PO Detail
4. ตรวจสอบ Lucide icons render

### ปัญหา: ลบไฟล์แล้วยังเห็นอยู่
**แก้ไข**:
1. Hard refresh browser (Ctrl+F5)
2. ตรวจสอบ database ว่า field เป็น NULL แล้ว
3. ตรวจสอบ filesystem ว่าไฟล์ถูกลบแล้ว

---

## 📝 Checklist สำหรับ Production

- [ ] ทดสอบ Upload ไฟล์ทุกประเภท (PDF, JPG, PNG, GIF)
- [ ] ทดสอบ Upload ไฟล์ขนาดใหญ่ (ใกล้ 10MB)
- [ ] ทดสอบ Replace ไฟล์ (ลบไฟล์เก่าอัตโนมัติ)
- [ ] ทดสอบ Delete ไฟล์
- [ ] ทดสอบ Authorization (Sale, Sale Admin, Admin)
- [ ] ทดสอบ View ไฟล์ในแท็บใหม่
- [ ] ตรวจสอบ Audit Trail (Comments)
- [ ] ตรวจสอบ Responsive Design (Mobile)
- [ ] Backup database ก่อน deploy
- [ ] ทดสอบ Rollback plan

---

## 📚 เอกสารที่เกี่ยวข้อง

- `FEATURE_ANALYSIS_DOCUMENT_UPLOAD.md` - การวิเคราะห์ฟีเจอร์
- `API_REFERENCE.md` - คู่มือ API (ต้องอัปเดต)
- `DATABASE_SCHEMA.md` - โครงสร้างฐานข้อมูล (ต้องอัปเดต)
- `frontend_document_upload.html` - Frontend component
- `api_document_upload.py` - Backend API reference

---

## 🎉 สรุป

การพัฒนา Backend เสร็จสมบูรณ์แล้ว ✅

**ขั้นตอนถัดไป**:
1. Integrate Frontend เข้า `app.html`
2. ทดสอบทุกฟังก์ชัน
3. Deploy to production

**ประมาณเวลาที่เหลือ**: 30-45 นาที (Frontend Integration + Testing)

---

**Created**: 2026-02-07  
**Version**: 1.0  
**Status**: Backend Complete, Frontend Ready for Integration

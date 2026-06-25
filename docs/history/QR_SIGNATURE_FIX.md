# 🔧 แก้ไข QR Code Signature Flow - v1.7.1 (Update 10)

**วันที่:** 23 มกราคม 2026 เวลา 12:55 น.  
**ปัญหา:** เมื่อลูกค้าเซ็นชื่อผ่าน QR Code แล้ว:
1. QR Code Modal หน้าจอ Sale ไม่ปิดเอง
2. Status เปลี่ยนเป็น Completed แล้ว แต่ไม่มีไฟล์ PDF ขึ้นในส่วน Scanned PO (ขึ้นลิงก์เสียหรือหาไม่เจอ)

**สถานะ:** ✅ แก้ไขเสร็จสมบูรณ์

---

## 🐛 ปัญหาที่พบ

### 1. QR Code ไม่ปิดเอง
- Frontend `startPOPolling` ไม่มีการเช็ค Status 'Completed' เพื่อสั่งปิด Modal `closeQRModal()`

### 2. ไม่แสดงไฟล์ PDF/Signature
- Frontend พยายามดึงตัวแปร `po.signedFileUrl` แต่ Backend (`PurchaseOrder.to_dict`) ไม่ได้ส่งตัวแปรนี้กลับมา
- ส่งกลับแค่ `signedFile` (ชื่อไฟล์) ทำให้ Frontend แสดงผลผิดพลาดหรือไม่แสดง

---

## ✅ การแก้ไข

### 1. Backend (`app.py`)
เพิ่มการส่ง `signedFileUrl` และ `signatureImageUrl` กลับไปให้ Frontend ใน `to_dict()`

```python
        return {
            # ...
            'signedFile': self.signedFile,
            # ✅ Added URLs for Frontend
            'signedFileUrl': f"/product-images/{self.signedFile}" if self.signedFile else None,
            'signatureImageUrl': f"/product-images/{self.signatureImage}" if self.signatureImage else None,
            # ...
        }
```
*Note: ใช้ Route `/product-images/` เนื่องจากรองรับการอ่านไฟล์จาก Upload Folder (`serve_product_image` function)*

### 2. Frontend (`app.html`)
เพิ่ม Logic ใน `startPOPolling` ให้สั่งปิด QR Modal เมื่อ Status เป็น Completed

```javascript
                    // 1.1 Auto-Close QR Modal if Completed
                    if (po.status === 'Completed') {
                        closeQRModal();
                    }
```

---

## 📊 ผลลัพธ์

### After Fix:
1.  **Scan & Sign:** ลูกค้าเซ็นเสร็จกด Submit
2.  **Auto Update:** หน้าจอ Sale จะตรวจพบ Status 'Completed'
    - Badge เปลี่ยนเป็นสีเขียว (Completed)
    - **QR Modal ปิดลงอัตโนมัติ**
    - **Scanned PO Box:** แสดงลิงก์ไปยังไฟล์ PDF (ที่เซ็นแล้ว) หรือลายเซ็นทันที

---

## 🚀 วิธี Deploy / Apply Patch

```bash
# Docker Environment
docker-compose restart web

# Local Environment
# Restart python app.py
```
*Frontend Change doesn't require server restart but might need Browser Refresh (Ctrl+F5)*

---

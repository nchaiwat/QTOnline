# 🔧 แก้ไข Status Not Updating (PO Code Error) - v1.7.1 (Update 11)

**วันที่:** 23 มกราคม 2026 เวลา 13:45 น.  
**ปัญหา:** Sale Admin กด Approve หรือ Request Changes แล้ว Status ไม่เปลี่ยนเป็นค่าใหม่ (ยังคงเป็น Pending Review)  
**สถานะ:** ✅ แก้ไขเสร็จสมบูรณ์

---

## 🐛 ปัญหาที่พบ

### อาการ:
- Sale Admin กดปุ่ม **Approve** หรือ **Request Changes**
- หน้าเว็บเหมือนจะทำงานเรียบร้อย (ไม่มี Alert Error)
- แต่ Status ของ PO **ไม่เปลี่ยน** ยังคงเป็นเหมือนเดิม
- (ใน Console Server จะพบ error 500 แต่ Frontend ไม่ได้แสดงออกมาให้ชัดเจน)

### สาเหตุ:
- **AttributeError: 'PurchaseOrder' object has no attribute 'poCode'**
- ในไฟล์ `app.py` ส่วนของฟังก์ชัน `manage_po` (PUT method)
- มีการเรียกใช้ตัวแปร `po.poCode` ในส่วนของการสร้าง Notification Message
- แต่จริงๆ แล้วใน Model `PurchaseOrder` ตั้งชื่อ field ว่า `poNumber`
- ทำให้เกิด Error กลางทาง และ Transaction ถูกยกเลิก (Rollback) ข้อมูลจึงไม่อัปเดต

---

## ✅ การแก้ไข

### แก้ไข Variable Name ใน `app.py`

เปลี่ยนจาก `po.poCode` เป็น `po.poNumber` ให้ถูกต้องตาม Model Definition

```python
# Before (Error)
msg = f"... PO: {po.poCode} ..."
notify_text = f"PO {po.poCode} status is now ..."

# After (Fixed)
msg = f"... PO: {po.poNumber} ..."
notify_text = f"PO {po.poNumber} status is now ..."
```

---

## 📊 ผลลัพธ์

### After:
- กด Approve -> Status เปลี่ยนเป็น **Approved** ทันที
- กด Request Changes -> Status เปลี่ยนเป็น **Changes Requested** ทันที
- Telegram & Notification เด้งเตือนถูกต้องพร้อมเลข PO

---

## 🚀 วิธี Deploy / Apply Patch

```bash
# Docker Environment
docker-compose restart web

# Local Environment
# Restart python app.py
```

---

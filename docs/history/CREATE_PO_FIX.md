# 🔧 แก้ไข Create PO Selecting Error - v1.7.1 (Update 6)

**วันที่:** 23 มกราคม 2026 เวลา 10:55 น.  
**ปัญหา:** หน้า Create PO ไม่สามารถเลือก Customer และ Product ได้ (ขึ้น "Error loading customers/products")  
**สถานะ:** ✅ แก้ไขเสร็จสมบูรณ์

---

## 🐛 ปัญหาที่พบ

### อาการ:
- กดเลือก Customer หรือ Product ในหน้า Create PO
- Modal เด้งขึ้นมา แต่แสดงข้อความผิดพลาด "Error loading customers." หรือ "Error loading products."
- Console ไม่แสดง Error 500 หรือ 400 จาก Server (แปลว่า API เรียกสำเร็จ)

### สาเหตุ:
- **API Response Mismatch:**
  - Backend ส่งข้อมูลกลับมาเป็น **Array** `[{}, {}, ...]` (เมื่อไม่ได้ขอ Page)
  - Frontend (`app.html`) เขียนโค้ดดักไว้ว่าต้องเป็น object ที่มี key `items` (`data.items`)
  - เมื่อ `data` เป็น Array ทำให้ `data.items` เป็น `undefined` -> Code ตีว่าเป็น Empty List หรือ Error

---

## ✅ การแก้ไข

### ปรับปรุง Frontend Logic (`app.html`)

แก้ไขฟังก์ชัน `openProductSearchModal` และ `ensureCustomerCache` ให้รองรับข้อมูลทั้ง 2 แบบ (Array หรือ Object)

```javascript
// BEFORE (Bug)
productSearchCache = Array.isArray(data.items) ? data.items : [];

// AFTER (Fixed)
// ตรวจสอบว่าเป็น Array โดยตรง หรือเป็น Object ที่มี items
productSearchCache = Array.isArray(data) ? data : (data.items || []);
```

ทำแบบเดียวกันกับ `customerSearchCache`

---

## 📊 ผลลัพธ์

### Before (มีปัญหา):
```
❌ Search Modal: แสดง "Error loading..."
❌ Dropdown: ไม่แสดงรายการสินค้า/ลูกค้า
```

### After (แก้ไขแล้ว):
```
✅ Search Modal: แสดงรายการสินค้า/ลูกค้า ครบถ้วน
✅ Create PO: สามารถเลือก Customer และ Product ลง PO ได้ตามปกติ
```

---

## 🚀 วิธี Deploy / Apply Patch

```bash
# Docker Environment
docker-compose restart web

# Local Environment
# Restart python app.py (ถ้ามีการแก้ Python, แต่รอบนี้แก้ HTML อาจต้อง Refresh Browser Hard Reload)
```

⚠️ **สำคัญ:** เนื่องจากเป็นการแก้ไขไฟล์ HTML/JS ผู้ใช้งานต้องทำการ **Hard Refresh** (Ctrl+F5) ที่ Browser เพื่อให้โหลด Code ใหม่

---

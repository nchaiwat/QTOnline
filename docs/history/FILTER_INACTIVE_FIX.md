# 🔧 แก้ไข Filter Inactive Data for Dropdowns - v1.7.1 (Update 7)

**วันที่:** 23 มกราคม 2026 เวลา 11:00 น.  
**ปัญหา:** Dropdown เลือก Customer และ Product แสดงรายการที่ Inactive (เลิกใช้/ปิดใช้งาน) ปนมาด้วย ทำให้ User เผลอเลือกผิด  
**สถานะ:** ✅ แก้ไขเสร็จสมบูรณ์

---

## 🐛 ปัญหาที่พบ

### อาการ:
- User กดค้นหา Customer หรือ Product เพื่อสร้าง PO
- รายการที่ถูก Set Status เป็น **Inactive** (สีเทาในหน้า Management) ยังคงโผล่ขึ้นมาให้เลือก

### สาเหตุ:
- API `list_customers` และ `list_products` ดึงข้อมูลทั้งหมดโดยไม่ได้ Filter Status
- Frontend เรียกใช้ API ตัวเดียวกันกับหน้า Management (ซึ่งหน้า Management ต้องแสดงทั้งหมด) แต่แยกกันที่ Parameter `page` (Dropdown ไม่ส่ง page)

---

## ✅ การแก้ไข

### Modifiy Backend Logic (`app.py`)

ปรับปรุง Logic ใน `list_customers` และ `list_products` โดยเช็คว่าถ้าไม่มีการส่ง `page` มา (ซึ่งแปลว่าเป็น Dropdown Search) ให้ทำการ Filter เอาเฉพาะ Active Records เท่านั้น

#### 1. Customers API
```python
@app.route('/api/customers', methods=['GET'])
def list_customers():
    # ...
    # กรณี Dropdown (ไม่ส่ง page มา)
    if not page:
         # ✅ Added Filter: inactive=False
        query = query.filter_by(inactive=False)
    # ...
```

#### 2. Products API
```python
@app.route('/api/products', methods=['GET'])
def list_products():
    # ...
    # สำหรับ Dropdown (ไม่มี page)
    # ✅ Added Filter: inactive is False OR Null
    query = query.filter(or_(Product.inactive == False, Product.inactive == None))
    # ...
```

---

## 📊 ผลลัพธ์

### Before:
- ค้นหา "Customer A" (Inactive) -> **เจอ** และเลือกได้

### After:
- ค้นหา "Customer A" (Inactive) -> **ไม่เจอ**
- หน้า Management Table -> ยังคงแสดง "Customer A" (Inactive) ได้ตามปกติ (เพราะส่ง parameter `page` ไป)

---

## 🚀 วิธี Deploy / Apply Patch

```bash
# Docker Environment
docker-compose restart web

# Local Environment
# Restart python app.py
```

---

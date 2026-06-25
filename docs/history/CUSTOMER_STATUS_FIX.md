# 🔧 แก้ไข Customer/Product Deactive Error - v1.7.1 (Update 4)

**วันที่:** 23 มกราคม 2026 เวลา 10:35 น.  
**ปัญหา:** Customer ไม่สามารถ Disactive ได้ ขึ้น Error 405 Method Not Allowed  
**สถานะ:** ✅ แก้ไขเสร็จสมบูรณ์

---

## 🐛 ปัญหาที่พบ

### อาการ:
- กดปุ่ม **Deactivate** (ไอคอนกากบาท) ที่ Customer Management
- หรือกดปุ่ม **บันทึก** / **ลบ**
- ขึ้น Error ใน Console:
  ```
  PUT http://localhost:8080/api/customers/CBT-0001
  405 (Method Not Allowed)
  ```

### สาเหตุ:
- **Missing Methods:** Route `/api/customers/<key>` และ `/api/products/<key>` ใน `app.py` ถูกกำหนดให้รองรับแค่ `GET` เท่านั้น
- ทำให้เมื่อ Frontend ส่งคำสั่ง `PUT` (Update) หรือ `DELETE` ไปยัง Server จึงถูกปฏิเสธกลับมา

---

## ✅ การแก้ไข

### ปรับปรุง API Routes

**ไฟล์:** `app.py`

#### 1. Customer API
เพิ่ม `PUT` และ `DELETE` ให้กับ `get_customer_detail`

```python
@app.route('/api/customers/<key>', methods=['GET', 'PUT', 'DELETE']) # ✅ Added methods
@login_required
def get_customer_detail(key):
    # ... logic for find customer ...
    
    # GET Logic (Original)
    if request.method == 'GET':
        return jsonify(cust.to_detail_dict())

    # PUT Logic (New - For Update/Deactive)
    if request.method == 'PUT':
        # ... update fields logic ...
        db.session.commit()
        return jsonify({"success": True, "customer": cust.to_detail_dict()})

    # DELETE Logic (New)
    if request.method == 'DELETE':
        db.session.delete(cust)
        db.session.commit()
        return jsonify({"success": True})
```

#### 2. Product API (Preventive Fix)
แก้ไข `get_product_detail` ในลักษณะเดียวกัน เพื่อป้องกันปัญหาเมื่อแก้ไขหรือลบสินค้า

```python
@app.route('/api/products/<key>', methods=['GET', 'PUT', 'DELETE']) # ✅ Added methods
```

---

## 📊 ผลลัพธ์

### Before (มีปัญหา):
```
❌ Deactive Customer → 405 Method Not Allowed
❌ Edit Customer → 405 Method Not Allowed
❌ Delete Customer → 405 Method Not Allowed
```

### After (แก้ไขแล้ว):
```
✅ Deactive Customer → Success (Status เปลี่ยนเป็น Inactive)
✅ Edit/Delete Customer → Success
✅ Edit/Delete Product → Success (แถมให้)
```

---

## 🚀 วิธี Deploy / Apply Patch

```bash
# Docker Environment
docker-compose restart web

# Local Environment
# Restart python app.py
```

---

## ✅ Checklist

- [ ] ลองกด Deactive Customer แล้วต้องไม่Error
- [ ] Status ต้องเปลี่ยนเป็น Inactive (สีเทา)
- [ ] ลองกด View Product และแก้ไขข้อมูล (Optional)

---

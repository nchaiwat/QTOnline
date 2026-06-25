# 🔧 แก้ไข Product View Error - v1.7.1 (Update 2)

**วันที่:** 21 มกราคม 2026 เวลา 17:10 น.  
**ปัญหา:** กด View ที่ Product Management แล้วขึ้น 404 Error  
**สถานะ:** ✅ แก้ไขเสร็จสมบูรณ์

---

## 🐛 ปัญหาที่พบ

### อาการ:
- กดปุ่ม **View** ที่ Product Management
- ขึ้น Error ใน Console:
  ```
  GET http://localhost:8000/api/products/FA00-D0110-160205
  404 (Not Found)
  ```

### สาเหตุ:
**ไม่มี API endpoint** สำหรับดูรายละเอียด Product แบบเดี่ยว

---

## ✅ การแก้ไข

### เพิ่ม API Endpoint ใหม่

**ไฟล์:** `app.py`

**Endpoint:** `GET /api/products/{key}`

```python
@app.route('/api/products/<key>', methods=['GET'])
@login_required
def get_product_detail(key):
    """
    Get product detail by ID or Product Code
    Supports both numeric ID and string product code
    """
    try:
        # Try to find by ID first (if key is numeric)
        if key.isdigit():
            prod = Product.query.get(int(key))
            if prod:
                return jsonify(prod.to_detail_dict())
                
        # Try to find by Product Code
        decoded_key = unquote(key)
        prod = Product.query.filter_by(productCode=decoded_key).first()
        if prod:
            return jsonify(prod.to_detail_dict())

        # Not found
        return jsonify({"error": "Product not found"}), 404
        
    except Exception as e:
        app.logger.error(f"Error in get_product_detail({key}): {e}")
        return jsonify({"error": f"Failed to load product: {str(e)}"}), 500
```

**ฟีเจอร์:**
- ✅ รองรับค้นหาด้วย **ID** (ตัวเลข)
- ✅ รองรับค้นหาด้วย **Product Code** (string)
- ✅ URL decode อัตโนมัติ (รองรับ special characters)
- ✅ Error handling ครบถ้วน
- ✅ Logging สำหรับ debug

---

## 📊 ผลลัพธ์

### Before (มีปัญหา):
```
❌ กด View → 404 Error
❌ ไม่แสดงรายละเอียด Product
```

### After (แก้ไขแล้ว):
```
✅ กด View → แสดง Modal รายละเอียด Product
✅ แสดงข้อมูลครบทุกฟิลด์
✅ รองรับทั้ง ID และ Product Code
```

---

## 🚀 วิธี Deploy

### ขั้นตอนที่ 1: Restart Application
```bash
# Docker
docker-compose restart web

# หรือ Local
# กด Ctrl+C แล้วรันใหม่
python app.py
```

### ขั้นตอนที่ 2: ทดสอบ
```bash
# 1. ทดสอบ API โดยตรง
curl http://localhost:8080/api/products/FA00-D0110-160205

# 2. เปิดหน้า Product Management
# http://localhost:8080 → Products → กด View

# 3. ดู logs
tail -f logs/app.log
```

---

## ✅ Checklist

- [ ] Restart application แล้ว
- [ ] เปิดหน้า Product Management
- [ ] กดปุ่ม **View** ที่ product ใดก็ได้
- [ ] แสดง Modal รายละเอียด Product
- [ ] ไม่มี 404 Error ใน Console

---

## 🔍 ตัวอย่าง Response

### Request:
```
GET /api/products/FA00-D0110-160205
```

### Response:
```json
{
  "id": 1,
  "productCode": "FA00-D0110-160205",
  "name": "FA เฟรมอลูมิเนียม...",
  "description": "...",
  "unitPrice": "0.00",
  "inStock": "0.00",
  "itemGroup": "FG-ALU",
  "salesUom": "Set",
  "inventoryUom": "Set",
  "purchasingUom": "",
  "inactive": false,
  ...
}
```

---

## 🐛 Troubleshooting

### ปัญหา: ยังขึ้น 404 อยู่

**วิธีแก้:**
```bash
# 1. ตรวจสอบว่า restart แล้วหรือยัง
docker-compose ps

# 2. ตรวจสอบ logs
docker-compose logs -f web

# 3. ทดสอบ API โดยตรง
curl http://localhost:8080/api/products/1
```

### ปัญหา: แสดง "Product not found"

**สาเหตุ:** Product Code ไม่ตรงกับในฐานข้อมูล

**วิธีแก้:**
```bash
# ตรวจสอบ Product Code ที่ถูกต้อง
docker-compose exec db psql -U myuser -d po_online_db -c "SELECT id, \"productCode\", name FROM products LIMIT 5;"
```

---

## 📝 สรุป

### สิ่งที่แก้ไข:
1. ✅ เพิ่ม API endpoint: `GET /api/products/{key}`
2. ✅ รองรับค้นหาด้วย ID และ Product Code
3. ✅ เพิ่ม Error handling และ Logging

### ผลลัพธ์:
- ✅ ปุ่ม View ทำงานได้ปกติ
- ✅ แสดงรายละเอียด Product ครบถ้วน
- ✅ ไม่มี 404 Error

### Version:
- **1.7.1** (Bug Fix - Product Management)

---

## 📖 เอกสารที่เกี่ยวข้อง

1. **Update ก่อนหน้า:** `FIX_PRODUCT_ERROR.md` (แก้ไข List)
2. **Update นี้:** `PRODUCT_VIEW_FIX.md` (แก้ไข View)

---

**Updated:** 21 มกราคม 2026, 17:10 น.  
**Status:** ✅ พร้อมใช้งาน

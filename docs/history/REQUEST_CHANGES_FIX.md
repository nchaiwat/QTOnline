# 🔧 แก้ไข Can't Request Changes (Manage PO API) - v1.7.1 (Update 8)

**วันที่:** 23 มกราคม 2026 เวลา 11:15 น.  
**ปัญหา:** กด Request Changes แล้ว Status ไม่เปลี่ยนเป็น "Changes Requested" แต่ยังคงเป็น "Pending Review" โดยไม่มี Error แจ้งเตือน  
**สถานะ:** ✅ แก้ไขเสร็จสมบูรณ์

---

## 🐛 ปัญหาที่พบ

### อาการ:
- Sale Admin ใส่ Comment และกดปุ่ม **Request Changes**
- Popup หายไป หน้าจอ Refresh
- แต่ Status ของ PO ยังคงเป็น **Pending Review** เหมือนเดิม (ไม่เปลี่ยน)
- ทำให้ Sale #1 ไม่รู้ว่าต้องแก้ไขงาน

### สาเหตุ:
- **API `manage_po` (`PUT /api/pos/<id>`) ใน `app.py` เขียนผิดพลาดอย่างรุนแรง**
- Code ส่วน `if request.method == 'PUT':` **หายไป** (ไม่มีอยู่เลย)
- Code ส่วนของ `DELETE` มีการ Paste code ของการสร้าง Item แทรกเข้าไปแบบผิดที่ (Dead Code)
- ทำให้เมื่อเรียก PUT เข้ามา Code จะวิ่งผ่านไปจนถึง `return jsonify(po.to_dict())` โดยที่ **ไม่มีการอัปเดตข้อมูลใดๆ** ลง Database เลย

---

## ✅ การแก้ไข

### Rewrite `manage_po` function ใน `app.py`

เขียน Logic ใหม่ให้ถูกต้อง ครอบคลุม GET, PUT, และ DELETE

```python
@app.route('/api/pos/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_po(id):
    po = PurchaseOrder.query.get_or_404(id)
    
    # GET: return detail
    if request.method == 'GET': 
        return jsonify(po.to_dict())
        
    # DELETE: check status and delete
    if request.method == 'DELETE': 
        # ... validation ...
        db.session.delete(po)
        db.session.commit()
        return '', 204

    # PUT: Update Status / Items / DeliveryDate (MISSING LOGIC FIXED HERE)
    if request.method == 'PUT': 
        data = request.json
        
        # Update Status
        if 'status' in data:
            po.status = data['status']
            
        # Update Other Fields (items, dates) if provided
        # ...
        
    db.session.commit()
    return jsonify(po.to_dict())
```

---

## 📊 ผลลัพธ์

### Before:
- กด Request Changes -> Server ตอบ 200 OK -> แต่ Status ไม่เปลี่ยน

### After:
- กด Request Changes -> Server อัปเดต Status เป็น "Changes Requested"
- Sale #1 เห็นสถานะเปลี่ยน และปุ่ม Edit PO จะกลับมาทำงานได้

---

## 🚀 วิธี Deploy / Apply Patch

```bash
# Docker Environment
docker-compose restart web

# Local Environment
# Restart python app.py
```

---

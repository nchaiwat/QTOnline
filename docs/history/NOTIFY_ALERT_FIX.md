# 🔧 แก้ไข Missing Notifications - v1.7.1 (Update 9)

**วันที่:** 23 มกราคม 2026 เวลา 11:30 น.  
**ปัญหา:** Status PO เปลี่ยนแปลง แต่ Telegram ไม่เด้ง และ Notification ในเว็บไม่อัปเดต  
**สถานะ:** ✅ แก้ไขเสร็จสมบูรณ์

---

## 🐛 ปัญหาที่พบ

### อาการ:
- Sale Admin กด Request Changes, Approved
- หน้าเว็บเปลี่ยน Status เรียบร้อย
- แต่ **ไม่มีข้อความเข้า Telegram Group**
- และ **ไม่มี Notification ขึ้นมุมขวาบน** ของคนที่เกี่ยวข้อง

### สาเหตุ:
- เมื่อมีการแก้ไขฟังก์ชัน `manage_po` ใน Update 8 (เพื่อแก้ปัญหา Status ไม่เปลี่ยน)
- ผมได้ลบ Logic ส่วนของการแจ้งเตือน (Notifications Logic) ออกไปโดยไม่ตั้งใจ
- ทำให้การทำงานเหลือแค่การ "บันทึกข้อมูล" แต่ขาดการ "สื่อสาร"

---

## ✅ การแก้ไข

### เพิ่ม Notification Logic กลับเข้าไปใน `app.py`

แก้ไข `manage_po` ให้ทำงานครบวงจร:

1.  **Detect Status Change:** ตรวจจับว่า Status มีการเปลี่ยนแปลงหรือไม่
2.  **Telegram Alert:** ส่งข้อความเข้ากลุ่ม พร้อม Icon แยกตามสถานะ
    - ✅ Approved
    - ⚠️ Changes Requested
    - ⏳ Pending Review
    - 🏁 Completed
3.  **In-App Notification:** สร้างแจ้งเตือนไปที่เจ้าของ PO (Sale) เมื่อ Admin มาดำเนินการ

```python
        # --- Handle Status Change & Notifications ---
        if 'status' in data and data['status'] != po.status:
            # ...
            # 1. Telegram Notification
            try:
                msg = f"{icon} <b>Status Update</b>\nPO: <b>{po.poCode}</b>..."
                send_telegram_msg(msg)
            except Exception as e: ...

            # 2. In-App Notification (To Sale User)
            if current_user.id != po.sale_user_id:
                create_notification(po.sale_user_id, notify_text, link_id=po.id)
```

---

## 📊 ผลลัพธ์

### After:
- **Telegram:** มีข้อความเด้งทันทีที่ Status เปลี่ยน
- **Web Notify:** Sale #1 จะเห็นกระดิ่งแดงแจ้งเตือนว่า "PO ... requires changes"

---

## 🚀 วิธี Deploy / Apply Patch

```bash
# Docker Environment
docker-compose restart web

# Local Environment
# Restart python app.py
```

---

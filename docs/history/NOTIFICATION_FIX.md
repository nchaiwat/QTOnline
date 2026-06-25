# 🔧 แก้ไข Notification Error - v1.7.1 (Update 5)

**วันที่:** 23 มกราคม 2026 เวลา 10:45 น.  
**ปัญหา:** Notification แสดงผลเป็น "undefined" และปุ่ม "Mark all read" กดแล้วไม่หาย  
**สถานะ:** ✅ แก้ไขเสร็จสมบูรณ์

---

## 🐛 ปัญหาที่พบ

### 1. ข้อความแสดงเป็น "undefined"
**สาเหตุ:**
- Backend ส่งข้อมูลกลับมาใน key ชื่อ `text` และ `linkId`
- Frontend พยายามดึงข้อมูลจาก key ชื่อ `message` และ `poId` ซึ่งไม่มีอยู่จริง (undefined)

### 2. ปุ่ม "Mark all read" ไม่ทำงาน
**สาเหตุ:**
- การเรียกใช้ฟังก์ชัน `fetchApi` ผิดรูปแบบ
- Code เดิม: `fetchApi(url, { method: 'POST' })` -> ส่ง object เข้าไปเป็น method ทำให้ browser ส่ง request ผิดพลาด (หรือเป็น GET) ทำให้เจอ 405 Method Not Allowed
- Code ที่ถูก: `fetchApi(url, 'POST')`

---

## ✅ การแก้ไข

### 1. Backend (`app.py`)
เพิ่ม `createdIso` ใน `Notification.to_dict()` เพื่อให้ Frontend คำนวณเวลา "Time Ago" ได้ถูกต้อง

```python
def to_dict(self):
    # ...
    return {
        # ...
        'createdIso': created_local.isoformat() if created_local else None
    }
```

### 2. Frontend (`app.html`)
แก้การดึงตัวแปรและการเรียก API

```javascript
// แก้ไขการดึงตัวแปร
list.innerHTML = notifications.map(n => `
    ... onclick="handleNotificationClick(${n.id}, ${n.linkId})"> ...
    <p ...>${n.text || 'No content'}</p> ...
`).join('');

// แก้ไขการเรียก API (Mark Read)
async function handleNotificationClick(id, poId) {
    await fetchApi(`/api/notifications/${id}/read`, 'POST'); // ✅ Correct
    ...
}

async function markAllNotificationsRead() {
    await fetchApi('/api/notifications/read-all', 'POST'); // ✅ Correct
    pollNotifications();
}
```

---

## 📊 ผลลัพธ์

### Before (มีปัญหา):
```
❌ Notification List: "undefined"
❌ Mark all read: ไม่มีการเปลี่ยนแปลง (Notify ไม่หาย)
```

### After (แก้ไขแล้ว):
```
✅ Notification List: แสดงข้อความแจ้งเตือนถูกต้อง (เช่น "PO PO26010001 created by...")
✅ Mark all read: Notification หายไปทันที (เคลียร์ Badge)
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

- [ ] Notification ต้องแสดงข้อความ ไม่ใช่ "undefined"
- [ ] เวลา (Time Ago) ต้องแสดงถูกต้อง
- [ ] กด "Mark all read" แล้ว Badge ต้องหายไป และ List ต้องว่างเปล่า (หรือแสดงว่าไม่มีใหม่)

---

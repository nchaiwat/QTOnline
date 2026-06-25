# วิธีการเข้าใช้งาน PO-Online

### 1. URL สำหรับเข้าใช้งาน
คุณสามารถเข้าใช้งานผ่าน Browser ได้ที่:
**http://157.173.219.153:8080**

### 2. การตรวจสอบกรณีเข้าใช้งานไม่ได้
หากไม่สามารถเข้าหน้าเว็บได้ ให้ตรวจสอบดังนี้:
1. **Hostinger Panel Firewall:** เข้าไปที่หน้าจัดการ VPS ใน Hostinger.com > เมนู **Settings** > **Firewall** แล้วสร้าง Rule เพื่อเปิด **Port 8080 (TCP)**
2. **Service Status:** รันคำสั่ง `sudo systemctl status po-online` เพื่อดูว่าแอปหยุดทำงานหรือไม่
3. **Restart Service:** หากมีการแก้ไขโค้ด ให้รัน `sudo systemctl restart po-online`

### 3. การแก้ไขไฟล์
หากต้องการแก้ไขโค้ดในอนาคต ให้แก้ไขที่ `/var/www/po-online` และทำการ Restart service ทุกครั้ง

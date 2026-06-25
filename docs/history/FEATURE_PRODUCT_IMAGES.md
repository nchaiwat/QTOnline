# 🖼️ ฟีเจอร์ใหม่: Product Thumbnail Images ในหน้า PO Detail + PDF Print

## 📋 อธิบายฟีเจอร์
เพิ่มความสามารถในการแสดงรูปสินค้าเล็ก (Thumbnail) ในตาราง PO Detail พร้อมฟีเจอร์ขยายรูปใหญ่เมื่อ click
และแสดงรูปสินค้าในไฟล์ PDF ที่พิมพ์ออกมาด้วย

## ✨ ฟีเจอร์ที่เพิ่ม

### 1. **Thumbnail Images ในตาราง PO Detail**
- เพิ่มคอลัมน์ "Image" ที่อยู่ก่อนชื่อสินค้า
- แสดงรูปเล็ก 56x56px (w-14 h-14) ของแต่ละสินค้า
- รูปมีเอฟเฟกต์ hover (opacity fade)
- Cursor เปลี่ยนเป็น pointer เมื่อ hover

### 2. **Image Modal Lightbox**
- โมดอล popup แบบ full-screen สำหรับแสดงรูปใหญ่
- ปุ่ม Close (X) ที่มุมบนขวา
- แสดงชื่อสินค้าใต้รูป
- ปิดโมดอลได้โดย:
  - คลิกปุ่ม X
  - กด Escape key
  - คลิกพื้นที่สีดำด้านนอก (ตั้งแต่ bg-opacity-80)

### 3. **Data Binding จาก Backend**
- `POItem.to_dict()` ในไฟล์ `app.py` ส่ง `imageUrl` ไปด้วย
- เชื่อมกับ Product table เพื่อค้นหา URL รูป
- หากไม่มีรูป จะใช้ placeholder image

### 4. **📄 Product Images ในไฟล์ PDF Print** ✨ NEW
- เพิ่มคอลัมน์ "Image" ในตาราง Items ของ PDF
- แสดงรูปสินค้า 50x50px ในแต่ละบรรทัด
- ถ้าไม่มีรูป จะแสดง "No Image" placeholder
- รูปแสดงในคุณภาพที่ดีสำหรับการพิมพ์

## 🔧 ไฟล์ที่แก้ไข

### 1. **app.py**
```python
class POItem(db.Model):
    # เพิ่ม relationship
    product = db.relationship('Product', backref='po_items')
    
    def to_dict(self):
        # เพิ่มบรรทัด
        "imageUrl": product.imageUrl if product else None
```

### 2. **app.html**

#### HTML Structure
- **Thumbnail Column**: เพิ่มที่หน้า PO Detail items table
- **Image Modal (D)**: โมดอลสำหรับขยายรูป
  ```html
  <div id="image-modal">
      <!-- Close button, image container, product name -->
  </div>
  ```
#### JavaScript Functions
- `openImageModal(imageUrl, productName)`: เปิดโมดอล
- `closeImageModal()`: ปิดโมดอล
- `handleImageModalEscape(e)`: จัดการการกด Escape key

### 3. **po_print.html** ✨ NEW (PDF Template)

#### HTML Changes
- เพิ่มคอลัมน์ "Image" ในตาราง Items (ระหว่าง "No." และ "Description")
- แสดง `item.imageUrl` ในรูป 50x50px
- ถ้าไม่มี imageUrl ให้แสดง placeholder "No Image"
- เพิ่ม empty rows ให้ตรงกับจำนวนคอลัมน์ใหม่

#### CSS Changes
```css
.items-table .item-image {
    width: 50px;
    height: 50px;
    object-fit: cover;
}
```

## 💻 โค้ด JavaScript ที่เพิ่ม (app.html)
// 15. Image Modal Functions
function openImageModal(imageUrl, productName) {
    document.getElementById('image-modal').style.display = 'flex';
    document.getElementById('image-modal-img').src = imageUrl;
    document.getElementById('image-modal-title').textContent = productName;
    document.addEventListener('keydown', handleImageModalEscape);
}

function closeImageModal() {
    document.getElementById('image-modal').style.display = 'none';
    document.getElementById('image-modal-img').src = '';
    document.getElementById('image-modal-title').textContent = '';
    document.removeEventListener('keydown', handleImageModalEscape);
}

function handleImageModalEscape(e) {
    if (e.key === 'Escape') {
        closeImageModal();
    }
}
```

## 🎨 Styling
- **Thumbnail**: 56x56px, rounded corners, object-cover
- **Modal**: Black background (opacity 80%), centered
- **Image**: max-width/height responsive, centered
- **Close button**: Top-right, white text, hover effect

## 📐 Layout
```
PO Detail Items Table:
┌─────────┬────────────┬─────┬──────────┬──────────┬───────┐
│ Image   │ Product    │ Qty │ Price    │ Discount │ Total │
├─────────┼────────────┼─────┼──────────┼──────────┼───────┤
│ [img]   │ Widget A   │ 2   │ 150.00   │ 0%       │ 300   │
│ [img]   │ Widget B   │ 1   │ 300.50   │ 0%       │ 301   │
└─────────┴────────────┴─────┴──────────┴──────────┴───────┘

Click on image → opens lightbox modal
```

## ✅ การทดสอบ
1. **หน้า Web (app.html)**
   - ไป PO Detail page
   - ดู items table - ควรมีคอลัมน์รูปด้านหน้า
   - Click ที่รูป - ควรเปิด modal พร้อมรูปใหญ่
   - Try: 
     - Click X button → ปิด
     - Press Escape → ปิด

2. **ไฟล์ PDF Print**
   - ไป PO Detail page
   - Click "Print Official PO" หรือ "Print Draft"
   - PDF ควรแสดงรูปสินค้าในคอลัมน์ Image
   - ถ้าไม่มีรูป จะแสดง "No Image" placeholder

## 🚀 ข้อดีที่เพิ่ม
✅ ช่วยให้ทุกฝ่ายเห็นรูปสินค้าจริง ทั้งในหน้า web และ PDF
✅ ป้องกันความสับสนเมื่อมีสินค้าชื่อคล้าย
✅ ประสบการณ์ User ที่ดีขึ้น
✅ สามารถขยายใหญ่เพื่อดูรายละเอียด
✅ เอกสาร PO มีความสมบูรณ์ขึ้น (มีรูปสินค้าประกอบ)

## 📝 หมายเหตุ
- ถ้า imageUrl เป็น null ก็ใช้ placeholder image แทน
- รูปแสดงใน object-cover mode (crop เพื่อให้พอดี)
- Keyboard support (Escape) ถูกเพิ่มเข้าไป

---

**สร้างเมื่อ**: 14 Nov 2025
**ฟีเจอร์**: Product Thumbnail Gallery + Lightbox Modal

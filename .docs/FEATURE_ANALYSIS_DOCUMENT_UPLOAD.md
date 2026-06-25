# Feature Analysis: Additional Document Upload for PO

## 📋 Requirements Summary

### New Upload Fields (2 fields)
1. **Customer Location/Map** - ไฟล์แผนที่หรือข้อมูล Location สำหรับการส่งของ
2. **Customer PO** - ไฟล์ PO ของลูกค้า (Reference Document)

### Business Rules
- ✅ Optional (ไม่บังคับต้อง Upload)
- ✅ Maximum 1 file per field
- ✅ Can replace existing file (auto-delete old file)
- ✅ Accessible by Sale (owner) and Sale Admin/Administrator
- ✅ Upload anytime after PO creation

---

## 🔍 Impact Analysis

### 1. Database Changes (models.py)

#### Current Structure
```python
class PurchaseOrder(db.Model):
    # Existing signature-related fields
    signedFile = db.Column(db.Text)
    signedFileUrl = db.Column(db.Text)
    signatureImage = db.Column(db.Text)
    signedAt = db.Column(db.DateTime)
```

#### Proposed Changes
```python
class PurchaseOrder(db.Model):
    # ... existing fields ...
    
    # NEW: Customer Location/Map
    customerLocationFile = db.Column(db.Text)  # Filename
    customerLocationFileUrl = db.Column(db.Text)  # Full URL
    customerLocationUploadedAt = db.Column(db.DateTime)
    customerLocationUploadedBy = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # NEW: Customer PO Document
    customerPoFile = db.Column(db.Text)  # Filename
    customerPoFileUrl = db.Column(db.Text)  # Full URL
    customerPoUploadedAt = db.Column(db.DateTime)
    customerPoUploadedBy = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # NEW: Relationships
    location_uploader = db.relationship('User', foreign_keys=[customerLocationUploadedBy])
    po_uploader = db.relationship('User', foreign_keys=[customerPoUploadedBy])
```

#### Migration SQL
```sql
-- File: migrate_add_document_uploads.sql
ALTER TABLE purchase_orders 
ADD COLUMN customer_location_file TEXT,
ADD COLUMN customer_location_file_url TEXT,
ADD COLUMN customer_location_uploaded_at TIMESTAMP,
ADD COLUMN customer_location_uploaded_by INTEGER REFERENCES users(id),
ADD COLUMN customer_po_file TEXT,
ADD COLUMN customer_po_file_url TEXT,
ADD COLUMN customer_po_uploaded_at TIMESTAMP,
ADD COLUMN customer_po_uploaded_by INTEGER REFERENCES users(id);

-- Add indexes for performance
CREATE INDEX idx_po_location_uploader ON purchase_orders(customer_location_uploaded_by);
CREATE INDEX idx_po_po_uploader ON purchase_orders(customer_po_uploaded_by);
```

#### Update to_dict() Method
```python
def to_dict(self):
    return {
        # ... existing fields ...
        
        # NEW: Customer Location
        'customerLocationFile': self.customerLocationFile,
        'customerLocationFileUrl': self.customerLocationFileUrl,
        'customerLocationUploadedAt': ensure_bangkok(self.customerLocationUploadedAt).strftime('%d-%m-%Y %H:%M') if self.customerLocationUploadedAt else None,
        'customerLocationUploadedBy': self.location_uploader.fullName if self.location_uploader else None,
        
        # NEW: Customer PO
        'customerPoFile': self.customerPoFile,
        'customerPoFileUrl': self.customerPoFileUrl,
        'customerPoUploadedAt': ensure_bangkok(self.customerPoUploadedAt).strftime('%d-%m-%Y %H:%M') if self.customerPoUploadedAt else None,
        'customerPoUploadedBy': self.po_uploader.fullName if self.po_uploader else None,
    }
```

---

### 2. Backend API Changes (app.py)

#### New API Endpoints

##### A. Upload Customer Location
```python
@app.route('/api/pos/<int:id>/upload-location', methods=['POST'])
@login_required
def upload_customer_location(id):
    """
    Upload customer location/map file
    
    Authorization: PO Owner OR Sale Admin OR Administrator
    File Types: PDF, JPG, JPEG, PNG, GIF (images and PDFs)
    Max Size: 10MB
    """
    po = PurchaseOrder.query.get_or_404(id)
    
    # Authorization check
    if current_user.id != po.sale_user_id and current_user.role not in ['Administrator', 'Sale Admin']:
        return jsonify({"error": "Unauthorized"}), 403
    
    # Validate file
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    # Validate file type
    allowed_extensions = {'pdf', 'jpg', 'jpeg', 'png', 'gif'}
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        return jsonify({"error": "Invalid file type. Allowed: PDF, JPG, PNG, GIF"}), 400
    
    try:
        # Delete old file if exists
        if po.customerLocationFile:
            old_path = os.path.join(app.config['UPLOAD_FOLDER'], po.customerLocationFile)
            if os.path.exists(old_path):
                os.remove(old_path)
        
        # Save new file
        filename = secure_filename(f"location_{po.poNumber}_{int(datetime.now().timestamp())}.{ext}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Update database
        po.customerLocationFile = filename
        po.customerLocationFileUrl = f"/uploads/{filename}"
        po.customerLocationUploadedAt = now_bangkok()
        po.customerLocationUploadedBy = current_user.id
        
        # Add comment log
        comment = Comment(
            po_id=po.id,
            user_id=current_user.id,
            user=current_user.fullName,
            text=f"Uploaded Customer Location: {file.filename}"
        )
        db.session.add(comment)
        
        db.session.commit()
        
        return jsonify({
            "message": "Location file uploaded successfully",
            "fileUrl": po.customerLocationFileUrl,
            "filename": filename
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
```

##### B. Upload Customer PO
```python
@app.route('/api/pos/<int:id>/upload-customer-po', methods=['POST'])
@login_required
def upload_customer_po_file(id):
    """
    Upload customer PO document
    
    Authorization: PO Owner OR Sale Admin OR Administrator
    File Types: PDF, JPG, JPEG, PNG, GIF
    Max Size: 10MB
    """
    po = PurchaseOrder.query.get_or_404(id)
    
    # Authorization check
    if current_user.id != po.sale_user_id and current_user.role not in ['Administrator', 'Sale Admin']:
        return jsonify({"error": "Unauthorized"}), 403
    
    # Validate file
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    # Validate file type
    allowed_extensions = {'pdf', 'jpg', 'jpeg', 'png', 'gif'}
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        return jsonify({"error": "Invalid file type. Allowed: PDF, JPG, PNG, GIF"}), 400
    
    try:
        # Delete old file if exists
        if po.customerPoFile:
            old_path = os.path.join(app.config['UPLOAD_FOLDER'], po.customerPoFile)
            if os.path.exists(old_path):
                os.remove(old_path)
        
        # Save new file
        filename = secure_filename(f"customer_po_{po.poNumber}_{int(datetime.now().timestamp())}.{ext}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Update database
        po.customerPoFile = filename
        po.customerPoFileUrl = f"/uploads/{filename}"
        po.customerPoUploadedAt = now_bangkok()
        po.customerPoUploadedBy = current_user.id
        
        # Add comment log
        comment = Comment(
            po_id=po.id,
            user_id=current_user.id,
            user=current_user.fullName,
            text=f"Uploaded Customer PO: {file.filename}"
        )
        db.session.add(comment)
        
        db.session.commit()
        
        return jsonify({
            "message": "Customer PO file uploaded successfully",
            "fileUrl": po.customerPoFileUrl,
            "filename": filename
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
```

##### C. Delete Customer Location
```python
@app.route('/api/pos/<int:id>/delete-location', methods=['DELETE'])
@login_required
def delete_customer_location(id):
    """
    Delete customer location file
    
    Authorization: PO Owner OR Sale Admin OR Administrator
    """
    po = PurchaseOrder.query.get_or_404(id)
    
    # Authorization check
    if current_user.id != po.sale_user_id and current_user.role not in ['Administrator', 'Sale Admin']:
        return jsonify({"error": "Unauthorized"}), 403
    
    if not po.customerLocationFile:
        return jsonify({"error": "No location file to delete"}), 400
    
    try:
        # Delete file from filesystem
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], po.customerLocationFile)
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # Update database
        old_filename = po.customerLocationFile
        po.customerLocationFile = None
        po.customerLocationFileUrl = None
        po.customerLocationUploadedAt = None
        po.customerLocationUploadedBy = None
        
        # Add comment log
        comment = Comment(
            po_id=po.id,
            user_id=current_user.id,
            user=current_user.fullName,
            text=f"Deleted Customer Location: {old_filename}"
        )
        db.session.add(comment)
        
        db.session.commit()
        
        return jsonify({"message": "Location file deleted successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
```

##### D. Delete Customer PO
```python
@app.route('/api/pos/<int:id>/delete-customer-po', methods=['DELETE'])
@login_required
def delete_customer_po_file(id):
    """
    Delete customer PO file
    
    Authorization: PO Owner OR Sale Admin OR Administrator
    """
    po = PurchaseOrder.query.get_or_404(id)
    
    # Authorization check
    if current_user.id != po.sale_user_id and current_user.role not in ['Administrator', 'Sale Admin']:
        return jsonify({"error": "Unauthorized"}), 403
    
    if not po.customerPoFile:
        return jsonify({"error": "No customer PO file to delete"}), 400
    
    try:
        # Delete file from filesystem
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], po.customerPoFile)
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # Update database
        old_filename = po.customerPoFile
        po.customerPoFile = None
        po.customerPoFileUrl = None
        po.customerPoUploadedAt = None
        po.customerPoUploadedBy = None
        
        # Add comment log
        comment = Comment(
            po_id=po.id,
            user_id=current_user.id,
            user=current_user.fullName,
            text=f"Deleted Customer PO: {old_filename}"
        )
        db.session.add(comment)
        
        db.session.commit()
        
        return jsonify({"message": "Customer PO file deleted successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
```

---

### 3. Frontend Changes (app.html)

#### A. PO Detail View - Add Document Section

**Location**: After PO items table, before comments section

```html
<!-- NEW: Additional Documents Section -->
<div id="po-documents-section" style="display: none; margin-top: 30px;">
    <h3 style="color: var(--text-primary); margin-bottom: 20px;">
        <i data-lucide="paperclip"></i> เอกสารเพิ่มเติม
    </h3>
    
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
        <!-- Customer Location/Map -->
        <div class="document-upload-card">
            <div class="document-header">
                <i data-lucide="map-pin"></i>
                <span>แผนที่/ตำแหน่งลูกค้า</span>
            </div>
            
            <div id="location-file-display" style="display: none;">
                <div class="file-info">
                    <i data-lucide="file"></i>
                    <span id="location-filename"></span>
                </div>
                <div class="file-meta">
                    <small id="location-uploaded-info"></small>
                </div>
                <div class="file-actions">
                    <button onclick="viewFile('location')" class="btn-view">
                        <i data-lucide="eye"></i> ดูไฟล์
                    </button>
                    <button onclick="deleteDocument('location')" class="btn-delete">
                        <i data-lucide="trash-2"></i> ลบ
                    </button>
                </div>
            </div>
            
            <div id="location-upload-form" style="display: none;">
                <input type="file" id="location-file-input" accept=".pdf,.jpg,.jpeg,.png,.gif" style="display: none;">
                <button onclick="document.getElementById('location-file-input').click()" class="btn-upload">
                    <i data-lucide="upload"></i> อัปโหลดแผนที่
                </button>
                <small style="color: var(--text-secondary); display: block; margin-top: 10px;">
                    รองรับ: PDF, JPG, PNG, GIF (สูงสุด 10MB)
                </small>
            </div>
        </div>
        
        <!-- Customer PO Document -->
        <div class="document-upload-card">
            <div class="document-header">
                <i data-lucide="file-text"></i>
                <span>PO ของลูกค้า</span>
            </div>
            
            <div id="customer-po-file-display" style="display: none;">
                <div class="file-info">
                    <i data-lucide="file"></i>
                    <span id="customer-po-filename"></span>
                </div>
                <div class="file-meta">
                    <small id="customer-po-uploaded-info"></small>
                </div>
                <div class="file-actions">
                    <button onclick="viewFile('customer-po')" class="btn-view">
                        <i data-lucide="eye"></i> ดูไฟล์
                    </button>
                    <button onclick="deleteDocument('customer-po')" class="btn-delete">
                        <i data-lucide="trash-2"></i> ลบ
                    </button>
                </div>
            </div>
            
            <div id="customer-po-upload-form" style="display: none;">
                <input type="file" id="customer-po-file-input" accept=".pdf,.jpg,.jpeg,.png,.gif" style="display: none;">
                <button onclick="document.getElementById('customer-po-file-input').click()" class="btn-upload">
                    <i data-lucide="upload"></i> อัปโหลด PO ลูกค้า
                </button>
                <small style="color: var(--text-secondary); display: block; margin-top: 10px;">
                    รองรับ: PDF, JPG, PNG, GIF (สูงสุด 10MB)
                </small>
            </div>
        </div>
    </div>
</div>

<style>
.document-upload-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 20px;
}

.document-header {
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 15px;
    font-size: 16px;
}

.file-info {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px;
    background: var(--bg-primary);
    border-radius: 8px;
    margin-bottom: 10px;
}

.file-meta {
    color: var(--text-secondary);
    font-size: 13px;
    margin-bottom: 15px;
}

.file-actions {
    display: flex;
    gap: 10px;
}

.btn-view, .btn-delete, .btn-upload {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 16px;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.2s;
}

.btn-view {
    background: var(--primary-color);
    color: white;
}

.btn-view:hover {
    background: var(--primary-dark);
}

.btn-delete {
    background: var(--danger-color);
    color: white;
}

.btn-delete:hover {
    background: #c0392b;
}

.btn-upload {
    background: var(--success-color);
    color: white;
    width: 100%;
    justify-content: center;
}

.btn-upload:hover {
    background: #27ae60;
}
</style>
```

#### B. JavaScript Functions

```javascript
// Update viewPO function to show documents section
async function viewPO(id) {
    // ... existing code ...
    
    // NEW: Show documents section if user can edit
    const canEdit = (currentUser.role === 'Administrator' || 
                     currentUser.role === 'Sale Admin' || 
                     po.saleUserId === currentUser.id);
    
    if (canEdit) {
        document.getElementById('po-documents-section').style.display = 'block';
        updateDocumentDisplay(po);
    }
}

// NEW: Update document display based on PO data
function updateDocumentDisplay(po) {
    // Customer Location
    if (po.customerLocationFile) {
        document.getElementById('location-file-display').style.display = 'block';
        document.getElementById('location-upload-form').style.display = 'none';
        document.getElementById('location-filename').textContent = po.customerLocationFile;
        document.getElementById('location-uploaded-info').textContent = 
            `อัปโหลดโดย ${po.customerLocationUploadedBy || 'N/A'} เมื่อ ${po.customerLocationUploadedAt || 'N/A'}`;
    } else {
        document.getElementById('location-file-display').style.display = 'none';
        document.getElementById('location-upload-form').style.display = 'block';
    }
    
    // Customer PO
    if (po.customerPoFile) {
        document.getElementById('customer-po-file-display').style.display = 'block';
        document.getElementById('customer-po-upload-form').style.display = 'none';
        document.getElementById('customer-po-filename').textContent = po.customerPoFile;
        document.getElementById('customer-po-uploaded-info').textContent = 
            `อัปโหลดโดย ${po.customerPoUploadedBy || 'N/A'} เมื่อ ${po.customerPoUploadedAt || 'N/A'}`;
    } else {
        document.getElementById('customer-po-file-display').style.display = 'none';
        document.getElementById('customer-po-upload-form').style.display = 'block';
    }
}

// NEW: Handle file upload
document.getElementById('location-file-input').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    // Validate file size (10MB)
    if (file.size > 10 * 1024 * 1024) {
        alert('ไฟล์มีขนาดใหญ่เกิน 10MB');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`/api/pos/${currentPO.id}/upload-location`, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            showToast('อัปโหลดแผนที่สำเร็จ', 'success');
            viewPO(currentPO.id); // Refresh view
        } else {
            const error = await response.json();
            alert(error.error || 'เกิดข้อผิดพลาด');
        }
    } catch (error) {
        console.error('Upload error:', error);
        alert('เกิดข้อผิดพลาดในการอัปโหลด');
    }
});

document.getElementById('customer-po-file-input').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    // Validate file size (10MB)
    if (file.size > 10 * 1024 * 1024) {
        alert('ไฟล์มีขนาดใหญ่เกิน 10MB');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`/api/pos/${currentPO.id}/upload-customer-po`, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            showToast('อัปโหลด PO ลูกค้าสำเร็จ', 'success');
            viewPO(currentPO.id); // Refresh view
        } else {
            const error = await response.json();
            alert(error.error || 'เกิดข้อผิดพลาด');
        }
    } catch (error) {
        console.error('Upload error:', error);
        alert('เกิดข้อผิดพลาดในการอัปโหลด');
    }
});

// NEW: View file in new tab
function viewFile(type) {
    let fileUrl;
    if (type === 'location') {
        fileUrl = currentPO.customerLocationFileUrl;
    } else if (type === 'customer-po') {
        fileUrl = currentPO.customerPoFileUrl;
    }
    
    if (fileUrl) {
        window.open(fileUrl, '_blank');
    }
}

// NEW: Delete document
async function deleteDocument(type) {
    const confirmMsg = type === 'location' 
        ? 'ต้องการลบไฟล์แผนที่ใช่หรือไม่?' 
        : 'ต้องการลบไฟล์ PO ลูกค้าใช่หรือไม่?';
    
    if (!confirm(confirmMsg)) return;
    
    const endpoint = type === 'location' 
        ? `/api/pos/${currentPO.id}/delete-location`
        : `/api/pos/${currentPO.id}/delete-customer-po`;
    
    try {
        const response = await fetchApi(endpoint, 'DELETE');
        if (response) {
            showToast('ลบไฟล์สำเร็จ', 'success');
            viewPO(currentPO.id); // Refresh view
        }
    } catch (error) {
        console.error('Delete error:', error);
        alert('เกิดข้อผิดพลาดในการลบไฟล์');
    }
}
```

---

## 📝 Implementation Checklist

### Phase 1: Database (30 min)
- [ ] Update `models.py` - Add 8 new columns
- [ ] Create `migrate_add_document_uploads.sql`
- [ ] Apply migration to database
- [ ] Update `to_dict()` method
- [ ] Test database changes

### Phase 2: Backend API (1 hour)
- [ ] Create `/api/pos/<id>/upload-location` endpoint
- [ ] Create `/api/pos/<id>/upload-customer-po` endpoint
- [ ] Create `/api/pos/<id>/delete-location` endpoint
- [ ] Create `/api/pos/<id>/delete-customer-po` endpoint
- [ ] Add file validation logic
- [ ] Add authorization checks
- [ ] Test all endpoints with Postman

### Phase 3: Frontend UI (1.5 hours)
- [ ] Add document section HTML
- [ ] Add CSS styling
- [ ] Implement file upload handlers
- [ ] Implement view file function
- [ ] Implement delete file function
- [ ] Update `viewPO()` function
- [ ] Test UI interactions

### Phase 4: Testing (30 min)
- [ ] Test upload with different file types
- [ ] Test file size validation
- [ ] Test replace file (auto-delete old)
- [ ] Test delete file
- [ ] Test authorization (Sale vs Admin)
- [ ] Test file viewing

### Phase 5: Documentation (15 min)
- [ ] Update API_REFERENCE.md
- [ ] Update DATABASE_SCHEMA.md
- [ ] Add migration notes

---

## 🎯 Expected Results

### User Experience
1. Sale เปิด PO → เห็นส่วน "เอกสารเพิ่มเติม" 2 ช่อง
2. คลิก "อัปโหลดแผนที่" → เลือกไฟล์ → อัปโหลดสำเร็จ
3. เห็นชื่อไฟล์ + ข้อมูลผู้อัปโหลด + ปุ่ม "ดู" และ "ลบ"
4. คลิก "ดู" → เปิดไฟล์ในแท็บใหม่
5. อัปโหลดไฟล์ใหม่ → ไฟล์เก่าถูกลบอัตโนมัติ
6. คลิก "ลบ" → ยืนยัน → ไฟล์ถูกลบ กลับไปสถานะ "อัปโหลด"

### Database Impact
- เพิ่ม 8 columns ใน `purchase_orders` table
- เพิ่ม 2 indexes
- ไม่กระทบข้อมูลเดิม (columns เป็น nullable)

### File Storage
- ไฟล์เก็บใน `/uploads/` folder
- Naming convention: `location_{poNumber}_{timestamp}.{ext}`
- Auto-cleanup เมื่อมีการ replace หรือ delete

---

## ⚠️ Potential Issues & Solutions

### Issue 1: File Size Too Large
**Solution**: Validate on both frontend and backend (10MB limit)

### Issue 2: Concurrent Upload
**Solution**: Use timestamp in filename to avoid conflicts

### Issue 3: Orphaned Files
**Solution**: Implement cleanup script to remove files not in database

### Issue 4: File Type Security
**Solution**: Whitelist only safe extensions, validate MIME type

---

## 🚀 Future Enhancements

1. **Multiple Files**: Allow multiple files per category (gallery)
2. **File Preview**: Show thumbnail for images, PDF preview
3. **Download All**: Zip all documents for download
4. **Version History**: Keep old versions of replaced files
5. **Cloud Storage**: Move to S3/Cloud Storage for scalability

---

**Analysis Date**: 2026-02-07  
**Estimated Development Time**: 3-4 hours  
**Priority**: Medium  
**Complexity**: Low-Medium

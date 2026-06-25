# PO-Online System Architecture Documentation

## 📋 สารบัญ
1. [ภาพรวมระบบ](#ภาพรวมระบบ)
2. [โครงสร้างฐานข้อมูล](#โครงสร้างฐานข้อมูล)
3. [การทำงานของแต่ละ Module](#การทำงานของแต่ละ-module)
4. [CRUD Operations](#crud-operations)
5. [Workflow สำคัญ](#workflow-สำคัญ)
6. [Security & Authorization](#security--authorization)
7. [Best Practices](#best-practices)

---

## ภาพรวมระบบ

### Technology Stack
- **Backend**: Flask (Python)
- **Database**: PostgreSQL
- **Frontend**: Vanilla JavaScript + HTML + CSS
- **Deployment**: Docker + Gunicorn
- **Authentication**: Flask-Login
- **PDF Generation**: ReportLab
- **QR Code**: qrcode library
- **Notifications**: Telegram Bot API

### Architecture Pattern
```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (SPA)                       │
│              app.html (Single Page App)                 │
└────────────────────┬────────────────────────────────────┘
                     │ REST API (JSON)
┌────────────────────▼────────────────────────────────────┐
│                  Backend (Flask)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │  app.py  │  │models.py │  │ utils.py │             │
│  │ (Routes) │  │ (Models) │  │(Helpers) │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└────────────────────┬────────────────────────────────────┘
                     │ SQLAlchemy ORM
┌────────────────────▼────────────────────────────────────┐
│              PostgreSQL Database                        │
│  Users | Customers | Products | POs | Items | Comments │
└─────────────────────────────────────────────────────────┘
```

---

## โครงสร้างฐานข้อมูล

### 1. Users Table
**ไฟล์**: `models.py` → Class `User`

```python
users
├── id (PK)
├── username (UNIQUE)
├── password (hashed with bcrypt)
├── fullName
├── role (Sale, Sale Admin, Administrator)
├── signature_image (Base64 encoded)
├── status (active/inactive)
├── lastLogin
└── createdAt
```

**Relationships**:
- `pos` → PurchaseOrder (one-to-many, as creator)
- `cancelled_pos` → PurchaseOrder (one-to-many, as canceller)
- `requested_cancel_pos` → PurchaseOrder (one-to-many, as requester)

**Key Methods**:
- `to_dict()`: Serialize user data (excludes password)

---

### 2. Customers Table
**ไฟล์**: `models.py` → Class `Customer`

```python
customers
├── id (PK)
├── customerCode (UNIQUE, INDEX)
├── name (INDEX)
├── taxId
├── billToAddress (JSON: line1, line2, tel)
├── shipToAddress (JSON: line1, line2, tel)
├── status (active/inactive)
└── [40+ SAP fields...]
```

**Key Methods**:
- `to_dict()`: Basic info for lists
- `to_detail_dict()`: Full details including addresses

**Special Features**:
- JSON fields for flexible address storage
- SAP integration ready (CSV import/export)

---

### 3. Products Table
**ไฟล์**: `models.py` → Class `Product`

```python
products
├── id (PK)
├── productCode (UNIQUE, INDEX)
├── name (INDEX)
├── price
├── inStock
├── imageUrl
├── status (active/inactive)
└── [40+ SAP fields...]
```

**Key Methods**:
- `to_dict()`: Basic info for lists
- `to_detail_dict()`: Full details

**Image Handling**:
- Stored in `/uploads/product_images/`
- Fallback to `/static/product_images/`
- URL builder: `build_product_image_url()`

---

### 4. PurchaseOrders Table (Core)
**ไฟล์**: `models.py` → Class `PurchaseOrder`

```python
purchase_orders
├── id (PK)
├── poNumber (UNIQUE, INDEX, format: POYYMM0001)
├── customerId (FK to customers.customerCode)
├── customerName
├── sale_user_id (FK to users.id)
├── saleId (Sale name)
├── amount (Total value)
├── status (Draft, Pending Review, Approved, etc.)
├── created
├── deliveryDate
├── signedFile (PDF path)
├── signedFileUrl
├── signatureImage (Digital signature)
├── accessToken (UUID for customer portal)
├── signedAt
│
├── Cancellation Fields:
│   ├── cancelReason
│   ├── cancelledAt
│   ├── cancelledBy (FK to users.id)
│   ├── cancelRequestBy (FK to users.id)
│   ├── cancelRequestAt
│   ├── cancelRequestReason
│   └── previousStatus
```

**Relationships**:
- `items` → POItem (one-to-many, cascade delete)
- `comments` → Comment (one-to-many, cascade delete)
- `creator` → User (many-to-one)
- `canceller` → User (many-to-one)
- `requester` → User (many-to-one)
- `customer_rel` → Customer (many-to-one, viewonly)

**Status Flow**:
```
Draft → Pending Review → Approved → Completed
                ↓           ↓          ↓
         Changes Requested  ↓          ↓
                            ↓          ↓
                   Cancellation Requested
                            ↓
                        Cancelled
```

**Key Methods**:
- `to_dict()`: Full serialization with all related data

---

### 5. POItems Table
**ไฟล์**: `models.py` → Class `POItem`

```python
po_items
├── id (PK)
├── po_id (FK to purchase_orders.id)
├── productId (FK to products.id)
├── productCode
├── name
├── qty
├── price
├── discount (%)
├── total (calculated)
└── imageUrl
```

**Relationships**:
- `po` → PurchaseOrder (many-to-one)
- `product` → Product (many-to-one, viewonly)

---

### 6. Comments Table
**ไฟล์**: `models.py` → Class `Comment`

```python
comments
├── id (PK)
├── po_id (FK to purchase_orders.id)
├── user_id (FK to users.id)
├── user (User name)
├── text
└── created
```

**Use Cases**:
- Status change logs
- Admin feedback
- Cancellation reasons
- General communication

---

### 7. Notifications Table
**ไฟล์**: `models.py` → Class `Notification`

```python
notifications
├── id (PK)
├── user_id (FK to users.id)
├── message
├── link_id (PO ID)
├── is_read (Boolean)
└── created
```

**Key Methods**:
- `to_dict()`: Serialize notification

**Helper Function**:
- `create_notification(user_id, message, link_id)`: Create new notification

---

## การทำงานของแต่ละ Module

### app.py - Main Application

#### 1. Authentication & Session Management

**Login Flow** (`/api/auth/login`):
```python
def login():
    1. Rate limiting check (max 5 attempts per IP)
    2. Validate username/password
    3. Check bcrypt hash
    4. Create Flask-Login session
    5. Update lastLogin timestamp
    6. Return user data + role
```

**Authorization Decorator**:
```python
@roles_required('Administrator', 'Sale Admin')
def protected_route():
    # Only specified roles can access
    # Returns 403 if unauthorized
```

---

#### 2. PO Management APIs

**GET /api/pos** - List All POs
```python
def manage_pos():
    # Query optimization with joinedload
    query = PurchaseOrder.query
    
    # Role-based filtering:
    if Admin/Sale Admin:
        # See all EXCEPT other people's Drafts
        filter(status != 'Draft' OR sale_user_id == current_user.id)
    else:
        # Sale: See only own POs
        filter(sale_user_id == current_user.id)
    
    # Eager loading to prevent N+1 queries:
    .options(
        joinedload(creator),
        joinedload(customer_rel),
        joinedload(requester),
        joinedload(canceller),
        selectinload(comments),
        joinedload(items).joinedload(product)
    )
    
    return [po.to_dict() for po in pos]
```

**POST /api/pos** - Create New PO
```python
def manage_pos():
    1. Generate PO Number (POYYMM0001)
    2. Create PurchaseOrder record
    3. Create POItem records for each item
    4. Set status (Draft or Pending Review)
    5. Generate accessToken (UUID)
    6. Commit to database
    7. Return created PO
```

**GET /api/pos/<id>** - Get Single PO
```python
def manage_po(id):
    # Security checks:
    if po.status == 'Draft' and po.sale_user_id != current_user.id:
        return 403 Unauthorized
    
    if not Admin and po.sale_user_id != current_user.id:
        return 403 Unauthorized
    
    return po.to_dict()
```

**PUT /api/pos/<id>** - Update PO
```python
def manage_po(id):
    # Handle status changes:
    if status changed:
        1. Send Telegram notification
        2. Create in-app notification
        3. Add comment log
    
    # Update fields:
    - customerId, customerName
    - deliveryDate
    - amount
    - items (delete old, create new)
    
    # Special handling:
    - If Pending Review → Approved: Send notifications
    - If Changes Requested: Notify Sale
```

**DELETE /api/pos/<id>** - Delete PO
```python
def manage_po(id):
    # Only allow deletion of:
    - Draft (by anyone)
    - Pending Review (by Admin only)
    
    # Send Telegram notification if not Draft
    # Cascade delete items and comments
```

---

#### 3. Cancellation Workflow (Multi-Step)

**POST /api/pos/<id>/request-cancel** - Request Cancellation
```python
def request_cancel_po(id):
    # Authorization:
    - Creator (Sale) OR Admin/Sale Admin
    
    # Validation:
    - Status must be Approved or Completed
    - Reason required
    
    # Actions:
    1. Save previousStatus
    2. Set status = 'Cancellation Requested'
    3. Store cancelRequestBy, cancelRequestAt, cancelRequestReason
    4. Send Telegram notification to Admins
    5. Add comment log
    
    return {"status": "Cancellation Requested"}
```

**POST /api/pos/<id>/approve-cancel** - Approve Cancellation
```python
def approve_cancel_po(id):
    # Authorization: Admin/Sale Admin only
    
    # Validation:
    - Status must be 'Cancellation Requested'
    
    # Actions:
    1. Set status = 'Cancelled'
    2. Copy cancelRequestReason → cancelReason
    3. Set cancelledAt, cancelledBy
    4. Send Telegram notification
    5. Notify Sale owner
    6. Add comment log
    
    # Financial Impact:
    - Amount deducted from Sale's stats
    - Excluded from dashboard metrics
    
    return {"status": "Cancelled"}
```

**POST /api/pos/<id>/reject-cancel** - Reject Cancellation
```python
def reject_cancel_po(id):
    # Authorization: Admin/Sale Admin only
    
    # Validation:
    - Status must be 'Cancellation Requested'
    
    # Actions:
    1. Revert status to previousStatus
    2. Send Telegram notification
    3. Notify Sale owner
    4. Add comment log with rejection reason
    
    return {"status": previousStatus}
```

---

#### 4. Customer Portal & Digital Signature

**GET /p/<token>** - Customer Portal View
```python
def customer_portal_view(token):
    # Public access (no login required)
    
    1. Find PO by accessToken
    2. Render customer_portal.html
    3. Display PO details, items, company info
    4. Show signature pad if not signed
```

**POST /api/customer/sign/<token>** - Digital Signature
```python
def sign_customer_po(token):
    1. Validate token
    2. Decode Base64 signature image
    3. Save to /uploads/signatures/
    4. Update PO:
       - signatureImage = filename
       - signedAt = now
       - status = 'Completed'
    5. Generate PDF with signature
    6. Send Telegram notification
    7. Notify Sale owner
    
    return {"success": True}
```

---

#### 5. PDF Generation

**Helper Function**: `_generate_pdf_bytes(po, is_draft=True)`
```python
def _generate_pdf_bytes(po, is_draft):
    1. Create ReportLab Canvas
    2. Add company logo and info
    3. Add "DRAFT" watermark if is_draft
    4. Add customer info
    5. Add items table with:
       - Product code, name
       - Quantity, price, discount
       - Total per item
    6. Add summary (subtotal, VAT, grand total)
    7. Add signature section:
       - Sale signature (from User.signature_image)
       - Customer signature (if completed)
    8. Return PDF bytes
```

**GET /api/pos/<id>/print** - Print/Download PDF
```python
def print_po(id):
    is_draft = request.args.get('draft', 'false') == 'true'
    
    pdf_bytes = _generate_pdf_bytes(po, is_draft)
    
    return send_file(
        BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=False,
        download_name=f'{po.poNumber}.pdf'
    )
```

---

#### 6. QR Code Generation

**GET /api/pos/<id>/qr** - Generate QR Code
```python
def get_po_qr_code(id):
    1. Build customer portal URL:
       https://domain.com/p/{accessToken}
    
    2. Generate QR code image
    3. Return as PNG image
    
    # Use case: Print on PDF for customer scanning
```

---

#### 7. File Upload & Management

**POST /api/products/<key>/upload-image** - Upload Product Image
```python
def upload_product_image(key):
    1. Validate file type (jpg, jpeg, png, gif, webp)
    2. Secure filename
    3. Save to /uploads/product_images/
    4. Update Product.imageUrl
    5. Return image URL
```

**POST /api/users/<id>/upload-signature** - Upload User Signature
```python
def upload_user_signature(id):
    1. Decode Base64 image
    2. Save to /uploads/signatures/
    3. Update User.signature_image
    4. Return success
```

**GET /uploads/<filename>** - Serve Uploaded Files
```python
def download_file(filename):
    # Serve PDFs, images, signatures
    return send_from_directory(UPLOAD_FOLDER, filename)
```

---

#### 8. Notification System

**GET /api/notifications** - Get User Notifications
```python
def get_notifications():
    # Get unread notifications for current user
    notifications = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).order_by(created.desc()).all()
    
    return [n.to_dict() for n in notifications]
```

**POST /api/notifications/<id>/read** - Mark as Read
```python
def read_notification(id):
    notification.is_read = True
    db.session.commit()
```

**POST /api/notifications/read-all** - Mark All as Read
```python
def read_all_notifications():
    Notification.query.filter_by(
        user_id=current_user.id
    ).update({is_read: True})
```

---

## CRUD Operations

### Create (C)

#### Create PO
```
POST /api/pos
Body: {
  customerId, customerName, deliveryDate,
  status, total,
  items: [{productId, name, qty, price, discount, total}]
}
→ Generate poNumber
→ Create PurchaseOrder + POItems
→ Return created PO
```

#### Create Customer
```
POST /api/customers
Body: {customerCode, name, taxId, ...}
→ Validate unique customerCode
→ Create Customer
→ Return created customer
```

#### Create Product
```
POST /api/products
Body: {productCode, name, price, ...}
→ Validate unique productCode
→ Create Product
→ Return created product
```

---

### Read (R)

#### List with Filtering
```
GET /api/pos
→ Role-based filtering
→ Eager load relationships
→ Return array of POs

GET /api/customers?q=search_term
→ Search by code or name
→ Filter active only
→ Return matching customers

GET /api/products?q=search_term
→ Search by code or name
→ Filter active only
→ Return matching products
```

#### Get Single Record
```
GET /api/pos/<id>
→ Authorization check
→ Return full PO with items, comments

GET /api/customers/<code>
→ Return customer details

GET /api/products/<code>
→ Return product details
```

---

### Update (U)

#### Update PO
```
PUT /api/pos/<id>
Body: {customerId, deliveryDate, items, ...}
→ Update PO fields
→ Delete old items
→ Create new items
→ Handle status changes
→ Send notifications
→ Return updated PO
```

#### Update Customer
```
PUT /api/customers/<code>
Body: {name, taxId, addresses, ...}
→ Update customer fields
→ Return updated customer
```

#### Update Product
```
PUT /api/products/<code>
Body: {name, price, inStock, ...}
→ Update product fields
→ Return updated product
```

---

### Delete (D)

#### Delete PO
```
DELETE /api/pos/<id>
→ Check permissions
→ Cascade delete items, comments
→ Send notification
→ Return 204 No Content
```

#### Soft Delete (Deactivate)
```
PUT /api/customers/<code>
Body: {status: 'inactive'}
→ Mark as inactive
→ Hide from dropdowns

PUT /api/products/<code>
Body: {status: 'inactive'}
→ Mark as inactive
→ Hide from dropdowns
```

---

## Workflow สำคัญ

### 1. PO Creation Workflow

```
Sale User:
1. Navigate to PO Management
2. Click "Create New PO"
3. Select Customer (dropdown with search)
4. Set Delivery Date
5. Add Items:
   - Select Product (dropdown with search)
   - Set Quantity
   - Price auto-filled from Product
   - Apply Discount (optional)
   - Total calculated automatically
6. Review Total Amount
7. Choose:
   - Save as Draft (status = Draft)
   - Submit for Review (status = Pending Review)
8. System generates PO Number (POYYMM0001)
9. If Pending Review:
   - Send Telegram notification to Admins
   - Create in-app notification for Admins
```

---

### 2. PO Approval Workflow

```
Admin/Sale Admin:
1. Receive notification (Telegram + In-App)
2. Navigate to PO Management
3. Filter by "Pending Review"
4. Click PO to view details
5. Review items, amounts, customer
6. Choose:
   
   A. Approve:
      - Click "Approve" button
      - Status → Approved
      - Send notification to Sale
      - Generate QR code for customer portal
   
   B. Request Changes:
      - Add comment explaining required changes
      - Click "Request Changes"
      - Status → Changes Requested
      - Send notification to Sale
```

---

### 3. Customer Signature Workflow

```
Customer (via QR Code):
1. Scan QR code from printed PO
2. Open customer portal (/p/<token>)
3. Review PO details
4. Draw signature on canvas
5. Click "Confirm Signature"
6. System:
   - Saves signature image
   - Updates status → Completed
   - Generates final PDF with signature
   - Sends notification to Sale
   - Sends Telegram notification
```

---

### 4. Cancellation Workflow (2-Step)

```
Sale (Request):
1. Open Approved/Completed PO
2. Click "Request Cancel"
3. Enter cancellation reason
4. Submit request
5. Status → Cancellation Requested
6. Telegram notification sent to Admins
7. Wait for Admin decision

Admin (Approve/Reject):
1. Receive notification
2. Review cancellation request
3. Choose:
   
   A. Approve:
      - Click "Accept Cancellation"
      - Status → Cancelled
      - Amount deducted from stats
      - Notify Sale
   
   B. Reject:
      - Click "Reject Cancellation"
      - Enter rejection reason (optional)
      - Status reverts to previous
      - Notify Sale
```

---

## Security & Authorization

### Role-Based Access Control (RBAC)

#### Administrator
- Full system access
- User management
- View all POs (except others' Drafts)
- Approve/reject POs
- Approve/reject cancellations
- Delete any PO
- Access all reports

#### Sale Admin
- View all POs (except others' Drafts)
- Approve/reject POs
- Approve/reject cancellations
- Cannot manage users
- Access all reports

#### Sale
- View only own POs
- Create POs
- Edit own Drafts
- Request cancellations
- Cannot approve POs
- Cannot delete Approved/Completed POs

---

### Data Visibility Rules

1. **Draft POs**: Only visible to creator
2. **Other Statuses**: Visible to creator + Admins
3. **Notifications**: Only visible to recipient
4. **Comments**: Visible to anyone who can view the PO

---

### Security Best Practices

1. **Password Hashing**: bcrypt with salt
2. **Session Management**: Flask-Login secure sessions
3. **Rate Limiting**: 5 login attempts per IP
4. **Input Validation**: All user inputs sanitized
5. **SQL Injection Prevention**: SQLAlchemy ORM
6. **File Upload Security**: 
   - Whitelist file extensions
   - Secure filename generation
   - Size limits
7. **API Authorization**: Decorator-based role checks
8. **CSRF Protection**: Flask built-in

---

## Best Practices

### 1. Database Queries

**❌ Bad (N+1 Problem)**:
```python
pos = PurchaseOrder.query.all()
for po in pos:
    print(po.creator.fullName)  # Extra query per PO!
```

**✅ Good (Eager Loading)**:
```python
pos = PurchaseOrder.query.options(
    joinedload(PurchaseOrder.creator)
).all()
for po in pos:
    print(po.creator.fullName)  # No extra queries
```

---

### 2. Error Handling

**Always use try-except for database operations**:
```python
try:
    db.session.add(new_po)
    db.session.commit()
    return jsonify(new_po.to_dict()), 201
except Exception as e:
    db.session.rollback()
    app.logger.error(f"Error creating PO: {e}")
    return jsonify({"error": str(e)}), 500
```

---

### 3. Notification Pattern

**Whenever a PO status changes**:
```python
# 1. Telegram notification
send_telegram_msg(f"📝 PO {po.poNumber} {new_status}")

# 2. In-app notification
create_notification(
    user_id=po.sale_user_id,
    message=f"PO {po.poNumber} is now {new_status}",
    link_id=po.id
)

# 3. Comment log
comment = Comment(
    po_id=po.id,
    user_id=current_user.id,
    user=current_user.fullName,
    text=f"Status changed to {new_status}"
)
db.session.add(comment)
```

---

### 4. Frontend-Backend Communication

**Always use consistent JSON structure**:
```javascript
// Frontend request
const result = await fetchApi('/api/pos', 'POST', {
    customerId: 'C001',
    items: [{productId: 1, qty: 10, ...}]
});

// Backend response
{
    "id": 123,
    "poNumber": "PO2601001",
    "status": "Draft",
    ...
}
```

---

### 5. Code Organization

**Separation of Concerns**:
- `app.py`: Routes and request handling
- `models.py`: Database models and business logic
- `utils.py`: Helper functions (dates, encryption, etc.)
- `extensions.py`: Flask extensions initialization
- `app.html`: Frontend SPA

---

## สรุป

ระบบ PO-Online ออกแบบมาเพื่อ:
1. **ความปลอดภัย**: Role-based access, secure sessions
2. **ประสิทธิภาพ**: Eager loading, optimized queries
3. **ความโปร่งใส**: Audit trail via comments, notifications
4. **ความยืดหยุ่น**: Multi-step workflows, digital signatures
5. **การบูรณาการ**: SAP CSV import/export, Telegram notifications

การแก้ไขโค้ดควรคำนึงถึง:
- **Database relationships**: การเปลี่ยน model ต้องอัปเดต relationships
- **Authorization**: ตรวจสอบ role ก่อนทุก operation
- **Notifications**: แจ้งเตือนผู้เกี่ยวข้องเมื่อมีการเปลี่ยนแปลง
- **Logging**: บันทึก comment สำหรับ audit trail
- **Error handling**: Rollback database เมื่อเกิด error

---

**เอกสารนี้สร้างขึ้นเมื่อ**: 2026-02-07  
**เวอร์ชัน**: 1.7.2  
**ผู้จัดทำ**: Antigravity AI Assistant

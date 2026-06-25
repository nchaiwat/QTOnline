# PO-Online API Reference

## 📚 Table of Contents
- [Authentication APIs](#authentication-apis)
- [PO Management APIs](#po-management-apis)
- [Cancellation APIs](#cancellation-apis)
- [Customer APIs](#customer-apis)
- [Product APIs](#product-apis)
- [User Management APIs](#user-management-apis)
- [Notification APIs](#notification-apis)
- [File Upload APIs](#file-upload-apis)
- [Customer Portal APIs](#customer-portal-apis)
- [Utility APIs](#utility-apis)

---

## Authentication APIs

### POST /api/auth/login
**Description**: User login  
**Authorization**: Public  
**Rate Limit**: 5 attempts per IP

**Request Body**:
```json
{
  "username": "sale01",
  "password": "password123"
}
```

**Response (200)**:
```json
{
  "id": 1,
  "username": "sale01",
  "fullName": "นาย ขายดี มากมาย",
  "role": "Sale",
  "status": "active"
}
```

**Errors**:
- `401`: Invalid credentials
- `429`: Too many login attempts
- `403`: Account inactive

---

### POST /api/auth/logout
**Description**: User logout  
**Authorization**: Required

**Response (200)**:
```json
{
  "message": "Logged out successfully"
}
```

---

### GET /api/auth/me
**Description**: Get current user info  
**Authorization**: Required

**Response (200)**:
```json
{
  "id": 1,
  "username": "sale01",
  "fullName": "นาย ขายดี มากมาย",
  "role": "Sale",
  "status": "active",
  "lastLogin": "07-02-2026 18:30"
}
```

---

## PO Management APIs

### GET /api/pos
**Description**: List all purchase orders  
**Authorization**: Required  
**Filtering**: Role-based (Sale sees own, Admin sees all except others' Drafts)

**Query Parameters**:
- None (filtering done on frontend)

**Response (200)**:
```json
[
  {
    "id": 1,
    "poNumber": "PO2601001",
    "customerId": "C001",
    "customerName": "บริษัท ลูกค้าดี จำกัด",
    "saleUserId": 2,
    "saleId": "นาย ขายดี มากมาย",
    "amount": 50000.00,
    "status": "Approved",
    "created": "05-01-2026 14:30",
    "createdIso": "2026-01-05T14:30:00+07:00",
    "deliveryDate": "15-01-2026",
    "deliveryDateIso": "2026-01-15",
    "signedFile": null,
    "signedFileUrl": null,
    "signatureImageUrl": null,
    "accessToken": "abc123-def456-ghi789",
    "items": [
      {
        "id": 1,
        "productId": 10,
        "productCode": "PROD001",
        "name": "สินค้า A",
        "qty": 10,
        "price": 5000.00,
        "discount": 0,
        "total": 50000.00,
        "imageUrl": "/uploads/product_images/prod001.jpg"
      }
    ],
    "comments": [
      {
        "id": 1,
        "user": "Admin",
        "text": "Approved",
        "created": "05-01-2026 15:00",
        "createdIso": "2026-01-05T15:00:00+07:00"
      }
    ],
    "canApprove": false,
    "billToAddress": "123 ถนนสุขุมวิท กรุงเทพฯ 10110",
    "shipToAddress": "456 ถนนพระราม 4 กรุงเทพฯ 10110",
    "cancelReason": null,
    "cancelledAt": null,
    "cancelledAtIso": null,
    "cancelledBy": null,
    "cancelRequestBy": null,
    "cancelRequestAt": null,
    "cancelRequestAtIso": null,
    "cancelRequestReason": null,
    "previousStatus": null,
    "signedAt": null,
    "signedAtIso": null
  }
]
```

---

### GET /api/pos/:id
**Description**: Get single purchase order  
**Authorization**: Required + Ownership check

**Response (200)**: Same as single PO object above

**Errors**:
- `403`: Unauthorized to view this PO
- `404`: PO not found

---

### POST /api/pos
**Description**: Create new purchase order  
**Authorization**: Required

**Request Body**:
```json
{
  "customerId": "C001",
  "customerName": "บริษัท ลูกค้าดี จำกัด",
  "deliveryDate": "2026-01-15",
  "status": "Draft",
  "total": 50000.00,
  "items": [
    {
      "productId": 10,
      "name": "สินค้า A",
      "qty": 10,
      "price": 5000.00,
      "discount": 0,
      "total": 50000.00
    }
  ]
}
```

**Response (201)**: Created PO object

**Errors**:
- `400`: Invalid data
- `500`: Database error

---

### PUT /api/pos/:id
**Description**: Update purchase order  
**Authorization**: Required + Ownership check

**Request Body**: Same as POST (partial updates allowed)

**Response (200)**: Updated PO object

**Side Effects**:
- Status changes trigger notifications
- Items are replaced (delete old, create new)
- Comments added for status changes

---

### DELETE /api/pos/:id
**Description**: Delete purchase order  
**Authorization**: Required (Draft: anyone, Others: Admin only)

**Response (204)**: No content

**Errors**:
- `403`: Cannot delete processed PO
- `404`: PO not found

---

## Cancellation APIs

### POST /api/pos/:id/request-cancel
**Description**: Request PO cancellation  
**Authorization**: Required (Creator OR Admin)

**Request Body**:
```json
{
  "reason": "ลูกค้าขอยกเลิกคำสั่งซื้อ"
}
```

**Response (200)**:
```json
{
  "message": "Cancellation request submitted",
  "status": "Cancellation Requested"
}
```

**Side Effects**:
- Status → Cancellation Requested
- Telegram notification to Admins
- Comment added

**Errors**:
- `400`: Only Approved/Completed POs can be cancelled
- `400`: Reason required
- `403`: Unauthorized

---

### POST /api/pos/:id/approve-cancel
**Description**: Approve cancellation request  
**Authorization**: Admin/Sale Admin only

**Request Body**: `{}` (empty)

**Response (200)**:
```json
{
  "message": "PO Cancelled successfully",
  "status": "Cancelled"
}
```

**Side Effects**:
- Status → Cancelled
- Amount deducted from stats
- Telegram notification
- In-app notification to Sale
- Comment added

**Errors**:
- `400`: PO not in Cancellation Requested status
- `403`: Unauthorized

---

### POST /api/pos/:id/reject-cancel
**Description**: Reject cancellation request  
**Authorization**: Admin/Sale Admin only

**Request Body**:
```json
{
  "reason": "ข้อมูลไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง"
}
```

**Response (200)**:
```json
{
  "message": "Cancellation request rejected",
  "status": "Approved"
}
```

**Side Effects**:
- Status reverts to previousStatus
- Telegram notification
- In-app notification to Sale
- Comment added

---

## Customer APIs

### GET /api/customers
**Description**: List all customers  
**Authorization**: Required

**Query Parameters**:
- `q` (optional): Search term (searches code and name)

**Response (200)**:
```json
[
  {
    "id": 1,
    "customerCode": "C001",
    "name": "บริษัท ลูกค้าดี จำกัด",
    "taxId": "1234567890123",
    "status": "active"
  }
]
```

---

### GET /api/customers/:code
**Description**: Get customer details  
**Authorization**: Required

**Response (200)**:
```json
{
  "id": 1,
  "customerCode": "C001",
  "name": "บริษัท ลูกค้าดี จำกัด",
  "taxId": "1234567890123",
  "billToAddress": {
    "line1": "123 ถนนสุขุมวิท",
    "line2": "กรุงเทพฯ 10110",
    "tel": "02-123-4567"
  },
  "shipToAddress": {
    "line1": "456 ถนนพระราม 4",
    "line2": "กรุงเทพฯ 10110",
    "tel": "02-765-4321"
  },
  "status": "active",
  "creditLimit": 100000.00,
  ...
}
```

---

### POST /api/customers
**Description**: Create new customer  
**Authorization**: Admin only

**Request Body**:
```json
{
  "customerCode": "C002",
  "name": "บริษัท ลูกค้าใหม่ จำกัด",
  "taxId": "9876543210987",
  "billToAddress": {
    "line1": "789 ถนนพระราม 3",
    "line2": "กรุงเทพฯ 10120",
    "tel": "02-999-8888"
  },
  "shipToAddress": {
    "line1": "789 ถนนพระราม 3",
    "line2": "กรุงเทพฯ 10120",
    "tel": "02-999-8888"
  }
}
```

**Response (201)**: Created customer object

---

### PUT /api/customers/:code
**Description**: Update customer  
**Authorization**: Admin only

**Request Body**: Same as POST (partial updates allowed)

**Response (200)**: Updated customer object

---

## Product APIs

### GET /api/products
**Description**: List all products  
**Authorization**: Required

**Query Parameters**:
- `q` (optional): Search term (searches code and name)

**Response (200)**:
```json
[
  {
    "id": 1,
    "productCode": "PROD001",
    "name": "สินค้า A",
    "price": 5000.00,
    "inStock": 100,
    "imageUrl": "/uploads/product_images/prod001.jpg",
    "status": "active"
  }
]
```

---

### GET /api/products/:code
**Description**: Get product details  
**Authorization**: Required

**Response (200)**:
```json
{
  "id": 1,
  "productCode": "PROD001",
  "name": "สินค้า A",
  "price": 5000.00,
  "inStock": 100,
  "imageUrl": "/uploads/product_images/prod001.jpg",
  "status": "active",
  "itemGroup": "กลุ่ม A",
  ...
}
```

---

### POST /api/products
**Description**: Create new product  
**Authorization**: Admin only

**Request Body**:
```json
{
  "productCode": "PROD002",
  "name": "สินค้า B",
  "price": 3000.00,
  "inStock": 50
}
```

**Response (201)**: Created product object

---

### PUT /api/products/:code
**Description**: Update product  
**Authorization**: Admin only

**Request Body**: Same as POST (partial updates allowed)

**Response (200)**: Updated product object

---

## User Management APIs

### GET /api/users
**Description**: List all users  
**Authorization**: Admin only

**Response (200)**:
```json
[
  {
    "id": 1,
    "username": "admin",
    "fullName": "ผู้ดูแลระบบ",
    "role": "Administrator",
    "status": "active",
    "lastLogin": "07-02-2026 18:30",
    "createdAt": "01-01-2026 00:00"
  }
]
```

---

### POST /api/users
**Description**: Create new user  
**Authorization**: Admin only

**Request Body**:
```json
{
  "username": "sale02",
  "password": "password123",
  "fullName": "นาง ขายเก่ง สุดๆ",
  "role": "Sale"
}
```

**Response (201)**: Created user object (password excluded)

---

### PUT /api/users/:id
**Description**: Update user  
**Authorization**: Admin only

**Request Body**:
```json
{
  "fullName": "นาง ขายเก่ง มากขึ้น",
  "role": "Sale Admin",
  "status": "active"
}
```

**Response (200)**: Updated user object

---

### DELETE /api/users/:id
**Description**: Delete user  
**Authorization**: Admin only

**Response (204)**: No content

**Errors**:
- `400`: Cannot delete yourself
- `400`: Cannot delete last admin

---

## Notification APIs

### GET /api/notifications
**Description**: Get user notifications  
**Authorization**: Required

**Response (200)**:
```json
[
  {
    "id": 1,
    "message": "PO PO2601001 has been Approved",
    "link_id": 1,
    "is_read": false,
    "created": "05-01-2026 15:00",
    "createdIso": "2026-01-05T15:00:00+07:00"
  }
]
```

---

### POST /api/notifications/:id/read
**Description**: Mark notification as read  
**Authorization**: Required

**Response (200)**:
```json
{
  "message": "Notification marked as read"
}
```

---

### POST /api/notifications/read-all
**Description**: Mark all notifications as read  
**Authorization**: Required

**Response (200)**:
```json
{
  "message": "All notifications marked as read"
}
```

---

## File Upload APIs

### POST /api/products/:code/upload-image
**Description**: Upload product image  
**Authorization**: Admin only

**Request**: `multipart/form-data`
- `file`: Image file (jpg, jpeg, png, gif, webp)

**Response (200)**:
```json
{
  "message": "Image uploaded successfully",
  "imageUrl": "/uploads/product_images/prod001_abc123.jpg"
}
```

**Errors**:
- `400`: No file provided
- `400`: Invalid file type

---

### POST /api/users/:id/upload-signature
**Description**: Upload user signature  
**Authorization**: Admin only

**Request Body**:
```json
{
  "signature": "data:image/png;base64,iVBORw0KGgoAAAANS..."
}
```

**Response (200)**:
```json
{
  "message": "Signature uploaded successfully"
}
```

---

## Customer Portal APIs

### GET /p/:token
**Description**: Customer portal view (HTML page)  
**Authorization**: Public (token-based)

**Response**: HTML page with PO details and signature pad

---

### GET /api/customer/po/:token
**Description**: Get PO by access token  
**Authorization**: Public (token-based)

**Response (200)**: PO object

**Errors**:
- `404`: Invalid or expired token

---

### POST /api/customer/sign/:token
**Description**: Submit customer signature  
**Authorization**: Public (token-based)

**Request Body**:
```json
{
  "signature": "data:image/png;base64,iVBORw0KGgoAAAANS..."
}
```

**Response (200)**:
```json
{
  "success": true,
  "message": "Signature saved successfully"
}
```

**Side Effects**:
- Status → Completed
- Signature image saved
- PDF generated with signature
- Telegram notification
- In-app notification to Sale

---

## Utility APIs

### GET /api/pos/:id/print
**Description**: Generate PDF  
**Authorization**: Required

**Query Parameters**:
- `draft` (optional): "true" for draft watermark

**Response**: PDF file

---

### GET /api/pos/:id/qr
**Description**: Generate QR code  
**Authorization**: Required

**Response**: PNG image (QR code linking to customer portal)

---

### POST /api/pos/:id/comments
**Description**: Add comment to PO  
**Authorization**: Required

**Request Body**:
```json
{
  "text": "กรุณาตรวจสอบจำนวนสินค้าอีกครั้ง"
}
```

**Response (201)**:
```json
{
  "id": 5,
  "user": "Admin",
  "text": "กรุณาตรวจสอบจำนวนสินค้าอีกครั้ง",
  "created": "07-02-2026 18:30",
  "createdIso": "2026-02-07T18:30:00+07:00"
}
```

---

### GET /uploads/:filename
**Description**: Serve uploaded files  
**Authorization**: Public

**Response**: File (PDF, image, etc.)

---

### GET /api/health
**Description**: Health check  
**Authorization**: Public

**Response (200)**:
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2026-02-07T18:30:00+07:00"
}
```

---

## Error Responses

All APIs follow consistent error format:

**400 Bad Request**:
```json
{
  "error": "Invalid data provided"
}
```

**401 Unauthorized**:
```json
{
  "error": "Authentication required"
}
```

**403 Forbidden**:
```json
{
  "error": "Insufficient permissions"
}
```

**404 Not Found**:
```json
{
  "error": "Resource not found"
}
```

**500 Internal Server Error**:
```json
{
  "error": "An unexpected error occurred"
}
```

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-07  
**Author**: Antigravity AI Assistant

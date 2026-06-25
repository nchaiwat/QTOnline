# PO-Online Database Schema & Migration Guide

## 📊 Database Overview

**Database Type**: PostgreSQL  
**ORM**: SQLAlchemy  
**Migration Strategy**: SQL Scripts + SQLAlchemy create_all()

---

## Current Schema (Version 1.7.2)

### Tables Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Database Schema                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  users (7 records typical)                             │
│    ├── PK: id                                          │
│    ├── UNIQUE: username                                │
│    └── Relationships: pos, cancelled_pos, requested_   │
│                                                         │
│  customers (~100-1000 records)                         │
│    ├── PK: id                                          │
│    ├── UNIQUE: customerCode                            │
│    └── Relationships: purchase_orders (viewonly)       │
│                                                         │
│  products (~500-5000 records)                          │
│    ├── PK: id                                          │
│    ├── UNIQUE: productCode                             │
│    └── Relationships: po_items (viewonly)              │
│                                                         │
│  purchase_orders (Main table)                          │
│    ├── PK: id                                          │
│    ├── UNIQUE: poNumber                                │
│    ├── FK: sale_user_id → users.id                    │
│    ├── FK: cancelledBy → users.id                     │
│    ├── FK: cancelRequestBy → users.id                 │
│    ├── FK: customerId → customers.customerCode        │
│    └── Relationships: items, comments, creator, etc.   │
│                                                         │
│  po_items (Line items)                                 │
│    ├── PK: id                                          │
│    ├── FK: po_id → purchase_orders.id (CASCADE)       │
│    ├── FK: productId → products.id                    │
│    └── Relationships: po, product                      │
│                                                         │
│  comments (Audit trail)                                │
│    ├── PK: id                                          │
│    ├── FK: po_id → purchase_orders.id (CASCADE)       │
│    ├── FK: user_id → users.id                         │
│    └── Relationships: po                               │
│                                                         │
│  notifications (In-app alerts)                         │
│    ├── PK: id                                          │
│    ├── FK: user_id → users.id                         │
│    └── Relationships: user                             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Detailed Table Schemas

### 1. users

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(150) NOT NULL,  -- bcrypt hashed
    full_name VARCHAR(200),
    role VARCHAR(50) DEFAULT 'Sale',  -- Sale, Sale Admin, Administrator
    signature_image TEXT,  -- Base64 encoded image
    status VARCHAR(20) DEFAULT 'active',  -- active, inactive
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_status ON users(status);
```

**Constraints**:
- `username` must be unique
- `role` must be one of: Sale, Sale Admin, Administrator
- `status` must be one of: active, inactive

**Sample Data**:
```sql
INSERT INTO users (username, password, full_name, role) VALUES
('admin', '$2b$12$...', 'ผู้ดูแลระบบ', 'Administrator'),
('sale01', '$2b$12$...', 'นาย ขายดี มากมาย', 'Sale');
```

---

### 2. customers

```sql
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    customer_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    tax_id VARCHAR(20),
    bill_to_address JSONB,  -- {line1, line2, tel}
    ship_to_address JSONB,  -- {line1, line2, tel}
    status VARCHAR(20) DEFAULT 'active',
    
    -- SAP Integration Fields (40+ columns)
    card_type VARCHAR(10),
    group_code VARCHAR(50),
    currency VARCHAR(10),
    federal_tax_id VARCHAR(50),
    ...
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_customers_code ON customers(customer_code);
CREATE INDEX idx_customers_name ON customers(name);
CREATE INDEX idx_customers_status ON customers(status);
```

**JSONB Structure for Addresses**:
```json
{
  "line1": "123 ถนนสุขุมวิท",
  "line2": "กรุงเทพฯ 10110",
  "tel": "02-123-4567"
}
```

**Sample Data**:
```sql
INSERT INTO customers (customer_code, name, tax_id, bill_to_address, ship_to_address) VALUES
('C001', 'บริษัท ลูกค้าดี จำกัด', '1234567890123', 
 '{"line1": "123 ถนนสุขุมวิท", "line2": "กรุงเทพฯ 10110", "tel": "02-123-4567"}',
 '{"line1": "456 ถนนพระราม 4", "line2": "กรุงเทพฯ 10110", "tel": "02-765-4321"}');
```

---

### 3. products

```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    product_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    price NUMERIC(18, 2) DEFAULT 0,
    in_stock INTEGER DEFAULT 0,
    image_url TEXT,
    status VARCHAR(20) DEFAULT 'active',
    
    -- SAP Integration Fields (40+ columns)
    item_group VARCHAR(100),
    manage_batch_no VARCHAR(10),
    serial_no_management VARCHAR(10),
    ...
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_products_code ON products(product_code);
CREATE INDEX idx_products_name ON products(name);
CREATE INDEX idx_products_status ON products(status);
```

**Sample Data**:
```sql
INSERT INTO products (product_code, name, price, in_stock, image_url) VALUES
('PROD001', 'สินค้า A', 5000.00, 100, '/uploads/product_images/prod001.jpg');
```

---

### 4. purchase_orders (Core Table)

```sql
CREATE TABLE purchase_orders (
    id SERIAL PRIMARY KEY,
    po_number VARCHAR(50) UNIQUE NOT NULL,  -- Format: POYYMM0001
    customer_id VARCHAR(50),  -- FK to customers.customer_code
    customer_name VARCHAR(200),
    sale_user_id INTEGER REFERENCES users(id),
    sale_id VARCHAR(200),  -- Denormalized sale name
    amount NUMERIC(18, 2) DEFAULT 0,
    status VARCHAR(50) DEFAULT 'Draft',
    created TIMESTAMP DEFAULT NOW(),
    delivery_date DATE,
    
    -- Digital Signature
    signed_file TEXT,  -- PDF filename
    signed_file_url TEXT,
    signature_image TEXT,  -- Customer signature filename
    signed_at TIMESTAMP,
    
    -- Customer Portal
    access_token VARCHAR(100) UNIQUE,  -- UUID for public access
    
    -- Cancellation Info (Original)
    cancel_reason TEXT,
    cancelled_at TIMESTAMP,
    cancelled_by INTEGER REFERENCES users(id),
    
    -- Cancellation Request Info (NEW in v1.7.2)
    cancel_request_by INTEGER REFERENCES users(id),
    cancel_request_at TIMESTAMP,
    cancel_request_reason TEXT,
    previous_status VARCHAR(50)
);

CREATE INDEX idx_po_number ON purchase_orders(po_number);
CREATE INDEX idx_po_customer ON purchase_orders(customer_id);
CREATE INDEX idx_po_sale ON purchase_orders(sale_user_id);
CREATE INDEX idx_po_status ON purchase_orders(status);
CREATE INDEX idx_po_created ON purchase_orders(created);
CREATE INDEX idx_po_token ON purchase_orders(access_token);
```

**Status Values**:
- `Draft`: Initial creation
- `Pending Review`: Submitted for approval
- `Changes Requested`: Admin requested changes
- `Approved`: Approved by admin
- `Completed`: Customer signed
- `Cancellation Requested`: Pending cancellation approval
- `Cancelled`: Finalized cancellation

**Sample Data**:
```sql
INSERT INTO purchase_orders (
    po_number, customer_id, customer_name, sale_user_id, 
    sale_id, amount, status, access_token
) VALUES (
    'PO2601001', 'C001', 'บริษัท ลูกค้าดี จำกัด', 2,
    'นาย ขายดี มากมาย', 50000.00, 'Approved', 
    'abc123-def456-ghi789'
);
```

---

### 5. po_items

```sql
CREATE TABLE po_items (
    id SERIAL PRIMARY KEY,
    po_id INTEGER REFERENCES purchase_orders(id) ON DELETE CASCADE,
    product_id INTEGER,  -- FK to products.id (soft reference)
    product_code VARCHAR(50),
    name VARCHAR(255),
    qty INTEGER DEFAULT 1,
    price NUMERIC(18, 2) DEFAULT 0,
    discount NUMERIC(5, 2) DEFAULT 0,  -- Percentage
    total NUMERIC(18, 2) DEFAULT 0,
    image_url TEXT
);

CREATE INDEX idx_po_items_po ON po_items(po_id);
CREATE INDEX idx_po_items_product ON po_items(product_id);
```

**Calculation**:
```
total = (price * qty) * (1 - discount/100)
```

**Sample Data**:
```sql
INSERT INTO po_items (po_id, product_id, product_code, name, qty, price, discount, total) VALUES
(1, 10, 'PROD001', 'สินค้า A', 10, 5000.00, 0, 50000.00);
```

---

### 6. comments

```sql
CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    po_id INTEGER REFERENCES purchase_orders(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id),
    user VARCHAR(150),  -- Denormalized user name
    text TEXT NOT NULL,
    created TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_comments_po ON comments(po_id);
CREATE INDEX idx_comments_created ON comments(created);
```

**Use Cases**:
- Status change logs
- Admin feedback
- Cancellation reasons
- General communication

**Sample Data**:
```sql
INSERT INTO comments (po_id, user_id, user, text) VALUES
(1, 1, 'Admin', 'Approved - ตรวจสอบแล้วเรียบร้อย');
```

---

### 7. notifications

```sql
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    message TEXT NOT NULL,
    link_id INTEGER,  -- PO ID for navigation
    is_read BOOLEAN DEFAULT FALSE,
    created TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_read ON notifications(is_read);
CREATE INDEX idx_notifications_created ON notifications(created);
```

**Sample Data**:
```sql
INSERT INTO notifications (user_id, message, link_id) VALUES
(2, 'PO PO2601001 has been Approved', 1);
```

---

## Relationships Diagram

```
users (1) ──────< (N) purchase_orders [creator]
users (1) ──────< (N) purchase_orders [canceller]
users (1) ──────< (N) purchase_orders [requester]
users (1) ──────< (N) notifications

customers (1) ──────< (N) purchase_orders [viewonly]

products (1) ──────< (N) po_items [viewonly]

purchase_orders (1) ──────< (N) po_items [CASCADE DELETE]
purchase_orders (1) ──────< (N) comments [CASCADE DELETE]
```

---

## Migration History

### Migration 1: Initial Schema (v1.0.0)
**File**: Auto-created by SQLAlchemy  
**Date**: 2025-11-01

Created tables:
- users
- customers
- products
- purchase_orders
- po_items
- comments
- notifications

---

### Migration 2: Cancellation Request Fields (v1.7.2)
**File**: `migrate_cancel_request.sql`  
**Date**: 2026-02-06

```sql
-- Add cancellation request tracking fields
ALTER TABLE purchase_orders 
ADD COLUMN cancel_request_by INTEGER REFERENCES users(id),
ADD COLUMN cancel_request_at TIMESTAMP,
ADD COLUMN cancel_request_reason TEXT,
ADD COLUMN previous_status VARCHAR(50);

-- Add indexes for performance
CREATE INDEX idx_po_cancel_request_by ON purchase_orders(cancel_request_by);
```

**Purpose**: Support multi-step cancellation workflow

**How to Apply**:
```bash
# Connect to database
docker exec -it po-online-db psql -U myuser -d po_online

# Run migration
\i migrate_cancel_request.sql

# Verify
\d purchase_orders
```

---

## How to Create New Migration

### Step 1: Modify Model
Edit `models.py`:
```python
class PurchaseOrder(db.Model):
    # Add new field
    new_field = db.Column(db.String(100))
```

### Step 2: Create SQL Migration Script
Create `migrate_new_field.sql`:
```sql
-- Migration: Add new_field to purchase_orders
-- Date: 2026-02-XX
-- Author: Your Name

ALTER TABLE purchase_orders 
ADD COLUMN new_field VARCHAR(100);

-- Add index if needed
CREATE INDEX idx_po_new_field ON purchase_orders(new_field);

-- Update existing records if needed
UPDATE purchase_orders SET new_field = 'default_value' WHERE new_field IS NULL;
```

### Step 3: Apply Migration
```bash
# Development (Docker)
docker exec -it po-online-db psql -U myuser -d po_online -f migrate_new_field.sql

# Production (VPS)
psql -U myuser -d po_online -f migrate_new_field.sql
```

### Step 4: Update to_dict() Method
```python
def to_dict(self):
    return {
        ...
        'newField': self.new_field
    }
```

### Step 5: Restart Application
```bash
# Docker
docker-compose restart web

# VPS
sudo systemctl restart po-online
```

---

## Common Migration Scenarios

### Adding a Column
```sql
ALTER TABLE table_name 
ADD COLUMN column_name TYPE DEFAULT value;
```

### Modifying a Column
```sql
ALTER TABLE table_name 
ALTER COLUMN column_name TYPE new_type;
```

### Adding an Index
```sql
CREATE INDEX idx_name ON table_name(column_name);
```

### Adding a Foreign Key
```sql
ALTER TABLE table_name 
ADD CONSTRAINT fk_name 
FOREIGN KEY (column_name) 
REFERENCES other_table(id);
```

### Dropping a Column
```sql
ALTER TABLE table_name 
DROP COLUMN column_name;
```

---

## Database Backup & Restore

### Backup
```bash
# Full database backup
docker exec po-online-db pg_dump -U myuser po_online > backup_$(date +%Y%m%d).sql

# Compressed backup
docker exec po-online-db pg_dump -U myuser po_online | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Restore
```bash
# From SQL file
docker exec -i po-online-db psql -U myuser po_online < backup_20260207.sql

# From compressed file
gunzip -c backup_20260207.sql.gz | docker exec -i po-online-db psql -U myuser po_online
```

---

## Performance Optimization

### Indexes
Current indexes are optimized for:
- Unique constraints (username, customerCode, productCode, poNumber)
- Foreign keys (sale_user_id, customer_id, po_id)
- Frequent queries (status, created, is_read)

### Query Optimization
Use eager loading to prevent N+1 queries:
```python
PurchaseOrder.query.options(
    joinedload(PurchaseOrder.creator),
    joinedload(PurchaseOrder.items).joinedload(POItem.product)
).all()
```

### JSONB Indexes
For customers and products with JSONB fields:
```sql
CREATE INDEX idx_customers_bill_address ON customers USING GIN (bill_to_address);
```

---

## Data Integrity Rules

1. **Cascade Deletes**: 
   - Deleting a PO deletes all items and comments
   - Deleting a user does NOT delete their POs (FK set to NULL)

2. **Soft Deletes**:
   - Customers and Products use `status = 'inactive'`
   - Never hard delete if referenced by POs

3. **Denormalization**:
   - `customer_name` and `sale_id` stored in POs for historical accuracy
   - Even if customer/user is deleted, PO retains the name

4. **Unique Constraints**:
   - `poNumber` must be unique (enforced by database)
   - `accessToken` must be unique (enforced by database)

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-07  
**Database Version**: 1.7.2

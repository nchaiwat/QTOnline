import os
import sys
import csv
import io
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal, InvalidOperation
from flask_login import UserMixin, current_user
from extensions import db
from sqlalchemy import or_, text, func
from sqlalchemy.orm import joinedload, foreign, remote, contains_eager, subqueryload

from utils import (
    now_bangkok,
    ensure_bangkok,
    BANGKOK_TZ,
    _parse_decimal,
    _parse_bool,
    _decimal_to_str,
    _parse_date,
    _clean,
    _date_to_iso,
)

# --- CSV Columns ---
CUSTOMER_CSV_COLUMNS = [
    "BP Code",
    "BP Name",
    "Remarks",
    "Account Balance",
    "Foreign Name",
    "BP Currency",
    "Accounts Receivable/Payable",
    "Group Code",
    "Price List No.",
    "Alias Name",
    "Federal Tax ID",
    "Bill-to Building/Floor/Room",
    "Bill-to Street",
    "Bill-to City",
    "Bill-to County",
    "Bill-to Country",
    "Bill-to Block",
    "Bill-to Street No.",
    "Bill-to Zip Code",
    "Global Location Number",
    "Payment Terms Code",
    "Ship to Building/Floor/Room",
    "Ship-to Street",
    "Ship-to City",
    "Ship-to County",
    "Ship-to Country",
    "Ship-to Block",
    "Ship-to Street No.",
    "Ship-to Zip Code",
    "Creation Date",
    "Inactive",
    "Tax Code",
    "BP Branch",
    "Tax Group",
    "Telephone 1",
    "Telephone 2",
    "Sales Employee Code",
    "Self-Employed",
    "Mobile Phone",
    "Shipping Type",
    "Credit Limit",
    "Update Full Time",
    "Remark 1",
]

PRODUCT_CSV_COLUMNS = [
    "Item No.",
    "Item Description",
    "Item Group",
    "Recommended Price (Ex.VAT)",
    "Item Cost (Ex.VAT)",
    "In Stock",
    "Inactive",
]

MOCK_CUSTOMER_DATA = {
    "Customer A": {
        "name": "ลูกค้าเจ้าที่ 1 (Mock Co., Ltd.)",
        "address_line1": "123 Mockingbird Lane",
        "address_line2": "Bangkok 10110",
        "tel": "081-000-1111",
        "tax_id": "1234567890123",
    },
    "Customer B": {
        "name": "Dynasty (Test Inc.)",
        "address_line1": "456 Test Road",
        "address_line2": "Samut Prakan 10540",
        "tel": "082-000-2222",
        "tax_id": "0987654321098",
    },
    "Customer C": {
        "name": "Home Pro (Demo PLC)",
        "address_line1": "789 Demo Street",
        "address_line2": "Nonthaburi 11110",
        "tel": "083-000-3333",
        "tax_id": "5556667778889",
    },
    "default": {
        "name": "Unknown Customer",
        "address_line1": "N/A",
        "address_line2": "N/A",
        "tel": "N/A",
        "tax_id": "N/A",
    },
}

COMPANY_DATA = {
    "name": "บริษัท วินโดว์ เอเชีย จำกัด (มหาชน) สำนักงานใหญ่",
    "address_line1": "15/1 หมู่1 ถ.พระราม2 ต.บางน้ำจืด",
    "address_line2": "อ.เมือง จ.สมุทรสาคร 74000",
    "tax_id": "Tax ID: 0107565000271",
    "tel": "Tel: 02-123-1734",
    "fax": "02-123-1733",
    "logo_url": "https://windowasia.com/wp-content/uploads/2022/03/logo.png",
    "vendor": {
        "name": "บริษัท วินโดว์ เอเชีย จำกัด (มหาชน)",
        "address_line1": "15/1 หมู่1 ถ.พระราม2 ต.บางน้ำจืด",
        "address_line2": "อ.เมือง จ.สมุทรสาคร 74000",
        "tel": "02-123-1734",
        "fax": "02-123-1733",
        "tax_id": "Tax ID: 0107565000271",
    },
}


def build_product_image_url(raw_value: str | None) -> str | None:
    if not raw_value:
        return None
    value = str(raw_value).strip()
    if not value:
        return None
    if value.startswith(("http://", "https://")):
        return value
    filename = value.split("/")[-1]
    return f"/product-images/{filename}"


# --- Models ---
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    fullName = db.Column(db.String(150))
    target_amount = db.Column(db.Float, default=0.0)
    phoneNumber = db.Column(db.String(50))
    signature_image = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="active")
    lastLogin = db.Column(db.DateTime)
    createdAt = db.Column(db.DateTime, default=now_bangkok)

    def to_dict(self):
        created_local = ensure_bangkok(self.createdAt)
        last_login_local = ensure_bangkok(self.lastLogin)
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "fullName": self.fullName,
            "targetAmount": self.target_amount,
            "phoneNumber": self.phoneNumber or "",
            "signatureImage": self.signature_image,
            "status": getattr(self, "status", "active"),
            "createdAt": (
                created_local.strftime("%d-%m-%Y %H:%M") if created_local else "-"
            ),
            "lastLogin": (
                last_login_local.strftime("%d-%m-%Y %H:%M") if last_login_local else "-"
            ),
        }


class Customer(db.Model):
    __tablename__ = "customers"
    id = db.Column(db.Integer, primary_key=True)
    customerCode = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    remarks = db.Column(db.String(255))
    accountBalance = db.Column(db.Numeric(18, 2))
    foreignName = db.Column(db.String(200))
    currency = db.Column(db.String(50))
    arAccount = db.Column(db.String(200))
    groupCode = db.Column(db.String(100))
    priceListNo = db.Column(db.String(100))
    aliasName = db.Column(db.String(200))
    taxId = db.Column(db.String(50))
    billToBuilding = db.Column(db.String(200))
    billToStreet = db.Column(db.String(200))
    billToCity = db.Column(db.String(200))
    billToCounty = db.Column(db.String(200))
    billToCountry = db.Column(db.String(200))
    billToZipCode = db.Column(db.String(20))
    paymentTermsCode = db.Column(db.String(100))
    shipToBuilding = db.Column(db.String(200))
    shipToStreet = db.Column(db.String(200))
    shipToCity = db.Column(db.String(200))
    shipToCounty = db.Column(db.String(200))
    shipToCountry = db.Column(db.String(200))
    shipToZipCode = db.Column(db.String(20))
    creationDate = db.Column(db.Date)
    inactive = db.Column(db.Boolean, default=False)
    taxCode = db.Column(db.String(50))
    branch = db.Column(db.String(100))
    taxGroup = db.Column(db.String(100))
    telephone1 = db.Column(db.String(50))
    telephone2 = db.Column(db.String(50))
    salesEmployeeCode = db.Column(db.String(100))
    selfEmployed = db.Column(db.Boolean)
    mobilePhone = db.Column(db.String(50))
    shippingType = db.Column(db.String(100))
    creditLimit = db.Column(db.Numeric(18, 2))
    updateFullTime = db.Column(db.String(50))
    remark1 = db.Column(db.String(255))

    def to_dict(self):
        return {
            "id": self.id,
            "customerCode": self.customerCode,
            "name": self.name,
            "remarks": self.remarks,
            "billTo": {
                "building": self.billToBuilding,
                "street": self.billToStreet,
                "city": self.billToCity,
                "province": self.billToCounty,
                "country": self.billToCountry,
                "zipCode": self.billToZipCode,
            },
            "shipTo": {
                "building": self.shipToBuilding,
                "street": self.shipToStreet,
                "city": self.shipToCity,
                "province": self.shipToCounty,
                "country": self.shipToCountry,
                "zipCode": self.shipToZipCode,
            },
            "currency": self.currency,
            "paymentTermsCode": self.paymentTermsCode,
            "accountBalance": _decimal_to_str(self.accountBalance),
            "creditLimit": _decimal_to_str(self.creditLimit),
            "branch": self.branch,
            "taxGroup": self.taxGroup,
            "taxCode": self.taxCode,
            "telephone1": self.telephone1,
            "telephone2": self.telephone2,
            "mobilePhone": self.mobilePhone,
            "taxId": self.taxId,
            "remark": self.remark1,
            "inactive": self.inactive,
        }

    def to_detail_dict(self):
        d = self.to_dict()
        d.update(
            {
                "foreignName": self.foreignName,
                "arAccount": self.arAccount,
                "groupCode": self.groupCode,
                "priceListNo": self.priceListNo,
                "aliasName": self.aliasName,
                "creationDate": _date_to_iso(self.creationDate),
                "salesEmployeeCode": self.salesEmployeeCode,
                "selfEmployed": self.selfEmployed,
                "shippingType": self.shippingType,
                "updateFullTime": self.updateFullTime,
                "billToBuilding": self.billToBuilding,
                "billToStreet": self.billToStreet,
                "billToCity": self.billToCity,
                "billToProvince": self.billToCounty,
                "billToCountry": self.billToCountry,
                "billToZipCode": self.billToZipCode,
                "shipToBuilding": self.shipToBuilding,
                "shipToStreet": self.shipToStreet,
                "shipToCity": self.shipToCity,
                "shipToProvince": self.shipToCounty,
                "shipToCountry": self.shipToCountry,
                "shipToZipCode": self.shipToZipCode,
            }
        )
        return d


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    productCode = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    imageUrl = db.Column(db.String(500))
    unitPrice = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    inStock = db.Column(db.Numeric(18, 2))
    itemGroup = db.Column(db.String(200))
    inactive = db.Column(db.Boolean, default=False)
    itemCost = db.Column(db.Numeric(18, 2))

    def to_dict(self):
        try:
            # If imageUrl is empty, use the default pattern based on productCode
            img_url = self.imageUrl
            if not img_url:
                img_url = f"/product-images/{self.productCode}.jpg"

            return {
                "id": self.id,
                "productCode": self.productCode or "",
                "code": self.productCode or "",
                "name": self.name or "",
                "imageUrl": (
                    build_product_image_url(img_url) if img_url else None
                ),
                "unitPrice": (
                    float(self.unitPrice) if self.unitPrice is not None else 0.0
                ),
                "price": float(self.unitPrice) if self.unitPrice is not None else 0.0,
                "itemGroup": self.itemGroup or "",
                "itemCost": (
                    float(self.itemCost) if self.itemCost is not None else 0.0
                ),
                "inactive": bool(self.inactive),
                "inStock": _decimal_to_str(self.inStock),
            }
        except Exception as e:
            return {
                "id": self.id,
                "productCode": str(self.productCode),
                "code": str(self.productCode),
                "name": str(self.name),
                "error": str(e),
            }

    def to_detail_dict(self):
        return self.to_dict()


class PurchaseOrder(db.Model):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        db.Index("idx_po_sale_created", "sale_user_id", "created"),
    )
    id = db.Column(db.Integer, primary_key=True)
    poNumber = db.Column(db.String(50), unique=True, nullable=False, index=True)
    customerId = db.Column(db.String(50), nullable=False, index=True)
    customerName = db.Column(db.String(255))
    poShipTo = db.Column(db.Text)  # Manually editable ship to
    sale_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    saleId = db.Column(db.String(150))
    amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default="Draft", index=True)
    created = db.Column(db.DateTime, default=now_bangkok, index=True)
    updatedAt = db.Column(db.DateTime, default=now_bangkok, onupdate=now_bangkok, index=True)
    deliveryDate = db.Column(db.Date)
    signedFile = db.Column(db.String(255))
    signedFileUrl = db.Column(db.Text)
    signatureImage = db.Column(db.String(255))
    accessToken = db.Column(db.String(100), unique=True)
    signedAt = db.Column(db.DateTime)

    # NEW: Multi-step Discount
    discount_percent_1 = db.Column(db.Float, default=0.0)
    discount_percent_2 = db.Column(db.Float, default=0.0)

    # Cancellation Info
    cancelReason = db.Column(db.Text)
    cancelledAt = db.Column(db.DateTime)
    cancelledBy = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # NEW: Cancellation Request Info
    cancelRequestBy = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    cancelRequestAt = db.Column(db.DateTime)
    cancelRequestReason = db.Column(db.Text)
    previousStatus = db.Column(db.String(50))  # To revert if rejected

    # NEW: Customer Location/Map Document
    customerLocationFile = db.Column(db.Text)
    customerLocationFileUrl = db.Column(db.Text)
    customerLocationUploadedAt = db.Column(db.DateTime)
    customerLocationUploadedBy = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True
    )

    # NEW: Customer PO Document
    customerPoFile = db.Column(db.Text)
    customerPoFileUrl = db.Column(db.Text)
    customerPoUploadedAt = db.Column(db.DateTime)
    customerPoUploadedBy = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True
    )

    items = db.relationship(
        "POItem", backref="po", lazy=True, cascade="all, delete-orphan"
    )
    comments = db.relationship(
        "Comment", backref="po", lazy=True, cascade="all, delete-orphan"
    )
    creator = db.relationship("User", backref="pos", foreign_keys=[sale_user_id])
    canceller = db.relationship(
        "User", foreign_keys=[cancelledBy], backref="cancelled_pos"
    )
    requester = db.relationship(
        "User", foreign_keys=[cancelRequestBy], backref="requested_cancel_pos"
    )
    location_uploader = db.relationship(
        "User", foreign_keys=[customerLocationUploadedBy], backref="location_uploads"
    )
    po_uploader = db.relationship(
        "User", foreign_keys=[customerPoUploadedBy], backref="po_uploads"
    )
    customer_rel = db.relationship(
        "Customer",
        primaryjoin="foreign(PurchaseOrder.customerId) == remote(Customer.customerCode)",
        viewonly=True,
        uselist=False,
    )

    def get_customer_name(self):
        """Reliably get the customer name from relationship or stored field."""
        if self.customer_rel and self.customer_rel.name:
            return self.customer_rel.name

        # Fallback to stored name if it's not just the ID
        stored_name = self.customerName
        c_id = self.customerId
        if stored_name and str(stored_name).strip() != str(c_id).strip():
            return stored_name

        return self.customerId or "Unknown"

    def to_dict(self):
        sale_name = (
            self.creator.fullName if self.creator else (self.saleId or "Unknown")
        )
        stored_name = self.customerName
        s_name_str = str(stored_name).strip() if stored_name else ""
        c_id_str = str(self.customerId).strip() if self.customerId else ""
        is_bad_stored_name = (s_name_str == c_id_str) or (not s_name_str)

        cust_name = None
        bill_to_address = ""
        ship_to_address = ""
        tax_id = None

        if self.customer_rel:
            cust_name = self.customer_rel.name
            tax_id = self.customer_rel.taxId

            # Deduplicate: if building equals name, avoid showing it again in address
            b_build = self.customer_rel.billToBuilding
            if b_build and cust_name and b_build.strip() == cust_name.strip():
                b_build = None

            bill_parts = [
                b_build,
                self.customer_rel.billToStreet,
                self.customer_rel.billToCity,
                self.customer_rel.billToCounty,
                self.customer_rel.billToCountry,
                self.customer_rel.billToZipCode,
            ]
            bill_to_address = " ".join(filter(None, bill_parts))

            s_build = self.customer_rel.shipToBuilding
            if s_build and cust_name and s_build.strip() == cust_name.strip():
                s_build = None

            ship_parts = [
                s_build,
                self.customer_rel.shipToStreet,
                self.customer_rel.shipToCity,
                self.customer_rel.shipToCounty,
                self.customer_rel.shipToCountry,
                self.customer_rel.shipToZipCode,
            ]
            ship_temp = " ".join(filter(None, ship_parts))
            ship_to_address = ship_temp if ship_temp.strip() else bill_to_address

        if not cust_name and stored_name and not is_bad_stored_name:
            cust_name = stored_name

        if self.customerId in MOCK_CUSTOMER_DATA:
            mock = MOCK_CUSTOMER_DATA[self.customerId]
            if not cust_name:
                cust_name = mock["name"]
            if not tax_id:
                tax_id = mock.get("tax_id")
            if not bill_to_address:
                bill_to_address = (
                    f"{mock.get('address_line1', '')} {mock.get('address_line2', '')}"
                )
            if not ship_to_address:
                ship_to_address = bill_to_address

        if not cust_name:
            cust_name = stored_name if stored_name else self.customerId

        created_dt = ensure_bangkok(self.created)

        delivery_date_display = None
        delivery_date_slash = None
        delivery_date_iso = None
        if self.deliveryDate:
            try:
                date_obj = self.deliveryDate
                if isinstance(date_obj, str):
                    date_obj = _parse_date(date_obj)
                if isinstance(date_obj, (date, datetime)):
                    delivery_date_display = date_obj.strftime("%d-%m-%Y")
                    delivery_date_slash = date_obj.strftime("%d/%m/%Y")
                    delivery_date_iso = date_obj.strftime("%Y-%m-%d")
            except:
                pass

        can_approve = False
        if current_user.is_authenticated:
            if (
                current_user.role in ["Administrator", "Sale Admin"]
                and self.status == "Pending Review"
            ):
                can_approve = True

        cancelled_at_dt = ensure_bangkok(self.cancelledAt)

        updated_dt = ensure_bangkok(self.updatedAt) if self.updatedAt else created_dt

        res = {
            "id": self.id,
            "poNumber": self.poNumber,
            "customerId": self.customerId,
            "customerName": cust_name,
            "taxId": tax_id,
            "saleUserId": self.sale_user_id,
            "saleId": sale_name,
            "amount": self.amount,
            "status": self.status,
            "created": created_dt.strftime("%d-%m-%Y") if created_dt else None,
            "createdIso": created_dt.isoformat() if created_dt else None,
            "updatedAt": updated_dt.strftime("%d-%m-%Y %H:%M") if updated_dt else None,
            "updatedAtIso": updated_dt.isoformat() if updated_dt else None,
            "deliveryDate": delivery_date_display,
            "deliveryDateIso": delivery_date_iso,
            "deliveryDateSlash": delivery_date_slash,
            "signedFile": self.signedFile,
            "signedFileUrl": f"/uploads/{self.signedFile}" if self.signedFile else None,
            "signatureImageUrl": (
                f"/uploads/{self.signatureImage}" if self.signatureImage else None
            ),
            "accessToken": self.accessToken,
            "items": [item.to_dict() for item in self.items],
            "comments": [comment.to_dict() for comment in self.comments],
            "canApprove": can_approve,
            "billToAddress": bill_to_address or "N/A",
            "shipToAddress": self.poShipTo if self.poShipTo else (ship_to_address or "N/A"),
            "cancelReason": self.cancelReason,
            "cancelledAt": (
                cancelled_at_dt.strftime("%d-%m-%Y %H:%M") if cancelled_at_dt else None
            ),
            "cancelledAtIso": cancelled_at_dt.isoformat() if cancelled_at_dt else None,
            "cancelledBy": self.canceller.fullName if self.canceller else None,
            "cancelRequestBy": self.requester.fullName if self.requester else None,
            "cancelRequestAt": (
                ensure_bangkok(self.cancelRequestAt).strftime("%d-%m-%Y %H:%M")
                if self.cancelRequestAt
                else None
            ),
            "cancelRequestAtIso": (
                ensure_bangkok(self.cancelRequestAt).isoformat()
                if self.cancelRequestAt
                else None
            ),
            "cancelRequestReason": self.cancelRequestReason,
            "previousStatus": self.previousStatus,
            "signedAt": (
                ensure_bangkok(self.signedAt).strftime("%d-%m-%Y %H:%M")
                if self.signedAt
                else None
            ),
            "signedAtIso": (
                ensure_bangkok(self.signedAt).isoformat() if self.signedAt else None
            ),
            # NEW: Customer Documents
            "customerLocationFile": self.customerLocationFile,
            "customerLocationFileUrl": self.customerLocationFileUrl,
            "customerLocationUploadedAt": (
                ensure_bangkok(self.customerLocationUploadedAt).strftime(
                    "%d-%m-%Y %H:%M"
                )
                if self.customerLocationUploadedAt
                else None
            ),
            "customerLocationUploadedBy": (
                self.location_uploader.fullName if self.location_uploader else None
            ),
            "customerPoFile": self.customerPoFile,
            "customerPoFileUrl": self.customerPoFileUrl,
            "customerPoUploadedAt": (
                ensure_bangkok(self.customerPoUploadedAt).strftime("%d-%m-%Y %H:%M")
                if self.customerPoUploadedAt
                else None
            ),
            "customerPoUploadedBy": (
                self.po_uploader.fullName if self.po_uploader else None
            ),
            # NEW: Calculated Breakdown
            "discountPercent1": self.discount_percent_1 or 0.0,
            "discountPercent2": self.discount_percent_2 or 0.0,
        }

        # Calculate values dynamically (VAT-exclusive logic)
        subtotal = sum(item.total for item in self.items)
        
        # 1. Discount Step 1
        disc1_amount = subtotal * ((self.discount_percent_1 or 0.0) / 100.0)
        total_after_1 = subtotal - disc1_amount

        # 2. Discount Step 2
        disc2_amount = total_after_1 * ((self.discount_percent_2 or 0.0) / 100.0)
        total_after_2 = total_after_1 - disc2_amount

        # 3. VAT 7%
        vat_amount = total_after_2 * 0.07
        grand_total = total_after_2 + vat_amount

        res.update({
            "subtotal": subtotal,
            "discountAmount1": disc1_amount,
            "totalAfterDiscount1": total_after_1,
            "discountAmount2": disc2_amount,
            "totalAfterDiscount2": total_after_2,
            "vatAmount": vat_amount,
            "grandTotal": grand_total,
            "amount": grand_total # Main field
        })
        return res

    def to_summary_dict(self):
        sale_name = (
            self.creator.fullName if self.creator else (self.saleId or "Unknown")
        )
        cust_name = self.get_customer_name()
        created_dt = ensure_bangkok(self.created)
        updated_dt = ensure_bangkok(self.updatedAt) if self.updatedAt else created_dt

        delivery_date_display = None
        delivery_date_iso = None
        if self.deliveryDate:
            try:
                d_obj = self.deliveryDate
                if isinstance(d_obj, str):
                    d_obj = _parse_date(d_obj)
                if isinstance(d_obj, (date, datetime)):
                    delivery_date_display = d_obj.strftime("%d-%m-%Y")
                    delivery_date_iso = d_obj.strftime("%Y-%m-%d")
            except:
                pass

        return {
            "id": self.id,
            "poNumber": self.poNumber,
            "customerId": self.customerId,
            "customerName": cust_name,
            "saleUserId": self.sale_user_id,
            "saleId": sale_name,
            "amount": self.amount or 0.0,
            "status": self.status,
            "created": created_dt.strftime("%d-%m-%Y") if created_dt else None,
            "createdIso": created_dt.isoformat() if created_dt else None,
            "updatedAt": updated_dt.strftime("%d-%m-%Y %H:%M") if updated_dt else None,
            "updatedAtIso": updated_dt.isoformat() if updated_dt else None,
            "deliveryDate": delivery_date_display,
            "deliveryDateIso": delivery_date_iso,
            "accessToken": self.accessToken,
        }



class POItem(db.Model):
    __tablename__ = "po_items"
    id = db.Column(db.Integer, primary_key=True)
    po_id = db.Column(db.Integer, db.ForeignKey("purchase_orders.id"), nullable=False)
    productId = db.Column(db.Integer)
    productCode = db.Column(db.String(50))
    name = db.Column(db.String(255))
    qty = db.Column(db.Integer, default=1)
    price = db.Column(db.Float, default=0.0)
    recommendedPrice = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    imageUrl = db.Column(db.Text)
    product = db.relationship(
        "Product",
        primaryjoin="POItem.productId == Product.id",
        foreign_keys=[productId],
        viewonly=True,
    )

    @property
    def resolved_image_url(self):
        code = (self.productCode or "").strip()
        img = self.imageUrl
        if self.product:
            if not code:
                code = (self.product.productCode or "").strip()
            if not img:
                img = self.product.imageUrl
        if not img and code:
            img = f"/product-images/{code}.jpg"
        return build_product_image_url(img)

    def to_dict(self):
        code = (self.productCode or "").strip()
        img = self.imageUrl
        if self.product:
            if not code:
                code = (self.product.productCode or "").strip()
            if not img:
                img = self.product.imageUrl
        display_name = (self.name or "").strip()
        if code and display_name.startswith(code):
            display_name = display_name[len(code) :].lstrip("-").strip() or display_name
        
        # Fallback to default product image path if no image URL is found
        if not img and code:
            img = f"/product-images/{code}.jpg"

        return {
            "id": self.id,
            "productId": self.productId,
            "productCode": code,
            "name": display_name,
            "qty": self.qty,
            "price": self.price,
            "recommendedPrice": self.recommendedPrice or 0.0,
            "discount": self.discount or 0.0,
            "total": self.total,
            "imageUrl": build_product_image_url(img),
        }


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    po_id = db.Column(db.Integer, db.ForeignKey("purchase_orders.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user = db.Column(db.String(150))
    text = db.Column(db.Text, nullable=False)
    created = db.Column(db.DateTime, default=now_bangkok)

    def to_dict(self):
        local = ensure_bangkok(self.created)
        return {
            "user": self.user,
            "text": self.text,
            "created_at": local.strftime("%d-%m-%Y %H:%M") if local else "",
        }


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    text = db.Column(db.String(255), nullable=False)
    link_id = db.Column(db.Integer, nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created = db.Column(db.DateTime, default=now_bangkok)

    def to_dict(self):
        local = ensure_bangkok(self.created)
        return {
            "id": self.id,
            "text": self.text,
            "linkId": self.link_id,
            "isRead": self.is_read,
            "createdAt": local.strftime("%d-%m-%Y %H:%M") if local else "",
            "createdIso": local.isoformat() if local else None,
        }


def create_notification(user_id, text, link_id=None):
    try:
        notif = Notification(user_id=user_id, text=text, link_id=link_id)
        db.session.add(notif)
    except Exception as e:
        print(f"Error creating notification: {e}")


# --- Centralized Identity Management (CIAM) & Audit Models ---
class CiamSetting(db.Model):
    __tablename__ = "ciam_settings"
    id = db.Column(db.Integer, primary_key=True)
    is_enabled = db.Column(db.Boolean, default=True, nullable=False)
    api_key = db.Column(db.String(100), nullable=False)
    allowed_ips = db.Column(db.Text, default="157.173.219.153, 192.168.12.11, 127.0.0.1")
    default_role = db.Column(db.String(50), default="Sale")
    updated_at = db.Column(db.DateTime, default=now_bangkok, onupdate=now_bangkok)

    def to_dict(self):
        updated_local = ensure_bangkok(self.updated_at)
        return {
            "id": self.id,
            "isEnabled": self.is_enabled,
            "apiKey": self.api_key,
            "allowedIps": self.allowed_ips or "",
            "defaultRole": self.default_role or "Sale",
            "updatedAt": updated_local.strftime("%d-%m-%Y %H:%M") if updated_local else None,
        }


class CiamAuditLog(db.Model):
    __tablename__ = "ciam_audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=now_bangkok, index=True)
    client_ip = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(50), nullable=False, index=True)  # list_accounts, update_account_status, create_account
    target_username = db.Column(db.String(150), nullable=True, index=True)
    previous_status = db.Column(db.String(20), nullable=True)
    new_status = db.Column(db.String(20), nullable=True)
    reason = db.Column(db.Text, nullable=True)
    updated_by = db.Column(db.String(150), nullable=True)
    status_code = db.Column(db.Integer, default=200)
    message = db.Column(db.Text, nullable=True)

    def to_dict(self):
        created_local = ensure_bangkok(self.created_at)
        return {
            "id": self.id,
            "createdAt": created_local.strftime("%d-%m-%Y %H:%M:%S") if created_local else None,
            "createdAtIso": created_local.isoformat() if created_local else None,
            "clientIp": self.client_ip,
            "action": self.action,
            "targetUsername": self.target_username or "-",
            "previousStatus": self.previous_status,
            "newStatus": self.new_status,
            "reason": self.reason or "-",
            "updatedBy": self.updated_by or "-",
            "statusCode": self.status_code,
            "message": self.message or "",
        }


class LoginLog(db.Model):
    __tablename__ = "login_logs"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=now_bangkok, index=True)
    username = db.Column(db.String(150), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    ip_address = db.Column(db.String(50), nullable=False)
    user_agent = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), nullable=False, index=True)  # SUCCESS, FAILED_CREDENTIALS, ACCOUNT_DISABLED, USER_NOT_FOUND
    failure_reason = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        created_local = ensure_bangkok(self.created_at)
        return {
            "id": self.id,
            "createdAt": created_local.strftime("%d-%m-%Y %H:%M:%S") if created_local else None,
            "createdAtIso": created_local.isoformat() if created_local else None,
            "username": self.username,
            "userId": self.user_id,
            "ipAddress": self.ip_address,
            "userAgent": self.user_agent or "-",
            "status": self.status,
            "failureReason": self.failure_reason or "-",
        }



# --- CRUD Helpers ---
def _assign_customer_fields(customer: Customer, row: dict):
    customer.name = _clean(row.get("BP Name")) or customer.name
    customer.remarks = _clean(row.get("Remarks"))
    customer.accountBalance = _parse_decimal(row.get("Account Balance"))
    customer.foreignName = _clean(row.get("Foreign Name"))
    customer.currency = _clean(row.get("BP Currency"))
    customer.arAccount = _clean(row.get("Accounts Receivable/Payable"))
    customer.groupCode = _clean(row.get("Group Code"))
    customer.priceListNo = _clean(row.get("Price List No."))
    customer.aliasName = _clean(row.get("Alias Name"))
    customer.taxId = _clean(row.get("Federal Tax ID"))
    customer.billToBuilding = _clean(row.get("Bill-to Building/Floor/Room"))
    customer.billToStreet = _clean(row.get("Bill-to Street"))
    customer.billToCity = _clean(row.get("Bill-to City"))
    customer.billToCounty = _clean(row.get("Bill-to County"))
    customer.billToCountry = _clean(row.get("Bill-to Country"))
    customer.billToZipCode = _clean(row.get("Bill-to Zip Code"))
    customer.paymentTermsCode = _clean(row.get("Payment Terms Code"))
    customer.shipToBuilding = _clean(row.get("Ship to Building/Floor/Room"))
    customer.shipToStreet = _clean(row.get("Ship-to Street"))
    customer.shipToCity = _clean(row.get("Ship-to City"))
    customer.shipToCounty = _clean(row.get("Ship-to County"))
    customer.shipToCountry = _clean(row.get("Ship-to Country"))
    customer.shipToZipCode = _clean(row.get("Ship-to Zip Code"))
    customer.creationDate = _parse_date(row.get("Creation Date"))
    ib = _parse_bool(row.get("Inactive"))
    if ib is not None:
        customer.inactive = ib
    customer.taxCode = _clean(row.get("Tax Code"))
    customer.branch = _clean(row.get("BP Branch"))
    customer.taxGroup = _clean(row.get("Tax Group"))
    customer.telephone1 = _clean(row.get("Telephone 1"))
    customer.telephone2 = _clean(row.get("Telephone 2"))
    customer.salesEmployeeCode = _clean(row.get("Sales Employee Code"))
    se = _parse_bool(row.get("Self-Employed"))
    if se is not None:
        customer.selfEmployed = se
    customer.mobilePhone = _clean(row.get("Mobile Phone"))
    customer.shippingType = _clean(row.get("Shipping Type"))
    cl = _parse_decimal(row.get("Credit Limit"))
    if cl is not None:
        customer.creditLimit = cl
    customer.updateFullTime = _clean(row.get("Update Full Time"))
    customer.remark1 = _clean(row.get("Remark 1"))


def _assign_product_fields(product: Product, row: dict):
    product.name = _clean(row.get("Item Description")) or product.name
    product.itemGroup = _clean(row.get("Item Group")) or product.itemGroup
    
    # Prices
    selling_price = _parse_decimal(row.get("Recommended Price (Ex.VAT)"))
    cost_price = _parse_decimal(row.get("Item Cost (Ex.VAT)"))
    
    if selling_price is not None:
        product.unitPrice = float(selling_price)
    if cost_price is not None:
        product.itemCost = float(cost_price)
        
    product.inStock = _parse_decimal(row.get("In Stock"))
    
    ia = _parse_bool(row.get("Inactive"))
    if ia is not None:
        product.inactive = ia


def _update_customer_from_payload(customer: Customer, payload: dict | None):
    if not payload:
        return
    for f in [
        "name",
        "remarks",
        "foreignName",
        "currency",
        "arAccount",
        "groupCode",
        "priceListNo",
        "aliasName",
        "taxId",
        "billToBuilding",
        "billToStreet",
        "billToCity",
        "billToCounty",
        "billToCountry",
        "billToZipCode",
        "paymentTermsCode",
        "shipToBuilding",
        "shipToStreet",
        "shipToCity",
        "shipToCounty",
        "shipToCountry",
        "shipToZipCode",
        "taxCode",
        "branch",
        "taxGroup",
        "telephone1",
        "telephone2",
        "salesEmployeeCode",
        "mobilePhone",
        "shippingType",
        "updateFullTime",
        "remark1",
    ]:
        if f in payload:
            setattr(customer, f, _clean(payload[f]))
    for f in ["accountBalance", "creditLimit"]:
        if f in payload:
            setattr(customer, f, _parse_decimal(payload[f]))
    for f in ["selfEmployed", "inactive"]:
        if f in payload:
            pb = _parse_bool(str(payload[f]))
            if pb is not None:
                setattr(customer, f, pb)
    if "creationDate" in payload:
        pd = _parse_date(payload["creationDate"])
        if pd:
            customer.creationDate = pd


def _update_product_from_payload(product: Product, payload: dict | None):
    if not payload:
        return
    u_in = "unitPrice" in payload
    c_in = "itemCost" in payload
    s_fields = [
        "name",
        "description",
        "itemGroup",
        "uomGroup",
        "salesUom",
        "inventoryUom",
        "purchasingUom",
        "itemRemarks",
        "foreignName",
        "location",
        "lastName",
        "activeRemarks",
    ]
    for f in s_fields:
        if f in payload:
            setattr(product, f, _clean(payload[f]))
    for f in ["inactive"]:
        if f in payload:
            pb = _parse_bool(str(payload[f]))
            if pb is not None:
                setattr(product, f, pb)
    for f in ["unitPrice", "inStock", "itemCost"]:
        if f in payload:
            setattr(product, f, _parse_decimal(payload[f]))
    if "productionDate" in payload:
        pd = _parse_date(payload["productionDate"])
        if pd:
            product.productionDate = pd
    if c_in and not u_in and product.itemCost is not None:
        product.unitPrice = product.itemCost


def import_customer_from_csv(file_data):
    # Use io.StringIO to read binary data as text
    if isinstance(file_data, bytes):
        stream = io.StringIO(file_data.decode("utf-8-sig", errors="ignore"))
    else:
        stream = io.StringIO(file_data)

    reader = csv.DictReader(stream)
    stats = {"inserted": 0, "updated": 0, "skippedInactive": 0, "skippedBlank": 0}

    for row in reader:
        code = _clean(row.get("BP Code"))
        if not code:
            stats["skippedBlank"] += 1
            continue

        # Skip if inactive and not already in DB
        inactive = _parse_bool(row.get("Inactive"))

        customer = Customer.query.filter_by(customerCode=code).first()
        if customer:
            _assign_customer_fields(customer, row)
            stats["updated"] += 1
        else:
            if inactive:
                stats["skippedInactive"] += 1
                continue
            customer = Customer(customerCode=code)
            _assign_customer_fields(customer, row)
            db.session.add(customer)
            stats["inserted"] += 1

    db.session.commit()
    return stats


def import_product_from_csv(file_data):
    if isinstance(file_data, bytes):
        stream = io.StringIO(file_data.decode("utf-8-sig", errors="ignore"))
    else:
        stream = io.StringIO(file_data)

    reader = csv.DictReader(stream)
    stats = {"inserted": 0, "updated": 0, "skippedInactive": 0, "skippedBlank": 0}

    for row in reader:
        code = _clean(row.get("Item No."))
        if not code:
            stats["skippedBlank"] += 1
            continue

        inactive = _parse_bool(row.get("Inactive"))

        product = Product.query.filter_by(productCode=code).first()
        if product:
            _assign_product_fields(product, row)
            stats["updated"] += 1
        else:
            if inactive:
                stats["skippedInactive"] += 1
                continue
            product = Product(productCode=code)
            _assign_product_fields(product, row)
            db.session.add(product)
            stats["inserted"] += 1

    db.session.commit()
    return stats


def get_template_csv(type_name):
    output = io.StringIO()
    if type_name == "customer":
        writer = csv.DictWriter(output, fieldnames=CUSTOMER_CSV_COLUMNS)
        writer.writeheader()
        
        # Export CURRENT customers
        customers = Customer.query.order_by(Customer.customerCode).all()
        for c in customers:
            writer.writerow({
                "BP Code": c.customerCode,
                "BP Name": c.name,
                "Remarks": c.remarks,
                "Account Balance": c.accountBalance,
                "Foreign Name": c.foreignName,
                "BP Currency": c.currency,
                "Accounts Receivable/Payable": c.arAccount,
                "Group Code": c.groupCode,
                "Price List No.": c.priceListNo,
                "Alias Name": c.aliasName,
                "Federal Tax ID": c.taxId,
                "Bill-to Building/Floor/Room": c.billToBuilding,
                "Bill-to Street": c.billToStreet,
                "Bill-to City": c.billToCity,
                "Bill-to County": c.billToCounty,
                "Bill-to Country": c.billToCountry,
                "Bill-to Zip Code": c.billToZipCode,
                "Payment Terms Code": c.paymentTermsCode,
                "Ship to Building/Floor/Room": c.shipToBuilding,
                "Ship-to Street": c.shipToStreet,
                "Ship-to City": c.shipToCity,
                "Ship-to County": c.shipToCounty,
                "Ship-to Country": c.shipToCountry,
                "Ship-to Zip Code": c.shipToZipCode,
                "Creation Date": c.creationDate.isoformat() if c.creationDate else "",
                "Inactive": "Yes" if c.inactive else "No",
                "Tax Code": c.taxCode,
                "BP Branch": c.branch,
                "Tax Group": c.taxGroup,
                "Telephone 1": c.telephone1,
                "Telephone 2": c.telephone2,
                "Sales Employee Code": c.salesEmployeeCode,
                "Self-Employed": "Yes" if c.selfEmployed else "No",
                "Mobile Phone": c.mobilePhone,
                "Shipping Type": c.shippingType,
                "Credit Limit": c.creditLimit,
                "Update Full Time": c.updateFullTime,
                "Remark 1": c.remark1,
            })
    else:
        writer = csv.DictWriter(output, fieldnames=PRODUCT_CSV_COLUMNS)
        writer.writeheader()
        
        # Export CURRENT products
        products = Product.query.order_by(Product.productCode).all()
        for p in products:
            writer.writerow({
                "Item No.": p.productCode,
                "Item Description": p.name,
                "Item Group": p.itemGroup,
                "Recommended Price (Ex.VAT)": p.unitPrice,
                "Item Cost (Ex.VAT)": p.itemCost,
                "In Stock": p.inStock,
                "Inactive": "Yes" if p.inactive else "No",
            })
            
    return "\ufeff" + output.getvalue()

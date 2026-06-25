from app import app
from extensions import db
from models import PurchaseOrder
import json
from datetime import datetime

with app.app_context():
    pos = PurchaseOrder.query.order_by(PurchaseOrder.created.desc()).all()
    print(f"Total POs: {len(pos)}")
    for p in pos:
        print(f"PO: {p.poNumber}, Created: {p.created}")

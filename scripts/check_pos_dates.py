from app import app
from extensions import db
from models import PurchaseOrder
import json
import sys
import os

# Add current directory to path to ensure relative imports work
sys.path.append(os.path.abspath("."))

with app.app_context():
    pos = PurchaseOrder.query.order_by(PurchaseOrder.created.desc()).limit(10).all()
    results = []
    for p in pos:
        results.append({
            "poNumber": p.poNumber,
            "created": p.created.isoformat() if p.created else None,
            "dict": p.to_dict()
        })
    print(json.dumps(results, indent=2))

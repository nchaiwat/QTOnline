from app import app, db, User, PurchaseOrder

with app.app_context():
    print("--- Users ---")
    users = User.query.all()
    for u in users:
        print(f"User: {u.username} (ID: {u.id}), FullName: {u.fullName}, Sig: {u.signatureImage}")

    print("\n--- Latest PO ---")
    po = PurchaseOrder.query.order_by(PurchaseOrder.id.desc()).first()
    if po:
        print(f"PO: {po.poNumber}, Creator ID: {po.saleId}")
        if po.creator:
             print(f"Creator (via rel): {po.creator.fullName}, Sig: {po.creator.signatureImage}")
        else:
             print("Creator relationship is None")

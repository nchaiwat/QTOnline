from app import app, db, Customer, Product, PurchaseOrder, POItem

def cleanup():
    with app.app_context():
        print("Starting cleanup...")

        # --- 1. Cleanup Products ---
        # Get all product IDs used in PO Items
        # We use a set for faster lookup
        used_product_ids = {
            row[0] for row in db.session.query(POItem.productId).distinct().all()
        }

        # Get all products
        all_products = Product.query.all()
        
        products_to_delete = []
        for p in all_products:
            if p.id not in used_product_ids:
                products_to_delete.append(p)
        
        print(f"Found {len(products_to_delete)} unused products.")
        for p in products_to_delete:
            print(f"Deleting Product: {p.productCode} - {p.name}")
            db.session.delete(p)

        # --- 2. Cleanup Customers ---
        # Get all customer codes used in Purchase Orders
        # PurchaseOrder.customerId stores the customerCode
        used_customer_codes = {
            row[0] for row in db.session.query(PurchaseOrder.customerId).distinct().all() 
            if row[0] # Filter out None/Empty if any
        }

        # Get all customers
        all_customers = Customer.query.all()
        
        customers_to_delete = []
        for c in all_customers:
            # Check if customerCode is in the used list
            if c.customerCode not in used_customer_codes:
                customers_to_delete.append(c)
        
        print(f"Found {len(customers_to_delete)} unused customers.")
        for c in customers_to_delete:
            print(f"Deleting Customer: {c.customerCode} - {c.name}")
            db.session.delete(c)

        # Commit changes
        if products_to_delete or customers_to_delete:
            db.session.commit()
            print("Database updated successfully.")
        else:
            print("No changes needed.")

        print("Cleanup complete.")

if __name__ == "__main__":
    cleanup()

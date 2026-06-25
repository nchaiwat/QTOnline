import sys
from app import app, db, POItem, Comment, Notification, PurchaseOrder, Product, Customer

def reset_all_data():
    """
    สคริปต์สำหรับล้างข้อมูลทั้งระบบ (ยกเว้น Users)
    """
    with app.app_context():
        print("-" * 50)
        print("!!! WARNING: DANGER ZONE !!!")
        print("-" * 50)
        print("สคริปต์นี้จะลบข้อมูลทั้งหมดในตารางต่อไปนี้:")
        print("1. PO Items (รายการสินค้าในบิล)")
        print("2. Comments (ความคิดเห็น)")
        print("3. Notifications (การแจ้งเตือน)")
        print("4. Purchase Orders (ใบสั่งซื้อ)")
        print("5. Products (สินค้า)")
        print("6. Customers (ลูกค้า)")
        print("\n* ข้อมูล Users (ผู้ใช้งาน) จะไม่ถูกลบ *")
        print("-" * 50)
        
        confirm = input("คุณแน่ใจหรือไม่ที่จะลบข้อมูลทั้งหมด? พิมพ์ 'YES' เพื่อยืนยัน: ")
        
        if confirm != 'YES':
            print("ยกเลิกการทำงาน")
            return

        try:
            print("\nกำลังดำเนินการ...")
            
            # 1. ลบตารางที่มี Transaction (Children)
            c_items = POItem.query.delete()
            c_comments = Comment.query.delete()
            c_notifs = Notification.query.delete()
            print(f"- ลบ Transaction ย่อย: Items={c_items}, Comments={c_comments}, Notifs={c_notifs}")
            
            # 2. ลบเอกสาร (Parents)
            c_pos = PurchaseOrder.query.delete()
            print(f"- ลบใบสั่งซื้อ (POs): {c_pos}")
            
            # 3. ลบ Master Data
            c_prod = Product.query.delete()
            c_cust = Customer.query.delete()
            print(f"- ลบข้อมูลหลัก: Products={c_prod}, Customers={c_cust}")
            
            db.session.commit()
            print("\n[SUCCESS] ลบข้อมูลทั้งหมดเรียบร้อยแล้ว!")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] เกิดข้อผิดพลาด: {e}")

if __name__ == "__main__":
    reset_all_data()

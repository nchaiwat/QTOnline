import os
import sys

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app
from extensions import db
from models import SystemSetting
from sqlalchemy import text


def run_migration():
    print("=====================================================")
    print(" Starting SAP B1, Telegram & AI Copilot Migration... ")
    print("=====================================================")
    with app.app_context():
        # 1. Ensure all tables are created
        print("[1/3] Ensuring tables exist...")
        db.create_all()
        print("      Tables verified successfully.")

        # 2. Add SAP columns to users table
        print("[2/3] Updating users table schema with SAP B1 columns...")
        user_cols = [
            ("sap_account", "VARCHAR(100)"),
            ("sap_password", "VARCHAR(255)"),
            ("can_use_sap_api", "BOOLEAN DEFAULT FALSE"),
        ]
        for col_name, col_type in user_cols:
            try:
                sql = f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_type};"
                db.session.execute(text(sql))
                print(f"      - Column '{col_name}' ({col_type}): OK")
            except Exception as e:
                print(f"      - Column '{col_name}' warning: {e}")
        db.session.commit()

        # 3. Initialize default SystemSettings
        print("[3/3] Initializing default system_settings...")
        default_settings = [
            # Telegram
            ("telegram_bot_token", os.environ.get("TELEGRAM_BOT_TOKEN", "8214911655:AAG5RKU6m75AOc3Wws0FqVBqn1CicDLsVWI"), "Telegram Bot API Token", "telegram", "encrypted"),
            ("telegram_group_id", os.environ.get("TELEGRAM_GROUP_ID", "-5241471050"), "Telegram Chat/Group ID สำหรับรับแจ้งเตือน", "telegram", "string"),
            ("telegram_api_base_url", os.environ.get("TELEGRAM_API_BASE_URL", "https://api.telegram.org"), "Telegram API Base URL", "telegram", "string"),
            ("telegram_enabled", "true", "เปิด/ปิดระบบการส่งแจ้งเตือน Telegram อัตโนมัติ", "telegram", "boolean"),
            
            # SAP B1
            ("sap_b1_service_url", "https://sap.windowasia.com:50000/b1s/v1", "SAP Business One Service Layer API URL", "sap_b1", "string"),
            ("sap_b1_company_db", "WINDOW_ASIA_LIVE", "SAP B1 Company Database Name", "sap_b1", "string"),
            ("sap_b1_enabled", "false", "เปิด/ปิดการเชื่อมต่อระบบ SAP Business One API", "sap_b1", "boolean"),
            ("sap_b1_default_bu", "SALE-DL", "SAP B1 Default Business Unit (CostingCode)", "sap_b1", "string"),
            ("sap_b1_default_dept", "SA", "SAP B1 Default Department (CostingCode2)", "sap_b1", "string"),

            # AI Copilot (CIAM Spec v2.8.0)
            ("ai_copilot_enabled", "false", "เปิด/ปิดระบบผู้ช่วยอัจฉริยะ AI Copilot ประจำระบบ", "ai_copilot", "boolean"),
            ("ai_provider", "google", "ผู้ให้บริการ AI Engine (google / openai / anthropic)", "ai_copilot", "string"),
            ("ai_model", "gemini-2.5-flash", "ชื่อโมเดล AI มาตรฐาน", "ai_copilot", "string"),
            ("ai_api_key", "", "API Key สำหรับ AI Provider (Zero-Training Commercial Tier)", "ai_copilot", "encrypted"),
            ("ai_system_prompt", "คุณคือ AI ผู้ช่วยอัจฉริยะ (AI Copilot) ประจำระบบ QT-Online บริษัท วินโดว์ เอเชีย จำกัด (มหาชน) มีหน้าที่ให้ข้อมูลสรุป ค้นหา วิเคราะห์ยอดขาย และจำลองผลกระทบในรูปแบบ Read-Only เท่านั้น ห้ามทำการแก้ไขหรือลบข้อมูลในระบบ", "System Prompt สำหรับกำหนดบทบาทและข้อจำกัดความปลอดภัยของ AI", "ai_copilot", "string"),
        ]

        for key, val, desc, cat, dtype in default_settings:
            existing = SystemSetting.query.filter_by(key=key).first()
            if not existing:
                SystemSetting.set_value(key, val, description=desc, category=cat, data_type=dtype)
                print(f"      - Created setting: '{key}' ({cat})")
            elif key == "sap_b1_default_bu" and existing.value == "WA":
                SystemSetting.set_value(key, "SALE-DL", description=desc, category=cat, data_type=dtype)
                print(f"      - Updated setting: '{key}' to 'SALE-DL'")
            else:
                print(f"      - Exists setting: '{key}'")
        
        # 4. Set default 20% discount on existing products without discount
        print("[4/4] Updating existing products discount to 20% for SAP B1...")
        try:
            update_sql = 'UPDATE products SET "discountPercent" = 20.0 WHERE "discountPercent" IS NULL OR "discountPercent" = 0.0;'
            result = db.session.execute(text(update_sql))
            db.session.commit()
            print(f"      - Updated {result.rowcount} products to 20.0% discount.")
        except Exception as e:
            print(f"      - Product discount update warning: {e}")

        print("=====================================================")
        print(" Migration completed successfully!                   ")
        print("=====================================================")


if __name__ == "__main__":
    run_migration()

#!/usr/bin/env python3
"""
Generate Secure Secrets for PO-Online Production
Run this script to generate new SECRET_KEY and ENCRYPTION_KEY
"""

import secrets
from cryptography.fernet import Fernet

print("=" * 70)
print("🔐 PO-Online Secret Generator")
print("=" * 70)
print()

# Generate Flask SECRET_KEY
secret_key = secrets.token_urlsafe(32)
print("1. Flask SECRET_KEY:")
print(f"   SECRET_KEY={secret_key}")
print()

# Generate Encryption KEY
encryption_key = Fernet.generate_key().decode()
print("2. Encryption KEY:")
print(f"   ENCRYPTION_KEY={encryption_key}")
print()

print("=" * 70)
print("📋 วิธีใช้งาน:")
print("=" * 70)
print("1. คัดลอกค่าด้านบนไปใส่ในไฟล์ .env")
print("2. Restart Docker: docker-compose restart web")
print("3. ตรวจสอบ: curl http://localhost:8080/health")
print()
print("⚠️  คำเตือน:")
print("   - อย่า commit ค่าเหล่านี้ลง Git")
print("   - เก็บไว้ในที่ปลอดภัย")
print("   - ถ้าเปลี่ยน ENCRYPTION_KEY ลายเซ็นเก่าจะอ่านไม่ได้")
print("=" * 70)

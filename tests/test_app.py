import re
from playwright.sync_api import Page, expect

# Test Case 1: Successful Login
def test_successful_login(page: Page):
    # ไปที่หน้าเว็บของคุณที่รันบน Port 8080
    page.goto("http://localhost:8080/")

    # (สำคัญ!) กรุณาเปลี่ยน "#username", "#password", "#login-button" 
    # ให้ตรงกับ id หรือ selector ของ element ในหน้าเว็บของคุณ
    page.get_by_label("Username").fill("admin")
    page.get_by_label("Password").fill("password123")
    
    # แก้ไขโดยการเพิ่ม exact=True เพื่อให้เลือกปุ่มที่ถูกต้อง
    page.get_by_role("button", name="Login", exact=True).click()

    # ตรวจสอบว่ามีข้อความ "Login successful!" แสดงขึ้นมา
    # (สำคัญ!) กรุณาเปลี่ยน locator ให้ตรงกับ element ที่แสดงผลลัพธ์
    success_message = page.locator("#status-message")
    expect(success_message).to_have_text("Login successful!")


# Test Case 2: Failed Login
def test_failed_login(page: Page):
    # ไปที่หน้าเว็บของคุณ
    page.goto("http://localhost:8080/")

    # กรอกข้อมูลที่ไม่ถูกต้อง
    page.get_by_label("Username").fill("admin")
    page.get_by_label("Password").fill("wrongpassword")

    # แก้ไขโดยการเพิ่ม exact=True เพื่อให้เลือกปุ่มที่ถูกต้อง
    page.get_by_role("button", name="Login", exact=True).click()

    # ตรวจสอบว่ามีข้อความ "Invalid credentials" แสดงขึ้นมา
    error_message = page.locator("#status-message")
    import re
from playwright.sync_api import Page, expect

# Test Case 1: Successful Login
def test_successful_login(page: Page):
    # ไปที่หน้าเว็บของคุณที่รันบน Port 8080
    page.goto("http://localhost:8080/")

    # (สำคัญ!) กรุณาเปลี่ยน "#username", "#password", "#login-button" 
    # ให้ตรงกับ id หรือ selector ของ element ในหน้าเว็บของคุณ
    page.get_by_label("Username").fill("admin")
    page.get_by_label("Password").fill("password123")
    
    # แก้ไขโดยการเพิ่ม exact=True เพื่อให้เลือกปุ่มที่ถูกต้อง
    page.get_by_role("button", name="Login", exact=True).click()

    # ตรวจสอบว่ามีข้อความ "Login successful!" แสดงขึ้นมา
    # (สำคัญ!) กรุณาเปลี่ยน locator ให้ตรงกับ element ที่แสดงผลลัพธ์
    success_message = page.locator("#status-message")
    expect(success_message).to_have_text("Login successful!")


# Test Case 2: Failed Login
def test_failed_login(page: Page):
    # ไปที่หน้าเว็บของคุณ
    page.goto("http://localhost:8080/")

    # กรอกข้อมูลที่ไม่ถูกต้อง
    page.get_by_label("Username").fill("admin")
    page.get_by_label("Password").fill("wrongpassword")

    # แก้ไขโดยการเพิ่ม exact=True เพื่อให้เลือกปุ่มที่ถูกต้อง
    page.get_by_role("button", name="Login", exact=True).click()

    # ตรวจสอบว่ามีข้อความ "Invalid credentials" แสดงขึ้นมา
    error_message = page.locator("#status-message")
    
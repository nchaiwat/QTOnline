# Corporate Standard: Centralized Identity Management API Specification
**Document Version:** 1.0.0  
**Status:** Approved Standard (มาตรฐานกลางระดับองค์กร)  
**Target Audience:** Software Engineers, Solution Architects, DevOps, IT System Administrators  
**Reference Applications:** IRM (Reference Implementation), QMS, ERP, WMS, CRM, and all Future In-House Applications

---

## 1. บทนำและวัตถุประสงค์ (Overview & Objectives)

เอกสารฉบับนี้กำหนด **ข้อกำหนดมาตรฐานระดับองค์กร (Corporate Standard API Blueprint)** สำหรับการเชื่อมโยงการบริหารจัดการบัญชีผู้ใช้งาน (Identity & Access Management - IAM) ระหว่าง **ระบบบริหารจัดการส่วนกลาง (Central Management App)** กับ **Application ต่างๆ ภายในองค์กร** ทั้งหมด

### ปัญหาที่เอกสารฉบับนี้แก้ไข (Problem Statement)
ในองค์กรที่มี Application หลากหลายระบบ หากไม่มีมาตรฐานกลางในการเชื่อมต่อ:
1. **Orphaned / Ghost Accounts:** เมื่อพนักงานลาออก ฝ่ายบุคคลแจ้ง IT แต่ IT ลืมปิดสิทธิ์ในบางระบบ ทำให้พนักงานเก่ายังคงเข้าถึงข้อมูลสำคัญของบริษัทได้
2. **Lack of Central Audit Trail:** ฝ่าย IT Audit ไม่สามารถมองเห็นภาพรวมได้ว่า พนักงาน 1 คน มีสิทธิ์เข้าถึงระบบใดบ้างในองค์กร
3. **Manual Overhead:** เจ้าหน้าที่ต้องเสียเวลา Login เข้าไปปิดสิทธิ์ทีละ Application ซ้ำซ้อน

### แนวทางแก้ไข (Solution Architecture)
Application ทุกตัวที่พัฒนาขึ้นในองค์กรจะต้องสร้าง REST API ตามข้อกำหนดในเอกสารนี้ เพื่อให้ **Central Management App** สามารถ:
1. **ดึงทะเบียนรายชื่อผู้ใช้ทั้งหมด (Account Inventory / Reconciliation)** จากทุกระบบไปรวมไว้ที่ Dashboard ส่วนกลาง
2. **สั่งเปิด/ระงับการใช้งานบัญชี (Instant Offboarding / Status Provisioning)** ได้ทันทีจากศูนย์กลางแบบ Real-time

```
┌─────────────────────────────────────────────────────────────┐
│               Central Management App (IAM)                  │
│       (Single Source of Truth / HRIS Integration)           │
└──────────────────────────────┬──────────────────────────────┘
                               │
            HTTPS + Machine-to-Machine API Key
            + Client IP Whitelisting Validation
                               │
       ┌───────────────────────┼───────────────────────┐
       ▼                       ▼                       ▼
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│  IRM App     │        │  QMS App     │        │ Future Apps  │
│ (Implemented)│        │ (To Conform) │        │ (To Conform) │
└──────────────┘        └──────────────┘        └──────────────┘
```

---

## 2. มาตรฐานความปลอดภัย (Security Requirements)

เนื่องจาก API ชุดนี้เป็น Administrative API ที่มีผลต่อสถานะการเข้าใช้งานระบบ จึงต้องบังคับใช้มาตรการความปลอดภัยขั้นสูงสุดดังนี้:

### 2.1 Machine-to-Machine (M2M) Authentication
* ไม่อนุญาตให้ใช้ User JWT หรือ Cookies ทั่วไป
* คำขอทุกคำขอต้องแนบ Header ลับเฉพาะ:
  ```http
  X-Management-API-Key: sec_<app_name>_mgmt_<random_hex_32_chars>
  ```
* ระบบปลายทางต้องตรวจสอบ Key ด้วยอัลกอริทึม **Constant-Time String Comparison** (เช่น `secrets.compare_digest`) เพื่อป้องกันการโจมตีแบบ Timing Attack

### 2.2 IP Whitelisting (Defense-in-Depth)
* Application ปลายทางต้องมีระบบตรวจเช็ค Client IP Address
* รับคำขอเฉพาะ IP ของเครื่อง **Central Management Server** ที่กำหนดไว้เท่านั้น (เช่น `157.173.219.153`, `192.168.12.11`)
* หากมี Reverse Proxy คั่นกลาง ต้องอ่านค่าจาก Header `X-Forwarded-For` อย่างปลอดภัย

### 2.3 Least Privilege & Zero Data Leakage
* **ข้อมูลที่อนุญาตให้ส่งกลับ:** `id`, `username`, `full_name`, `email`, `department`, `telegram_chat_id`, `is_active`, `last_login_at`, `created_at`
* **ข้อมูลที่ห้ามส่งกลับเด็ดขาด (Strictly Forbidden):** 
  * ❌ `password`, `password_hash`, `salt`
  * ❌ ข้อมูลทางธุรกิจ (เช่น ราคาสินค้า, ใบสั่งซื้อ, ข้อมูลลูกค้า, ตัวเลขทางการเงิน)

### 2.4 Audit Trail Requirement
* Application ทุกตัวต้องบันทึกประวัติการเรียก API นี้ลงใน **Transaction Audit Log** เสมอ:
  * วันที่และเวลา (UTC)
  * IP ผู้ส่งคำขอ
  * Action ที่ทำ (`list_accounts`, `update_account_status`)
  * สถานะก่อนหน้า (Previous Status) และสถานะใหม่ (New Status)
  * ผู้สั่งการ (Updated By) และเหตุผล (Reason)

---

## 3. รายละเอียด API Endpoints (API Specification)

**Base URL Prefix ที่กำหนด:** `/api/v1/directory`

---

### 3.1 Endpoint 1: ดึงรายชื่อบัญชีผู้ใช้ทั้งหมด (Account Inventory)

ใช้สำหรับให้ Central Management App ดึงข้อมูลผู้ใช้งานไปทำ Inventory และตรวจสอบความสอดคล้องของสิทธิ์ (Reconciliation)

* **HTTP Method:** `GET`
* **Path:** `/api/v1/directory/accounts`
* **Request Headers:**
  | Header Name | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `X-Management-API-Key` | String | **Yes** | Secret Token ประจำ Application |
  | `Content-Type` | String | Yes | `application/json` |

* **Query Parameters (Optional):**
  | Parameter | Type | Default | Description |
  | :--- | :--- | :--- | :--- |
  | `status` | String | `all` | ตัวกรองสถานะ: `all`, `active`, `inactive` |
  | `department` | String | - | กรองเฉพาะแผนก เช่น `Purchasing`, `Warehouse` |
  | `search` | String | - | ค้นหาจาก Username, Full Name หรือ Email |

#### Response Format (200 OK):
```json
{
  "application_name": "IRM (Incoming Raw Material)",
  "total_accounts": 25,
  "active_accounts": 23,
  "inactive_accounts": 2,
  "accounts": [
    {
      "id": 1,
      "username": "somchai.p",
      "full_name": "สมชาย พากเพียร",
      "email": "somchai.p@company.com",
      "department": "Purchasing",
      "telegram_chat_id": "987654321",
      "group_name": "Purchasing Staff",
      "use_ad_auth": true,
      "is_active": true,
      "last_login_at": "2026-09-02T08:15:30Z",
      "created_at": "2026-01-10T03:00:00Z",
      "updated_at": "2026-09-02T08:15:30Z"
    },
    {
      "id": 2,
      "username": "wichai.k",
      "full_name": "วิชัย การค้า",
      "email": "wichai.k@company.com",
      "department": "Warehouse",
      "telegram_chat_id": null,
      "group_name": "Warehouse Operator",
      "use_ad_auth": false,
      "is_active": false,
      "last_login_at": "2026-08-15T10:20:00Z",
      "created_at": "2026-02-01T04:30:00Z",
      "updated_at": "2026-08-31T17:00:00Z"
    }
  ]
}
```

---

### 3.2 Endpoint 2: สั่งเปิดหรือระงับการใช้งานบัญชี (Status Provisioning)

ใช้สำหรับให้ Central Management App ส่งคำสั่งระงับสิทธิ์ (Disable) เมื่อพนักงานลาออก หรือเปิดใช้งานใหม่ (Re-activate)

* **HTTP Method:** `PATCH`
* **Path:** `/api/v1/directory/accounts/{username}/status`
* **Path Parameters:**
  * `{username}` : รหัสบัญชีผู้ใช้ในระบบ (sAMAccountName หรือ Username)
* **Request Headers:**
  | Header Name | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `X-Management-API-Key` | String | **Yes** | Secret Token ประจำ Application |
  | `Content-Type` | String | Yes | `application/json` |

* **Request Body (JSON):**
```json
{
  "is_active": false,
  "reason": "Employee resigned effective 2026-09-02 (Ticket #HR-9842)",
  "updated_by": "Central-IAM-Service"
}
```

#### Response Format (200 OK):
```json
{
  "username": "somchai.p",
  "is_active": false,
  "message": "Account 'somchai.p' status has been successfully updated to INACTIVE.",
  "updated_at": "2026-09-02T13:50:45.123456Z"
}
```

---

### 3.3 Endpoint 3: สร้างบัญชีผู้ใช้งานใหม่ (Account Provisioning)

ใช้สำหรับให้ Central Management App สั่งสร้างบัญชีผู้ใช้ใหม่ใน Application ปลายทางแบบ Real-time เมื่อมีพนักงาน Onboard หรือได้รับสิทธิ์ใช้งานระบบเพิ่มเติม

* **HTTP Method:** `POST`
* **Path:** `/api/v1/directory/accounts`
* **Request Headers:**
  | Header Name | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `X-Management-API-Key` | String | **Yes** | Secret Token ประจำ Application |
  | `Content-Type` | String | Yes | `application/json` |

* **Request Body (JSON):**
```json
{
  "username": "somchai.p",
  "full_name": "สมชาย พากเพียร",
  "email": "somchai.p@company.com",
  "department": "Purchasing",
  "group_name": "PU User",
  "use_ad_auth": true,
  "created_by": "Central-IAM-Service"
}
```

* **Field Specifications:**
  * `username` *(String, Required)*: ชื่อบัญชีผู้ใช้งาน (sAMAccountName เดียวกับ AD)
  * `full_name` *(String, Required)*: ชื่อ-นามสกุลจริง
  * `email` *(String, Optional)*: อีเมลองค์กรของพนักงาน
  * `department` *(String, Optional)*: แผนกงาน
  * `group_name` *(String, Optional)*: สิทธิ์/Role ในระบบปลายทาง (เช่น `PU User`, `Admin`, `QA Inspector`)
  * `use_ad_auth` *(Boolean, Optional, Default: `true`)*: ยืนยันตัวตนผ่าน AD หรือไม่
  * `created_by` *(String, Optional, Default: `"Central-IAM-Service"`)*: ชื่อผู้สั่งสร้าง

#### Response Format (201 Created):
```json
{
  "success": true,
  "id": 26,
  "username": "somchai.p",
  "message": "Account 'somchai.p' created successfully.",
  "group_name": "PU User",
  "is_active": true,
  "created_at": "2026-09-05T09:00:00.000000Z"
}
```

---

## 4. มาตรฐาน HTTP Status Codes และ Error Handling

เมื่อเกิดข้อผิดพลาด Application ปลายทางต้องส่ง HTTP Status Code ตามมาตรฐานดังนี้:

| Status Code | ความหมาย | สาเหตุที่เกิดขึ้น | JSON Body ที่ต้องส่งกลับ |
| :--- | :--- | :--- | :--- |
| **200 OK** | สำเร็จ | ดึงข้อมูลหรืออัปเดตสถานะสำเร็จ | ส่งข้อมูลผลลัพธ์ตาม Spec |
| **201 Created** | สร้างสำเร็จ | สร้างบัญชีผู้ใช้ใหม่สำเร็จ | ส่งข้อมูลบัญชีที่สร้างใหม่ |
| **400 Bad Request** | Request ผิดพลาด | ข้อมูลใน Body ไม่ถูกต้อง หรือขาดฟิลด์บังคับ | `{"detail": "Validation error: username and full_name are required"}` |
| **401 Unauthorized** | ไม่มีสิทธิ์ยืนยันตัวตน | ไม่มี Header `X-Management-API-Key` หรือ Key ไม่ถูกต้อง | `{"detail": "Invalid or missing X-Management-API-Key header."}` |
| **403 Forbidden** | ปฏิเสธการเข้าถึง | IP ไม่อยู่ใน Whitelist หรือระบบปิด API ไว้ | `{"detail": "Origin IP '...' is not permitted."}` |
| **404 Not Found** | ไม่พบข้อมูล | ไม่พบบัญชี `{username}` ที่ระบุในระบบนี้ | `{"detail": "User account '...' does not exist."}` |
| **409 Conflict** | ข้อมูลซ้ำซ้อน | บัญชี `{username}` มีอยู่แล้วในระบบ | `{"detail": "User account already exists."}` |
| **500 Server Error** | เซิร์ฟเวอร์มีปัญหา | Database Error ภายในระบบปลายทาง | `{"detail": "Internal server error: ..."}` |

---

## 5. ตัวอย่างโค้ดเรียกใช้งาน (Integration Code Examples)

### 5.1 ตัวอย่าง cURL

```bash
# 1. ทดสอบดึงรายชื่อผู้ใช้ทั้งหมด
curl -X GET "https://irm.windowasia.com/api/v1/directory/accounts?status=active" \
  -H "X-Management-API-Key: sec_irm_mgmt_9a4f21e8d3b76c501e4a" \
  -H "Content-Type: application/json"

# 2. สั่ง Disable บัญชีพนักงานที่ลาออก
curl -X PATCH "https://irm.windowasia.com/api/v1/directory/accounts/somchai.p/status" \
  -H "X-Management-API-Key: sec_irm_mgmt_9a4f21e8d3b76c501e4a" \
  -H "Content-Type: application/json" \
  -d '{
    "is_active": false,
    "reason": "Resigned - HR Ticket #9901",
    "updated_by": "Central-Admin"
  }'

# 3. สั่งสร้างบัญชีผู้ใช้ใหม่ (Provision Account)
curl -X POST "https://irm.windowasia.com/api/v1/directory/accounts" \
  -H "X-Management-API-Key: sec_irm_mgmt_9a4f21e8d3b76c501e4a" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "somchai.p",
    "full_name": "สมชาย พากเพียร",
    "email": "somchai.p@company.com",
    "department": "Purchasing",
    "group_name": "PU User",
    "use_ad_auth": true,
    "created_by": "Central-IAM-Service"
  }'
```

---

### 5.2 ตัวอย่าง Python (Central Management Service Client)

```python
import httpx

CENTRAL_CLIENT_CONFIG = {
    "irm": {
        "base_url": "https://irm.windowasia.com/api/v1/directory",
        "api_key": "sec_irm_mgmt_9a4f21e8d3b76c501e4a",
    },
    "qms": {
        "base_url": "https://qms.windowasia.com/api/v1/directory",
        "api_key": "sec_qms_mgmt_8b7c32a1e...",
    },
}

async def disable_user_across_all_apps(username: str, reason: str):
    """
    ฟังก์ชันสั่งปิดสิทธิ์พนักงานพร้อมกันทุก Application ภายในองค์กร
    """
    results = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        for app_name, conf in CENTRAL_CLIENT_CONFIG.items():
            url = f"{conf['base_url']}/accounts/{username}/status"
            headers = {
                "X-Management-API-Key": conf["api_key"],
                "Content-Type": "application/json",
            }
            payload = {
                "is_active": False,
                "reason": reason,
                "updated_by": "Central-IAM-Service",
            }
            try:
                response = await client.patch(url, headers=headers, json=payload)
                if response.status_code == 200:
                    results[app_name] = {"status": "SUCCESS", "detail": response.json()}
                elif response.status_code == 404:
                    results[app_name] = {"status": "SKIPPED", "detail": "User not in this app"}
                else:
                    results[app_name] = {"status": "FAILED", "code": response.status_code, "detail": response.text}
            except Exception as e:
                results[app_name] = {"status": "ERROR", "detail": str(e)}
                
    return results
```

---

### 5.3 ตัวอย่าง Node.js / TypeScript

```typescript
import axios from 'axios';

interface UpdateStatusPayload {
  is_active: boolean;
  reason: string;
  updated_by: string;
}

export async function setAccountStatus(
  appBaseUrl: string,
  apiKey: string,
  username: string,
  isActive: boolean,
  reason: string
) {
  const url = `${appBaseUrl}/api/v1/directory/accounts/${encodeURIComponent(username)}/status`;
  
  const response = await axios.patch(
    url,
    {
      is_active: isActive,
      reason: reason,
      updated_by: 'Central-Identity-Service',
    } as UpdateStatusPayload,
    {
      headers: {
        'X-Management-API-Key': apiKey,
        'Content-Type': 'application/json',
      },
      timeout: 8000,
    }
  );

  return response.data;
}
```

---

## 6. Implementation Checklist สำหรับ Application อื่นๆ ที่จะพัฒนาตาม

เมื่อทีมพัฒนาจะสร้าง Application ใหม่ หรือจะนำมาตรฐานนี้ไปติดตั้งบนระบบเดิม (เช่น QMS, WMS) ให้ตรวจสอบตาม Checklist นี้:

- [ ] **1. Secret Key Management:** มีหน้าจอ System Settings ให้ Admin ปลายทางสร้าง/สุ่มเปลี่ยน/คัดลอก `X-Management-API-Key`
- [ ] **2. IP Filter Middleware:** มีการเช็ค IP Server ของ Central Management ใน Request Handler
- [ ] **3. Endpoint Implementation:** พัฒนาทั้ง `GET /accounts` และ `PATCH /accounts/{username}/status` ครบถ้วน
- [ ] **4. Field Mapping:** ปรับฟิลด์ให้ส่งออกตามชื่อมาตรฐาน (`username`, `full_name`, `email`, `department`, `is_active`)
- [ ] **5. No Credential Leak:** ตรวจสอบอย่างละเอียดว่าไม่มีการส่งคืนรหัสผ่านหรือ Hash ใดๆ
- [ ] **6. Transaction Logging:** ทุกคำขอถูกบันทึกลงฐานข้อมูล Audit Log ของ Application ปลายทางเพื่อการตรวจสอบ
- [ ] **7. API Documentation:** ตรวจสอบให้ Endpoints แสดงผลบน Swagger/OpenAPI Docs (`/docs`) อย่างถูกต้อง
